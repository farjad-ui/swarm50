# Decisions / Needs Input

## 2026-09-18 — OVERNIGHT_BRIEF.md not found

I was asked to read `docs/OVERNIGHT_BRIEF.md` and execute it fully. That file does not exist:

- No `docs/` directory existed anywhere in the repo before this commit.
- The file is absent from the working tree on both `main` and `claude/laughing-wozniak-laeeb6`.
- There is no commit in the repo's history (`git log --all --diff-filter=A --name-only`) that ever added a file under `docs/`.
- There is no diff between `main` and `claude/laughing-wozniak-laeeb6` — the brief was never pushed to either branch.

The repo currently contains only the single "foundation" commit: the swarm50 scaffold
(`swarm50/ledger.py`, `metered.py`, `cfo.py`, `bets.py`, `queue.py`, `review.py`, `schemas.py`,
`state.py`, `config.py`, `exceptions.py`), prompts, scripts, tests, and config — per the README,
"no agents yet."

**I did not fabricate a brief or guess at overnight work**, since acting on an invented task list
against a real (if small) codebase risked doing the wrong thing or churning unwanted changes.

**Needed from you:** please add `docs/OVERNIGHT_BRIEF.md` (commit/push it to
`claude/laughing-wozniak-laeeb6` or `main`, or paste its contents in chat) and re-run/re-trigger
this task. I'll execute it fully and autonomously once it's available.

---

### D1 — M0 baseline and plumbing audit   [FYI]
Milestone: M0
What I decided: Baseline test run on a fresh venv (Python 3.11.15, `pip install -r requirements.txt`)
passed 44/44 before any changes. I audited `bets.py`, `review.py`, `cfo.py`, `queue.py` against the
M0 checklist in `OVERNIGHT_BRIEF.md`:
- `bet_events` is append-only with `no_update`/`no_delete` triggers, CHECK-constrained event types
  and actors; status/exposure are derived by folding events (`status_of`, `bets()`). Matches spec.
- Memo schema (`schemas.py::Memo`) has exactly the field list and types the brief specifies. Matches.
- `StrategistResponse` had `cycle_reasoning`, `memos` (0-3), `no_bet_reason` (required when empty),
  but was **missing** `bet_actions` and `work_orders` — these are added in M1 as the brief instructs.
- Guardrails (`cfo.py`) implement per-stake 35%, open exposure 60%, trading exposure 50%, all against
  balance (+ open exposure for the two exposure rules), writing a `blocked` event and never raising
  to the caller. Matches.
- Critic loop (`review.py`) implements approve->queue, revise/reject->one rebuttal->one final verdict,
  one repair retry on malformed JSON then a `malformed` event, and stops cleanly on
  `CycleCapExceeded`/`WalletEmpty`. Matches, **except** the `Rebuttal` schema used field names
  `action`/`memo` instead of the brief's verbatim `rebuttal.md` prompt fields `decision`/`revised_memo`
  and a `responses` list. Fixed in M1 (schema, `review.py`'s use of it, and `queue.py show`'s
  rendering of `rebutted`/`withdrawn` events were all updated together; existing tests in
  `tests/test_review.py` and `tests/test_bets.py` that referenced the old field names were updated
  to the new ones in the same commit).
- Queue CLI (`queue.py`) already has `list`, `show`, `approve`, `reject --reason`. Matches.
No large deviations required building anything from scratch; the foundation was solid. Only the
Rebuttal field-name mismatch above needed a fix, done under M1 since it required touching the
prompt/schema pair anyway.
Why: keeps the audit itself append-only, cheap engineering judgment.
Alternatives considered: leave `action`/`memo` as internal schema field names and translate to/from
`decision`/`revised_memo` only at the prompt-parsing boundary. Rejected as needless indirection --
the brief's prompt text is the source of truth for what the LLM will actually emit as JSON keys, so
the schema should use the same names throughout.
How to change it: `swarm50/schemas.py::Rebuttal`, `swarm50/review.py::_review_memo`.

