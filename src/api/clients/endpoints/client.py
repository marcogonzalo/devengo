from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from api.common.utils.database import get_db
from src.api.clients.models.client import Client, ClientExternalId
from src.api.clients.schemas.client import ClientCreate, ClientRead, ClientUpdate, ClientExternalIdCreate, ClientExternalIdRead
from src.api.clients.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


@router.post("/", response_model=ClientRead)
def create_client(
    client_data: ClientCreate,
    client_service: ClientService = Depends(get_client_service)
):
    """Create a new client"""
    return client_service.create_client(client_data)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int,
    client_service: ClientService = Depends(get_client_service)
):
    """Get a client by ID"""
    client = client_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/", response_model=List[ClientRead])
def get_clients(
    skip: int = 0,
    limit: int = 100,
    client_service: ClientService = Depends(get_client_service)
):
    """Get a list of clients"""
    return client_service.get_clients(skip, limit)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int,
    client_data: ClientUpdate,
    client_service: ClientService = Depends(get_client_service)
):
    """Update a client"""
    client = client_service.update_client(client_id, client_data)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    client_service: ClientService = Depends(get_client_service)
):
    """Delete a client"""
    success = client_service.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}


@router.post("/{client_id}/external-ids", response_model=ClientExternalIdRead)
def add_external_id(
    client_id: int,
    external_id_data: ClientExternalIdCreate,
    client_service: ClientService = Depends(get_client_service)
):
    """Add an external ID to a client"""
    client = client_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client_service.add_external_id(client_id, external_id_data)


@router.get("/external-id/{system}/{external_id}", response_model=Optional[ClientRead])
def get_client_by_external_id(
    system: str,
    external_id: str,
    client_service: ClientService = Depends(get_client_service)
):
    """Get a client by external ID"""
    client = client_service.get_client_by_external_id(system, external_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
