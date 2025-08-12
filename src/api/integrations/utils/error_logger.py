from typing import Optional, Dict, Any
from sqlmodel import Session
from src.api.integrations.services.integration_error_service import IntegrationErrorService
from src.api.integrations.schemas.integration_error import IntegrationErrorCreate
from src.api.common.utils.database import get_db


def log_integration_error(
    integration_name: str,
    operation_type: str,
    external_id: str,
    entity_type: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None,
    client_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    db: Optional[Session] = None
) -> None:
    """
    Log an integration error to the database
    
    Args:
        integration_name: Name of the integration (e.g., 'fourgeeks', 'holded', 'notion')
        operation_type: Type of operation that failed (e.g., 'enrollment', 'invoice', 'client')
        external_id: External ID from the integration system
        entity_type: Type of entity (e.g., 'cohort', 'invoice', 'client')
        error_message: Human-readable error message
        error_details: Additional error details as JSON
        client_id: Related client ID (optional)
        contract_id: Related contract ID (optional)
        db: Database session (optional, will create one if not provided)
    """
    try:
        # Create database session if not provided
        if db is None:
            db = next(get_db())
        
        # Create error service
        error_service = IntegrationErrorService(db)
        
        # Create error data
        error_data = IntegrationErrorCreate(
            integration_name=integration_name,
            operation_type=operation_type,
            external_id=external_id,
            entity_type=entity_type,
            error_message=error_message,
            error_details=error_details or {},
            client_id=client_id,
            contract_id=contract_id
        )
        
        # Log the error (this will create or update existing error)
        error_service.create_error(error_data)
        
    except Exception as e:
        # If we can't log the error, at least print it to console
        print(f"Failed to log integration error: {e}")
        print(f"Original error: {error_message}")
        print(f"Integration: {integration_name}, Operation: {operation_type}, Entity: {entity_type}, External ID: {external_id}")
