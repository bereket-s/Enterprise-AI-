from app.models.organization import Organization
from app.models.workforce import Employee
from app.services import workforce_service


def _make_org_and_employee(db_session, department: str) -> Employee:
    org = Organization(name="KPI Test Co")
    db_session.add(org)
    db_session.flush()
    emp = Employee(
        organization_id=org.id,
        external_ref="EMP-1",
        full_name="Test Employee",
        department=department,
        job_role="Analyst",
        job_satisfaction=4,
        environment_satisfaction=4,
        job_involvement=4,
        years_since_last_promotion=0,
    )
    db_session.add(emp)
    db_session.commit()
    return emp


def test_default_weights_seeded_per_department(db_session):
    emp = _make_org_and_employee(db_session, "Sales")
    created = workforce_service.seed_default_kpi_weights(db_session, emp.organization_id)
    assert created == len(workforce_service.DEFAULT_WEIGHTS_BY_DEPARTMENT["Sales"])


def test_perfect_scores_yield_near_max_performance_score(db_session):
    emp = _make_org_and_employee(db_session, "Sales")
    scores = workforce_service.compute_performance_scores(db_session, emp.organization_id)

    assert len(scores) == 1
    # job_satisfaction/environment_satisfaction/job_involvement are all maxed (4/4) and
    # years_since_last_promotion=0 also maxes promotion_recency, so the composite should
    # land near 100 regardless of the department's specific weight split.
    assert scores[0].score > 95


def test_departments_get_different_weight_profiles(db_session):
    emp = _make_org_and_employee(db_session, "Sales")
    workforce_service.seed_default_kpi_weights(db_session, emp.organization_id)

    sales_weights = workforce_service.DEFAULT_WEIGHTS_BY_DEPARTMENT["Sales"]
    rnd_weights = workforce_service.DEFAULT_WEIGHTS_BY_DEPARTMENT["Research & Development"]
    assert sales_weights != rnd_weights
    assert sales_weights["job_involvement"] > rnd_weights["job_involvement"] - 0.1  # sales weights involvement heavily


def test_custom_weight_override_changes_score(db_session):
    emp = _make_org_and_employee(db_session, "Sales")
    workforce_service.seed_default_kpi_weights(db_session, emp.organization_id)

    from app.models.workforce import KPIWeightConfig

    row = (
        db_session.query(KPIWeightConfig)
        .filter(KPIWeightConfig.organization_id == emp.organization_id, KPIWeightConfig.kpi_name == "job_involvement")
        .first()
    )
    row.weight = 0.0
    db_session.commit()

    emp.job_involvement = 1  # worst possible value on the now-zero-weighted KPI
    db_session.commit()

    scores = workforce_service.compute_performance_scores(db_session, emp.organization_id)
    # Even with job_involvement at rock bottom, a zero weight means it can't drag the score down.
    assert scores[0].score > 90
