from enum import Enum
from pydantic import BaseModel
from typing import Dict, Any, Optional

class FindingType(str, Enum):
    COLUMN_REMOVED = "COLUMN_REMOVED"
    COLUMN_TYPE_CHANGED = "COLUMN_TYPE_CHANGED"
    COLUMN_NULLABILITY_CHANGED = "COLUMN_NULLABILITY_CHANGED"
    JOIN_KEY_CHANGED = "JOIN_KEY_CHANGED"
    GRAIN_CHANGE = "GRAIN_CHANGE"
    POTENTIAL_BREAKAGE = "POTENTIAL_BREAKAGE"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Finding(BaseModel):
    finding_type: FindingType
    severity: Severity
    base_risk: int
    evidence: Dict[str, Any]
    confidence: Optional[float] = 1.0
    description: str
