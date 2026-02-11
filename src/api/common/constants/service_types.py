"""
Program type constants and enums for service classification
"""

from enum import Enum


class ServiceType(str, Enum):
    """Program type enumeration"""
    FULL_STACK = "FS"
    DATA_SCIENCE = "DS"
    CYBERSECURITY = "CS"
    AI_ENGINEERING = "AIE"
    UNKNOWN = "UNKNOWN"


# Program type display names
SERVICE_TYPE_NAMES = {
    ServiceType.FULL_STACK: "Full-Stack",
    ServiceType.DATA_SCIENCE: "Data Science",
    ServiceType.CYBERSECURITY: "Cybersecurity",
    ServiceType.AI_ENGINEERING: "AI Engineering",
    ServiceType.UNKNOWN: "Unknown"
}

# Service name keywords for classification
SERVICE_KEYWORDS = {
    ServiceType.FULL_STACK: ["full-stack", "fullstack", " isa "],
    ServiceType.DATA_SCIENCE: ["data science", "ai/ml", "machine learning"],
    ServiceType.CYBERSECURITY: ["ciberseguridad", "cybersecurity"],
    ServiceType.AI_ENGINEERING: [
        "ai engineering", "ai-engineering", "ai-eng", "ai-engineer", "ai engineer", "aie"]
}

# Cohort slug patterns for classification
SERVICE_PERIOD_PATTERNS = {
    ServiceType.FULL_STACK: ["-fs-", "fs-", "-fs", "madrid-ft"],
    ServiceType.DATA_SCIENCE: ["-ds-", "ds-", "-ds", "-ai-", "-ml-"],
    ServiceType.CYBERSECURITY: ["-cs-", "cs-", "-cs"],
    ServiceType.AI_ENGINEERING: ["-aie-", "aie-", "-aie"]
}

# All valid service types
ALL_SERVICE_TYPES = [
    ServiceType.FULL_STACK,
    ServiceType.DATA_SCIENCE,
    ServiceType.CYBERSECURITY,
    ServiceType.AI_ENGINEERING,
    ServiceType.UNKNOWN
]
