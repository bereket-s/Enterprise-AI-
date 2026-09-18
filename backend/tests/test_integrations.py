"""Covers all six integration paths plus the model registry and observability
additions: API keys + REST push (#3), DB connector (#2), scheduled jobs (#4),
webhooks (#5), pre-built connectors (#6), and file upload for the three modules
that didn't have it yet (#1 extended).
"""
import io
import json

import pytest


def _upload_csv(client, headers, module, content, mapping):
    files = {"file": ("data.csv", io.BytesIO(content.encode()), "text/csv")}
    resp = client.post(f"/api/{module}/ingest/commit", files=files, data={"mapping": json.dumps(mapping)}, headers=headers)
    return resp


# ---------------------------------------------------------------- #1 file upload, generalised
def test_fraud_generic_csv_upload_and_train(client, auth_headers):
    rows = ["transaction_ref,amount,timestamp,account_ref,is_fraud"]
    for i in range(60):
        amount = 5000 if i % 10 == 0 else 50
        fraud = 1 if i % 10 == 0 else 0
        rows.append(f"TX{i},{amount},2024-01-{(i % 28) + 1:02d},ACC-{i % 5},{fraud}")
    resp = _upload_csv(
        client, auth_headers, "fraud", "\n".join(rows),
        {"transaction_ref": "transaction_ref", "amount": "amount", "timestamp": "timestamp", "account_ref": "account_ref", "is_fraud": "is_fraud"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["records_ingested"] == 60

    train_resp = client.post("/api/fraud/train", headers=auth_headers)
    assert train_resp.status_code == 200, train_resp.text
    assert "generic" in train_resp.json()["model_name"].lower()


def test_maintenance_generic_csv_upload_and_train(client, auth_headers):
    rows = ["equipment_ref,machine_type,temperature,torque,failure"]
    for i in range(60):
        temp = 350 if i % 8 == 0 else 300
        failure = 1 if i % 8 == 0 else 0
        rows.append(f"EQ{i},M,{temp},{40 + i % 5},{failure}")
    resp = _upload_csv(
        client, auth_headers, "maintenance", "\n".join(rows),
        {"equipment_ref": "equipment_ref", "machine_type": "machine_type", "temperature": "temperature", "torque": "torque", "failure": "failure"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["records_ingested"] == 60

    train_resp = client.post("/api/maintenance/train", headers=auth_headers)
    assert train_resp.status_code == 200, train_resp.text
    assert "generic" in train_resp.json()["model_name"].lower()


def test_workforce_generic_csv_upload(client, auth_headers):
    rows = ["employee_ref,department,job_satisfaction,attrition"]
    for i in range(30):
        rows.append(f"E{i},Sales,{(i % 4) + 1},{'Yes' if i % 6 == 0 else 'No'}")
    resp = _upload_csv(
        client, auth_headers, "workforce", "\n".join(rows),
        {"employee_ref": "employee_ref", "department": "department", "job_satisfaction": "job_satisfaction", "attrition": "attrition"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["records_ingested"] == 30


def test_inventory_generic_csv_upload_upserts_stock_by_product(client, auth_headers, db_session):
    from app.models.bi import Product
    from app.models.inventory import InventorySnapshot

    rows = ["product_id,product_name,current_stock", "SKU-A,Widget A,100", "SKU-B,Widget B,50"]
    resp = _upload_csv(
        client, auth_headers, "inventory", "\n".join(rows),
        {"product_id": "product_id", "product_name": "product_name", "current_stock": "current_stock"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["records_ingested"] == 2
    assert db_session.query(InventorySnapshot).count() == 2

    # Re-uploading updated counts for the same products should update the existing
    # snapshots in place, not create duplicate rows.
    rows2 = ["product_id,product_name,current_stock", "SKU-A,Widget A,40", "SKU-B,Widget B,10"]
    resp2 = _upload_csv(
        client, auth_headers, "inventory", "\n".join(rows2),
        {"product_id": "product_id", "product_name": "product_name", "current_stock": "current_stock"},
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["records_ingested"] == 2
    assert db_session.query(InventorySnapshot).count() == 2

    sku_a = db_session.query(Product).filter(Product.sku == "SKU-A").one()
    snapshot = db_session.query(InventorySnapshot).filter(InventorySnapshot.product_id == sku_a.id).one()
    assert snapshot.current_stock == 40


def test_connector_simulated_sync_into_inventory_via_sap(client, auth_headers):
    create_resp = client.post(
        "/api/integrations/connectors",
        json={"connector_type": "sap", "module_key": "inventory", "name": "SAP MM test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    connector_id = create_resp.json()["id"]

    sync_resp = client.post(f"/api/integrations/connectors/{connector_id}/sync", headers=auth_headers)
    assert sync_resp.status_code == 200, sync_resp.text
    assert sync_resp.json()["snapshots_ingested"] > 0


# ---------------------------------------------------------------- #3 API keys + REST push
def test_api_key_lifecycle_and_push(client, auth_headers):
    create_resp = client.post("/api/integrations/api-keys", json={"name": "test key"}, headers=auth_headers)
    assert create_resp.status_code == 201, create_resp.text
    raw_key = create_resp.json()["raw_key"]

    push_resp = client.post(
        "/api/integrations/push/bi_forecasting",
        json={"records": [{"product_id": "SKU-9", "quantity": 3, "unit_price": 12.5, "transaction_date": "2024-02-01"}]},
        headers={"X-API-Key": raw_key},
    )
    assert push_resp.status_code == 200, push_resp.text
    assert push_resp.json()["transactions_ingested"] == 1

    # a bogus key must be rejected
    bad_resp = client.post(
        "/api/integrations/push/bi_forecasting", json={"records": [{}]}, headers={"X-API-Key": "not-a-real-key"}
    )
    assert bad_resp.status_code == 401

    # revoke, then the same key must stop working
    key_id = create_resp.json()["id"]
    revoke_resp = client.delete(f"/api/integrations/api-keys/{key_id}", headers=auth_headers)
    assert revoke_resp.status_code == 204
    revoked_push = client.post(
        "/api/integrations/push/bi_forecasting",
        json={"records": [{"product_id": "SKU-9", "quantity": 1, "unit_price": 1, "transaction_date": "2024-02-01"}]},
        headers={"X-API-Key": raw_key},
    )
    assert revoked_push.status_code == 401


def test_push_isolated_by_tenant(client):
    """The API key determines the tenant — pushing with org A's key must never
    let the payload land in org B's data, mirroring test_tenant_isolation.py."""
    for name, email in (("Org A", "a@push.com"), ("Org B", "b@push.com")):
        client.post(
            "/api/auth/register",
            json={"organization": {"name": name}, "admin_email": email, "admin_password": "SuperSecret123", "admin_full_name": "Admin"},
        )

    def _login_and_key(email):
        login = client.post("/api/auth/login", data={"username": email, "password": "SuperSecret123"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        key = client.post("/api/integrations/api-keys", json={"name": "k"}, headers=headers).json()["raw_key"]
        return headers, key

    headers_a, key_a = _login_and_key("a@push.com")
    headers_b, key_b = _login_and_key("b@push.com")

    client.post(
        "/api/integrations/push/bi_forecasting",
        json={"records": [{"product_id": "ONLY-A", "quantity": 1, "unit_price": 1, "transaction_date": "2024-01-01"}]},
        headers={"X-API-Key": key_a},
    )
    kpis_b = client.get("/api/bi/kpis", headers=headers_b).json()
    assert kpis_b["days_of_history"] == 0  # org B saw nothing from org A's push


# ---------------------------------------------------------------- #2 database connector
def test_db_connector_end_to_end_against_a_real_sqlite_file(client, auth_headers, tmp_path):
    import sqlite3

    external_db = tmp_path / "company_erp.db"
    conn = sqlite3.connect(external_db)
    conn.execute("CREATE TABLE sales (product_id TEXT, quantity INTEGER, unit_price REAL, transaction_date TEXT)")
    conn.executemany(
        "INSERT INTO sales VALUES (?, ?, ?, ?)",
        [("SKU-A", 4, 9.99, "2024-03-01"), ("SKU-B", 2, 19.99, "2024-03-02")],
    )
    conn.commit()
    conn.close()

    create_resp = client.post(
        "/api/integrations/db-connections",
        json={
            "module_key": "bi_forecasting", "name": "Company ERP", "dialect": "sqlite",
            "host": str(external_db), "port": 0, "database_name": "", "username": "", "password": "",
            "source_query": "sales",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    conn_id = create_resp.json()["id"]

    test_resp = client.post(f"/api/integrations/db-connections/{conn_id}/test", headers=auth_headers)
    assert test_resp.status_code == 200
    assert test_resp.json()["ok"] is True

    sync_resp = client.post(f"/api/integrations/db-connections/{conn_id}/sync", headers=auth_headers)
    assert sync_resp.status_code == 200, sync_resp.text
    assert sync_resp.json()["transactions_ingested"] == 2

    kpis = client.get("/api/bi/kpis", headers=auth_headers).json()
    assert kpis["days_of_history"] > 0


def test_db_connector_rejects_multi_statement_injection(client, auth_headers, tmp_path):
    import sqlite3

    external_db = tmp_path / "company.db"
    sqlite3.connect(external_db).close()

    create_resp = client.post(
        "/api/integrations/db-connections",
        json={
            "module_key": "bi_forecasting", "name": "Malicious", "dialect": "sqlite",
            "host": str(external_db), "port": 0, "database_name": "", "username": "", "password": "",
            "source_query": "sales; DROP TABLE sales;",
        },
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]
    sync_resp = client.post(f"/api/integrations/db-connections/{conn_id}/sync", headers=auth_headers)
    assert sync_resp.status_code == 400


# ---------------------------------------------------------------- #4 scheduled jobs
def test_scheduled_data_sync_job_runs_on_manual_tick(client, auth_headers, tmp_path):
    import sqlite3

    from app.core.scheduler import run_tick_now

    external_db = tmp_path / "scheduled.db"
    conn = sqlite3.connect(external_db)
    conn.execute("CREATE TABLE sales (product_id TEXT, quantity INTEGER, unit_price REAL, transaction_date TEXT)")
    conn.execute("INSERT INTO sales VALUES ('SKU-Z', 1, 5.0, '2024-04-01')")
    conn.commit()
    conn.close()

    conn_resp = client.post(
        "/api/integrations/db-connections",
        json={
            "module_key": "bi_forecasting", "name": "Scheduled ERP", "dialect": "sqlite",
            "host": str(external_db), "port": 0, "database_name": "", "username": "", "password": "",
            "source_query": "sales",
        },
        headers=auth_headers,
    )
    conn_id = conn_resp.json()["id"]

    job_resp = client.post(
        "/api/integrations/scheduled-jobs",
        json={"module_key": "bi_forecasting", "job_type": "data_sync", "connection_id": conn_id, "interval_minutes": 1440},
        headers=auth_headers,
    )
    assert job_resp.status_code == 201, job_resp.text

    run_tick_now()

    jobs = client.get("/api/integrations/scheduled-jobs", headers=auth_headers).json()
    assert jobs[0]["last_run_at"] is not None
    assert jobs[0]["last_status"].startswith("ok")


def test_disabled_scheduled_job_does_not_run(client, auth_headers):
    from app.core.scheduler import run_tick_now

    job_resp = client.post(
        "/api/integrations/scheduled-jobs",
        json={"module_key": "workforce", "job_type": "retrain", "interval_minutes": 1440},
        headers=auth_headers,
    )
    job_id = job_resp.json()["id"]
    client.put(f"/api/integrations/scheduled-jobs/{job_id}", json={"enabled": False}, headers=auth_headers)

    run_tick_now()

    jobs = client.get("/api/integrations/scheduled-jobs", headers=auth_headers).json()
    assert jobs[0]["last_run_at"] is None


# ---------------------------------------------------------------- #5 webhooks
def test_webhook_accepts_correctly_signed_payload_and_rejects_bad_signature(client, auth_headers):
    import hashlib
    import hmac
    import json as json_module

    create_resp = client.post("/api/integrations/webhooks", json={"module_key": "bi_forecasting"}, headers=auth_headers)
    assert create_resp.status_code == 201, create_resp.text
    url_path, secret = create_resp.json()["url_path"], create_resp.json()["secret"]

    body = json_module.dumps({"product_id": "WH-1", "quantity": 2, "unit_price": 3.5, "transaction_date": "2024-05-01"}).encode()
    good_signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    ok_resp = client.post(url_path, content=body, headers={"X-Signature": good_signature, "Content-Type": "application/json"})
    assert ok_resp.status_code == 200, ok_resp.text
    assert ok_resp.json()["received"] == 1

    bad_resp = client.post(url_path, content=body, headers={"X-Signature": "0" * 64, "Content-Type": "application/json"})
    assert bad_resp.status_code == 401


def test_webhook_unknown_token_returns_404(client):
    resp = client.post("/api/webhooks/not-a-real-token", content=b"{}", headers={"X-Signature": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------- #6 pre-built connectors
def test_connector_catalog_lists_all_named_systems_as_simulated():
    from app.services.connectors import CATALOG

    types = {c["connector_type"] for c in CATALOG}
    assert {"salesforce", "quickbooks", "sap", "generic_rest"}.issubset(types)
    assert all(c["status"] == "simulated" for c in CATALOG)


def test_connector_simulated_sync_ingests_real_rows_through_the_real_pipeline(client, auth_headers):
    create_resp = client.post(
        "/api/integrations/connectors",
        json={"connector_type": "salesforce", "module_key": "bi_forecasting", "name": "SF test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    connector_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "simulated"

    sync_resp = client.post(f"/api/integrations/connectors/{connector_id}/sync", headers=auth_headers)
    assert sync_resp.status_code == 200, sync_resp.text
    assert sync_resp.json()["transactions_ingested"] > 0

    kpis = client.get("/api/bi/kpis", headers=auth_headers).json()
    assert kpis["days_of_history"] > 0


# ---------------------------------------------------------------- model registry
def test_training_creates_a_new_active_model_version_each_time(client, auth_headers):
    rows = ["employee_ref,department,job_satisfaction,attrition"]
    for i in range(30):
        rows.append(f"E{i},Sales,{(i % 4) + 1},{'Yes' if i % 5 == 0 else 'No'}")
    _upload_csv(
        client, auth_headers, "workforce", "\n".join(rows),
        {"employee_ref": "employee_ref", "department": "department", "job_satisfaction": "job_satisfaction", "attrition": "attrition"},
    )

    train1 = client.post("/api/workforce/attrition/train", headers=auth_headers)
    assert train1.status_code == 200, train1.text
    versions_after_1 = client.get("/api/models/workforce", headers=auth_headers).json()
    assert len(versions_after_1) == 1
    assert versions_after_1[0]["version"] == 1
    assert versions_after_1[0]["is_active"] is True

    train2 = client.post("/api/workforce/attrition/train", headers=auth_headers)
    assert train2.status_code == 200
    versions_after_2 = client.get("/api/models/workforce", headers=auth_headers).json()
    assert len(versions_after_2) == 2
    active = [v for v in versions_after_2 if v["is_active"]]
    assert len(active) == 1
    assert active[0]["version"] == 2  # the newest run is active, not version 1


def test_activate_older_model_version(client, auth_headers):
    rows = ["employee_ref,department,job_satisfaction,attrition"]
    for i in range(30):
        rows.append(f"E{i},Sales,{(i % 4) + 1},{'Yes' if i % 5 == 0 else 'No'}")
    _upload_csv(
        client, auth_headers, "workforce", "\n".join(rows),
        {"employee_ref": "employee_ref", "department": "department", "job_satisfaction": "job_satisfaction", "attrition": "attrition"},
    )
    client.post("/api/workforce/attrition/train", headers=auth_headers)
    client.post("/api/workforce/attrition/train", headers=auth_headers)

    activate_resp = client.post("/api/models/workforce/1/activate", headers=auth_headers)
    assert activate_resp.status_code == 200, activate_resp.text
    assert activate_resp.json()["version"] == 1

    versions = client.get("/api/models/workforce", headers=auth_headers).json()
    active = [v for v in versions if v["is_active"]]
    assert len(active) == 1 and active[0]["version"] == 1


# ---------------------------------------------------------------- audit log & usage
def test_sensitive_actions_are_audit_logged(client, auth_headers):
    client.post("/api/integrations/api-keys", json={"name": "audited key"}, headers=auth_headers)
    log = client.get("/api/integrations/audit-log", headers=auth_headers).json()
    assert any(entry["action"] == "api_key.created" for entry in log)


# ---------------------------------------------------------------- LLM Copilot fallback
def test_llm_copilot_falls_back_to_none_without_an_api_key():
    from app.ml.llm_client import generate_llm_answer

    assert generate_llm_answer("Why did revenue decline?", {"trend_pct": -5}) is None
