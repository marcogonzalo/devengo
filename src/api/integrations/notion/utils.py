"""
Notion integration utilities for educational status validation and processing.

This module contains business logic specific to Notion educational statuses
and their mapping to contract processing outcomes.
"""
from typing import Optional, Dict
from datetime import date
from fastapi.logger import logger


def is_educational_status_ended(status: str) -> bool:
    """
    Check if educational status represents successful completion or formal ending.
    
    Args:
        status: Educational status from Notion
        
    Returns:
        True if status indicates successful completion (GRADUATED, NOT_COMPLETING, ENDED)
    """
    ended_statuses = ['GRADUATED', 'NOT_COMPLETING', 'ENDED']
    return status in ended_statuses


def is_educational_status_dropped(status: str) -> bool:
    """
    Check if educational status represents a dropout or suspension scenario.
    
    Args:
        status: Educational status from Notion
        
    Returns:
        True if status indicates dropout or suspension (DROPPED, EARLY_DROPPED, SUSPENDED)
    """
    dropped_suspended_statuses = ['DROPPED', 'EARLY_DROPPED', 'SUSPENDED']
    return status in dropped_suspended_statuses


def categorize_educational_status(status: str) -> str:
    """
    Categorize educational status for contract accrual processing.
    
    Args:
        status: Educational status from Notion
        
    Returns:
        Category string: 'ended', 'dropped', or 'active'
    """
    if is_educational_status_ended(status):
        return 'ended'
    elif is_educational_status_dropped(status):
        return 'dropped'
    else:
        return 'active'


async def get_client_educational_data(client) -> Optional[Dict]:
    """
    Check if client exists in Notion and return educational data.
    
    Args:
        client: Client object with identifier and external_id methods
        
    Returns:
        Dictionary with educational_status and status_change_date, or None if not found
    """
    from .config import NotionConfig
    from .client import NotionClient

    notion_config = NotionConfig()
    notion_client = NotionClient(notion_config)
    try:
        page = await notion_client.get_page_content(client.get_external_id('notion'))
    except Exception as e:
        page = None

    if not page:
        try:
            page = await notion_client.get_page_by_email(
                database_id=notion_config.database_id, 
                property_name="Email", 
                value=client.identifier
            )
        except Exception as e:
            print('get_client_educational_data_error', e)
            logger.warning(f"Failed to check client {client.id} in Notion: {str(e)}")
            return None

    if not page:
        return None

    # Parse Notion page properties
    properties = page.get('properties', {})
    
    # Extract educational status
    educational_status = properties.get('Educational Status')
    if educational_status and educational_status.get("select"):
        educational_status = educational_status.get("select", {}).get("name")
        educational_status = "_".join(educational_status.upper().split())
    # Extract status change date ('Drop Date' or 'Certificated At')
    # 'Drop Date ' must remain with a space at the end because its the right label
    status_change_date = properties.get('Drop Date ')
    if not (status_change_date and status_change_date.get("date")):
        status_change_date = properties.get('Certificated At')
    if status_change_date and status_change_date.get("date"):
        status_change_date = status_change_date.get("date", {}).get("start")
        # Convert string to date if needed
        if isinstance(status_change_date, str):
            try:
                status_change_date = date.fromisoformat(status_change_date)
            except (ValueError, TypeError):
                status_change_date = None

    return {
        'educational_status': educational_status,
        'status_change_date': status_change_date
    } 