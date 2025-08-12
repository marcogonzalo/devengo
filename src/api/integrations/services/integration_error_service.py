from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select, and_, or_
from sqlalchemy import func
from src.api.integrations.models.integration_error import IntegrationError
from src.api.integrations.schemas.integration_error import (
    IntegrationErrorCreate, 
    IntegrationErrorUpdate, 
    IntegrationErrorFilter,
    IntegrationErrorSummary
)
from src.api.common.utils.datetime import get_current_datetime


class IntegrationErrorService:
    """Service class for managing integration errors"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_error(self, error_data: IntegrationErrorCreate) -> IntegrationError:
        """
        Create a new integration error, ensuring uniqueness
        
        Args:
            error_data: Data for the new error
            
        Returns:
            IntegrationError: The created error or existing error if duplicate
        """
        # Check if error already exists for the same entity
        existing_error = self._find_existing_error(
            integration_name=error_data.integration_name,
            operation_type=error_data.operation_type,
            external_id=error_data.external_id,
            entity_type=error_data.entity_type,
            client_id=error_data.client_id,
            contract_id=error_data.contract_id
        )
        
        if existing_error:
            # Update existing error with new details if it's not resolved
            if not existing_error.is_resolved:
                existing_error.error_message = error_data.error_message
                existing_error.error_details = error_data.error_details
                existing_error.updated_at = get_current_datetime()
                self.db.commit()
                self.db.refresh(existing_error)
            return existing_error
        
        # Create new error
        error = IntegrationError(**error_data.model_dump())
        self.db.add(error)
        self.db.commit()
        self.db.refresh(error)
        return error

    def get_error(self, error_id: int) -> Optional[IntegrationError]:
        """Get an integration error by ID"""
        return self.db.get(IntegrationError, error_id)

    def get_errors(self, filters: IntegrationErrorFilter) -> dict:
        """
        Get integration errors with filtering and pagination
        
        Args:
            filters: Filter criteria and pagination
            
        Returns:
            dict: Dictionary containing 'errors' list and 'total' count
        """
        # Build base query for counting
        count_query = select(func.count(IntegrationError.id))
        
        # Build base query for data
        data_query = select(IntegrationError)
        
        # Apply filters
        conditions = []
        
        if filters.integration_name:
            conditions.append(IntegrationError.integration_name == filters.integration_name)
        
        if filters.operation_type:
            conditions.append(IntegrationError.operation_type == filters.operation_type)
        
        if filters.entity_type:
            conditions.append(IntegrationError.entity_type == filters.entity_type)
        
        if filters.is_resolved is not None:
            conditions.append(IntegrationError.is_resolved == filters.is_resolved)
        
        if filters.is_ignored is not None:
            conditions.append(IntegrationError.is_ignored == filters.is_ignored)
        
        if filters.client_id:
            conditions.append(IntegrationError.client_id == filters.client_id)
        
        if filters.contract_id:
            conditions.append(IntegrationError.contract_id == filters.contract_id)
        
        if conditions:
            count_query = count_query.where(and_(*conditions))
            data_query = data_query.where(and_(*conditions))
        
        # Get total count
        total = self.db.exec(count_query).first()
        
        # Order by creation date (newest first)
        data_query = data_query.order_by(IntegrationError.created_at.desc())
        
        # Apply pagination
        data_query = data_query.offset(filters.offset).limit(filters.limit)
        
        # Get paginated data
        errors = self.db.exec(data_query).all()
        
        return {
            "errors": errors,
            "total": total or 0
        }

    def update_error(self, error_id: int, update_data: IntegrationErrorUpdate) -> Optional[IntegrationError]:
        """
        Update an integration error
        
        Args:
            error_id: ID of the error to update
            update_data: Data to update
            
        Returns:
            IntegrationError: Updated error or None if not found
        """
        error = self.get_error(error_id)
        if not error:
            return None
        
        # Store original values before updating
        was_resolved = error.is_resolved
        was_ignored = error.is_ignored
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(error, field, value)
        
        # Set resolved_at timestamp if resolving
        if update_data.is_resolved is True and not was_resolved:
            error.resolved_at = get_current_datetime().isoformat()
        
        # Set ignored_at timestamp if ignoring
        if update_data.is_ignored is True and not was_ignored:
            error.ignored_at = get_current_datetime().isoformat()
        
        error.updated_at = get_current_datetime()
        
        self.db.commit()
        self.db.refresh(error)
        return error

    def delete_error(self, error_id: int) -> bool:
        """
        Delete an integration error
        
        Args:
            error_id: ID of the error to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        error = self.get_error(error_id)
        if not error:
            return False
        
        self.db.delete(error)
        self.db.commit()
        return True

    def resolve_error(self, error_id: int, resolution_notes: Optional[str] = None) -> Optional[IntegrationError]:
        """
        Mark an error as resolved
        
        Args:
            error_id: ID of the error to resolve
            resolution_notes: Optional notes about the resolution
            
        Returns:
            IntegrationError: Resolved error or None if not found
        """
        update_data = IntegrationErrorUpdate(
            is_resolved=True,
            resolution_notes=resolution_notes
        )
        return self.update_error(error_id, update_data)

    def ignore_error(self, error_id: int, ignore_notes: Optional[str] = None) -> Optional[IntegrationError]:
        """
        Mark an error as ignored
        
        Args:
            error_id: ID of the error to ignore
            ignore_notes: Optional notes about why it was ignored
            
        Returns:
            IntegrationError: Ignored error or None if not found
        """
        update_data = IntegrationErrorUpdate(
            is_ignored=True,
            ignore_notes=ignore_notes
        )
        return self.update_error(error_id, update_data)

    def get_summary(self) -> IntegrationErrorSummary:
        """
        Get summary statistics for integration errors
        
        Returns:
            IntegrationErrorSummary: Summary statistics
        """
        # Total counts
        total_errors = self.db.exec(select(func.count(IntegrationError.id))).first() or 0
        resolved_errors = self.db.exec(
            select(func.count(IntegrationError.id)).where(IntegrationError.is_resolved == True)
        ).first() or 0
        ignored_errors = self.db.exec(
            select(func.count(IntegrationError.id)).where(IntegrationError.is_ignored == True)
        ).first() or 0
        unresolved_errors = total_errors - resolved_errors - ignored_errors
        
        # Counts by integration
        integration_counts = self.db.exec(
            select(IntegrationError.integration_name, func.count(IntegrationError.id))
            .group_by(IntegrationError.integration_name)
        ).all()
        errors_by_integration = {row[0]: row[1] for row in integration_counts}
        
        # Counts by operation type
        operation_counts = self.db.exec(
            select(IntegrationError.operation_type, func.count(IntegrationError.id))
            .group_by(IntegrationError.operation_type)
        ).all()
        errors_by_operation = {row[0]: row[1] for row in operation_counts}
        
        # Counts by entity type
        entity_counts = self.db.exec(
            select(IntegrationError.entity_type, func.count(IntegrationError.id))
            .group_by(IntegrationError.entity_type)
        ).all()
        errors_by_entity_type = {row[0]: row[1] for row in entity_counts}
        
        return IntegrationErrorSummary(
            total_errors=total_errors,
            resolved_errors=resolved_errors,
            unresolved_errors=unresolved_errors,
            ignored_errors=ignored_errors,
            errors_by_integration=errors_by_integration,
            errors_by_operation=errors_by_operation,
            errors_by_entity_type=errors_by_entity_type
        )

    def _find_existing_error(
        self,
        integration_name: str,
        operation_type: str,
        external_id: str,
        entity_type: str,
        client_id: Optional[int] = None,
        contract_id: Optional[int] = None
    ) -> Optional[IntegrationError]:
        """
        Find an existing error for the same entity to prevent duplicates
        
        Args:
            integration_name: Name of the integration
            operation_type: Type of operation
            external_id: External ID from the integration
            entity_type: Type of entity
            client_id: Related client ID
            contract_id: Related contract ID
            
        Returns:
            IntegrationError: Existing error if found, None otherwise
        """
        conditions = [
            IntegrationError.integration_name == integration_name,
            IntegrationError.operation_type == operation_type,
            IntegrationError.external_id == external_id,
            IntegrationError.entity_type == entity_type
        ]
        
        # Add optional conditions
        if client_id is not None:
            conditions.append(IntegrationError.client_id == client_id)
        if contract_id is not None:
            conditions.append(IntegrationError.contract_id == contract_id)
        
        query = select(IntegrationError).where(and_(*conditions))
        return self.db.exec(query).first()

    def bulk_resolve_errors(
        self, 
        error_ids: List[int], 
        resolution_notes: Optional[str] = None
    ) -> int:
        """
        Bulk resolve multiple errors
        
        Args:
            error_ids: List of error IDs to resolve
            resolution_notes: Optional notes about the resolution
            
        Returns:
            int: Number of errors successfully resolved
        """
        resolved_count = 0
        current_time = get_current_datetime().isoformat()
        
        for error_id in error_ids:
            error = self.get_error(error_id)
            if error and not error.is_resolved:
                error.is_resolved = True
                error.resolved_at = current_time
                error.resolution_notes = resolution_notes
                error.updated_at = get_current_datetime()
                resolved_count += 1
        
        self.db.commit()
        return resolved_count

    def bulk_ignore_errors(
        self, 
        error_ids: List[int], 
        ignore_notes: Optional[str] = None
    ) -> int:
        """
        Bulk ignore multiple errors
        
        Args:
            error_ids: List of error IDs to ignore
            ignore_notes: Optional notes about why they were ignored
            
        Returns:
            int: Number of errors successfully ignored
        """
        ignored_count = 0
        current_time = get_current_datetime().isoformat()
        
        for error_id in error_ids:
            error = self.get_error(error_id)
            if error and not error.is_ignored:
                error.is_ignored = True
                error.ignored_at = current_time
                error.ignore_notes = ignore_notes
                error.updated_at = get_current_datetime()
                ignored_count += 1
        
        self.db.commit()
        return ignored_count
