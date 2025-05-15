from datetime import date
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import extract
from collections import defaultdict
import csv
from io import StringIO

from src.api.common.constants.services import ServicePeriodStatus
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
            .join(ServiceContract.periods)
            .join(ServiceContract.contract_accrual)
            .filter(
                ServicePeriod.start_date <= end_date,
                ServicePeriod.end_date >= start_date
            )
            .order_by(
                ServiceContract.contract_date,
                ServicePeriod.start_date,
                Client.name,
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
                "Period": period.name or "",
                "Service": service.name,
                "Period Status": period.status.value,
                "Total to accrue": contract_accrual.total_amount_to_accrue,
                "Pending to accrue": contract_accrual.remaining_amount_to_accrue,
                "Period start date": period.start_date,
                "Period end date": period.end_date,
            }

            # Add monthly accrual amounts
            key = (contract_accrual.id, period.id)
            period_accruals = accruals_by_contract_period.get(key, {})

            for month_key, month_name in months:
                row[month_name] = period_accruals.get(month_key, 0.0)

            csv_data.append(row)

        return {
            "headers": ["Contract start date", "Client", "Email", "Period", "Service",
                        "Period Status", "Total to accrue", "Pending to accrue",
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
