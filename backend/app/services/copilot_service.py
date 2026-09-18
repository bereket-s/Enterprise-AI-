"""AI Copilot: natural-language Q&A over an org's already-computed metrics.

Default behaviour is fully deterministic (intent keyword-matching + a template
engine over real query results) so the platform works with zero external
dependencies or API keys. If settings.llm_api_key is set, the same retrieved
facts are handed to an LLM to phrase a richer answer instead of the template —
the facts themselves always come from the database, never from the LLM, so the
copilot cannot hallucinate numbers that aren't in the org's own data.

Intent classification is a scored keyword match (not "first keyword found wins"):
every intent's keyword list is checked, matches are counted, and the
highest-scoring intent wins — so a question that happens to mention two
domains ("fraud in inventory") resolves to whichever domain it engages more
strongly, rather than whichever intent happens to be listed first in the dict.
A low-confidence match still returns an answer but flags the uncertainty and
suggests the closest known example question, instead of silently guessing.
"""
from __future__ import annotations

import difflib

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.bi import ForecastResult, Product, SalesTransaction
from app.models.copilot import ChatLog
from app.models.fraud import FraudTransaction
from app.models.inventory import ReorderRecommendation
from app.models.maintenance import Equipment
from app.models.workforce import Employee, Goal, PerformanceScore
from app.services import bi_service

settings = get_settings()

INTENT_KEYWORDS: dict[str, list[str]] = {
    "revenue_trend": [
        "revenue", "sales decline", "sales drop", "why did sales", "performance decrease",
        "performance decline", "how are sales", "sales trend", "growth",
    ],
    "top_products": ["top product", "best seller", "best-selling", "best performing product", "most sold"],
    "stockout_risk": [
        "run out", "stockout", "reorder", "inventory", "purchase next", "restock", "low stock",
    ],
    "fraud_risk": [
        "fraud", "risk transaction", "suspicious", "highest-risk transaction", "anomaly", "scam",
    ],
    "equipment_risk": [
        "machine", "equipment", "inspect", "maintenance", "breakdown", "failure risk", "sensor",
    ],
    "department_attention": [
        "department needs attention", "which department", "underperform", "department performance",
        "worst department", "best department",
    ],
    "forecast_outlook": [
        "forecast", "predict revenue", "next week", "next month", "outlook", "projection", "expected revenue",
    ],
    "goal_progress": [
        "goal", "target", "on track", "progress toward", "kpi progress",
    ],
}

# One representative example question per intent, used both as frontend suggestion
# chips and as "did you mean" hints when a question scores too low to answer confidently.
EXAMPLE_QUESTIONS: dict[str, str] = {
    "revenue_trend": "Why did our revenue decline?",
    "top_products": "What are our top products?",
    "stockout_risk": "Which products are most likely to run out?",
    "fraud_risk": "Show me the highest-risk transactions",
    "equipment_risk": "Which machines should we inspect first?",
    "department_attention": "Which department needs attention?",
    "forecast_outlook": "What is our revenue forecast for next month?",
    "goal_progress": "Are we on track to hit our goals?",
}

MIN_CONFIDENT_SCORE = 1  # at least one real keyword hit required to commit to an intent
LOW_CONFIDENCE_SIMILARITY_CUTOFF = 0.55


def classify_intent(question: str) -> tuple[str, int]:
    """Returns (intent, score). intent is 'unknown' when no keyword matched at all."""
    q = question.lower()
    scores = {intent: sum(1 for kw in keywords if kw in q) for intent, keywords in INTENT_KEYWORDS.items()}
    best_intent, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < MIN_CONFIDENT_SCORE:
        return "unknown", 0
    return best_intent, best_score


def _closest_example_question(question: str) -> str | None:
    """Fuzzy fallback for typos/paraphrases that share no exact keyword substring,
    e.g. 'wich prducts will run out' still suggests the stockout example question."""
    candidates = list(EXAMPLE_QUESTIONS.values())
    matches = difflib.get_close_matches(question, candidates, n=1, cutoff=LOW_CONFIDENCE_SIMILARITY_CUTOFF)
    return matches[0] if matches else None


