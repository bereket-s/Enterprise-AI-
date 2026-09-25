# Appendix C: Automated Test Evidence

44 automated tests (`backend/tests/`) exercise authentication, multi-tenant data
isolation, module gating, every module's ML pipeline, the AI Copilot, all six
data-integration paths, the model registry, and the column-mapping utility shared by
every ingestion path. Run with:

```
cd backend && pytest -v
```

Test files: `test_auth.py`, `test_tenant_isolation.py`, `test_ml_pipelines.py`,
`test_workforce_kpi.py`, `test_copilot.py`, `test_integrations.py`,
`test_data_mapping.py`.
