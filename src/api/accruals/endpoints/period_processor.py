from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.common.utils.database import get_db
from src.api.accruals.schemas import ProcessPeriodRequest, ProcessPeriodResponse, ProcessingStatus
from src.api.accruals.services.period_processor import PeriodProcessor

router = APIRouter(prefix="/accruals", tags=["accruals"])


@router.post("/process-accrue-in-month", response_model=ProcessPeriodResponse)
def process_accrue_in_month(
    request: ProcessPeriodRequest,
    db: Session = Depends(get_db)
):
    """
    Process accruals for all relevant service periods within the specified month.

    This endpoint will:
    1. Find all ServicePeriods overlapping with the target month.
    2. Calculate and create AccruedPeriod records for each relevant ServicePeriod.
    3. Handle special contract statuses like DROPPED during calculation.
    """
    processor = PeriodProcessor(db)

    # Get all relevant service periods for the month
    service_periods = processor.get_service_periods_for_month(
        request.period_start_date)

    # Process each service period
    results = []
    successful = 0
    failed = 0

    for period in service_periods:
        result = processor.process_service_period(
            period, request.period_start_date)
        results.append(result)

        if result.status == ProcessingStatus.SUCCESS:
            # Count success only if an accrual record was actually created or explicitly not needed
            if result.accrued_period is not None or "No accrual needed" in (result.message or ""):
                successful += 1
            # Consider cases where success means 0 accrual as success
        elif result.status == ProcessingStatus.FAILED:
            failed += 1

    # Note: successful + failed might not equal total_periods if some periods resulted in 0 accrual without errors
    # Adjust counting logic if needed based on how 'success' should be defined for zero-accrual cases

    total_processed = len(service_periods)  # Number of periods attempted

    return ProcessPeriodResponse(
        period_start_date=request.period_start_date,
        total_periods_processed=total_processed,
        # Periods successfully processed (incl. 0 accrual)
        successful_periods=successful,
        failed_periods=failed,  # Periods that failed processing
        results=results
    )
