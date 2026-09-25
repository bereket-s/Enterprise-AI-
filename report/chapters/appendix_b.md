# Appendix B: Raw Data and Model Outputs

- Raw downloaded files: `data/raw/*.csv` (regenerated on demand by running
  `python backend/scripts/download_datasets.py`; not committed to version control —
  see `.gitignore` — to keep the repository lightweight and reproducible from source).
- Full pipeline run output (equivalent to an SPSS/Excel output file for this
  system-development project): `report/chapter4_results.json`, produced by
  `backend/scripts/seed_demo_org.py`.
- Persisted per-run evaluation records: `ModelEvaluation` table (one row per
  training run, per module) in the application database
  (`backend/platform.db` for local SQLite runs).
- Trained model artefacts: `backend/app/ml/artifacts/*.joblib`.
