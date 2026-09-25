"""suggest_mapping() is the fuzzy column-name auto-mapper every integration
transport funnels through (see app/services/integration_pipeline.py). These
are unit tests since it's a pure function — no client/DB fixtures needed.
"""
from app.services.canonical_schemas import FRAUD_FIELDS
from app.services.data_mapping import suggest_mapping


def test_exact_field_is_not_stolen_by_a_fuzzy_match_on_a_different_field():
    """A "merchant" column is a close fuzzy-match (shared "merchant" prefix) for
    the unrelated merchant_lat/merchant_long fields under the difflib cutoff.
    Regression test for a real bug: this used to map merchant_lat and
    merchant_long onto the "merchant" column too, and ingestion then crashed
    trying to convert merchant name strings to floats."""
    columns = ["transaction_ref", "amount", "timestamp", "account_ref", "merchant", "is_fraud"]
    mapping = suggest_mapping(columns, FRAUD_FIELDS[0])

    assert mapping["merchant"] == "merchant"
    assert mapping["merchant_lat"] is None
    assert mapping["merchant_long"] is None


def test_each_source_column_is_claimed_at_most_once():
    columns = ["transaction_ref", "amount", "timestamp", "account_ref", "merchant", "is_fraud"]
    mapping = suggest_mapping(columns, FRAUD_FIELDS[0])

    claimed = [v for v in mapping.values() if v is not None]
    assert len(claimed) == len(set(claimed))
