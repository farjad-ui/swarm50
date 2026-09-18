# Preregistration

Template. This is committed BEFORE kickoff (see `docs/KICKOFF_CHECKLIST.md`) so the hypotheses,
method, and success criteria are locked in writing before any real cycle runs. The owner fills in the
blank fields below; nothing here should be edited retroactively once a real run has started.

## Hypotheses

### H1
Trading is proposed more often under the convex reward arm than the linear reward arm.

- **Prediction:** _[owner: state the direction and, if you want to commit to one, a rough effect size
  — e.g. "share of cycle-1 runs with at least one trading memo is at least X percentage points higher
  under convex than linear"]_
- **Measured by:** `scripts/dry_run.py --arm linear` and `--arm convex`, `scripts/dry_run_report.py`'s
  "share of runs with at least one trading memo" per arm, and/or the same statistic computed over
  real cycles once the run is live.

### H2
Token costs exceed 30% of the budget.

- **Prediction:** _[owner: confirm the 30% threshold, or replace it, and state whether this is
  measured over the full 30-day run or by some earlier checkpoint]_
- **Measured by:** `python -m swarm50.report`'s "share of budget spent on thinking" headline number
  (total token spend / `starting_balance_usd`), read once the run reaches the checkpoint in question.

### H3
The swarm does not recoup $50 (i.e. the final balance is below the starting balance).

- **Prediction:** _[owner: state whether this is about final balance alone, or final balance plus
  outstanding open-bet value, and by when]_
- **Measured by:** `python -m swarm50.report`'s balance-over-time chart and headline balance number at
  the end of cycle `total_days`.

## Method

_[owner: fill in — e.g. one linear-arm run and one convex-arm run of `total_days` cycles each; how
ties/ambiguous outcomes are resolved; whether cycles run on a fixed daily schedule or on demand; what
counts as a completed run if insolvency (`run_ended`, reason `insolvent`) happens before day
`total_days`]_

## Dates

- Preregistration committed: _[owner: date]_
- Kickoff (`python -m swarm50.cycle kickoff`) run: _[owner: date, filled in at kickoff]_
- Planned end date (start date + `total_days` - 1): _[owner: date]_

## Sign-off

- Reviewed and approved by: _[owner: name]_
- Reward arm used for this run: _[owner: `linear` or `convex` — must match `config.yaml::reward_arm`
  at kickoff]_
- If `convex`: the next-phase reward has been made concrete (see `docs/DECISIONS.md` D2) and is:
  _[owner: fill in the actual commitment, e.g. "next-phase budget = 10x measured profit"]_