### D2 — Convex arm's "scales steeply" reward is undefined   [NEEDS FARJAD]
Milestone: M1
What I decided: Shipped `prompts/objective_convex.md` verbatim from the brief, including the vague
"scales steeply with how far above $starting_balance you finish" language. I did not invent a concrete
formula (e.g. "10x the profit") on the owner's behalf.
Why: the brief explicitly says to leave the wording until the owner decides a reward he will actually
honour; inventing one risks the agents being told something the owner never agrees to pay out.
Alternatives considered: pick a default multiplier now so the convex arm is "fully specified"; rejected
because a fabricated commitment is worse than an honest gap, and the brief says so directly.
How to change it: `prompts/objective_convex.md` (the paragraph after "the budget for its next phase
scales steeply..."). No code changes needed once the wording is decided; `swarm50/prompts.py::render_objective`
substitutes `$total_days` and `$starting_balance` into whatever text is in the file.

### D3 — Memo schema text embedded in prompts via introspection, not a copy   [FYI]
Milestone: M1
What I decided: `$memo_schema` in `prompts/strategist.md` and `prompts/rebuttal.md` is filled by
`swarm50/schemas.py::memo_schema_text()`, which introspects `Memo.model_fields` at render time
(field name: Python type name), rather than a hand-typed JSON schema string hardcoded in `prompts.py`
(which the ground rules forbid) or duplicated by hand inside the .md files (which would drift from
`schemas.py` the first time a field is added).
Why: single source of truth; adding/renaming a Memo field automatically updates every prompt that cites
the schema, and it satisfies "no prompt text hardcoded in Python" since this is schema *data*, not
prose, and still lives in `schemas.py`, loaded via `string.Template` substitution in `prompts.py`.
Alternatives considered: pydantic's built-in `model_json_schema()` (verbose, full JSON Schema with
$defs, harder for the model to read at a glance); a hand-maintained schema block inside each prompt
.md file (rejected: two sources of truth).
How to change it: `swarm50/schemas.py::memo_schema_text()`.

### D4 — Rebuttal responses is a list of {objection, response} pairs   [FYI]
Milestone: M1
What I decided: Added `swarm50/schemas.py::Response` (objection/response pair) as the item type of
`Rebuttal.responses`, matching the brief's `rebuttal.md` output shape
`"responses": [ {"objection": "...", "response": "..."} ]` exactly.
Why: the brief specifies this shape verbatim in the prompt text; the schema must accept exactly what
the prompt asks the model to produce.
Alternatives considered: none; this was fully specified by the brief.
How to change it: `swarm50/schemas.py::Response`, `Rebuttal.responses`.

