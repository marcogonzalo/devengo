from datetime import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.logger import logger
from sqlmodel import Session
from src.api.services.services.service_contract import ServiceContractService
from src.api.common.utils.database import get_db
from src.api.services.endpoints.service import get_service_service
from src.api.services.endpoints.service_contract import get_service_contract_service
from src.api.services.services import ServiceService
from src.api.services.services.service_service import ServiceService
from src.api.integrations.holded import HoldedClient, HoldedConfig
from src.api.clients.services.client_service import ClientService
from src.api.invoices.services.invoice_service import InvoiceService
from src.api.clients.schemas.client import ClientCreate, ClientExternalIdCreate
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceUpdate
from src.api.services.schemas.service import ServiceUpdate, ServiceRead

router = APIRouter(prefix="/integrations/holded", tags=["integrations"])


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


def get_invoice_service(db: Session = Depends(get_db)):
    return InvoiceService(db)


def get_holded_client():
    config = HoldedConfig()
    return HoldedClient(config)


def accepted_service(service):
    return str(service.get("accountNum")).startswith("705000") and service.get("name")[0:2] == "ES"


def _create_client(contact, client_service):
    try:
        client_data = ClientCreate(
            identifier=contact.get("email"),
            name=contact.get("name", "")
        )
    except Exception as e:
        raise Exception(f"Contact with missing email: {contact.get('id')}.")

    client = client_service.create_client(client_data)

    # Add external ID
    external_id_data = ClientExternalIdCreate(
        system="holded",
        external_id=contact.get("id")
    )

    client_service.add_external_id(client.id, external_id_data)
    return client


async def _get_or_create_client(contact_id, client_service, holded_client):
    client = client_service.get_client_by_external_id(
        "holded", contact_id)
    if not client:
        contact = await holded_client.get_contact(contact_id)
        if not contact:
            raise Exception("Contact not found")
        client = _create_client(contact, client_service)
    return client


def _get_or_create_service_contract(client_id, service_id, service_contract_service):
    service_contract = service_contract_service.get_service_contract_by_client_and_service(
        client_id, service_id)
    if not service_contract:
        service_contract = service_contract_service.create_service_contract(
            client_id, service_id)
    return service_contract


def _create_invoice(document, client, invoice_service):
    # Convert to datetime as needed
    invoice_date = datetime.fromtimestamp(
        document.get("date")).date()
    due_date = datetime.fromtimestamp(document.get(
        "dueDate")).date() if document.get("dueDate") else None

    invoice_data = InvoiceCreate(
        external_id=document.get("id"),
        client_id=client.id if client else None,
        invoice_number=document.get("docNumber", ""),
        invoice_date=invoice_date,
        due_date=due_date,
        total_amount=document.get("total", 0.0),
        currency=document.get("currency", "EUR"),
        status=document.get("status", "pending")
    )

    invoice = invoice_service.create_invoice(invoice_data)
    return invoice

# Get the account identifier from products in Holded documents,
# and get the service from the account external id


def _get_service_from_products(products, service_service: ServiceService) -> ServiceRead:
    service = None
    try:
        service_external_id = products[0].get("account")
        service = service_service.get_service_by_external_id(
            service_external_id)
        if not service:
            raise Exception(f"Service not found: {service_external_id}")
    except Exception as e:
        logger.error(
            f"Error getting service from products: {e}")
    return service


@router.get("/sync-contacts")
async def sync_contacts(
    client_service: ClientService = Depends(get_client_service),
    holded_client: HoldedClient = Depends(get_holded_client),
    page: int = 1,
    per_page: int = 50
):
    """Sync contacts from Holded to the local database"""
    try:
        contacts = await holded_client.list_contacts(page=page, per_page=per_page)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for contact in contacts:
            try:
                # Check if client already exists by external ID
                existing_client = client_service.get_client_by_external_id(
                    "holded", contact.get("id"))

                if existing_client:
                    skipped_count += 1
                    continue

                # Create new client
                if not contact.get("email"):
                    skipped_count += 1
                    continue

                _create_client(contact, client_service)

                created_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync contacts: {str(e)}"
        )


