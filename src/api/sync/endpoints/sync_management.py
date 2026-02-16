from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from src.api.common.utils.database import get_db
from src.api.sync.models.sync_requests import SyncStepRequest, SyncProcessRequest, SyncStatusResponse
from src.api.sync.models.sync_execution import SyncExecution
from src.api.sync.services.sync_management_service import SyncManagementService

router = APIRouter()


@router.get("/available-steps", response_model=Dict[str, Any])
async def get_available_steps():
    """Get available sync steps."""
    return {
        "import_steps": [
            {"id": "services", "name": "Sync Services",
                "description": "Import services from Holded"},
            {"id": "invoices", "name": "Sync Invoices",
                "description": "Import invoices and clients from Holded"},
            {"id": "crm-clients", "name": "Sync CRM Clients",
                "description": "Import students from 4Geeks clients"},
            {"id": "service-periods", "name": "Sync Service Periods",
                "description": "Import enrollments from 4Geeks clients"},
            {"id": "notion-external-id", "name": "Sync Notion External IDs",
                "description": "Import page IDs from Notion clients"}
        ],
        "accrual_steps": [
            {"id": "accruals", "name": "Process Accruals",
                "description": "Process contract accruals for the specified period"}
        ]
    }


@router.get("/execution-order", response_model=List[str])
async def get_execution_order():
    """Get the fixed execution order for import steps."""
    return ["services", "invoices", "crm-clients", "service-periods", "notion-external-id"]


@router.post("/execute-step", response_model=SyncStatusResponse)
async def execute_single_sync_step(
    request: SyncStepRequest,
    db: Session = Depends(get_db)
):
    """Execute a single sync step."""
    try:
        # Validate required parameters
        if request.step in ["invoices", "accruals"]:
            if not request.year:
                raise HTTPException(
                    status_code=400,
                    detail="Year is required for invoices and accruals steps"
                )

        sync_service = SyncManagementService(db)
        result = await sync_service.execute_single_step(
            step=request.step,
            year=request.year,
            start_date=request.start_date,
            end_date=request.end_date,
            month=request.month
        )

        return SyncStatusResponse(
            status="success",
            message=f"Step '{request.step}' executed successfully",
            data=result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-process", response_model=SyncStatusResponse)
async def execute_sync_process(
    request: SyncProcessRequest,
    db: Session = Depends(get_db)
):
    """Execute a complete sync process."""
    try:
        # Validate required parameters
        if request.process_type == "import":
            if not request.year:
                raise HTTPException(
                    status_code=400,
                    detail="Year is required for import process"
                )
        elif request.process_type == "accrual":
            if not request.year:
                raise HTTPException(
                    status_code=400,
                    detail="Year is required for accrual process"
                )

        sync_service = SyncManagementService(db)
        result = await sync_service.execute_process(
            process_type=request.process_type,
            # Use first step as starting point
            starting_point=request.steps[0] if request.steps else "invoices",
            year=request.year,
            start_date=request.start_date,
            end_date=request.end_date,
            month=request.month
        )

        return SyncStatusResponse(
            status="success",
            message=f"{request.process_type.title()} process completed successfully",
            data=result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{process_id}", response_model=SyncStatusResponse)
async def get_process_status(
    process_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a sync process."""
    try:
        execution = db.query(SyncExecution).filter(
            SyncExecution.process_id == process_id).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Process not found")

        return SyncStatusResponse(
            status="success",
            message="Process status retrieved successfully",
            data={
                "process_id": execution.process_id,
                "process_type": execution.process_type,
                "status": execution.status,
                "steps": execution.steps,
                "year": execution.year,
                "month": execution.month,
                "start_date": execution.start_date,
                "end_date": execution.end_date,
                "result": execution.result,
                "error_message": execution.error_message,
                "created_at": execution.created_at.isoformat() if execution.created_at else None,
                "updated_at": execution.updated_at.isoformat() if execution.updated_at else None
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest-processed-month-year")
async def get_latest_processed_month_year(
    db: Session = Depends(get_db)
):
    """
    Get the latest month and year that has been processed (has invoices or accruals).
    Returns the next month/year that should be processed.

    For example, if the database has data until November 2025,
    this will return December 2025.
    """
    try:
        sync_service = SyncManagementService(db)
        result = sync_service.get_latest_processed_month_year()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
