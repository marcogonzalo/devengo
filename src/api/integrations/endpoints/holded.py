from datetime import datetime
from typing import Optional
from api.common.utils.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from src.api.integrations.holded import HoldedClient, HoldedConfig
from src.api.clients.services.client_service import ClientService
from src.api.invoices.services.invoice_service import InvoiceService
from src.api.clients.schemas.client import ClientCreate, ClientExternalIdCreate
from src.api.invoices.schemas.invoice import InvoiceCreate

router = APIRouter(prefix="/integrations/holded", tags=["integrations"])


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


def get_invoice_service(db: Session = Depends(get_db)):
    return InvoiceService(db)


def get_holded_client():
    config = HoldedConfig()
    return HoldedClient(config)


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
                email = contact.get("email")
                if not email:
                    skipped_count += 1
                    continue

                client_data = ClientCreate(
                    identifier=email,
                    name=contact.get("name", "")
                )

                client = client_service.create_client(client_data)

                # Add external ID
                external_id_data = ClientExternalIdCreate(
                    system="holded",
                    external_id=contact.get("id")
                )

                client_service.add_external_id(client.id, external_id_data)

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


@router.get("/sync-invoices")
async def sync_invoices(
    # client_service: ClientService = Depends(get_client_service),
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
                # client = client_service.get_client_by_external_id(
                #     "holded", contact_id)

                # Create invoice
                # Convert to datetime as needed
                invoice_date = datetime.fromtimestamp(
                    document.get("date")).date()
                due_date = datetime.fromtimestamp(document.get(
                    "dueDate")).date() if document.get("dueDate") else None

                invoice_data = InvoiceCreate(
                    external_id=document.get("id"),
                    # client_id=client.id if client else None,
                    invoice_number=document.get("number", ""),
                    invoice_date=invoice_date,
                    due_date=due_date,
                    total_amount=document.get("total", 0.0),
                    currency=document.get("currency", "EUR"),
                    status=document.get("status", "pending"),
                    original_data=document
                )

                invoice = invoice_service.create_invoice(invoice_data)
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
