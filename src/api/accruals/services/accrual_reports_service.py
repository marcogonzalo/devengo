from datetime import date
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import case
from collections import defaultdict
import csv
from io import StringIO

from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.services.models.service import Service
from src.api.clients.models.client import Client
from src.api.common.constants.services import ServiceContractStatus
from src.api.accruals.constants.accruals import ContractAccrualStatus


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
                # Include if any of these conditions are met:
                
                # Condition 1: Contract has at least one accrued period in the date range
                (ContractAccrual.id.in_(accrued_contract_ids_subquery)) |
                
                # Condition 2: Contract has contract_date before or during end_date AND
                # (contract is active OR contract accrual is not completed)
                (
                    # Contract was created before end of date range AND
                    (ServiceContract.contract_date <= end_date) &
                    (
                        # Either no contract accrual exists (new contract), OR
                        (ContractAccrual.id.is_(None)) |
                        # Contract accrual exists but is not completed (regardless of remaining amount)
                        (ContractAccrual.accrual_status != 'COMPLETED')
                    )
                )
            )
            .order_by(
                # Group by accrual status and activity:
                # 1. Contracts with accrued periods in the date range (priority)
                # 2. Active contracts 
                # 3. Contracts with incomplete accruals
                # 4. Contracts without accruals yet
                case(
                    (ContractAccrual.id.in_(accrued_contract_ids_subquery), 1),
                    (ServiceContract.status == ServiceContractStatus.ACTIVE, 2),
                    (
                        (ContractAccrual.id.isnot(None)) &
                        (ContractAccrual.accrual_status != ContractAccrualStatus.COMPLETED), 3
                    ),
                    (ContractAccrual.id.is_(None), 4),
                    else_=5  # Fallback for any other cases
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
        
        # First pass: organize accruals normally
        for accrual in accruals:
            month_key = f"{accrual.accrual_date.year}-{accrual.accrual_date.month:02d}"
            key = (accrual.contract_accrual_id, accrual.service_period_id)
            accruals_by_contract_period[key][month_key] = accrual.accrued_amount
        
        # Second pass: redistribute NULL service_period_id accruals to their corresponding periods
        # This handles final accruals (status=ENDED, accrual_portion=1.0) that have service_period_id=NULL
        null_period_accruals = []
        for accrual in accruals:
            if accrual.service_period_id is None:
                null_period_accruals.append(accrual)
        
        for null_accrual in null_period_accruals:
            # Find the service period that contains this accrual date for this contract
            contract_accrual = self.db.get(ContractAccrual, null_accrual.contract_accrual_id)
            if contract_accrual:
                # Look for service periods that overlap with this accrual date
                overlapping_periods = self.db.query(ServicePeriod).filter(
                    ServicePeriod.contract_id == contract_accrual.contract_id,
                    ServicePeriod.start_date <= null_accrual.accrual_date,
                    ServicePeriod.end_date >= null_accrual.accrual_date
                ).all()
                
                if overlapping_periods:
                    # Move the accrual amount from NULL period to the correct period
                    target_period = overlapping_periods[0]
                    month_key = f"{null_accrual.accrual_date.year}-{null_accrual.accrual_date.month:02d}"
                    
                    # Remove from NULL key
                    null_key = (null_accrual.contract_accrual_id, None)
                    if null_key in accruals_by_contract_period and month_key in accruals_by_contract_period[null_key]:
                        amount = accruals_by_contract_period[null_key][month_key]
                        del accruals_by_contract_period[null_key][month_key]
                        
                        # Add to correct period key
                        correct_key = (null_accrual.contract_accrual_id, target_period.id)
                        if correct_key not in accruals_by_contract_period:
                            accruals_by_contract_period[correct_key] = {}
                        accruals_by_contract_period[correct_key][month_key] = accruals_by_contract_period[correct_key].get(month_key, 0.0) + amount

        # Step 3: Organize data for CSV export
        csv_data = []
        previous_contract_id = None  # Track the previous contract ID

        for contract, client, service, period, contract_accrual in results:
            # Check if this is the first occurrence of this contract
            is_first_occurrence = contract.id != previous_contract_id
            
            row = {
                "Contract start date": contract.contract_date if is_first_occurrence else "",
                "Client": client.name if is_first_occurrence else "",
                "Email": client.identifier if is_first_occurrence else "",
                "Contract Status": contract.status.value if is_first_occurrence else "",
                "Service": service.name if is_first_occurrence else "",
                "Period": period.name if period else "No Period",
                "Period Status": period.status.value if period else "N/A",
                "Status Change Date": period.status_change_date if period else None,
                "Total to accrue": round(contract_accrual.total_amount_to_accrue, 2) if contract_accrual and is_first_occurrence else (contract.contract_amount if is_first_occurrence else ""),
                "Pending to accrue": round(contract_accrual.remaining_amount_to_accrue, 2) if contract_accrual and is_first_occurrence else (contract.contract_amount if is_first_occurrence else ""),
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
            
            # Update the previous contract ID
            previous_contract_id = contract.id

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
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary statistics for the accruals overview.
        
        Returns:
            Dictionary containing:
            - total_contracts: Total number of service contracts
            - total_amount: Total contract amounts
            - accrued_amount: Total amount already accrued
            - pending_amount: Total amount pending to accrue
        """
        # Get all service contracts with their accruals
        contracts_query = (
            self.db.query(ServiceContract, ContractAccrual)
            .outerjoin(ServiceContract.contract_accrual)
            .filter(ServiceContract.status.in_([
                ServiceContractStatus.ACTIVE,
                ServiceContractStatus.CANCELED,
                ServiceContractStatus.CLOSED
            ]))
        )
        
        contracts = contracts_query.all()
        
        # Calculate totals
        total_contracts = len(contracts)
        total_amount = sum(contract.contract_amount for contract, _ in contracts)
        
        # Calculate accrued and pending amounts
        accrued_amount = 0.0
        pending_amount = 0.0
        
        for contract, contract_accrual in contracts:
            if contract_accrual:
                # Total accrued is the difference between total to accrue and remaining
                accrued_this_contract = (
                    contract_accrual.total_amount_to_accrue - 
                    contract_accrual.remaining_amount_to_accrue
                )
                accrued_amount += accrued_this_contract
                pending_amount += contract_accrual.remaining_amount_to_accrue
            else:
                # No accrual record yet, so everything is pending
                pending_amount += contract.contract_amount
        
        return {
            "total_contracts": total_contracts,
            "total_amount": total_amount,
            "accrued_amount": accrued_amount,
            "pending_amount": pending_amount
        }