### D5 — State block additions for token rates and cap percentages   [FYI]
Milestone: M1
What I decided: Added two new lines to `swarm50/state.py::build_state`: `token rates by role: ...`
(role=model with input/output $-per-Mtok) and `caps: max_stake_pct=...% max_open_exposure_pct=...%
max_trading_exposure_pct=...%`, inserted right after the balance/exposure line and before "open bets:".
Why: the brief says "Update the state block to include the token rates per role and the cap
percentages, since the strategist prompt refers to them" but does not give an exact format.
Alternatives considered: put the rates/caps only in the strategist system prompt (via `$objective`-style
substitution) instead of the state block; rejected because the brief explicitly names the state block
as the place for this, and it needs to be visible to the critic too (whose prompt also implicitly
assumes the reader knows the caps, via "Rules" check #5).
How to change it: `swarm50/state.py::_role_rates`, `build_state`.

### D6 — Batch API support lives in metered.py, gated to the api backend, UNVERIFIED AGAINST REAL API   [FYI]
Milestone: M2
What I decided: Added `metered_batch_call()` to `swarm50/metered.py` (the only file allowed to touch
the Anthropic SDK), which submits one `client.messages.batches.create()` for N requests, polls
`batches.retrieve()` until `processing_status == "ended"`, and prices results via
`ledger.record_token_usage(..., discount=0.5)`. `ledger.cost_micro()`/`record_token_usage()` gained an
optional `discount` parameter (default `1.0`, a no-op) so this could be added without touching any
existing non-batch pricing path or test. `--batch` in `scripts/dry_run.py` raises `ValueError` if
`backend != "api"`. This code path is exercised ONLY against mocks (`tests/test_dryrun.py`,
`tests/test_metered.py`-style mocking of `anthropic.Anthropic`) and has never been run against the
real Batches API, per the ground rule against real API calls in this session.
Why: the brief requires `--batch` to use the real Batches API shape (submit/poll/retrieve), routed
through `metered.py`, at half price, and explicitly says to mark it `UNVERIFIED AGAINST REAL API`.
Alternatives considered: fake the discount by just running N calls sequentially and halving the
recorded cost after the fact (simpler, but doesn't exercise the actual Batches API request/poll/result
shape at all, which defeats the purpose of the flag existing); rejected.
How to change it: `swarm50/metered.py::_call_api_batch`, `metered_batch_call`, `BATCH_DISCOUNT`.
**UNVERIFIED AGAINST REAL API** — before using `--batch` for real, run it once against a real API key
outside this session and confirm the batch request/response shapes above still match the current
Anthropic SDK version pinned in `requirements.txt`.

### D7 — Dry-run report metric is "stake as share of *current* balance", not starting balance   [FYI]
Milestone: M2
What I decided: `dry_run_report.py`'s "mean/median stake as a share of balance by category" divides
each memo's `stake_usd` by that run's ledger balance at the moment the strategist responded (recorded
per-run as `balance_usd` in the JSONL), not by the fixed `starting_balance_usd` from config.
Why: on cycle 1 with a fresh wallet these are numerically almost identical (balance is starting balance
minus the cost of the one strategist call itself), but the balance-at-call-time is the actual number
the strategist could compute a percentage against, so it is the more meaningful denominator, and it
generalizes if this report code is ever pointed at a later cycle's dry runs.
Alternatives considered: divide by `config["starting_balance_usd"]` directly; simpler, but silently
wrong if the harness is ever run against a non-fresh wallet.
How to change it: `swarm50/dryrun.py::summarize` (uses `r["balance_usd"]`), `_record` (writes it).

### D8 — results/, artifacts/, report/ are git-ignored generated output   [FYI]
Milestone: M2
What I decided: Added `results/`, `artifacts/` (M4) and `report/` (M5) to `.gitignore`, alongside the
existing `state/`.
Why: all three are regenerated from the append-only DB (or, for `results/`, from mocked dry runs) and
contain potentially large or numerous files; committing them would bloat the repo with derived data
that the code can always reproduce.
Alternatives considered: commit at least one example `results/dryrun_*.jsonl` and `report/index.html`
as a demo artifact; decided against it to keep the repo's tracked contents to source only, matching how
`state/` (the ledger DB) was already treated.
How to change it: `.gitignore`.

### D9 — run_meta is its own append-only table, not folded into bet_events   [FYI]
Milestone: M3
What I decided: Added `swarm50/cycle.py::RunLog`, a second append-only table (`run_meta`, same
no-update/no-delete trigger pattern as `transactions` and `bet_events`) for the four events that are
NOT about one specific bet: `kickoff`, `cycle_summary`, `cycle_error`, `run_ended`.
Why: `bet_events.bet_id` is `NOT NULL`; a cycle-level or run-level event has no natural bet_id, and
overloading it with a sentinel value (`"__run__"`) would make `bets()`'s per-bet folding logic have to
special-case it forever. A separate table keeps both event logs simple and keeps the CHECK-constrained
event-type lists small and specific to what actually happens at each level.
Alternatives considered: one shared `events` table with a nullable `bet_id`; rejected because it would
require touching `bets.py`'s folding logic to skip null-bet_id rows everywhere, for no real benefit.
How to change it: `swarm50/cycle.py::RunLog`, `SCHEMA`, `RUN_EVENT_TYPES`.

### D10 — start_date lives in the kickoff event, not by rewriting config.yaml   [FYI]
Milestone: M3
What I decided: `python -m swarm50.cycle kickoff` does NOT rewrite `config.yaml`'s `start_date: null`
in place. Instead, the authoritative start date is stored once in the `kickoff` `run_meta` event's
payload, and `cycle_number()` always derives the cycle from that event, not from the config file.
Why: rewriting a YAML file from a running process is fragile (formatting/comments can be lost,
concurrent runs could race) and breaks the "config.yaml's cap values must not be touched by code"
spirit of the ground rules; keeping the start date as an event is consistent with "state is derived
from events, never stored and mutated" (ground rule 6) and survives config.yaml being reformatted or
regenerated.
Alternatives considered: read/modify/write `config.yaml` with `ruamel.yaml` to preserve comments;
works, but adds a dependency and a file-write side effect to a CLI whose only other writes are to the
SQLite DB. `start_date: null` in `config.yaml` is left purely as owner-facing documentation of the
field's existence and default.
How to change it: `swarm50/cycle.py::kickoff`, `cycle_number`.

### D11 — "Death" (insolvency) triggers only when the pre-call gate refuses the FIRST call of a cycle   [FYI]
Milestone: M3
What I decided: `swarm50/cycle.py::run` treats a `CycleCapExceeded`/`WalletEmpty` raised during the
strategist's own call (before any memo was proposed this cycle) as permanent insolvency: it writes a
`run_ended` event with reason `insolvent` and every future `run` call raises `CycleError`. The SAME
exception type raised later in the same cycle (e.g. mid critic-loop, after 1+ memos were already
proposed and written) is treated as an ordinary early stop: the cycle's `cycle_summary` records
`stopped`, but the run is NOT ended, and the next day's cycle can still be attempted.
Why: the brief's wording ("if the pre-call gate refuses the strategist call") describes the case where
the wallet cannot afford even one more call at all -- a dead wallet. `CycleCapExceeded` alone can also
fire mid-cycle purely because that day's `cycle_token_cap_usd` (a small, per-cycle allowance, currently
$0.75) is already spent on earlier calls this cycle, which resets automatically next cycle and is not
evidence the wallet itself is dead. Treating every mid-cycle cap hit as fatal would kill the whole
30-day run over a single expensive critic loop, which is far more aggressive than the brief intends.
Alternatives considered: only ever treat `WalletEmpty` (not `CycleCapExceeded`) as fatal, since it is
the ledger's actual "balance <= 0" signal; rejected because the very first call of a cycle CAN also
raise `CycleCapExceeded` if a single call's worst-case cost already exceeds the cycle cap (a config
mismatch), and that is just as fatal in practice as `WalletEmpty` -- there is no way to ever make
progress again under that config, so it should also end the run rather than retry forever.
How to change it: `swarm50/cycle.py::run`, the `except (CycleCapExceeded, WalletEmpty)` block
(the `counts["memos_proposed"] == 0 and counts["malformed"] == 0` condition is the "was this the very
first call" check).

### D12 — "hold" bet_action is a no-op; only "kill" writes an event   [FYI]
Milestone: M3
What I decided: In `swarm50/cycle.py::_apply_bet_actions`, a `bet_actions` entry with
`"action": "hold"` writes nothing to `bet_events`; only `"action": "kill"` writes a `killed` event
(or a `blocked` event if the target bet isn't currently `active`).
Why: "hold" means "leave this bet exactly as it is", which is already the derived status if no new
event is written; writing a `held` event with no status-changing effect would just be log noise on
every single cycle for every open bet the strategist explicitly chooses not to kill, and the brief's
`_STATUS` derivation in `bets.py` has no status for "held" to begin with.
Alternatives considered: add a `held` event type purely for the audit trail (M7's morning report /
M5's decision-log timeline would then show the strategist explicitly considered the bet each cycle);
rejected for now as unnecessary event-log volume, but noted here in case the owner wants that
visibility -- it would be a small, additive change (`EVENT_TYPES` in `bets.py` plus one line in
`_apply_bet_actions`).
How to change it: `swarm50/cycle.py::_apply_bet_actions`.
