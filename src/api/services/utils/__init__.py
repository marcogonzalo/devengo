"""
Utility functions for service-related operations
"""

from src.api.common.constants.program_types import (
    ProgramType,
    PROGRAM_TYPE_NAMES,
    SERVICE_KEYWORDS,
    COHORT_PATTERNS
)


def get_program_type_from_service_name(service_name: str) -> str:
    """
    Extract program type from service name
    
    Args:
        service_name: The service name to analyze
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not service_name:
        return ProgramType.UNKNOWN
    
    name_lower = service_name.lower()
    
    for program_type, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in name_lower for keyword in keywords):
            return program_type
    
    return ProgramType.UNKNOWN


def get_program_type_from_cohort_slug(cohort_slug: str) -> str:
    """
    Extract program type from cohort slug
    
    Args:
        cohort_slug: The cohort slug (e.g., "spain-fs-pt-85", "spain-ds-pt-45")
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not cohort_slug:
        return ProgramType.UNKNOWN
    
    slug_lower = cohort_slug.lower()
    
    for program_type, patterns in COHORT_PATTERNS.items():
        if any(pattern in slug_lower for pattern in patterns):
            return program_type
        
    return ProgramType.UNKNOWN


def validate_cohort_service_compatibility(cohort_slug: str, service_program_type: str) -> bool:
    """
    Validate that a cohort slug matches the service program type
    
    Args:
        cohort_slug: The cohort slug to validate
        service_program_type: The service program type (FS, DS, CS)
        
    Returns:
        True if compatible, False otherwise
    """
    cohort_program_type = get_program_type_from_cohort_slug(cohort_slug)
    return cohort_program_type == service_program_type


def get_program_type_display_name(program_type: str) -> str:
    """
    Get the display name for a program type
    
    Args:
        program_type: The program type code (FS, DS, CS)
        
    Returns:
        Display name for the program type
    """
    return PROGRAM_TYPE_NAMES.get(program_type, "Unknown")


def classify_program_type(text: str, source_type: str = "auto") -> str:
    """
    Classify program type from any text source
    
    Args:
        text: The text to classify (service name, cohort slug, etc.)
        source_type: "service", "cohort", or "auto" for automatic detection
        
    Returns:
        Program type: "FS", "DS", "CS", or "UNKNOWN"
    """
    if not text:
        return ProgramType.UNKNOWN
    
    if source_type == "service":
        return get_program_type_from_service_name(text)
    elif source_type == "cohort":
        return get_program_type_from_cohort_slug(text)
    else:
        # Try both approaches and return the first match
        service_result = get_program_type_from_service_name(text)
        if service_result != ProgramType.UNKNOWN:
            return service_result
        
        cohort_result = get_program_type_from_cohort_slug(text)
        return cohort_result 