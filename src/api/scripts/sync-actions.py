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
BASE_URL = os.environ.get("VITE_API_URL", "http://localhost:3001")

STEP_NAMES = [
    "services",
    "invoices",
    "crm-clients",
    "service-periods",
    "notion-external-id",
]


def extract_step_statistics(result, step_name):
    """Extract statistics from API response for a given step."""
    if not isinstance(result, dict):
        return {
            "step": step_name,
            "total_processed": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "total_errors": 0,
            "success": False,
            "error": "Invalid response format"
        }
    
    # Clean up empty error fields to prevent confusion
    if "error" in result and (not result["error"] or not str(result["error"]).strip()):
        logger.warning(f"Removing empty error field from {step_name} response")
        result.pop("error", None)
    
    # Handle error cases - only if error field exists and has a meaningful value
    if "error" in result and result["error"] and result["error"].strip():
        return {
            "step": step_name,
            "total_processed": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "total_errors": 1,
            "success": False,
            "error": result["error"]
        }
    
    # Extract common statistics from API responses
    stats = {
        "step": step_name,
        "total_processed": result.get("processed", 0),
        "total_created": result.get("created", 0),
        "total_updated": result.get("updated", 0),
        "total_skipped": result.get("skipped", 0),
        "total_failed": result.get("failed", 0),
        "total_errors": len(result.get("error_details", [])),
        "success": result.get("success", False)
    }
    
    # Handle special cases for different steps
    if step_name == "services":
        # Services might have different field names
        stats["total_processed"] = result.get("processed", result.get("total", 0))
        stats["total_created"] = result.get("created", result.get("new", 0))
        stats["total_updated"] = result.get("updated", result.get("modified", 0))
    
    elif step_name == "invoices":
        # Invoices might have different field names
        stats["total_processed"] = result.get("processed", result.get("total", 0))
        stats["total_created"] = result.get("created", result.get("new", 0))
        stats["total_updated"] = result.get("updated", result.get("modified", 0))
    
    elif step_name == "crm-clients":
        # CRM clients might have different field names
        stats["total_processed"] = result.get("processed", result.get("total", 0))
        stats["total_created"] = result.get("created", result.get("new", 0))
        stats["total_updated"] = result.get("updated", result.get("modified", 0))
    
    elif step_name == "service-periods":
        # Service periods might have different field names
        stats["total_processed"] = result.get("processed", result.get("total", 0))
        stats["total_created"] = result.get("created", result.get("new", 0))
        stats["total_updated"] = result.get("updated", result.get("modified", 0))
    
    elif step_name == "notion-external-id":
        # Notion sync has specific field names: linked, not_found
        total_processed = result.get("linked", 0) + result.get("not_found", 0)
        stats["total_processed"] = total_processed
        stats["total_created"] = result.get("linked", 0)
        stats["total_failed"] = result.get("not_found", 0)
        stats["total_skipped"] = total_processed - stats["total_created"] - stats["total_failed"]
    
    elif step_name == "accruals":
        # Accruals have a different structure with nested summary
        summary = result.get("summary", {})
        stats["total_processed"] = summary.get("total_contracts_processed", 0)
        stats["total_created"] = summary.get("successful_accruals", 0)
        stats["total_failed"] = summary.get("failed_accruals", 0)
        stats["total_skipped"] = summary.get("skipped_accruals", 0)
        # For accruals, we consider it successful if there are no failed accruals
        stats["success"] = summary.get("failed_accruals", 0) == 0
    
    return stats


async def make_api_call(client, url, params=None, method="GET", json_data=None):
    """Make an API call and return the response."""
    try:
        if method.upper() == "POST":
            response = await client.post(url, params=params, json=json_data)
        else:
            response = await client.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        
        # Validate that the response doesn't have empty error fields
        if isinstance(result, dict) and "error" in result:
            if not result["error"] or not result["error"].strip():
                logger.warning(f"API response contains empty error field: {result}")
                # Remove empty error field to prevent confusion
                result.pop("error", None)
        
        return result
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
    
    # Extract and format statistics
    stats = extract_step_statistics(services_result, "services")
    formatted_output = format_result_output(services_result, "services", "Services Import")
    logger.info(f"📊 Services Import Summary:\n{formatted_output}")
    
    return services_result, stats


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
    
    total_stats = {
        "step": "invoices",
        "total_processed": 0,
        "total_created": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "total_failed": 0,
        "total_errors": 0,
        "success": True,
        "error": None,
        "months_processed": 0,
        "monthly_results": []
    }
    
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
        
        # Extract statistics for this month
        month_stats = extract_step_statistics(invoices_clients_result, "invoices")
        month_stats["month"] = date_str
        
        # Accumulate totals
        total_stats["total_processed"] += month_stats["total_processed"]
        total_stats["total_created"] += month_stats["total_created"]
        total_stats["total_updated"] += month_stats["total_updated"]
        total_stats["total_skipped"] += month_stats["total_skipped"]
        total_stats["total_failed"] += month_stats["total_failed"]
        total_stats["total_errors"] += month_stats["total_errors"]
        total_stats["months_processed"] += 1
        total_stats["monthly_results"].append({
            "month": date_str,
            "result": invoices_clients_result,
            "stats": month_stats
        })
        
        # Log individual month results
        formatted_output = format_result_output(invoices_clients_result, "invoices", f"Month: {date_str}")
        logger.info(f"Invoices and Clients import for {date_str} completed:\n{formatted_output}")
    
    # Log total summary
    formatted_summary = format_result_output(total_stats, "invoices", "Summary for All Months")
    logger.info(f"📊 Invoices and Clients Import Summary:\n{formatted_summary}")
    
    return total_stats


