from datetime import date
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import case
from collections import defaultdict
import csv
from io import StringIO

from api.common.constants.services import ServiceContractStatus
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.services.models.service import Service
from src.api.clients.models.client import Client


class AccrualReportsService:
    def __init__(self, db: Session):
        self.db = db

    def get_accruals_export(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Fetch accruals data for CSV export within a specific date range.

        Args:
            start_date: Start date for filtering accruals
            end_date: End date for filtering accruals

        Returns:
            Dict containing service period data and accrual amounts by month
        """
        # Step 1: Get all service contracts with their related entities
        # Include contracts without service periods but that have accruals in the date range
        
        # First, get contract accrual IDs that have been accrued in the date range
        accrued_contract_ids_subquery = (
            self.db.query(AccruedPeriod.contract_accrual_id)
            .filter(
                AccruedPeriod.accrual_date >= start_date,
                AccruedPeriod.accrual_date <= end_date
            )
            .distinct()
        )
        
        query = (
            self.db.query(
                ServiceContract,
                Client,
                Service,
                ServicePeriod,
                ContractAccrual
            )
            .join(ServiceContract.client)
            .join(ServiceContract.service)
            .outerjoin(ServiceContract.periods)  # Left join to include contracts without periods
            .outerjoin(ServiceContract.contract_accrual)  # Left join to include contracts without contract accruals
            .filter(
                # Include if:
                # 1. Contract has at least one accrued period in the date range, OR
                # 2. Contract doesn't have accrued periods but its contract accrual is not completed and has remaining amount, OR
                # 3. Contract doesn't have a contract accrual but its start date is on or before the date range
                (ContractAccrual.id.in_(accrued_contract_ids_subquery)) |

                (
                    (ServiceContract.status == ServiceContractStatus.ACTIVE) &
                    (ServiceContract.contract_date <= end_date) &
                    ((ContractAccrual.id.is_(None)) | ((ContractAccrual.accrual_status != 'COMPLETED') &
                    (ContractAccrual.remaining_amount_to_accrue > 0)))
                    
                )
            )
            .order_by(
                # Group by accrual status:
                # 1. Cases with accrued periods in the date range (accrued contracts)
                # 2. Cases with incomplete accruals but no accrued periods in date range (accruable contracts)
                # 3. Cases without contract accruals (new contracts)
                case(
                    (ContractAccrual.id.in_(accrued_contract_ids_subquery), 1),
                    (
                        (ContractAccrual.id.notin_(accrued_contract_ids_subquery)) &
                        (ContractAccrual.accrual_status != 'COMPLETED') &
                        (ContractAccrual.remaining_amount_to_accrue > 0), 2
                    ),
                    (ContractAccrual.id.is_(None), 3),
                    else_=4  # Fallback for any edge cases
                ),
                Client.name,
                ServiceContract.contract_date,
                ServicePeriod.start_date.asc().nulls_first(),  # Handle null periods
            )
        )

        results = query.all()

        # Step 2: Get all accrued periods in the date range
        accruals_query = (
            self.db.query(AccruedPeriod)
            .filter(
                AccruedPeriod.accrual_date >= start_date,
                AccruedPeriod.accrual_date <= end_date
            )
        )

        accruals = accruals_query.all()

        # Create a dictionary mapping contract_accrual_id and service_period_id to accruals by month
        accruals_by_contract_period = defaultdict(dict)

        # Get all distinct months in the date range for column headers
        months = []
        # Ensure we start at beginning of month
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            month_key = f"{current_date.year}-{current_date.month:02d}"
            months.append((month_key, current_date.strftime("%B %Y")))

            # Move to the next month
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            current_date = date(year, month, 1)

        # Organize accruals by contract_accrual_id, service_period_id, and month
        # service_period_id can be None for accruals without associated periods
        # contract_accrual_id should always exist for accrued periods, but handling defensively
        for accrual in accruals:
            month_key = f"{accrual.accrual_date.year}-{accrual.accrual_date.month:02d}"
            key = (accrual.contract_accrual_id, accrual.service_period_id)
            accruals_by_contract_period[key][month_key] = accrual.accrued_amount

        # Step 3: Organize data for CSV export
        csv_data = []

        for contract, client, service, period, contract_accrual in results:
            row = {
                "Contract start date": contract.contract_date,
                "Client": client.name,
                "Email": client.identifier,
                "Contract Status": contract.status.value,
                "Service": service.name,
                "Period": period.name if period else "No Period",
                "Period Status": period.status.value if period else "N/A",
                "Status Change Date": period.status_change_date if period else None,
                "Total to accrue": round(contract_accrual.total_amount_to_accrue, 2) if contract_accrual else contract.contract_amount,
                "Pending to accrue": round(contract_accrual.remaining_amount_to_accrue, 2) if contract_accrual else contract.contract_amount,
                "Period start date": period.start_date if period else None,
                "Period end date": period.end_date if period else None,
            }

            # Add monthly accrual amounts
            # For contracts without periods, use None as service_period_id
            # For contracts without contract accruals, use None as contract_accrual_id
            period_id = period.id if period else None
            contract_accrual_id = contract_accrual.id if contract_accrual else None
            key = (contract_accrual_id, period_id)
            period_accruals = accruals_by_contract_period.get(key, {})

            for month_key, month_name in months:
                row[month_name] = period_accruals.get(month_key, 0.0)

            csv_data.append(row)

        return {
            "headers": ["Contract start date", "Client", "Email", "Contract Status", "Service", "Period",
                        "Period Status", "Status Change Date", "Total to accrue", "Pending to accrue",
                        "Period start date", "Period end date"] + [name for _, name in months],
            "data": csv_data,
            "months": [name for _, name in months]
        }

    def generate_accruals_csv(self, start_date: date, end_date: date) -> StringIO:
        """
        Generate a CSV file of accruals data for a specific date range.

        Args:
            start_date: Start date for filtering accruals
            end_date: End date for filtering accruals

        Returns:
            StringIO: CSV data as a StringIO object
        """
        accruals_data = self.get_accruals_export(start_date, end_date)

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=accruals_data["headers"])
        writer.writeheader()

        for row in accruals_data["data"]:
            writer.writerow(row)

        output.seek(0)
        return output