def _handle_revenue_trend(db: Session, org_id: int) -> tuple[str, dict]:
    kpis = bi_service.compute_kpis(db, org_id)
    if kpis["days_of_history"] == 0:
        return "No sales data has been ingested yet for this organization.", kpis
    direction = "increased" if kpis["trend_pct"] >= 0 else "declined"
    top = kpis["top_products"][:3]
    top_txt = ", ".join(f"{p['name']} (${p['revenue']:,.0f})" for p in top) if top else "no ranked products yet"
    answer = (
        f"Revenue has {direction} {abs(kpis['trend_pct'])}% comparing the first and second half of the "
        f"available history (total revenue ${kpis['total_revenue']:,.0f} over {kpis['days_of_history']} days). "
        f"Top contributors: {top_txt}."
    )
    return answer, kpis


def _handle_top_products(db: Session, org_id: int) -> tuple[str, dict]:
    kpis = bi_service.compute_kpis(db, org_id)
    top = kpis["top_products"][:5]
    if not top:
        return "No product sales data is available yet.", {}
    lines = "; ".join(f"{i+1}. {p['name']} - ${p['revenue']:,.0f}" for i, p in enumerate(top))
    return f"Top products by revenue: {lines}.", {"top_products": top}


def _handle_stockout_risk(db: Session, org_id: int) -> tuple[str, dict]:
    rows = (
        db.query(ReorderRecommendation, Product)
        .join(Product, Product.id == ReorderRecommendation.product_id)
        .filter(ReorderRecommendation.organization_id == org_id)
        .order_by(ReorderRecommendation.stockout_probability.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return "No inventory analysis has been run yet. Run the reorder analysis first.", {}
    lines = "; ".join(
        f"{p.name} (stock {r.current_stock}, {r.stockout_probability:.0%} stockout risk, "
        f"recommended order {r.recommended_order_qty:.0f})"
        for r, p in rows
    )
    return f"Highest stockout-risk products: {lines}.", {"count": len(rows)}


def _handle_fraud_risk(db: Session, org_id: int) -> tuple[str, dict]:
    rows = (
        db.query(FraudTransaction)
        .filter(FraudTransaction.organization_id == org_id)
        .order_by(FraudTransaction.risk_score.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return "No fraud model has scored any transactions yet.", {}
    lines = "; ".join(
        f"{t.external_ref} (${t.amount:,.2f}, risk {t.risk_score:.0%}: {t.reason_codes[0]})" for t in rows
    )
    return f"Highest-risk transactions: {lines}.", {"count": len(rows)}


def _handle_equipment_risk(db: Session, org_id: int) -> tuple[str, dict]:
    rows = (
        db.query(Equipment)
        .filter(Equipment.organization_id == org_id)
        .order_by(Equipment.failure_risk_score.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return "No maintenance model has scored any equipment yet.", {}
    lines = "; ".join(
        f"{e.external_ref} ({e.failure_risk_score:.0%} failure risk: {e.contributing_factors[0]})" for e in rows
    )
    return f"Equipment to inspect first: {lines}.", {"count": len(rows)}


def _handle_department_attention(db: Session, org_id: int) -> tuple[str, dict]:
    rows = (
        db.query(Employee.department, func.avg(PerformanceScore.score), func.count(PerformanceScore.id))
        .join(PerformanceScore, PerformanceScore.employee_id == Employee.id)
        .filter(Employee.organization_id == org_id)
        .group_by(Employee.department)
        .all()
    )
    if not rows:
        return "No performance scores have been computed yet. Run performance scoring first.", {}
    ranked = sorted(rows, key=lambda r: r[1])
    dept, avg_score, n = ranked[0]
    return (
        f"{dept} has the lowest average performance score ({avg_score:.1f}/100 across {n} employees) "
        f"and is the department most likely to need attention.",
        {"by_department": [{"department": d, "avg_score": round(a, 1), "employees": n} for d, a, n in ranked]},
    )


def _handle_forecast_outlook(db: Session, org_id: int) -> tuple[str, dict]:
    result = (
        db.query(ForecastResult)
        .filter(ForecastResult.organization_id == org_id, ForecastResult.scope == "company")
        .order_by(ForecastResult.generated_at.desc())
        .first()
    )
    if result is None:
        return "No forecast has been run yet. Run the BI forecast first.", {}
    future_points = [p for p in result.forecast_points if "actual" not in p or p.get("actual") is None]
    if not future_points:
        future_points = result.forecast_points[-result.horizon_days :]
    total_forecast = sum(p["predicted"] for p in future_points)
    avg_forecast = total_forecast / len(future_points) if future_points else 0
    return (
        f"Over the next {result.horizon_days} days, forecast revenue totals ${total_forecast:,.0f} "
        f"(avg ${avg_forecast:,.0f}/day), from a {result.model_name} model with a historical MAE of "
        f"${result.mae:,.0f} (MAPE {result.mape}%).",
        {"horizon_days": result.horizon_days, "total_forecast": round(total_forecast, 2)},
    )


def _handle_goal_progress(db: Session, org_id: int) -> tuple[str, dict]:
    goals = db.query(Goal).filter(Goal.organization_id == org_id).all()
    if not goals:
        return "No goals have been set yet for this organization.", {}
    on_track = [g for g in goals if g.progress_pct >= 75]
    behind = [g for g in goals if g.progress_pct < 50]
    lines = "; ".join(f"{g.title} ({g.progress_pct:.0f}% of target)" for g in goals[:5])
    return (
        f"{len(on_track)} of {len(goals)} goals are on track (>=75% of target); {len(behind)} are "
        f"behind (<50%). Current goals: {lines}.",
        {"total_goals": len(goals), "on_track": len(on_track), "behind": len(behind)},
    )


HANDLERS = {
    "revenue_trend": _handle_revenue_trend,
    "top_products": _handle_top_products,
    "stockout_risk": _handle_stockout_risk,
    "fraud_risk": _handle_fraud_risk,
    "equipment_risk": _handle_equipment_risk,
    "department_attention": _handle_department_attention,
    "forecast_outlook": _handle_forecast_outlook,
    "goal_progress": _handle_goal_progress,
}

GENERIC_FALLBACK = (
    "I can currently answer questions about: revenue/sales trends, top products, stockout risk, "
    "high-risk fraud transactions, equipment needing inspection, revenue forecasts, goal progress, "
    "and which department needs attention. Try asking one of those."
)


def ask(db: Session, org_id: int, user_id: int, question: str) -> ChatLog:
    intent, score = classify_intent(question)
    handler = HANDLERS.get(intent)
    if handler is None:
        suggestion = _closest_example_question(question)
        answer_text = (
            f'I\'m not confident I understood that. Did you mean: "{suggestion}"? Otherwise, {GENERIC_FALLBACK.lower()}'
            if suggestion
            else GENERIC_FALLBACK
        )
        source_data: dict = {"suggested_question": suggestion} if suggestion else {}
    else:
        answer_text, source_data = handler(db, org_id)
        if source_data:
            # Optional: rephrase the same, already-computed facts through an LLM
            # for a more natural answer. Only ever called with real facts already
            # in hand — see app/ml/llm_client.py's docstring for why this can
            # never let the Copilot invent a number that isn't in source_data.
            from app.ml.llm_client import generate_llm_answer

            llm_answer = generate_llm_answer(question, source_data)
            if llm_answer:
                answer_text = llm_answer

    log = ChatLog(
        organization_id=org_id,
        user_id=user_id,
        question=question,
        intent=intent,
        answer=answer_text,
        source_data=source_data,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