async def retrieve_clients_data_from_crm(client):
    """Step 3: Retrieve Clients data from CRM"""
    logger.info("Step 3: Retrieving Clients data from CRM")
    crm_clients_result = await make_api_call(
        client,
        f"{BASE_URL}/integrations/fourgeeks/sync-students-from-clients"
    )
    logger.info(f"CRM Clients data retrieval completed: {crm_clients_result}")
    
    # Extract and format statistics
    stats = extract_step_statistics(crm_clients_result, "crm-clients")
    formatted_output = format_result_output(crm_clients_result, "crm-clients", "CRM Clients Sync")
    logger.info(f"📊 CRM Clients Sync Summary:\n{formatted_output}")
    
    return crm_clients_result, stats


async def generate_service_periods_from_crm(client):
    """Step 4: Generate Service Periods from CRM"""
    logger.info("Step 4: Generating Service Periods from CRM")
    service_periods_result = await make_api_call(
        client, f"{BASE_URL}/integrations/fourgeeks/sync-enrollments-from-clients"
    )
    logger.info(
        f"Service Periods generation completed: {service_periods_result}")
    
    # Extract and format statistics
    stats = extract_step_statistics(service_periods_result, "service-periods")
    formatted_output = format_result_output(service_periods_result, "service-periods", "Service Periods Generation")
    logger.info(f"📊 Service Periods Generation Summary:\n{formatted_output}")
    
    return service_periods_result, stats


async def retrieve_notion_external_id_for_clients(client):
    """Step 5: Sync with Notion"""
    logger.info("Step 5: Syncing with Notion")
    notion_result = await make_api_call(
        client, f"{BASE_URL}/integrations/notion/sync-page-ids-from-clients"
    )
    logger.info(f"Notion sync completed: {notion_result}")
    
    # Extract and format statistics
    stats = extract_step_statistics(notion_result, "notion-external-id")
    formatted_output = format_result_output(notion_result, "notion-external-id", "Notion Sync")
    logger.info(f"📊 Notion Sync Summary:\n{formatted_output}")
    
    return notion_result, stats


