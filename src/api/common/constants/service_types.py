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
    AI_FLEX = "AI-FLEX"
    UNKNOWN = "UNKNOWN"


# Program type display names
SERVICE_TYPE_NAMES = {
    ServiceType.FULL_STACK: "Full-Stack",
    ServiceType.DATA_SCIENCE: "Data Science",
    ServiceType.CYBERSECURITY: "Cybersecurity",
    ServiceType.AI_ENGINEERING: "AI Engineering",
    ServiceType.AI_FLEX: "AI Flex",
    ServiceType.UNKNOWN: "Unknown"
}

# Service name keywords for classification
# Order matters: first match wins.
SERVICE_KEYWORDS = {
    ServiceType.FULL_STACK: ["full-stack", "fullstack", " isa "],
    ServiceType.DATA_SCIENCE: ["data science", "ai/ml", "machine learning"],
    ServiceType.CYBERSECURITY: ["ciberseguridad", "cybersecurity"],
    ServiceType.AI_ENGINEERING: [
        "ai engineering", "ai-engineering", "ai-eng", "ai-engineer", "ai engineer", "aie"],
    ServiceType.AI_FLEX: ["ai flex", "ai-flex"],
}

# Cohort slug patterns for classification
# Order matters: first match wins. Keep AI_FLEX before DATA_SCIENCE so
# "-ai-flex-" is not swallowed by DATA_SCIENCE's "-ai-" pattern.
SERVICE_PERIOD_PATTERNS = {
    ServiceType.FULL_STACK: ["-fs-", "fs-", "-fs", "madrid-ft"],
    ServiceType.AI_FLEX: ["-ai-flex-", "-aiflex-", "-ai-flex", "ai-flex-"],
    ServiceType.DATA_SCIENCE: ["-ds-", "ds-", "-ds", "-ai-", "-ml-"],
    ServiceType.CYBERSECURITY: ["-cs-", "cs-", "-cs"],
    ServiceType.AI_ENGINEERING: ["-aie-", "aie-", "-aie"],
}

# All valid service types
ALL_SERVICE_TYPES = [
    ServiceType.FULL_STACK,
    ServiceType.DATA_SCIENCE,
    ServiceType.CYBERSECURITY,
    ServiceType.AI_ENGINEERING,
    ServiceType.AI_FLEX,
    ServiceType.UNKNOWN
]
