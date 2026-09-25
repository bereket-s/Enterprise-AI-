# Chapter 5: Conclusion, Recommendations, and Limitations

## 5.1 Conclusion

This project set out to answer whether a single, modular, multi-tenant architecture
can deliver production-relevant predictive and prescriptive analytics across multiple
distinct business domains while keeping each module's data isolated, explainable, and
independently configurable (§1.4). Evaluated against the five objectives set in §1.5:

**Objective 1 (multi-tenant architecture)** was met: `test_tenant_isolation.py`
demonstrates, through the real HTTP API rather than unit-level assertions, that two
independently registered organisations cannot see each other's ingested data, and that
disabling a module returns a 403 even to that organisation's own administrator until
re-enabled — a claim additionally confirmed live in the heuristic walkthrough
(Appendix F) via a direct `fetch()` bypassing the UI entirely. **Objective 2
(predictive modules)** was met for four of four modules, each now reported as a
5-fold cross-validated mean ± std and benchmarked against Logistic Regression and
Random Forest with a paired significance test (§4.6), not a single split: results
range from strong (fraud ROC-AUC 0.988 ± 0.001, maintenance 0.964 ± 0.011) to modest
(attrition 0.708 ± 0.038) — the variation itself a valid, literature-consistent
finding, not a failure to meet the objective. **Objective 3 (configurable performance
scoring)** was met and unit-tested directly, and additionally confirmed live: a KPI
weight was edited through the running UI and verified, via network trace, to persist
through a real write path (Appendix F). **Objective 4 (AI Copilot)** was met at
prototype depth: eight intents (two added during this iteration) are handled from
real, organisation-specific data with zero hallucination risk, and a fuzzy-matched
"did you mean" suggestion now covers near-miss questions — though the intent set
remains closed rather than open-ended (§5.3). **Objective 5 (critical evaluation on
real data)** was met throughout Chapter 4, and extended by a researcher-conducted
heuristic usability walkthrough (Appendix F) that found and fixed two genuine defects
— a data-shape crash and a missing mobile breakpoint — neither of which the automated
test suite was positioned to catch.

The overall research question is therefore answered in the affirmative, with an
important qualification: the architecture *does* deliver isolated, explainable,
configurable analytics across five domains from one codebase, but the *quality* of
each module's predictions is bounded by the richness of its underlying features, not
by the architecture — a distinction the platform's own cross-validated, statistically
compared results make directly visible (fraud and maintenance, with causally direct
features, outperform attrition, whose available features are more indirect proxies,
regardless of which of three algorithms is used).

## 5.2 Recommendations

Three recommendations from this project's own earlier drafts — a live database
connector, an optional LLM-backed Copilot, and Alembic-managed migrations — were
implemented during the project rather than left as intentions, and are reported as
results in §4.8 rather than repeated here. What follows is the recommendation set that
remains genuinely open:

1. **Seasonally-adjust the BI trend metric.** Replace the simple first-half/second-half
   revenue comparison with a same-period year-over-year or seasonally-decomposed trend,
   to avoid conflating calendar seasonality with genuine growth (§4.1).
2. **Extend the Workforce module's feature set** where a real HR system is connected —
   in particular `OverTime` and richer engagement signals, which Raza et al. (2022)
   show materially improve attrition-model performance beyond what this project's
   public-mirror dataset retained.
3. **Obtain real OAuth credentials for the three named pre-built connectors**
   (Salesforce, QuickBooks, SAP), which currently run in a documented simulated mode
   (§4.8) — swapping in a live connection changes only where each adapter's rows come
   from, not the mapping, validation, or storage pipeline downstream of it.
4. **Add the remaining database dialect drivers** (`pymysql`, `pyodbc`, `cx_oracle`)
   for the connector's MySQL/SQL Server/Oracle options, which are exposed in the
   configuration UI but — unlike the PostgreSQL and SQLite dialects, both tested
   end-to-end in §4.8 — cannot yet be exercised without a real server of that type to
   test against.
5. **Continue broadening the AI Copilot's intent set** beyond its current eight
   (two added, plus a fuzzy-match fallback, during this project) and evaluate the
   now-implemented LLM-backed phrasing layer (§4.8) in a live deployment with an
   operator-supplied key — the phrasing layer only ever rephrases facts the
   deterministic handlers already retrieved, so broadening intent coverage remains a
   separate piece of work from enabling it.
6. **Move from shared-schema to schema-per-tenant isolation** before onboarding any
   organisation handling regulated data (§2.1's isolation-strength discussion), as
   documented in `docs/architecture.md §2`. Migrations are already Alembic-managed
   (§4.8), so this remaining step is a data-partitioning change, not a tooling one.
7. **Administer the prepared participant survey** (Appendix G) to a small (n=3–5)
   pilot group as the direct next step — the instrument, task scripts, and analysis
   plan are complete; only recruitment and scheduling remain.

## 5.3 Limitations of This Study

- **Synthesised inventory data.** The Online Retail dataset contains no real
  stock-on-hand figures; current stock was synthesised from recent demand (§3.4,
  §4.2). The reorder-point *calculation* is validated as functioning correctly, but
  the specific stockout-risk figures reported in §4.2 are not a validated claim about
  a real retailer's actual inventory position.
- **Reduced feature set in the Workforce dataset.** The public mirror used for the
  Employee Performance module retains 14 of the original IBM HR Analytics dataset's
  ~35 columns (§3.4), omitting fields (e.g. `OverTime`, `PerformanceRating`) that
  other published work identifies as materially predictive of attrition — a likely
  contributor to this project's more modest attrition-model performance (§4.5).
- **Sampled, not full-population, fraud and maintenance data.** Both modules train on
  a documented sample rather than each dataset's full population (§3.5), chosen for
  tractable local compute/storage within a capstone's resource budget; a production
  deployment would retrain on the full available history.
- **No live organisational evaluation with real participants, still.** A
  researcher-conducted heuristic walkthrough (Appendix F) and a fully prepared
  participant survey instrument (Appendix G) now exist — a genuine step beyond
  asserting this gap without addressing it — but the "does explanation quality change
  adoption behaviour" question (central to §2.2's literature) remains evaluated by
  design and expert heuristic here, not yet by real participants completing the
  scenarios in Appendix G. Recommendation 7 makes this the identified next step, not
  an open-ended intention.
- **Closed intent set, and an LLM phrasing layer not yet evaluated live.** The
  deployed Copilot answers eight intents via scored keyword classification with a
  fuzzy-match fallback; questions outside that set still receive a fixed fallback
  message rather than a flexible, open-ended answer. An optional LLM-backed phrasing
  layer was added during this project (§4.8) — it can only rephrase facts the
  deterministic handlers already retrieved, never invent new ones, so it does not
  widen intent coverage — but has not been evaluated in a live deployment with a
  real API key (Recommendation 5).
- **Single-split evaluation, now substantially mitigated.** Chapter 4 originally
  reported one seeded train/test split per model; every classification task is now
  additionally reported as a 5-fold cross-validated mean ± std with a paired
  significance test against two baseline algorithms (§3.6, §4.6) — which is what
  surfaced, for example, that the attrition model's single-split score had understated
  its true performance. What remains unaddressed is variance *across different random
  seeds* for the overall pipeline (only seed = 42 was run end-to-end); this is a
  smaller, more easily closed gap than the single-split problem this project set out
  to fix.
