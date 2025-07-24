#!/usr/bin/env python
"""
Bulk synchronization script that performs a series of API calls in sequence:
1. Import Services from Invoicing System
2. Import Invoices and Clients from Invoicing System
3. Retrieve Clients data from CRM (for each month in 2024)
4. Generate Service Periods from CRM
5. Perform accruals for each month in 2024
"""

import os
import asyncio
import httpx
from datetime import datetime
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base URL for API calls
BASE_URL = os.environ.get("VITE_API_URL", "http://localhost: 3001")

STEP_NAMES = [
    "services",
    "invoices",
    "crm-clients",
    "service-periods",
    "notion-external-id",
]


async def make_api_call(client, url, params=None):
    """Make an API call and return the response."""
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        logger.error(f"Response content: {e.response.text}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"error": str(e)}


async def import_services_from_invoicing_system(client):
    """Step 1: Import Services from Invoicing System"""
    logger.info("Step 1: Importing Services from Invoicing System")
    services_result = await make_api_call(
        client, f"{BASE_URL}/integrations/holded/sync-services"
    )
    logger.info(f"Services import completed: {services_result}")
    return services_result


def generate_monthly_timestamps(year):
    """Generate Unix timestamps for the first day of each month in the given year, plus Jan 1 of the next year."""
    timestamps = []
    for month in range(1, 13):
        dt = datetime(year, month, 1)
        timestamps.append(int(dt.timestamp()))
    # Add Jan 1 of the next year
    dt_next = datetime(year + 1, 1, 1)
    timestamps.append(int(dt_next.timestamp()))
    return timestamps


def generate_monthly_timestamps_from_range(start_date, end_date):
    """Generate Unix timestamps for the first day of each month from start_date to end_date (exclusive)."""
    timestamps = []
    current = datetime(start_date.year, start_date.month, 1)
    while current < end_date:
        timestamps.append(int(current.timestamp()))
        # Move to the first day of the next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)
    # Add end_date if it's the first of a month and not already included
    if end_date.day == 1 and int(end_date.timestamp()) not in timestamps:
        timestamps.append(int(end_date.timestamp()))
    return timestamps


async def import_invoices_and_clients_from_invoicing_system(client, monthly_timestamps):
    """Step 2: Import Invoices and Clients from Invoicing System"""
    logger.info("Step 2: Importing Invoices and Clients from Invoicing System")
    for i in range(len(monthly_timestamps) - 1):
        start_timestamp = monthly_timestamps[i]
        end_timestamp = monthly_timestamps[i + 1]
        date_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d')
        logger.info(f"Processing month starting: {date_str}")
        invoices_clients_result = await make_api_call(
            client,
            f"{BASE_URL}/integrations/holded/sync-invoices-and-clients",
            params={"start_timestamp": start_timestamp,
                    "end_timestamp": end_timestamp}
        )
        logger.info(
            f"Invoices and Clients import for {date_str} completed: {invoices_clients_result}")


async def retrieve_clients_data_from_crm(client):
    """Step 3: Retrieve Clients data from CRM"""
    logger.info("Step 3: Retrieving Clients data from CRM")
    crm_clients_result = await make_api_call(
        client,
        f"{BASE_URL}/integrations/fourgeeks/sync-students-from-clients"
    )
    logger.info(f"CRM Clients data retrieval completed: {crm_clients_result}")
    return crm_clients_result


async def generate_service_periods_from_crm(client):
    """Step 4: Generate Service Periods from CRM"""
    logger.info("Step 4: Generating Service Periods from CRM")
    service_periods_result = await make_api_call(
        client, f"{BASE_URL}/integrations/fourgeeks/sync-enrollments-from-clients"
    )
    logger.info(
        f"Service Periods generation completed: {service_periods_result}")
    return service_periods_result


async def retrieve_notion_external_id_for_clients(client):
    """Step 5: Sync with Notion"""
    logger.info("Step 5: Syncing with Notion")
    notion_result = await make_api_call(
        client, f"{BASE_URL}/integrations/notion/sync-page-ids-from-clients"
    )
    logger.info(f"Notion sync completed: {notion_result}")
    return notion_result


def format_result_output(result, step_name="", context=""):
    """Format API call results in a readable way."""
    if not result:
        return "No result returned"
    
    # Handle error cases
    if isinstance(result, dict) and "error" in result:
        return f"❌ ERROR: {result['error']}"
    
    # Create formatted output
    output_lines = []
    
    if context:
        output_lines.append(f"📋 Context: {context}")
    
    output_lines.append("=" * 60)
    
    if isinstance(result, dict):
        # Handle success status
        if result.get("success") is True:
            output_lines.append("✅ Status: SUCCESS")
        elif result.get("success") is False:
            output_lines.append("❌ Status: FAILED")
        
        # Special handling for accrual results
        if "period_start_date" in result and "results" in result:
            output_lines.append(f"📅 Period: {result['period_start_date']}")
            output_lines.append("")
            
            # Accrual summary metrics
            accrual_metrics = [
                ("total_periods_processed", "📊 Total Periods Processed"),
                ("successful_accruals", "✅ Successful Accruals"),
                ("failed_accruals", "❌ Failed Accruals"),
                ("existing_accruals", "🔄 Existing Accruals"),
                ("skipped_accruals", "⏭️ Skipped Accruals"),
            ]
            
            for key, label in accrual_metrics:
                if key in result:
                    output_lines.append(f"{label}: {result[key]}")
            
            # Process detailed results
            detailed_results = result.get("results", [])
            if detailed_results:
                output_lines.append("")
                output_lines.append(f"📋 Detailed Results ({len(detailed_results)} items):")
                
                # Group results by status
                status_groups = {}
                for item in detailed_results:
                    status = item.get("status", "UNKNOWN")
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(item)
                
                # Display grouped results
                for status, items in status_groups.items():
                    status_emoji = {
                        "SUCCESS": "✅",
                        "HALTED": "🛑", 
                        "FAILED": "❌",
                        "SKIPPED": "⏭️"
                    }.get(status, "ℹ️")
                    
                    output_lines.append(f"   {status_emoji} {status}: {len(items)} items")
                    
                    # Show first few examples for each status
                    for i, item in enumerate(items[:3], 1):
                        contract_id = item.get("contract_id", "N/A")
                        service_period_id = item.get("service_period_id", "N/A")
                        message = item.get("message", "No message")
                        
                        # Truncate long messages
                        if len(message) > 80:
                            message = message[:77] + "..."
                        
                        output_lines.append(f"      {i}. Contract {contract_id} (Period: {service_period_id})")
                        output_lines.append(f"         💬 {message}")
                    
                    if len(items) > 3:
                        output_lines.append(f"      ... and {len(items) - 3} more {status} items")
                    output_lines.append("")
        
        else:
            # Handle regular API results (non-accrual)
            # Display key metrics
            metrics_to_show = [
                ("created", "📈 Created"),
                ("updated", "🔄 Updated"), 
                ("processed", "⚙️ Processed"),
                ("linked", "🔗 Linked"),
                ("skipped", "⏭️ Skipped"),
                ("errors", "❌ Errors"),
                ("not_found", "🔍 Not Found"),
            ]
            
            for key, label in metrics_to_show:
                if key in result:
                    output_lines.append(f"{label}: {result[key]}")
            
            # Show error details if any
            error_details = result.get("error_details", [])
            if error_details:
                output_lines.append(f"🚨 Error Details ({len(error_details)} errors):")
                for i, error in enumerate(error_details[:5], 1):  # Show first 5 errors
                    output_lines.append(f"   {i}. {error}")
                if len(error_details) > 5:
                    output_lines.append(f"   ... and {len(error_details) - 5} more errors")
            
            # Show not found details if any
            not_found_details = result.get("not_found_details", [])
            if not_found_details:
                output_lines.append(f"🔍 Not Found Details ({len(not_found_details)} items):")
                for i, item in enumerate(not_found_details[:3], 1):  # Show first 3
                    output_lines.append(f"   {i}. {item}")
                if len(not_found_details) > 3:
                    output_lines.append(f"   ... and {len(not_found_details) - 3} more items")
            
            # Show any other relevant fields
            excluded_fields = {
                "success", "created", "updated", "processed", "linked", 
                "skipped", "errors", "error_details", "not_found", "not_found_details",
                "period_start_date", "total_periods_processed", "successful_accruals",
                "failed_accruals", "existing_accruals", "skipped_accruals", "results"
            }
            
            other_fields = {k: v for k, v in result.items() if k not in excluded_fields}
            
            if other_fields:
                output_lines.append("📊 Additional Info:")
                for key, value in other_fields.items():
                    if hasattr(value, '__len__'):
                        output_lines.append(f"   {key}: {len(value)} items")
                    else:
                        output_lines.append(f"   {key}: {value}")
    
    else:
        # For non-dict results, just show them as-is
        output_lines.append(f"📄 Result: {result}")
    
    output_lines.append("=" * 60)
    
    return "\n".join(output_lines)


async def perform_accruals(client, monthly_timestamps):
    """Perform accruals for each month in the given year"""
    logger.info("🔄 Step 6: Performing accruals for each month in selected year")
    total_results = {
        "months_processed": 0,
        "total_periods_processed": 0,
        "total_successful_accruals": 0,
        "total_failed_accruals": 0,
        "total_existing_accruals": 0,
        "total_skipped_accruals": 0,
        "total_errors": 0,
        "monthly_results": []
    }
    for i in range(len(monthly_timestamps) - 1):
        start_timestamp = monthly_timestamps[i]
        accrual_date = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d')
        logger.info(f"📅 Processing accruals for month: {accrual_date}")
        try:
            response = await client.post(
                f"{BASE_URL}/accruals/process-contracts",
                json={"period_start_date": accrual_date}
            )
            response.raise_for_status()
            result = response.json()
            formatted_output = format_result_output(result, "accruals", f"Month: {accrual_date}")
            logger.info(f"Accruals for {accrual_date} completed:\n{formatted_output}")
            total_results["months_processed"] += 1
            if isinstance(result, dict):
                total_results["total_periods_processed"] += result.get("total_periods_processed", 0)
                total_results["total_successful_accruals"] += result.get("successful_accruals", 0)
                total_results["total_failed_accruals"] += result.get("failed_accruals", 0)
                total_results["total_existing_accruals"] += result.get("existing_accruals", 0)
                total_results["total_skipped_accruals"] += result.get("skipped_accruals", 0)
            total_results["monthly_results"].append({
                "month": accrual_date,
                "result": result
            })
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error occurred during accruals for {accrual_date}: {e}")
            logger.error(f"Response content: {e.response.text}")
            total_results["total_errors"] += 1
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout error occurred during accruals for {accrual_date}: {e}")
            total_results["total_errors"] += 1
        except Exception as e:
            logger.error(f"❌ An error occurred during accruals for {accrual_date}: {e}")
            total_results["total_errors"] += 1
    summary_output = format_result_output(total_results, "accruals", "Summary for All Months")
    logger.info(f"📊 Accruals Summary:\n{summary_output}")


async def main(from_step: str = None, year: int = 2024, start_date: str = None, end_date: str = None):
    """Execute all synchronization steps in sequence, optionally starting from a specific step and/or year or date range."""
    STEP_FUNCTIONS = [
        import_services_from_invoicing_system,
        import_invoices_and_clients_from_invoicing_system,
        retrieve_clients_data_from_crm,
        generate_service_periods_from_crm,
        retrieve_notion_external_id_for_clients,
    ]
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        monthly_timestamps = generate_monthly_timestamps_from_range(start_dt, end_dt)
    else:
        monthly_timestamps = generate_monthly_timestamps(year)
    async with httpx.AsyncClient(timeout=600.0) as client:
        start_index = 0
        if from_step:
            if from_step == "accruals":
                await perform_accruals(client, monthly_timestamps=monthly_timestamps)
                return
            try:
                start_index = STEP_NAMES.index(from_step)
            except ValueError:
                logger.error(
                    f"Unknown step: {from_step}. Valid steps are: {', '.join(STEP_NAMES)}")
                return
        for func in STEP_FUNCTIONS[start_index:]:
            if func == import_invoices_and_clients_from_invoicing_system:
                await func(client, monthly_timestamps=monthly_timestamps)
            else:
                await func(client)
        logger.info("All synchronization steps completed successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bulk synchronization script.")
    parser.add_argument(
        "--from-step",
        type=str,
        choices=STEP_NAMES + ["accruals"],
        help=f"Start execution from this step (skipping previous steps). Choices: {', '.join(STEP_NAMES)}"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Target year for processing (e.g., 2024). Defaults to 2024 if not set."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for processing in YYYY-MM-DD format. Overrides --year if set."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (exclusive) for processing in YYYY-MM-DD format. Overrides --year if set."
    )
    args = parser.parse_args()
    asyncio.run(main(from_step=args.from_step, year=args.year, start_date=args.start_date, end_date=args.end_date))
