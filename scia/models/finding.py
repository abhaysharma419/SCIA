"""Risk finding models and classifications."""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

class FindingType(str, Enum):
    """Types of schema change findings."""

    COLUMN_REMOVED = "COLUMN_REMOVED"
    COLUMN_TYPE_CHANGED = "COLUMN_TYPE_CHANGED"
    COLUMN_NULLABILITY_CHANGED = "COLUMN_NULLABILITY_CHANGED"
    JOIN_KEY_CHANGED = "JOIN_KEY_CHANGED"
    GRAIN_CHANGE = "GRAIN_CHANGE"
    POTENTIAL_BREAKAGE = "POTENTIAL_BREAKAGE"

class Severity(str, Enum):
    """Severity levels for findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Finding(BaseModel):
    """Represents a single risk finding from schema analysis."""

    finding_type: FindingType
    severity: Severity
    base_risk: int
    evidence: Dict[str, Any]
    confidence: Optional[float] = 1.0
    description: str
