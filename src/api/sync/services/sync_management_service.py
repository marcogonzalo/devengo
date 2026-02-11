import os
import uuid
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
import httpx

from src.api.sync.models.sync_execution import SyncExecution, SyncExecutionStatus
from src.api.invoices.models.invoice import Invoice
from src.api.accruals.models.accrued_period import AccruedPeriod

logger = logging.getLogger(__name__)


class SyncManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = os.environ.get(
            "VITE_API_URL", "http://localhost:3001/api")
        self.running_processes: Dict[str, Dict[str, Any]] = {}

    async def execute_single_step(
        self,
        step: str,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a single sync step."""
        process_id = str(uuid.uuid4())

        # Create execution record
        execution = SyncExecution(
            process_id=process_id,
            process_type="single_step",
            status=SyncExecutionStatus.RUNNING,
            steps=json.dumps([step]),
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
        self.db.add(execution)
        self.db.commit()

        try:
            # Generate monthly timestamps if needed
            monthly_timestamps = None
            if year and month:
                monthly_timestamps = self._generate_monthly_timestamps_for_month(
                    year, month)
            elif year:
                monthly_timestamps = self._generate_monthly_timestamps_for_year(
                    year)

            # Execute the step
            result = await self._execute_step_api_call(
                step=step,
                year=year,
                start_date=start_date,
                end_date=end_date,
                month=month,
                monthly_timestamps=monthly_timestamps
            )

            # Check if result already has total_stats structure (from multi-month processing)
            # This happens for invoices and accruals when processing multiple months
            if isinstance(result, dict) and "total_processed" in result and "total_created" in result:
                # Result already has the processed structure
                total_stats = {
                    "total_processed": result.get("total_processed", 0),
                    "total_created": result.get("total_created", 0),
                    "total_updated": result.get("total_updated", 0),
                    "total_skipped": result.get("total_skipped", 0),
                    "total_failed": result.get("total_failed", 0),
                    "total_errors": result.get("total_errors", 0),
                    "total_received": result.get("total_received", 0),
                }
                # Extract step_stats from monthly_results if available, otherwise use total_stats
                if "monthly_results" in result and result["monthly_results"]:
                    # Use the first month's stats as representative (includes total_received for invoices)
                    step_stats = result["monthly_results"][0].get("stats", total_stats)
                else:
                    step_stats = total_stats
            else:
                # Extract statistics from raw API response
                step_stats = self._extract_step_statistics(result, step)
                total_stats = {
                    "total_processed": step_stats["total_processed"],
                    "total_created": step_stats["total_created"],
                    "total_updated": step_stats["total_updated"],
                    "total_skipped": step_stats["total_skipped"],
                    "total_failed": step_stats["total_failed"],
                    "total_errors": step_stats["total_errors"],
                    "total_received": step_stats.get("total_received", 0),
                }
            
            step_results = [{
                "step": step,
                "result": result,
                "stats": step_stats
            }]

            # Update execution record
            execution.status = SyncExecutionStatus.COMPLETED
            execution.result = json.dumps({
                "total_stats": total_stats,
                "step_results": step_results
            })
            self.db.commit()

            return {
                "process_id": process_id,
                "process_type": "single_step",
                "status": "completed",
                "total_stats": total_stats,
                "step_results": step_results
            }

        except Exception as e:
            logger.error(f"Error executing step {step}: {str(e)}")
            execution.status = SyncExecutionStatus.FAILED
            execution.error_message = str(e)
            self.db.commit()

            # Return consistent error format
            return {
                "process_id": process_id,
                "process_type": "single_step",
                "status": "failed",
                "total_stats": {
                    "total_processed": 0,
                    "total_created": 0,
                    "total_updated": 0,
                    "total_skipped": 0,
                    "total_failed": 0,
                    "total_errors": 1
                },
                "step_results": [{
                    "step": step,
                    "result": None,
                    "stats": {
                        "step": step,
                        "total_processed": 0,
                        "total_created": 0,
                        "total_updated": 0,
                        "total_skipped": 0,
                        "total_failed": 0,
                        "total_errors": 1,
                        "success": False,
                        "error": str(e)
                    }
                }],
                "error": str(e)
            }

    async def execute_process(
        self,
        process_type: str,
        starting_point: str,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a complete sync process."""
        process_id = str(uuid.uuid4())

        # Get steps to execute from starting point
        if process_type == "import":
            steps = self.get_steps_from_starting_point(starting_point)
        else:
            # For accrual, just use the starting point as the step
            steps = [starting_point]

        # Create execution record
        execution = SyncExecution(
            process_id=process_id,
            process_type=process_type,
            status=SyncExecutionStatus.RUNNING,
            steps=json.dumps(steps),
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
        self.db.add(execution)
        self.db.commit()

        try:
            # Generate monthly timestamps if needed
            monthly_timestamps = None
            if year and month:
                monthly_timestamps = self._generate_monthly_timestamps_for_month(
                    year, month)
            elif year:
                monthly_timestamps = self._generate_monthly_timestamps_for_year(
                    year)

            # Execute all steps
            step_results = []
            total_stats = {
                "total_processed": 0,
                "total_created": 0,
                "total_updated": 0,
                "total_skipped": 0,
                "total_failed": 0,
                "total_errors": 0
            }

            for step in steps:
                try:
                    result = await self._execute_step_api_call(
                        step=step,
                        year=year,
                        start_date=start_date,
                        end_date=end_date,
                        month=month,
                        monthly_timestamps=monthly_timestamps
                    )

                    # Extract statistics
                    step_stats = self._extract_step_statistics(result, step)
                    step_results.append({
                        "step": step,
                        "result": result,
                        "stats": step_stats
                    })

                    # Accumulate total stats
                    total_stats["total_processed"] += step_stats["total_processed"]
                    total_stats["total_created"] += step_stats["total_created"]
                    total_stats["total_updated"] += step_stats["total_updated"]
                    total_stats["total_skipped"] += step_stats["total_skipped"]
                    total_stats["total_failed"] += step_stats["total_failed"]
                    total_stats["total_errors"] += step_stats["total_errors"]

                except Exception as e:
                    logger.error(f"Error executing step {step}: {str(e)}")
                    step_results.append({
                        "step": step,
                        "result": None,
                        "stats": {
                            "step": step,
                            "total_processed": 0,
                            "total_created": 0,
                            "total_updated": 0,
                            "total_skipped": 0,
                            "total_failed": 0,
                            "total_errors": 1,
                            "success": False,
                            "error": str(e)
                        }
                    })
                    total_stats["total_errors"] += 1

            # Update execution record
            execution.status = SyncExecutionStatus.COMPLETED
            execution.result = json.dumps({
                "total_stats": total_stats,
                "step_results": step_results
            })
            self.db.commit()

            return {
                "process_id": process_id,
                "process_type": process_type,
                "status": "completed",
                "total_stats": total_stats,
                "step_results": step_results
            }

        except Exception as e:
            logger.error(f"Error executing process {process_type}: {str(e)}")
            execution.status = SyncExecutionStatus.FAILED
            execution.error_message = str(e)
            self.db.commit()

            return {
                "process_id": process_id,
                "process_type": process_type,
                "status": "failed",
                "error": str(e)
            }

    def get_available_steps(self) -> Dict[str, List[Dict[str, str]]]:
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

    def get_execution_order(self) -> List[str]:
        """Get the fixed execution order for import steps."""
        return ["services", "invoices", "crm-clients", "service-periods", "notion-external-id"]

    def get_steps_from_starting_point(self, starting_point: str) -> List[str]:
        """Get steps to execute from a starting point in the fixed order."""
        execution_order = self.get_execution_order()
        try:
            start_index = execution_order.index(starting_point)
            return execution_order[start_index:]
        except ValueError:
            # If starting point not found, return all steps
            return execution_order

    def _generate_monthly_timestamps_for_year(self, year: int) -> List[int]:
        """Generate Unix timestamps for the first day of each month in a given year."""
        timestamps = []
        for month in range(1, 13):
            dt = datetime(year, month, 1)
            timestamps.append(int(dt.timestamp()))
        # Add next year's January for the end boundary
        next_year_dt = datetime(year + 1, 1, 1)
        timestamps.append(int(next_year_dt.timestamp()))
        return timestamps

    def _generate_monthly_timestamps_for_month(self, year: int, month: int) -> List[int]:
        """Generate Unix timestamps for the first day of a specific month in a given year."""
        if 1 <= month <= 12:
            dt = datetime(year, month, 1)
            timestamps = [int(dt.timestamp())]
            # Add next month's first day as end boundary
            if month == 12:
                next_month_dt = datetime(year + 1, 1, 1)
            else:
                next_month_dt = datetime(year, month + 1, 1)
            timestamps.append(int(next_month_dt.timestamp()))
            return timestamps
        return []

    async def _execute_step_api_call(
        self,
        step: str,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[int] = None,
        monthly_timestamps: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Execute API call for a specific step."""
        async with httpx.AsyncClient(timeout=600.0) as client:
            if step == "services":
                return await self._call_api(client, f"{self.base_url}/integrations/holded/sync-services")

            elif step == "invoices":
                if monthly_timestamps:
                    # Process each month
                    total_stats = {
                        "total_processed": 0,
                        "total_created": 0,
                        "total_updated": 0,
                        "total_skipped": 0,
                        "total_failed": 0,
                        "total_errors": 0,
                        "total_received": 0,
                        "months_processed": 0,
                        "monthly_results": []
                    }

                    for i in range(len(monthly_timestamps) - 1):
                        start_timestamp = monthly_timestamps[i]
                        end_timestamp = monthly_timestamps[i + 1]

                        result = await self._call_api(
                            client,
                            f"{self.base_url}/integrations/holded/sync-invoices-and-clients",
                            params={
                                "start_timestamp": start_timestamp,
                                "end_timestamp": end_timestamp
                            }
                        )

                        # Accumulate stats
                        month_stats = self._extract_step_statistics(
                            result, "invoices")
                        total_stats["total_processed"] += month_stats["total_processed"]
                        total_stats["total_created"] += month_stats["total_created"]
                        total_stats["total_updated"] += month_stats["total_updated"]
                        total_stats["total_skipped"] += month_stats["total_skipped"]
                        total_stats["total_failed"] += month_stats["total_failed"]
                        total_stats["total_errors"] += month_stats["total_errors"]
                        total_stats["total_received"] += month_stats.get("total_received", 0)
                        total_stats["months_processed"] += 1
                        total_stats["monthly_results"].append({
                            "month": datetime.fromtimestamp(start_timestamp).strftime('%Y-%m'),
                            "stats": month_stats
                        })

                    return total_stats
                else:
                    raise ValueError("Invoices step requires date range")

            elif step == "crm-clients":
                return await self._call_api(client, f"{self.base_url}/integrations/fourgeeks/sync-students-from-clients")

            elif step == "service-periods":
                return await self._call_api(client, f"{self.base_url}/integrations/fourgeeks/sync-enrollments-from-clients")

            elif step == "notion-external-id":
                return await self._call_api(client, f"{self.base_url}/integrations/notion/sync-page-ids-from-clients")

            elif step == "accruals":
                if monthly_timestamps:
                    total_results = {
                        "months_processed": 0,
                        "monthly_results": [],
                        "total_processed": 0,
                        "total_created": 0,
                        "total_updated": 0,
                        "total_skipped": 0,
                        "total_failed": 0,
                        "total_errors": 0
                    }

                    # Process each month, excluding the last timestamp which is just the end boundary
                    for i in range(len(monthly_timestamps) - 1):
                        start_timestamp = monthly_timestamps[i]
                        accrual_date = datetime.fromtimestamp(
                            start_timestamp).strftime('%Y-%m-%d')

                        result = await self._call_api(
                            client,
                            f"{self.base_url}/accruals/process-contracts",
                            method="POST",
                            json_data={"period_start_date": accrual_date}
                        )

                        # Extract stats
                        month_stats = self._extract_step_statistics(
                            result, "accruals")
                        total_results["months_processed"] += 1
                        total_results["monthly_results"].append({
                            "month": accrual_date,
                            "stats": month_stats
                        })
                        
                        # Accumulate totals
                        total_results["total_processed"] += month_stats.get("total_processed", 0)
                        total_results["total_created"] += month_stats.get("total_created", 0)
                        total_results["total_updated"] += month_stats.get("total_updated", 0)
                        total_results["total_skipped"] += month_stats.get("total_skipped", 0)
                        total_results["total_failed"] += month_stats.get("total_failed", 0)
                        total_results["total_errors"] += month_stats.get("total_errors", 0)

                    return total_results
                else:
                    raise ValueError("Accruals step requires date range")

            else:
                raise ValueError(f"Unknown step: {step}")

    async def _call_api(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API call and return the response."""
        try:
            if method.upper() == "POST":
                response = await client.post(url, params=params, json=json_data)
            else:
                response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.error(f"Response content: {e.response.text}")
            raise Exception(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"API call error: {e}")
            raise Exception(f"API call failed: {e}")

    def _extract_step_statistics(self, result: Dict[str, Any], step_name: str) -> Dict[str, Any]:
        """Extract statistics from API response for a given step."""
        if not isinstance(result, dict):
            return {
                "step": step_name,
                "total_processed": 0,
                "total_created": 0,
                "total_updated": 0,
                "total_skipped": 0,
                "total_failed": 0,
                "total_errors": 1,
                "success": False,
                "error": "Invalid response format"
            }

        # Handle special case for invoices
        if step_name == "invoices":
            # Check if result already has accumulated stats (from multi-month processing in execute_process)
            if "total_processed" in result and "total_created" in result:
                stats = {
                    "step": step_name,
                    "total_processed": result.get("total_processed", 0),
                    "total_created": result.get("total_created", 0),
                    "total_updated": result.get("total_updated", 0),
                    "total_skipped": result.get("total_skipped", 0),
                    "total_failed": result.get("total_failed", 0),
                    "total_errors": result.get("total_errors", 0),
                    "total_received": result.get("total_received", 0),
                    "success": result.get("success", True)
                }
            else:
                # Single-month response: endpoint returns total_received, processed, created, updated, skipped, errors
                processed = result.get("processed", 0)
                total_received = result.get("total_received", 0) or (processed + result.get("skipped", 0) + result.get("errors", 0))
                stats = {
                    "step": step_name,
                    "total_processed": processed,
                    "total_created": result.get("created", 0),
                    "total_updated": result.get("updated", 0),
                    "total_skipped": result.get("skipped", 0),
                    "total_failed": 0,
                    "total_errors": result.get("errors", 0),
                    "total_received": total_received,
                    "success": result.get("success", True)
                }
        elif step_name == "notion-external-id":
            # Notion sync has specific field names: linked, not_found
            linked = result.get("linked", 0)
            not_found = result.get("not_found", 0)
            total_processed = linked + not_found
            stats = {
                "step": step_name,
                "total_processed": total_processed,
                "total_created": linked,  # linked = created external IDs
                "total_updated": 0,
                "total_skipped": 0,
                "total_failed": not_found,  # not_found = failed lookups
                "total_errors": len(result.get("not_found_details", [])),
                "success": result.get("success", True)
            }
        elif step_name == "crm-clients":
            # CRM clients sync (4Geeks) has specific field names: linked, not_found, errors
            linked = result.get("linked", 0)
            not_found = result.get("not_found", 0)
            errors_count = result.get("errors", 0)
            total_processed = linked + not_found + errors_count
            stats = {
                "step": step_name,
                "total_processed": total_processed,
                "total_created": linked,  # linked = created external IDs
                "total_updated": 0,
                "total_skipped": 0,
                "total_failed": not_found,  # not_found = clients not found in 4Geeks
                "total_errors": errors_count + len(result.get("error_details", [])),
                "success": result.get("success", True)
            }
        elif step_name == "accruals":
            # Check if result already has accumulated stats (from multi-month processing)
            if "total_processed" in result and "total_created" in result:
                # Result already has accumulated statistics
                stats = {
                    "step": step_name,
                    "total_processed": result.get("total_processed", 0),
                    "total_created": result.get("total_created", 0),
                    "total_updated": result.get("total_updated", 0),
                    "total_skipped": result.get("total_skipped", 0),
                    "total_failed": result.get("total_failed", 0),
                    "total_errors": result.get("total_errors", 0),
                    "success": result.get("success", True)
                }
            else:
                # Extract from single month response with summary structure
                summary = result.get("summary", {})
                stats = {
                    "step": step_name,
                    "total_processed": summary.get("total_contracts_processed", 0),
                    "total_created": summary.get("successful_accruals", 0),
                    "total_updated": 0,
                    "total_skipped": summary.get("skipped_accruals", 0),
                    "total_failed": summary.get("failed_accruals", 0),
                    "total_errors": summary.get("failed_accruals", 0),
                    "success": summary.get("failed_accruals", 0) == 0
                }
        else:
            # Extract common statistics for other steps
            stats = {
                "step": step_name,
                "total_processed": result.get("total_processed", result.get("processed", 0)),
                "total_created": result.get("created", 0),
                "total_updated": result.get("updated", 0),
                "total_skipped": result.get("skipped", 0),
                "total_failed": result.get("total_failed", 0),
                "total_errors": result.get("errors", 0),
                "success": result.get("success", True)
            }

        if "error" in result:
            stats["error"] = result["error"]

        return stats

    def get_latest_processed_month_year(self) -> Dict[str, Optional[int]]:
        """
        Get the latest month and year from invoices and accruals in the database.
        Returns the last month/year that has been processed (has data).

        Returns:
            Dictionary with 'year' and 'month' keys. Returns None if no data found.
        """
        # Get latest invoice date
        latest_invoice = self.db.query(
            func.max(Invoice.invoice_date).label('max_date')
        ).first()

        # Get latest accrual date
        latest_accrual = self.db.query(
            func.max(AccruedPeriod.accrual_date).label('max_date')
        ).first()

        latest_date = None

        # Compare both dates and get the latest one
        if latest_invoice and latest_invoice.max_date:
            latest_date = latest_invoice.max_date

        if latest_accrual and latest_accrual.max_date:
            if latest_date is None or latest_accrual.max_date > latest_date:
                latest_date = latest_accrual.max_date

        if latest_date:
            # Return the next month/year to process (the month after the latest)
            # If latest is November 2025, we want to show December 2025
            if latest_date.month == 12:
                return {
                    'year': latest_date.year + 1,
                    'month': 1  # January of next year
                }
            else:
                return {
                    'year': latest_date.year,
                    'month': latest_date.month + 1  # Next month
                }

        # If no data found, return None
        return {
            'year': None,
            'month': None
        }
