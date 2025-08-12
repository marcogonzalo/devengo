from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from src.api.integrations.services.integration_error_service import IntegrationErrorService
from src.api.integrations.schemas.integration_error import (
    IntegrationErrorCreate,
    IntegrationErrorRead,
    IntegrationErrorUpdate,
    IntegrationErrorFilter,
    IntegrationErrorSummary,
    BulkResolveRequest,
    BulkIgnoreRequest
)
from src.api.common.utils.database import get_db

router = APIRouter(prefix="/integrations/errors", tags=["integration-errors"])


def get_integration_error_service(db: Session = Depends(get_db)) -> IntegrationErrorService:
    """Dependency to get integration error service"""
    return IntegrationErrorService(db)


@router.get("/", response_model=List[IntegrationErrorRead])
async def get_integration_errors(
    integration_name: Optional[str] = Query(None, description="Filter by integration name"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    is_ignored: Optional[bool] = Query(None, description="Filter by ignored status"),
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    contract_id: Optional[int] = Query(None, description="Filter by contract ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Get integration errors with filtering and pagination"""
    filters = IntegrationErrorFilter(
        integration_name=integration_name,
        operation_type=operation_type,
        entity_type=entity_type,
        is_resolved=is_resolved,
        is_ignored=is_ignored,
        client_id=client_id,
        contract_id=contract_id,
        limit=limit,
        offset=offset
    )
    
    result = service.get_errors(filters)
    return result["errors"]


@router.get("/list", response_model=dict)
async def get_integration_errors_with_count(
    integration_name: Optional[str] = Query(None, description="Filter by integration name"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    is_ignored: Optional[bool] = Query(None, description="Filter by ignored status"),
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    contract_id: Optional[int] = Query(None, description="Filter by contract ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Get integration errors with filtering, pagination, and total count"""
    filters = IntegrationErrorFilter(
        integration_name=integration_name,
        operation_type=operation_type,
        entity_type=entity_type,
        is_resolved=is_resolved,
        is_ignored=is_ignored,
        client_id=client_id,
        contract_id=contract_id,
        limit=limit,
        offset=offset
    )
    
    return service.get_errors(filters)


@router.get("/summary", response_model=IntegrationErrorSummary)
async def get_integration_errors_summary(
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Get summary statistics for integration errors"""
    return service.get_summary()


@router.get("/{error_id}", response_model=IntegrationErrorRead)
async def get_integration_error(
    error_id: int,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Get a specific integration error by ID"""
    error = service.get_error(error_id)
    if not error:
        raise HTTPException(status_code=404, detail="Integration error not found")
    return error


@router.post("/", response_model=IntegrationErrorRead)
async def create_integration_error(
    error_data: IntegrationErrorCreate,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Create a new integration error (or update existing if duplicate)"""
    error = service.create_error(error_data)
    return error


@router.put("/{error_id}", response_model=IntegrationErrorRead)
async def update_integration_error(
    error_id: int,
    update_data: IntegrationErrorUpdate,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Update an integration error"""
    error = service.update_error(error_id, update_data)
    if not error:
        raise HTTPException(status_code=404, detail="Integration error not found")
    return error


@router.delete("/{error_id}")
async def delete_integration_error(
    error_id: int,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Delete an integration error"""
    success = service.delete_error(error_id)
    if not success:
        raise HTTPException(status_code=404, detail="Integration error not found")
    return {"message": "Integration error deleted successfully"}


@router.post("/{error_id}/resolve", response_model=IntegrationErrorRead)
async def resolve_integration_error(
    error_id: int,
    resolution_notes: Optional[str] = Query(None, description="Notes about how the error was resolved"),
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Mark an integration error as resolved"""
    error = service.resolve_error(error_id, resolution_notes)
    if not error:
        raise HTTPException(status_code=404, detail="Integration error not found")
    return error


@router.post("/bulk-resolve")
async def bulk_resolve_integration_errors(
    request: BulkResolveRequest,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Bulk resolve multiple integration errors"""
    resolved_count = service.bulk_resolve_errors(request.error_ids, request.resolution_notes)
    return {
        "message": f"Successfully resolved {resolved_count} out of {len(request.error_ids)} errors",
        "resolved_count": resolved_count,
        "total_requested": len(request.error_ids)
    }


@router.post("/{error_id}/ignore", response_model=IntegrationErrorRead)
async def ignore_integration_error(
    error_id: int,
    ignore_notes: Optional[str] = Query(None, description="Notes about why the error was ignored"),
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Mark an integration error as ignored"""
    error = service.ignore_error(error_id, ignore_notes)
    if not error:
        raise HTTPException(status_code=404, detail="Integration error not found")
    return error


@router.post("/bulk-ignore")
async def bulk_ignore_integration_errors(
    request: BulkIgnoreRequest,
    service: IntegrationErrorService = Depends(get_integration_error_service)
):
    """Bulk ignore multiple integration errors"""
    ignored_count = service.bulk_ignore_errors(request.error_ids, request.ignore_notes)
    return {
        "message": f"Successfully ignored {ignored_count} out of {len(request.error_ids)} errors",
        "ignored_count": ignored_count,
        "total_requested": len(request.error_ids)
    }
