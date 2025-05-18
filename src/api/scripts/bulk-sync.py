#!/usr/bin/env python
"""
Bulk synchronization script that performs a series of API calls in sequence:
1. Import Services from Invoicing System
2. Import Invoices and Clients from Invoicing System
3. Retrieve Clients data from CRM (for each month in 2024)
4. Generate Service Periods from CRM
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

# Timestamps for the first day of each month in 2024 through Jan 1, 2025
MONTHLY_TIMESTAMPS = [
    1704067200,  # 2024-01-01
    1706745600,  # 2024-02-01
    1709251200,  # 2024-03-01
    1711929600,  # 2024-04-01
    1714521600,  # 2024-05-01
    1717200000,  # 2024-06-01
    1719792000,  # 2024-07-01
    1722470400,  # 2024-08-01
    1725148800,  # 2024-09-01
    1727740800,  # 2024-10-01
    1730419200,  # 2024-11-01
    1733011200,  # 2024-12-01
    1735689600,  # 2025-01-01
]

STEP_NAMES = [
    "services",
    "invoices",
    "crm-clients",
    "service-periods",
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


async def import_invoices_and_clients_from_invoicing_system(client):
    """Step 2: Import Invoices and Clients from Invoicing System"""
    logger.info("Step 2: Importing Invoices and Clients from Invoicing System")
    for i in range(len(MONTHLY_TIMESTAMPS) - 1):
        start_timestamp = MONTHLY_TIMESTAMPS[i]
        end_timestamp = MONTHLY_TIMESTAMPS[i + 1]
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


async def main(from_step: str = None):
    """Execute all synchronization steps in sequence, optionally starting from a specific step."""
    STEP_FUNCTIONS = [
        import_services_from_invoicing_system,
        import_invoices_and_clients_from_invoicing_system,
        retrieve_clients_data_from_crm,
        generate_service_periods_from_crm,
    ]
    async with httpx.AsyncClient(timeout=300.0) as client:
        start_index = 0
        if from_step:
            try:
                start_index = STEP_NAMES.index(from_step)
            except ValueError:
                logger.error(
                    f"Unknown step: {from_step}. Valid steps are: {', '.join(STEP_NAMES)}")
                return
        for func in STEP_FUNCTIONS[start_index:]:
            await func(client)
        logger.info("All synchronization steps completed successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bulk synchronization script.")
    parser.add_argument(
        "--from-step",
        type=str,
        choices=STEP_NAMES,
        help=f"Start execution from this step (skipping previous steps). Choices: {', '.join(STEP_NAMES)}"
    )
    args = parser.parse_args()
    asyncio.run(main(from_step=args.from_step))
