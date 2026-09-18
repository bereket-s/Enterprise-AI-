"""Verifies the core multi-tenant claim: Company A can never see Company B's data,
even when both are authenticated, by exercising the BI module (ingest + KPIs) across
two separately registered organizations.
"""
import io


def _register_and_login(client, name, email):
    client.post(
        "/api/auth/register",
        json={
            "organization": {"name": name, "industry": "retail", "size": "1-50", "country": "US"},
            "admin_email": email,
            "admin_password": "SuperSecret123",
            "admin_full_name": "Org Admin",
        },
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": "SuperSecret123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ingest_one_product(client, headers, sku: str):
    csv_content = (
        "product_id,product_name,quantity,unit_price,transaction_date,customer_ref,country\n"
        f"{sku},Widget,5,9.99,2024-01-01,cust-1,US\n"
    )
    files = {"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    mapping = '{"product_id":"product_id","quantity":"quantity","unit_price":"unit_price","transaction_date":"transaction_date"}'
    resp = client.post("/api/bi/ingest/commit", files=files, data={"mapping": mapping}, headers=headers)
    assert resp.status_code == 200, resp.text


def test_organizations_cannot_see_each_others_products(client):
    headers_a = _register_and_login(client, "Company A", "admin@a.com")
    headers_b = _register_and_login(client, "Company B", "admin@b.com")

    _ingest_one_product(client, headers_a, "SKU-A")
    _ingest_one_product(client, headers_b, "SKU-B")

    kpis_a = client.get("/api/bi/kpis", headers=headers_a).json()
    kpis_b = client.get("/api/bi/kpis", headers=headers_b).json()

    skus_a = {p["sku"] for p in kpis_a["top_products"]}
    skus_b = {p["sku"] for p in kpis_b["top_products"]}

    assert skus_a == {"SKU-A"}
    assert skus_b == {"SKU-B"}
    assert "SKU-B" not in skus_a
    assert "SKU-A" not in skus_b


def test_disabling_a_module_returns_403(client):
    headers = _register_and_login(client, "Company C", "admin@c.com")

    toggle_resp = client.put("/api/org/modules/bi_forecasting", json={"enabled": False}, headers=headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] is False

    resp = client.get("/api/bi/kpis", headers=headers)
    assert resp.status_code == 403
