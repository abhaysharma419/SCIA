from scia.core.risk import RiskAssessment

def test_risk_low(finding_factory):
    f = finding_factory(base_risk=20)
    ra = RiskAssessment(findings=[f])
    assert ra.classification == "LOW"
    assert ra.risk_score == 20

def test_risk_medium(finding_factory):
    f = finding_factory(base_risk=50)
    ra = RiskAssessment(findings=[f])
    assert ra.classification == "MEDIUM"
    assert ra.risk_score == 50

def test_risk_high(finding_factory):
    f = finding_factory(base_risk=80)
    ra = RiskAssessment(findings=[f])
    assert ra.classification == "HIGH"
    assert ra.risk_score == 80

def test_risk_boundaries(finding_factory):
    # Boundary case: 29 is LOW
    ra_low = RiskAssessment(findings=[finding_factory(base_risk=29)])
    assert ra_low.classification == "LOW"
    
    # Boundary case: 30 is MEDIUM
    ra_medium = RiskAssessment(findings=[finding_factory(base_risk=30)])
    assert ra_medium.classification == "MEDIUM"
    
    # Boundary case: 69 is MEDIUM
    ra_medium2 = RiskAssessment(findings=[finding_factory(base_risk=69)])
    assert ra_medium2.classification == "MEDIUM"
    
    # Boundary case: 70 is HIGH
    ra_high = RiskAssessment(findings=[finding_factory(base_risk=70)])
    assert ra_high.classification == "HIGH"

def test_risk_to_dict(finding_factory):
    f = finding_factory(base_risk=50)
    ra = RiskAssessment(findings=[f])
    data = ra.to_dict()
    assert data["risk_score"] == 50
    assert data["classification"] == "MEDIUM"
    assert len(data["findings"]) == 1
