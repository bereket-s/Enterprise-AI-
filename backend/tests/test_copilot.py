import io


def test_copilot_falls_back_when_no_data(client, auth_headers):
    resp = client.post("/api/copilot/ask", json={"question": "Why did our revenue decline?"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "revenue_trend"
    assert "No sales data" in body["answer"]


def test_copilot_unknown_question_uses_fallback(client, auth_headers):
    resp = client.post("/api/copilot/ask", json={"question": "What is the meaning of life?"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["intent"] == "unknown"


def test_copilot_answers_from_real_ingested_data(client, auth_headers):
    csv_content = (
        "product_id,product_name,quantity,unit_price,transaction_date\n"
        "SKU-1,Widget,10,5.00,2024-01-01\n"
        "SKU-1,Widget,8,5.00,2024-01-02\n"
    )
    files = {"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    mapping = '{"product_id":"product_id","quantity":"quantity","unit_price":"unit_price","transaction_date":"transaction_date"}'
    ingest = client.post("/api/bi/ingest/commit", files=files, data={"mapping": mapping}, headers=auth_headers)
    assert ingest.status_code == 200

    resp = client.post("/api/copilot/ask", json={"question": "What are our top products?"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "top_products"
    assert "Widget" in body["answer"]

    history = client.get("/api/copilot/history", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_copilot_forecast_and_goal_intents_recognised_with_no_data(client, auth_headers):
    resp = client.post("/api/copilot/ask", json={"question": "What is our revenue forecast for next month?"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "forecast_outlook"
    assert "No forecast" in body["answer"]

    resp = client.post("/api/copilot/ask", json={"question": "Are we on track to hit our goals?"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["intent"] == "goal_progress"


def test_copilot_low_confidence_question_gets_a_suggestion():
    from app.services.copilot_service import classify_intent, _closest_example_question

    intent, score = classify_intent("blah blah nonsense question")
    assert intent == "unknown"
    assert score == 0

    # A typo'd but recognisable paraphrase of a known example question should still
    # surface a "did you mean" suggestion via fuzzy matching, even with zero exact
    # keyword hits.
    suggestion = _closest_example_question("wich prducts will run out soon?")
    assert suggestion == "Which products are most likely to run out?"


def test_classify_intent_picks_highest_scoring_not_first_listed():
    from app.services.copilot_service import classify_intent

    # Mentions both "machine" (equipment) and "fraud" twice — fraud should win on score.
    intent, score = classify_intent("Is this fraud, or a suspicious anomaly on the machine?")
    assert intent == "fraud_risk"
    assert score >= 2