@router.get("/sync-contracts")
async def sync_contracts(
    client_service: ClientService = Depends(get_client_service),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    holded_client: HoldedClient = Depends(get_holded_client),
    service_service: ServiceService = Depends(get_service_service),
    service_contract_service: ServiceContractService = Depends(
        get_service_contract_service),
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None
):
    """Sync invoices with their respective clientsfrom Holded to the local database"""
    try:
        documents = await holded_client.list_documents(starttmp=start_timestamp, endtmp=end_timestamp)

        processed_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for document in documents:
            try:
                document_id = document.get("id")
                logger.info(f"Processing document: {document_id}")


                # Get client by Holded contact ID
                try:
                    contact_id = document.get("contact")
                    client = await _get_or_create_client(contact_id, client_service, holded_client)
                except Exception as e:
                    logger.error(
                        f"Error getting client for document_id {document_id}: {e}")
                    client_service.db.rollback()
                    raise e
                
                # Check if invoice already exists
                invoice = invoice_service.get_invoice_by_external_id(
                    document_id)

                if not invoice:
                    try:
                        invoice = _create_invoice(document, client, invoice_service)
                    except Exception as e:
                        logger.error(
                            f"Error creating invoice for document_id {document_id}: {e}")
                        invoice_service.db.rollback()
                        raise e

                # Get service by Holded account ID
                service = _get_service_from_products(
                    document.get("products"), service_service)
                if not service:
                    logger.info(
                        f"Service not found. Skipping document_id: {document_id}")
                    skipped_count += 1
                    continue


                # Create service contract if it doesn't exist
                try:
                    service_contract = _get_or_create_service_contract(
                        client.id, service.id, service_contract_service)
                except Exception as e:
                    logger.error(
                        f"Error creating service contract for document_id {document_id}: {e}")
                    raise e
                
                # Update invoice with service contract id
                invoice_service.update_invoice(invoice.id, InvoiceUpdate(
                    service_contract_id=service_contract.id
                ))

                processed_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))
                logging.error(f"Error creating invoice: {e}")
        return {
            "success": True,
            "processed": processed_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync invoices: {str(e)}"
        )


@router.get("/sync-invoices")
async def sync_invoices(
    client_service: ClientService = Depends(get_client_service),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    holded_client: HoldedClient = Depends(get_holded_client),
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None
):
    """Sync invoices from Holded to the local database"""
    try:
        documents = await holded_client.list_documents(starttmp=start_timestamp, endtmp=end_timestamp)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for document in documents:
            try:
                # Check if invoice already exists
                existing_invoice = invoice_service.get_invoice_by_external_id(
                    document.get("id"))

                if existing_invoice:
                    skipped_count += 1
                    continue

                # Get client by Holded contact ID
                contact_id = document.get("contactId")
                client = client_service.get_client_by_external_id(
                    "holded", contact_id)

                # Create invoice
                invoice = _create_invoice(document, client, invoice_service)
                created_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync invoices: {str(e)}"
        )


@router.get("/sync-services")
async def sync_services(
    service_service: ServiceService = Depends(get_service_service),
    holded_client: HoldedClient = Depends(get_holded_client),
):
    """Sync services from Holded to the local database"""
    try:
        services = await holded_client.list_income_accounts()
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        for service in services:
            try:
                account_identifier = str(service.get('accountNum'))
                prefix = str(service.get('name'))[0:2]
                if not accepted_service(service):
                    skipped_count += 1
                    continue
                # Extract the id from the service data
                service_id = service.get('id')

                # Create a new service Pydantic model with external_id
                service_data = {
                    'external_id': service_id,
                    'name': service.get('name'),
                    'description': service.get('description'),
                    'account_identifier': account_identifier
                }

                existing_service = service_service.get_service_by_external_id(
                    service_id)
                if existing_service:
                    service_service.update_service(
                        existing_service.id, service_data)
                    updated_count += 1
                else:
                    service_service.create_service(service_data)
                    created_count += 1
            except Exception as e:
                error_count += 1
                errors.append(str(e))
        return {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync services: {str(e)}"
        )
