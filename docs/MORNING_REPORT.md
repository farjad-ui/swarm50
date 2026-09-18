# Morning report

Overnight build on branch `overnight-build`, milestones M0–M7, all committed and pushed. Start here,
then `docs/DECISIONS.md` for the full reasoning behind anything below.

## What got built, milestone by milestone

**M0 — Verify the foundation.** Set up a venv, installed `requirements.txt`, ran the full suite before
touching anything: 44/44 passed. Audited `bets.py`/`review.py`/`cfo.py`/`queue.py` against the brief's
checklist — the foundation already matched it closely; only the `Rebuttal` schema's field names
(`action`/`memo` vs. the brief's `decision`/`revised_memo`) needed fixing, done under M1 since it
required touching the prompt/schema pair together. (D1)

**M1 — The real prompts.** Replaced the placeholder `prompts/*.md` with the brief's texts verbatim,
added `prompts/objective_linear.md`/`objective_convex.md`/`critic_final.md`, and built
`swarm50/prompts.py` to load and fill them with `string.Template` (no prompt text in `.py` files).
Added `reward_arm`, `total_days`, `start_date` to `config.yaml`. Extended `StrategistResponse` with
`bet_actions`/`work_orders`. Fixed the `Rebuttal` schema to `responses`/`decision`/`revised_memo`,
matching the prompt exactly. Added a test asserting the two rendered strategist prompts differ ONLY in
the objective paragraph. (D2–D5)

**M2 — Dry-run harness.** `scripts/dry_run.py --arm linear|convex --n N [--batch] [--max-total-usd]`
and `scripts/dry_run_report.py`, backed by `swarm50/dryrun.py`. Strategist-only, no critic, no
staking, one repair retry, `--max-total-usd` (default $5.00) stops the harness before cumulative cost
would exceed it. `--batch` routes through a new `metered_batch_call` in `metered.py` (still the only
file touching the SDK), pricing at half rate via a new optional `discount` parameter on
`ledger.cost_micro`/`record_token_usage` (default 1.0, a no-op for every existing call site). Report
prints/writes `results/dryrun_summary.md`: share of runs with a trading memo, share with no bet,
category frequency, mean/median stake as a share of balance by category, mean p_total_loss, total
cost. Everything tested against mocks only; `--batch` is marked `UNVERIFIED AGAINST REAL API`. (D6–D8)

**M3 — Cycle runner.** `python -m swarm50.cycle kickoff` (writes a one-time `run_meta` kickoff event:
start date, reward arm, config hash; refuses to run twice) and `run [--force]`. Cycle number derives
from the kickoff event's start date, never from a mutated config file. Sequence: strategist call ->
apply `bet_actions` (kill writes a `killed` event; stake is never auto-returned) -> critic loop on new
memos -> execute `work_orders` -> `cycle_summary` event. Overdue bets (past `kill_by_cycle`) are
flagged prominently in the state block. Insolvency at the strategist's own call writes `run_ended`
(`insolvent`) and refuses all future cycles; a mid-cycle cap hit just ends that cycle early. Any other
exception is caught, logged as a `cycle_error` event with the traceback, and re-raised — the DB is left
usable for the next run. `queue.py` gained `record-return` and `close`. (D9–D12)

**M4 — Workers and human tasks.** `swarm50/workers.py::execute_work_orders`: no tools, no network;
runs only against bets whose derived status is `active` (others -> `blocked`); `max_tokens` capped by
`worker_max_tokens` (3000); writes deliverables to `artifacts/<bet_id>/<seq>_<type>.md` (git-ignored)
and a `work_completed` event with path/tokens/cost. `prompts/worker.md` written from scratch per the
brief's instruction, flagged for review. `swarm50/tasks.py`: approving a bet writes a
`human_task_requested` event per `human_actions_required` entry; `queue.py tasks list`/`tasks done`
manage the lifecycle; open tasks and their age appear in the state block. (D13–D15)

**M5 — Static report.** `python -m swarm50.report` writes a single self-contained `report/index.html`
(inline CSS, hand-rolled inline SVG bar/line charts, no external requests, no JS), read-only against
the DB: headline tiles (day, balance, total token spend, share of budget on thinking, open exposure),
balance-over-time chart, token spend by role/cycle, bets table with derived status/stake/returns/P&L,
blocked actions, open human tasks, and a collapsed decision-log timeline. All model-generated text is
HTML-escaped; tested against an empty DB, a fixture DB, and a hostile memo title. (D16–D18)

**M6 — Docs.** Rewrote `README.md` (architecture with a Mermaid diagram, how money flows, every CLI,
the backend switch) and wrote `docs/RULES.md`, `docs/PREREGISTRATION.md` (H1/H2/H3 with blank
method/dates/sign-off fields for the owner), and `docs/KICKOFF_CHECKLIST.md`.

**M7 — This report.**

### Final test suite

```
90 passed in 1.00s
```
(up from the 44/44 baseline recorded at M0; every milestone's commit was made only after the full
suite passed. Run `pytest -q` from the repo root to reproduce.)

## Every [NEEDS FARJAD] decision

- **D2** — The convex reward arm's "next-phase budget scales steeply" is left deliberately vague, per
  the brief; you need to decide and write in a concrete, honourable commitment (e.g. "10x profit")
  before ever running the convex arm for real. See `prompts/objective_convex.md` and
  `docs/PREREGISTRATION.md`'s sign-off section.
- **D13** — `prompts/worker.md` wording (tone/strictness of the honesty and AI-disclosure rules) was
  written by me per the brief's instruction and needs your read-through before a real run.

## Abandoned / unverified / gaps

- **Nothing was abandoned.** All eight milestones (M0–M7) were completed; no milestone needed a
  revert.
- **UNVERIFIED AGAINST REAL API**: `--batch` mode in `scripts/dry_run.py` / `metered_batch_call` in
  `swarm50/metered.py` (D6). It is fully unit-tested against mocks but has never been run against a
  real Anthropic API key or the real Message Batches API — do this once, deliberately, before relying
  on it for a real dry run.
- **Known gaps / things a real run will exercise that tests don't fully cover:**
  - `scripts/smoke_test.py` and `scripts/context_probe.py` were left as-is (not touched); they still
    make one real metered call each and were never run in this session, per the ground rules.
  - The dry-run report's "stake as a share of balance" (D7) uses the balance at the moment of that
    specific call, which on a fresh cycle-1 wallet is effectively `starting_balance_usd` minus one
    call's cost — fine for its intended use, but worth knowing if this code is ever reused to analyze
    a later cycle's numbers.
  - A PR was opened automatically: https://github.com/farjad-ui/swarm50/pull/1 (`overnight-build` ->
    `main`), NOT merged.
  - `report/index.html`'s charts are intentionally simple (no zoom/pan/hover beyond SVG `<title>`
    tooltips) since no JS is allowed in the report per the brief.

## Pull the branch and run tests (Windows PowerShell)

```powershell
git fetch origin overnight-build
git checkout overnight-build
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

The branch `overnight-build` is pushed to `origin` and a pull request against `main` is open at
https://github.com/farjad-ui/swarm50/pull/1 (not merged — for you to review).
