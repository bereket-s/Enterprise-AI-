# Appendix A: Secondary Data Sources (in place of questionnaire/interview evidence)

This project uses secondary, public datasets rather than a questionnaire or
interviews (justified in Chapter 3). Full provenance:

**Table A.1 — Dataset provenance, by module**

| Dataset | Source | Records used | Retrieval script |
|---|---|---|---|
| Online Retail | UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/352/online+retail | 541,909 raw / 530,104 cleaned | `backend/scripts/download_datasets.py::download_online_retail` |
| Simulated card transactions | HuggingFace mirror (Sparkov generator) — `dazzle-nu/CIS435-CreditCardFraudDetection` | 66,006 (stratified sample) | `download_credit_card_fraud` |
| AI4I 2020 Predictive Maintenance | UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset | 4,000 (random sample) | `download_ai4i2020` |
| IBM HR Analytics (Employee Attrition) | HuggingFace mirror — `eduvance/employee_attrition` | 1,370 | `download_employee_attrition` |
