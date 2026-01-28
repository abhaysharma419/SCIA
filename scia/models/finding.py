"""Risk finding models and classifications."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

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


class DependencyObject(BaseModel):
    """Represents a database object that depends on a changed schema element."""

    object_type: str  # VIEW, MATERIALIZED_VIEW, FUNCTION, PROCEDURE, TABLE
    name: str
    schema_name: str = Field(alias="schema")
    is_critical: bool = False

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "object_type": "VIEW",
                "name": "user_analytics_view",
                "schema": "ANALYTICS",
                "is_critical": True
            }
        }
    )


class ImpactDetail(BaseModel):
    """Details about downstream and upstream impact of a schema change."""

    direct_dependents: List[DependencyObject] = []
    transitive_dependents: List[DependencyObject] = []
    affected_applications: List[str] = []
    estimated_blast_radius: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "direct_dependents": [
                    {
                        "object_type": "VIEW",
                        "name": "user_view",
                        "schema": "ANALYTICS",
                        "is_critical": True
                    }
                ],
                "transitive_dependents": [],
                "affected_applications": ["dashboard", "reporting-service"],
                "estimated_blast_radius": 3
            }
        }
    )


class EnrichedFinding(Finding):
    """Extended finding with optional dependency impact details."""

    impact_detail: Optional[ImpactDetail] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "finding_type": "COLUMN_REMOVED",
                "severity": "HIGH",
                "base_risk": 80,
                "evidence": {"table": "users", "column": "email"},
                "confidence": 1.0,
                "description": "Column 'email' removed from 'users' table",
                "impact_detail": {
                    "direct_dependents": [
                        {
                            "object_type": "VIEW",
                            "name": "user_view",
                            "schema": "ANALYTICS"
                        }
                    ],
                    "affected_applications": ["auth-service"],
                    "estimated_blast_radius": 2
                }
            }
        }
    )
