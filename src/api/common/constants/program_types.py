"""
Program type constants and enums for service classification
"""

from enum import Enum


class ProgramType(str, Enum):
    """Program type enumeration"""
    FULL_STACK = "FS"
    DATA_SCIENCE = "DS"
    CYBERSECURITY = "CS"
    UNKNOWN = "UNKNOWN"


# Program type display names
PROGRAM_TYPE_NAMES = {
    ProgramType.FULL_STACK: "Full-Stack",
    ProgramType.DATA_SCIENCE: "Data Science",
    ProgramType.CYBERSECURITY: "Cybersecurity",
    ProgramType.UNKNOWN: "Unknown"
}

# Service name keywords for classification
SERVICE_KEYWORDS = {
    ProgramType.FULL_STACK: ["full-stack", "fullstack", " isa "],
    ProgramType.DATA_SCIENCE: ["data science", "ai/ml", "machine learning"],
    ProgramType.CYBERSECURITY: ["ciberseguridad", "cybersecurity"]
}

# Cohort slug patterns for classification
COHORT_PATTERNS = {
    ProgramType.FULL_STACK: ["-fs-", "fs-", "-fs"],
    ProgramType.DATA_SCIENCE: ["-ds-", "ds-", "-ds", "-ai-", "-ml-"],
    ProgramType.CYBERSECURITY: ["-cs-", "cs-", "-cs"]
}

# All valid program types
ALL_PROGRAM_TYPES = [
    ProgramType.FULL_STACK,
    ProgramType.DATA_SCIENCE,
    ProgramType.CYBERSECURITY,
    ProgramType.UNKNOWN
] 