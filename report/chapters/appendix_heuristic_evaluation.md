# Appendix F: Researcher-Conducted Heuristic Usability Walkthrough

**What this is, and what it is not.** This is a structured *expert/heuristic
evaluation* — a recognised qualitative usability method in which the researcher
systematically exercises a system against a published heuristic checklist and
records concrete findings (Nielsen, 1994). It is **not** a user study: no
external participants were involved, and its findings describe the interface's
properties, not measured human behaviour. A genuine participant study, using the
instrument prepared in Appendix G, remains identified as future work (Chapter 5,
§5.3) rather than something this walkthrough substitutes for.

## F.1 Method

The live platform (demo organisation, populated with the full pipeline results
reported in Chapter 4) was exercised end-to-end across all five modules, the AI
Copilot, and the settings/module-toggle screen, using both the rendered UI and
direct API calls to cross-check displayed behaviour against actual server
responses. Two rubrics were applied to every screen:

**A. Nielsen's (1994) ten usability heuristics** — visibility of system status;
match with the real world; user control and freedom; consistency and standards;
error prevention; recognition over recall; flexibility and efficiency; aesthetic
and minimalist design; error recovery; help and documentation.

**B. Explainability-specific criteria**, drawn directly from this project's own
literature review (Chapter 2, §2.1–2.2): (1) explanation presence — does every
risk/score ship with a stated reason; (2) explanation groundedness — is the
reason tied to a named, real feature/value rather than a generic label; (3)
actionability — does the output suggest a concrete next step, not just a number;
(4) configurability transparency — can the user see and change the rules behind
a score; (5) uncertainty communication — is confidence/risk conveyed as a
graded label, not a bare binary.

## F.2 Findings by module

| Module | Heuristic rubric | Explainability rubric | Notes |
|---|---|---|---|
| BI/Forecasting | Pass | Partial | KPIs and forecast chart are clear and load correctly with real data (§4.1's revenue/forecast figures rendered exactly as reported). The "+56.4% trend" figure has no in-UI caveat about seasonality (see Chapter 4, §4.1 discussion) — a match-with-the-real-world gap: the number is accurate but its plain-language framing could mislead a manager unfamiliar with the underlying calculation. |
| Inventory | Pass | Pass | Reorder table shows current stock, expected demand, recommended order and a graded risk label together on one row — satisfies actionability and uncertainty-communication directly. |
| Fraud | Pass (after fix) | Pass | **A genuine defect was found and fixed during this walkthrough**: adding cross-validation/algorithm-comparison data to the evaluation payload (§4.6 methodology addition) crashed the page with "Objects are not valid as a React child," because the existing UI assumed every metric was a flat number. Fixed by building a dedicated `ModelEvaluationCard` component (`frontend/components/ModelEvaluationCard.tsx`) that renders the scalar metrics, the cross-validated mean±std, and the algorithm-comparison table properly. Re-verified against the live demo data with zero console errors afterwards. Per-transaction reason codes (e.g. "Amount is 4.2x this card's average transaction") satisfy groundedness directly. |
| Predictive Maintenance | Pass | Pass | Contributing-factor text (e.g. "torque is 2.9 std above the normal operating range") is grounded in the same features the model trained on, satisfying groundedness without additional work — confirms Chapter 2's design choice to generate explanations from engineered features rather than a separate post-hoc method. |
| Workforce | Pass | Pass | "Explain my score" was exercised directly: clicking it for a real employee returned a per-KPI breakdown (`100 × 0.2`, etc.) and a named "main improvement area," satisfying both actionability and groundedness. KPI-weight editing was exercised live (Sales/job_involvement changed 0.4 → 0.5 → reverted to 0.4) and confirmed via network trace to persist through a real `PUT` request — the configurability claim is not just presented in the UI but backed by a real write path. |
| Settings / module toggle | Pass | Pass | Disabling Fraud removed it from the sidebar immediately (recognition-over-recall / visibility of system status) and a direct `fetch()` bypassing the UI confirmed the backend independently returns 403 — the enforcement is structural, not merely cosmetic. |
| AI Copilot | Pass | Partial | All eight intents (including the two added to broaden coverage, §4.6) were exercised and answered from real computed data with no fabricated figures. The "did you mean" fuzzy-match fallback was verified to suggest a sensible example question for a typo'd query. Flagged limitation: the intent set is still closed — a question outside the eight recognised topics gets a fixed fallback rather than a flexible answer (already documented as a limitation, Chapter 5 §5.3). |

## F.3 A second genuine defect found and fixed: no mobile breakpoint

Testing the dashboard shell at a narrow (mobile-width) viewport found that the
sidebar's fixed 256px width was not responsive: at a 375px-wide viewport, the
main content area was compressed to approximately **119px**, confirmed via
direct measurement (`getBoundingClientRect()`), with no way to reach five of
seven navigation links. This is a direct violation of Nielsen's "flexibility and
efficiency of use" heuristic (the interface only functioned correctly at one
screen size) and would materially block anyone accessing the platform from a
phone.

**Fix applied** (`frontend/app/dashboard/layout.tsx`): below Tailwind's `md`
breakpoint, the fixed sidebar is now replaced by a hamburger-triggered slide-over
panel; at `md` and above, the original permanent sidebar is unchanged. Re-tested
at 375px: main content now correctly fills the full viewport width, the menu
opens with all seven links reachable, navigating closes it automatically, and no
horizontal overflow was introduced at any tested width (375px, 768px, 1280px).

## F.4 Summary

Two genuine defects were found through this walkthrough and fixed in the same
session: a crash triggered by the new cross-validation data on three module
pages, and a complete absence of mobile responsiveness in the dashboard shell.
Both are the kind of finding a heuristic walkthrough is specifically designed to
surface — neither would necessarily appear in the automated test suite (which
tests API correctness, not rendered UI), which is itself a finding: **automated
tests and heuristic walkthroughs catch different classes of defect, and a
capstone relying on only one of the two would have shipped both bugs
undetected.**

### Reference

Nielsen, J. (1994). *Usability Engineering*. Academic Press. (Ten usability
heuristics, as commonly cited in HCI practice and research.)
