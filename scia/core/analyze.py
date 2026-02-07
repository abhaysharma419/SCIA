"""Schema change analysis and risk assessment."""
import logging
from typing import Dict, List, Optional

from scia.core.diff import diff_schemas
from scia.core.impact import analyze_downstream, analyze_upstream
from scia.core.risk import RiskAssessment
from scia.core.rules import apply_rules
from scia.models.finding import EnrichedFinding, ImpactDetail
from scia.models.schema import TableSchema
from scia.sql.heuristics import extract_signals
from scia.warehouse.base import WarehouseAdapter

logger = logging.getLogger(__name__)

async def analyze(
    before_schema: List[TableSchema],
    after_schema: List[TableSchema],
    sql_definitions: Optional[Dict[str, str]] = None,
    warehouse_adapter: Optional[WarehouseAdapter] = None,
    max_dependency_depth: int = 3,
    warnings: Optional[List[str]] = None
) -> RiskAssessment:
    """Core analysis orchestration with optional dependency enrichment.

    Args:
        before_schema: Initial schema definitions
        after_schema: Modified schema definitions
        sql_definitions: Optional SQL query definitions for signal extraction
        warehouse_adapter: Optional adapter for live impact analysis
        max_dependency_depth: Depth of downstream analysis
        warnings: Optional warnings list

    Returns:
        RiskAssessment with (potentially enriched) findings and classification
    """
    # 1. Diff schemas
    diff = diff_schemas(before_schema, after_schema)

    # 2. Extract SQL signals (if available)
    sql_signals = None
    if sql_definitions:
        sql_signals = extract_signals(sql_definitions)

    # 3. Apply rules
    findings = apply_rules(diff, sql_signals)

    # 4. Enrich findings with impact analysis (if adapter provided)
    final_findings = []
    if warehouse_adapter:
        for finding in findings:
            # If finding is linked to a table, analyze impact
            table_name = finding.evidence.get("table")
            # Also check for 'schema' to build fully qualified name if needed
            schema_name = finding.evidence.get("schema")

            if table_name:
                lookup_name = f"{schema_name}.{table_name}" if schema_name else table_name
                logger.debug("Found table %s in finding %s", lookup_name, finding.finding_type)

                downstream = await analyze_downstream(
                    lookup_name, warehouse_adapter, max_depth=max_dependency_depth
                )
                upstream = await analyze_upstream(lookup_name, warehouse_adapter)

                impact = ImpactDetail(
                    direct_dependents=downstream,
                    transitive_dependents=[],
                    upstream_dependencies=upstream,
                    affected_applications=[],
                    estimated_blast_radius=len(downstream)
                )

                # Adjust risk score based on blast radius
                # If no dependents found, reduce risk by 25% (as per user preference)
                adjusted_score = finding.risk_score
                if impact.estimated_blast_radius == 0 and finding.base_risk > 0:
                    adjusted_score = int(finding.risk_score * 0.75)

                enriched = EnrichedFinding(
                    **finding.model_dump(exclude={"risk_score"}),
                    risk_score=adjusted_score,
                    impact_detail=impact
                )
                final_findings.append(enriched)
            else:
                final_findings.append(finding)
    else:
        final_findings = findings

    # 5. Aggregate risk
    assessment = RiskAssessment(final_findings, warnings=warnings)

    return assessment
