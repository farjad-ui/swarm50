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
