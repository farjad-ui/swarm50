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
