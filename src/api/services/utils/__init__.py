"""
Utility functions for service-related operations
"""

from src.api.common.constants.service_types import (
    ServiceType,
    SERVICE_TYPE_NAMES,
    SERVICE_KEYWORDS,
    SERVICE_PERIOD_PATTERNS
)


def get_service_type_from_service_name(service_name: str) -> str:
    """
    Extract program type from service name
    
    Args:
        service_name: The service name to analyze
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not service_name:
        return ServiceType.UNKNOWN
    
    name_lower = service_name.lower()
    
    for service_type, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in name_lower for keyword in keywords):
            return service_type
    
    return ServiceType.UNKNOWN


def get_service_type_from_service_period_name(service_period_name: str) -> str:
    """
    Extract program type from cohort slug
    
    Args:
        service_period_name: The service period name (e.g., "spain-fs-pt-85", "spain-ds-pt-45")
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not service_period_name:
        return ServiceType.UNKNOWN
    
    slug_lower = service_period_name.lower()
    
    for service_type, patterns in SERVICE_PERIOD_PATTERNS.items():
        if any(pattern in slug_lower for pattern in patterns):
            return service_type
        
    return ServiceType.UNKNOWN


def validate_service_period_compatibility(service_period_name: str, service_service_type: str) -> bool:
    """
    Validate that a cohort slug matches the service type
    
    Args:
        service_name: The cohort slug to validate
        service_service_type: The service program type (FS, DS, CS)
        
    Returns:
        True if compatible, False otherwise
    """
    cohort_service_type = get_service_type_from_service_period_name(service_period_name)
    return cohort_service_type == service_service_type


def get_service_type_display_name(service_type: str) -> str:
    """
    Get the display name for a program type
    
    Args:
        service_type: The program type code (FS, DS, CS)
        
    Returns:
        Display name for the program type
    """
    return SERVICE_TYPE_NAMES.get(service_type, "Unknown")


def classify_service_type(text: str, source_type: str = "auto") -> str:
    """
    Classify program type from any text source
    
    Args:
        text: The text to classify (service name, cohort slug, etc.)
        source_type: "service", "cohort", or "auto" for automatic detection
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not text:
        return ServiceType.UNKNOWN
    
    if source_type == "service":
        return get_service_type_from_service_name(text)
    elif source_type == "cohort":
        return get_service_type_from_service_period_name(text)
    else:
        # Try both approaches and return the first match
        service_result = get_service_type_from_service_name(text)
        if service_result != ServiceType.UNKNOWN:
            return service_result
        
        cohort_result = get_service_type_from_service_period_name(text)
        return cohort_result 