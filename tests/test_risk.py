"""Tests for test_risk."""
from scia.core.risk import RiskAssessment

def test_risk_low(finding_factory):
    """Test function."""
    f = finding_factory(base_risk=10)
    ra = RiskAssessment(findings=[f])
    # 10 / (10 + 100) = 9%
    assert ra.classification == "LOW"
    assert ra.risk_score == 9

def test_risk_medium(finding_factory):
    """Test function."""
    f = finding_factory(base_risk=30)
    ra = RiskAssessment(findings=[f])
    # 30 / (130) = 23%
    assert ra.classification == "MEDIUM"
    assert ra.risk_score == 23

def test_risk_high(finding_factory):
    """Test function."""
    f = finding_factory(base_risk=80)
    ra = RiskAssessment(findings=[f])
    # 80 / 180 = 44%
    assert ra.classification == "HIGH"
    assert ra.risk_score == 44

def test_risk_boundaries(finding_factory):
    """Test function."""
    # Score 14 is LOW (threshold 15)
    # 16 / 116 = 13.8%
    ra_low = RiskAssessment(findings=[finding_factory(base_risk=16)])
    assert ra_low.classification == "LOW"

    # Score 15 is MEDIUM (threshold 15)
    # 18 / 118 = 15.2%
    ra_medium = RiskAssessment(findings=[finding_factory(base_risk=18)])
    assert ra_medium.classification == "MEDIUM"

    # Score 39 is MEDIUM (threshold 40)
    # 64 / 164 = 39%
    ra_medium2 = RiskAssessment(findings=[finding_factory(base_risk=64)])
    assert ra_medium2.classification == "MEDIUM"

    # Score 40 is HIGH (threshold 40)
    # 67 / 167 = 40.1%
    ra_high = RiskAssessment(findings=[finding_factory(base_risk=67)])
    assert ra_high.classification == "HIGH"

def test_risk_to_dict(finding_factory):
    """Test function."""
    f = finding_factory(base_risk=50)
    ra = RiskAssessment(findings=[f])
    data = ra.to_dict()
    assert data["risk_score"] == 33
    assert data["classification"] == "MEDIUM"
    assert len(data["findings"]) == 1
