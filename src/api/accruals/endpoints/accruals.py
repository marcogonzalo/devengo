from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from src.api.accruals.services.accrual_reports_service import AccrualReportsService
from src.api.common.utils.database import get_db
from src.api.accruals.schemas import ProcessPeriodRequest, ProcessPeriodResponse, ProcessingStatus
from src.api.accruals.services.period_processor import PeriodProcessor

router = APIRouter(prefix="/accruals", tags=["accruals"])


@router.post("/accrue-period", response_model=ProcessPeriodResponse)
def process_accruals_in_month(
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
    service_periods = processor.get_service_periods_in_month(
        request.period_start_date)

    # Get a list of all existing accruals for the month
    contract_ids_with_accruals = processor.get_contract_ids_with_accruals_in_month(
        request.period_start_date)

    # Process each service period
    results = []
    total_processed = len(service_periods)
    successful = 0
    skipped = 0
    failed = 0
    existing = len(contract_ids_with_accruals)

    #  Exclude periods that already have an accrual
    service_periods = [
        period for period in service_periods
        if period.contract.id not in contract_ids_with_accruals
    ]
    for period in service_periods:
        result = processor.accrue_service_period(
            period, request.period_start_date)
        results.append(result)

        if result.status == ProcessingStatus.SUCCESS:
            # Count success only if an accrual record was actually created or explicitly not needed
            if result.accrued_period is not None or "completed" in (result.message):
                successful += 1
            elif "No accrual needed" in (result.message) or "" in (result.message):
                skipped += 1
            elif result.status == ProcessingStatus.FAILED:
                failed += 1

    return ProcessPeriodResponse(
        period_start_date=request.period_start_date,
        total_periods_processed=total_processed,
        successful_accruals=successful,
        failed_accruals=failed,
        existing_accruals=existing,
        skipped_accruals=skipped,
        results=results
    )


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