def format_result_output(result, step_name="", context=""):
    """Format API call results in a readable way."""
    if not result:
        return "No result returned"
    
    # Handle error cases
    if isinstance(result, dict) and "error" in result and result["error"] is not None and result["error"] != "":
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
        
        # Special handling for overall summary (complete sync summary)
        elif "total_steps_completed" in result and "step_results" in result:
            output_lines.append("🎯 COMPLETE SYNC SUMMARY")
            output_lines.append("")
            
            # Overall summary metrics
            overall_metrics = [
                ("total_steps_completed", "🚀 Steps Completed"),
                ("total_processed", "📊 Total Processed"),
                ("total_created", "📈 Total Created"),
                ("total_updated", "🔄 Total Updated"),
                ("total_skipped", "⏭️ Total Skipped"),
                ("total_failed", "❌ Total Failed"),
                ("total_errors", "🚨 Total Errors"),
            ]
            
            for key, label in overall_metrics:
                if key in result:
                    output_lines.append(f"{label}: {result[key]}")
            
            # Show step results summary
            step_results = result.get("step_results", [])
            if step_results:
                output_lines.append("")
                output_lines.append(f"📋 Step Results ({len(step_results)} steps):")
                for step_result in step_results:
                    step_name = step_result.get("step", "Unknown")
                    step_stats = step_result.get("stats", {})
                    success_status = "✅" if step_stats.get("success", False) else "❌"
                    output_lines.append(f"   {success_status} {step_name}: {step_stats.get('total_processed', 0)} processed, "
                                      f"{step_stats.get('total_created', 0)} created, "
                                      f"{step_stats.get('total_skipped', 0)} skipped, "
                                      f"{step_stats.get('total_errors', 0)} errors")
        
        # Special handling for step statistics (aggregated results)
        elif "step" in result and "total_processed" in result:
            output_lines.append(f"📊 Step: {result['step'].upper()}")
            output_lines.append("")
            
            # Step summary metrics
            step_metrics = [
                ("total_processed", "📊 Total Processed"),
                ("total_created", "📈 Total Created"),
                ("total_updated", "🔄 Total Updated"),
                ("total_skipped", "⏭️ Total Skipped"),
                ("total_failed", "❌ Total Failed"),
                ("total_errors", "🚨 Total Errors"),
            ]
            
            for key, label in step_metrics:
                if key in result:
                    output_lines.append(f"{label}: {result[key]}")
            
            # Show months processed if available (for multi-month operations)
            if "months_processed" in result:
                output_lines.append(f"📅 Months Processed: {result['months_processed']}")
            
            # Show error if any
            if result.get("error"):
                output_lines.append(f"❌ Error: {result['error']}")
            
            # Show monthly results if available
            monthly_results = result.get("monthly_results", [])
            if monthly_results:
                output_lines.append("")
                output_lines.append(f"📋 Monthly Results ({len(monthly_results)} months):")
                for month_result in monthly_results[:5]:  # Show first 5 months
                    month = month_result.get("month", "Unknown")
                    month_stats = month_result.get("stats", {})
                    output_lines.append(f"   📅 {month}: {month_stats.get('total_processed', 0)} processed, "
                                      f"{month_stats.get('total_created', 0)} created, "
                                      f"{month_stats.get('total_skipped', 0)} skipped")
                if len(monthly_results) > 5:
                    output_lines.append(f"   ... and {len(monthly_results) - 5} more months")
        
        else:
            # Handle regular API results (non-accrual, non-step-statistics)
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
                "failed_accruals", "existing_accruals", "skipped_accruals", "results",
                "step", "total_processed", "total_created", "total_updated", 
                "total_skipped", "total_failed", "total_errors", "months_processed", "monthly_results",
                "total_steps_completed", "step_results"
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
            # Use make_api_call for consistency and better error handling
            result = await make_api_call(
                client, 
                f"{BASE_URL}/accruals/process-contracts",
                method="POST",
                json_data={"period_start_date": accrual_date}
            )
            
            # Check if there was an error in the API call
            if "error" in result and result["error"]:
                logger.error(f"❌ Error in accruals for {accrual_date}: {result['error']}")
                total_results["total_errors"] += 1
                continue
            
            # Extract statistics for this month
            month_stats = extract_step_statistics(result, "accruals")
            formatted_output = format_result_output(result, "accruals", f"Month: {accrual_date}")
            logger.info(f"Accruals for {accrual_date} completed:\n{formatted_output}")
            
            total_results["months_processed"] += 1
            if isinstance(result, dict):
                summary = result.get("summary", {})
                total_results["total_periods_processed"] += summary.get("total_contracts_processed", 0)
                total_results["total_successful_accruals"] += summary.get("successful_accruals", 0)
                total_results["total_failed_accruals"] += summary.get("failed_accruals", 0)
                total_results["total_existing_accruals"] += summary.get("existing_accruals", 0)
                total_results["total_skipped_accruals"] += summary.get("skipped_accruals", 0)
            
            total_results["monthly_results"].append({
                "month": accrual_date,
                "result": result,
                "stats": month_stats
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
    
    # Initialize overall statistics
    overall_stats = {
        "total_steps_completed": 0,
        "total_processed": 0,
        "total_created": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "total_failed": 0,
        "total_errors": 0,
        "step_results": []
    }
    
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
        
        # Execute steps and collect statistics
        for i, func in enumerate(STEP_FUNCTIONS[start_index:], start_index):
            step_name = STEP_NAMES[i]
            logger.info(f"🚀 Starting step {i+1}: {step_name}")
            
            try:
                if func == import_invoices_and_clients_from_invoicing_system:
                    step_stats = await func(client, monthly_timestamps=monthly_timestamps)
                else:
                    _, step_stats = await func(client)
                
                # Accumulate overall statistics
                overall_stats["total_steps_completed"] += 1
                overall_stats["total_processed"] += step_stats.get("total_processed", 0)
                overall_stats["total_created"] += step_stats.get("total_created", 0)
                overall_stats["total_updated"] += step_stats.get("total_updated", 0)
                overall_stats["total_skipped"] += step_stats.get("total_skipped", 0)
                overall_stats["total_failed"] += step_stats.get("total_failed", 0)
                overall_stats["total_errors"] += step_stats.get("total_errors", 0)
                overall_stats["step_results"].append({
                    "step": step_name,
                    "stats": step_stats
                })
                
            except Exception as e:
                logger.error(f"❌ Error in step {step_name}: {e}")
                overall_stats["total_errors"] += 1
                overall_stats["step_results"].append({
                    "step": step_name,
                    "stats": {
                        "step": step_name,
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
        
        # Display overall summary
        logger.info("🎉 All synchronization steps completed!")
        overall_summary = format_result_output(overall_stats, "overall", "Complete Sync Summary")
        logger.info(f"📊 Overall Summary:\n{overall_summary}")
        
        # Display individual step summaries
        logger.info("📋 Individual Step Summaries:")
        for step_result in overall_stats["step_results"]:
            step_name = step_result["step"]
            step_stats = step_result["stats"]
            step_summary = format_result_output(step_stats, step_name, f"Step: {step_name}")
            logger.info(f"\n{step_summary}")

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
