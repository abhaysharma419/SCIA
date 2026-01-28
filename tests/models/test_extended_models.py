"""Tests for extended data models."""
import pytest

from scia.models.finding import (
    DependencyObject,
    EnrichedFinding,
    Finding,
    FindingType,
    ImpactDetail,
    Severity,
)


def test_dependency_object_creation():
    """Test creating a DependencyObject."""
    dep = DependencyObject(
        object_type='VIEW',
        name='user_view',
        schema='ANALYTICS',
        is_critical=True
    )

    assert dep.object_type == 'VIEW'
    assert dep.name == 'user_view'
    assert dep.schema_name == 'ANALYTICS'
    assert dep.is_critical is True


def test_dependency_object_default_critical():
    """Test DependencyObject defaults is_critical to False."""
    dep = DependencyObject(
        object_type='VIEW',
        name='user_view',
        schema='ANALYTICS'
    )

    assert dep.is_critical is False


def test_dependency_object_serialization():
    """Test DependencyObject serializes to JSON."""
    dep = DependencyObject(
        object_type='VIEW',
        name='user_view',
        schema='ANALYTICS'
    )

    json_data = dep.model_dump()
    assert json_data['object_type'] == 'VIEW'
    assert json_data['name'] == 'user_view'


def test_impact_detail_empty():
    """Test creating empty ImpactDetail."""
    impact = ImpactDetail()

    assert impact.direct_dependents == []
    assert impact.transitive_dependents == []
    assert impact.affected_applications == []
    assert impact.estimated_blast_radius == 0


def test_impact_detail_with_dependents():
    """Test ImpactDetail with dependencies."""
    deps = [
        DependencyObject(object_type='VIEW', name='v1', schema='S1'),
        DependencyObject(object_type='TABLE', name='t1', schema='S1'),
    ]

    impact = ImpactDetail(
        direct_dependents=deps,
        affected_applications=['app1', 'app2'],
        estimated_blast_radius=2
    )

    assert len(impact.direct_dependents) == 2
    assert len(impact.affected_applications) == 2
    assert impact.estimated_blast_radius == 2


def test_impact_detail_serialization():
    """Test ImpactDetail serializes correctly."""
    impact = ImpactDetail(
        affected_applications=['app1'],
        estimated_blast_radius=1
    )

    json_data = impact.model_dump()
    assert json_data['affected_applications'] == ['app1']
    assert json_data['estimated_blast_radius'] == 1


def test_enriched_finding_without_impact():
    """Test EnrichedFinding without impact details."""
    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=80,
        evidence={'table': 'users', 'column': 'email'},
        description='Column removed'
    )

    assert finding.impact_detail is None
    assert finding.finding_type == FindingType.COLUMN_REMOVED


def test_enriched_finding_with_impact():
    """Test EnrichedFinding with impact details."""
    impact = ImpactDetail(
        direct_dependents=[
            DependencyObject(object_type='VIEW', name='v1', schema='S1')
        ],
        affected_applications=['app1'],
        estimated_blast_radius=1
    )

    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=80,
        evidence={'table': 'users', 'column': 'email'},
        description='Column removed',
        impact_detail=impact
    )

    assert finding.impact_detail is not None
    assert len(finding.impact_detail.direct_dependents) == 1


def test_enriched_finding_serialization():
    """Test EnrichedFinding serializes with impact details."""
    impact = ImpactDetail(
        affected_applications=['dashboard'],
        estimated_blast_radius=2
    )

    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_TYPE_CHANGED,
        severity=Severity.MEDIUM,
        base_risk=50,
        evidence={'table': 'orders', 'column': 'amount'},
        description='Type changed',
        impact_detail=impact
    )

    json_data = finding.model_dump()
    assert json_data['impact_detail'] is not None
    assert json_data['impact_detail']['estimated_blast_radius'] == 2


def test_enriched_finding_inherits_finding():
    """Test EnrichedFinding inherits from Finding."""
    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=80,
        evidence={'table': 'users'},
        description='Test'
    )

    assert isinstance(finding, Finding)
    assert finding.confidence == 1.0  # Default from Finding


def test_multiple_transitive_dependents():
    """Test ImpactDetail with transitive dependents."""
    direct = [
        DependencyObject(object_type='VIEW', name='v1', schema='S1')
    ]
    transitive = [
        DependencyObject(object_type='VIEW', name='v2', schema='S1'),
        DependencyObject(object_type='VIEW', name='v3', schema='S1'),
        DependencyObject(object_type='MATERIALIZED_VIEW', name='mv1', schema='S2'),
    ]

    impact = ImpactDetail(
        direct_dependents=direct,
        transitive_dependents=transitive,
        estimated_blast_radius=4
    )

    assert len(impact.direct_dependents) == 1
    assert len(impact.transitive_dependents) == 3
    assert impact.estimated_blast_radius == 4
