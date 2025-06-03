from datetime import date
from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.logger import logger

from src.api.accruals.services.accrual_reports_service import AccrualReportsService
from src.api.common.utils.database import get_db
from src.api.accruals.schemas import ProcessPeriodRequest, ContractAccrualProcessingResponse
from src.api.accruals.services.contract_accrual_processor import ContractAccrualProcessor

router = APIRouter(prefix="/accruals", tags=["accruals"])


@router.post("/process-contracts", response_model=ContractAccrualProcessingResponse)
async def process_contract_accruals(
    request: ProcessPeriodRequest,
    db: Session = Depends(get_db)
):
    """
    Process contract accruals for a specific month.

    This endpoint processes all eligible ServiceContracts for the specified month,
    applying the business logic defined in the accrual schema.
    """
    import time
    start_time = time.time()

    try:
        logger.info(
            f"Starting contract accrual processing for period: {request.period_start_date}")

        # Initialize the processor service
        processor = ContractAccrualProcessor(db)

        # Process all contracts for the target month (now async)
        results = await processor.process_all_contracts(request.period_start_date)

        # Format response
        response = ContractAccrualProcessingResponse(
            period_start_date=request.period_start_date,
            summary={
                "total_contracts_processed": results['total_processed'],
                "successful_accruals": results['successful'],
                "failed_accruals": results['failed'],
                "skipped_accruals": results['skipped']
            },
            processing_results=results['results'],
            notifications=results['notifications']
        )

        logger.info(f"Contract accrual processing completed. Processed: {results['total_processed']}, "
                    f"Successful: {results['successful']}, Failed: {results['failed']}, "
                    f"Skipped: {results['skipped']}")

        return response

    except Exception as e:
        logger.error(f"Error in contract accrual processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contract accrual processing failed: {str(e)}"
        )


@router.get("/process-contracts/schema")
def get_accrual_processing_schema():
    """
    Get the accrual processing schema documentation.

    Returns the business logic schema that defines how contract accruals
    are processed based on ServiceContract and ServicePeriod statuses.
    """
    return {
        "description": "Contract Accrual Processing Schema",
        "version": "1.0",
        "workflow": {
            "active_contracts": {
                "description": "Contracts with ACTIVE status",
                "rules": [
                    "Check ContractAccrual status (COMPLETE vs ACTIVE/PAUSED/Not found)",
                    "If COMPLETE: Update ServiceContract status based on total to accrue",
                    "If not COMPLETE: Check for ServicePeriods",
                    "Without ServicePeriods: Check Notion integration for educational status",
                    "With ServicePeriods: Process based on period status (ACTIVE/POSTPONED/DROPPED/ENDED)"
                ]
            },
            "canceled_contracts": {
                "description": "Contracts with CANCELED status",
                "rules": [
                    "Check ContractAccrual status",
                    "If COMPLETE: Ignore",
                    "If not COMPLETE: Validate consistency with ServicePeriods and Notion data",
                    "Process full accrual if conditions are met"
                ]
            },
            "closed_contracts": {
                "description": "Contracts with CLOSED status",
                "rules": [
                    "Check ContractAccrual status",
                    "If COMPLETE: Ignore",
                    "If not COMPLETE: Validate that all ServicePeriods are ENDED",
                    "Complete accrual processing"
                ]
            }
        },
        "integrations": {
            "notion": "Educational status validation for contracts without ServicePeriods",
            "service_periods": "Status-based accrual calculation (ACTIVE/POSTPONED/DROPPED/ENDED)"
        },
        "notifications": [
            "not_congruent_status: Status mismatches between systems",
            "missing_crm_data: Clients not found in CRM systems"
        ]
    }


@router.get("/export/csv", response_class=Response)
def export_accruals_as_csv(
    start_date: date = Query(...,
                             description="Start date for export (inclusive)"),
    end_date: date = Query(..., description="End date for export (inclusive)"),
    db: Session = Depends(get_db)
):
    """
    Export accruals within a date range as a CSV file.

    The CSV contains contract details, client information, and accrual amounts by month.
    Columns include contract details, client info, service periods, and monthly accrual amounts.
    """
    reports_service = AccrualReportsService(db)
    csv_data = reports_service.generate_accruals_csv(start_date, end_date)

    # Generate filename based on date range
    filename = f"accruals_{start_date.isoformat()}_{end_date.isoformat()}.csv"

    # Return CSV file as response
    return Response(
        content=csv_data.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
