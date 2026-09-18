# Appendix G: Participant Evaluation Survey Instrument (Prepared, Not Yet Administered)

**Status: this instrument is designed and ready to use, but has not been
administered to any participant.** It is included so that a genuine empirical
test of the Chapter 2 research framework's "decision-support value" side (§2.3)
— which the technical evaluation in Chapter 4 and the heuristic walkthrough in
Appendix F cannot themselves establish — can be run with real people (e.g. 3–5
classmates or colleagues) before or after submission, without any further
instrument design work. Administering it is identified as a direct next step in
Chapter 5, §5.2.

## G.1 Purpose

To measure whether the platform's explanations (fraud reason codes, maintenance
contributing factors, workforce score breakdowns) change a participant's
**decision confidence** and **trust**, compared with being shown the equivalent
raw score alone — directly testing the literature's central claim (Staley, 2025;
Sharma et al., 2024; Almtrf, 2025) that explanation quality, not raw accuracy,
drives adoption.

## G.2 Participants and ethics

- Target: 3–5 participants, ideally with some exposure to business, data, or
  software roles (not required — record role/background as a covariate, not a
  filter).
- **Consent script** (read or shown before starting): *"You're being asked to
  try a short demo of a student capstone analytics platform and answer some
  questions about it. This takes about 15 minutes, is anonymous unless you
  choose to give your name, and you can stop at any time. Your responses will
  only be used to evaluate this Master's project."*
- No personal, sensitive, or identifying data is collected unless a participant
  volunteers their name; if run, store responses without names by default.

## G.3 Procedure

1. Log the participant into the demo organisation (`admin@demo.local`) or a
   fresh test organisation, participant's choice.
2. Run the three task scenarios below **in order**, each followed immediately by
   its post-task questions (§G.4) before moving to the next.
3. Finish with the overall questionnaire (§G.5) and the open-ended questions
   (§G.6).

### Task 1 — Fraud

*"Open Fraud & Anomaly Detection. Pick any transaction marked Critical or High
risk. Based on what the page shows you, decide: would you Approve, Investigate,
or Block it? Tell me your decision and why."*

### Task 2 — Predictive Maintenance

*"Open Predictive Maintenance. Pick any equipment item marked Critical or High
risk. Would you schedule an inspection this week, or let it wait? Tell me your
decision and why."*

### Task 3 — Workforce

*"Open Employee Performance & Workforce Intelligence. Pick any employee, click
'Explain my score', and tell me: do you understand why they got that score? What
would you tell them to improve?"*

## G.4 Post-task questions (repeat after each task, 1–5 Likert: 1 = strongly
disagree, 5 = strongly agree)

1. The information shown was enough for me to make a decision.
2. I understood *why* the system reached this risk level / score.
3. I am confident my decision was the right one.
4. I would trust this output enough to act on it at work without double-checking it elsewhere.

## G.5 Overall questionnaire (after all three tasks, same 1–5 scale)

1. The explanations felt specific to the actual case, not generic.
2. The dashboard was easy to navigate.
3. I could tell what action the system wanted me to consider next.
4. I would rather use this than a system that only showed a percentage/score with no explanation.
5. I felt in control of the decision — the system supported me, it didn't decide for me.
6. The platform felt trustworthy overall.

## G.6 Open-ended questions

1. What was the most useful explanation you saw, and why?
2. What was confusing or unclear anywhere in the platform?
3. Is there anything the system should have told you but didn't?
4. Any other comments?

## G.7 Analysis plan (for whoever administers this)

- Report the **mean and range** of each Likert item across participants (n is
  too small for inferential statistics — treat this as descriptive/qualitative
  evidence, not a hypothesis test).
- Group the four post-task questions by module to see whether any one module's
  explanations scored consistently lower — that module becomes a prioritised
  target for improvement.
- Thematically group the open-ended answers (simple affinity grouping is
  sufficient at this scale — cluster similar comments by hand, no formal coding
  software required) and report the two or three most repeated themes verbatim,
  with attribution removed unless a participant explicitly consented to be
  named.
- Present results as a short addendum to Chapter 4 (or a future publication) —
  explicitly labelled as a small, non-generalisable pilot, consistent with the
  sample size.

## G.8 Why this was not administered within this capstone's timeline

Recruiting and scheduling even 3–5 external participants requires lead time and
falls outside the technical development and write-up window for this
submission (see Chapter 1, §1.6 scope). Preparing a complete, ready-to-run
instrument — rather than leaving "future user study" as an unspecified
intention — is itself the mitigation offered here: the gap is a scheduling
constraint, not an unaddressed design question.
