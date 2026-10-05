# Plan 1a: Foundation (code fixes + money model) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- Fix the review's six code defects (spec §17).
- Lay the money foundation every later plan builds on:
  - `refund` transactions and idempotent platform credits
  - per-bucket budget caps and a hard run cap
  - the window score
  - configurable token limits

**Architecture:**
- All changes stay inside the existing modules (`ledger.py`, `bets.py`, `cycle.py`, `review.py`,
  `workers.py`, `queue.py`, `metered.py`), plus one new module, `swarm50/score.py`.
- The ledger keeps its append-only design. Buckets and the run cap are derived by grouping existing
  `token_cost` rows by their `agent` tag, so no new money table is needed.

**Tech Stack:** Python 3.11+, SQLite (stdlib `sqlite3`), pydantic, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-05-digital-products-pivot-design.md` (v3.2), sections §3.3, §7.5,
§7.6, §7.8, §16, §17. Roadmap: `docs/superpowers/plans/2026-10-05-roadmap.md`.

## Global Constraints
- **Append-only:** ledger, bet log, run log and every new table refuse UPDATE/DELETE with triggers.
- **No mutation:** state is derived by folding events, never stored and mutated.
- **Single calls:** every AI call is one system prompt plus one user message, with no server-side tools.
- **One gateway:** `swarm50/metered.py` is the only module that touches any AI SDK or the `claude` CLI.
- **No prompt text in `.py` files.**
- **No agent-facing code path writes** `deposit`, `adjustment`, `revenue` or `refund` transactions.
- **Money** is integer micro-dollars (`1 USD = 1_000_000`).
- **Platform:** Python 3.11+ on Windows and Linux; `pathlib`; UTF-8.
- **Commits:** each task ends with the FULL suite passing (`python -m pytest -q`), then one commit whose
  message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Where to work:** branch `digital-products-pivot`. Use the repo venv (`.venv\Scripts\python` on
  Windows). No real network calls in tests.

---

### Task 0: Baseline

**Files:** none

- [ ] **Step 1: Confirm branch and green suite**

Run (PowerShell, repo root):
```
git status -sb
.venv\Scripts\python -m pytest -q
```
Expected: `## digital-products-pivot`, and `91 passed`.

---

### Task 1: False insolvency only on a refused first strategist call (spec §17.1)

**Files:**
- Modify: `swarm50/ledger.py` (add `last_tx_id`, `spent_since` below `cycle_spend`)
- Modify: `swarm50/cycle.py` (function `run`: record `start_tx`; replace the insolvency condition)
- Modify: `tests/conftest.py` (add `scripted` helper)
- Test: `tests/test_cycle.py`, `tests/test_ledger.py`

**Interfaces:**
- Produces:
  - `Ledger.last_tx_id() -> int`
  - `Ledger.spent_since(tx_id: int, agent: str | None = None) -> bool`
  - `tests.conftest.scripted(*steps, model="big")`, a `metered_call` side effect that records real spend

- [ ] **Step 1: Add the `scripted` test helper to `tests/conftest.py`** (append at the end of the file)

```python
def scripted(*steps, model="big"):
    """side_effect for a patched metered_call. Each step is a response (dict or raw string) that is
    recorded as real spend of 1 input + 1 output token, like the real gateway, or an Exception that is
    raised before anything is spent (like a refused pre-call budget check)."""
    it = iter(steps)

    def _call(ledger, cycle, agent, role, messages, **kwargs):
        step = next(it)
        if isinstance(step, Exception):
            raise step
        ledger.record_token_usage(cycle, agent, model, 1, 1)
        return result(step)
    return _call
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_cycle.py`:
1. Change the import lines to:
   ```python
   from swarm50.exceptions import CycleCapExceeded, WalletEmpty
   from tests.conftest import CONFIG, memo, result, scripted
   ```
2. **Delete** the whole function `test_insolvency_ends_run_permanently` (it asserts the old, wrong
   behaviour: a cap hit ending the run).
3. Append:

```python
def _active_bet(betlog, bet_id="c0-1"):
    betlog.append(1, bet_id, "proposed", memo(), "strategist")
    betlog.append(1, bet_id, "critiqued", CRIT_APPROVE, "critic")
    betlog.append(1, bet_id, "human_approved", {}, "human")
    betlog.append(1, bet_id, "staked", {"stake_usd": 5, "category": "digital_product"}, "cfo")


def test_wallet_empty_on_first_strategist_call_ends_run(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = WalletEmpty("balance $0.000000")
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["stopped"] == "WalletEmpty: balance $0.000000"
    assert runlog.run_ended_event()["payload"]["reason"] == "insolvent"
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 19))


def test_cycle_cap_on_first_strategist_call_does_not_end_run(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = CycleCapExceeded("cycle 1 think: over cap")
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["stopped"] == "CycleCapExceeded: cycle 1 think: over cap"
    assert runlog.run_ended_event() is None


def test_worker_refused_after_no_bet_strategist_does_not_end_run(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    _active_bet(betlog)
    calls.side_effect = scripted(strategist(reason="nothing new", work_orders=[
        {"bet_id": "c0-1", "task": "write copy", "deliverable_type": "text", "max_tokens": 100}]))
    with patch("swarm50.workers.metered_call", side_effect=WalletEmpty("balance $0.000000")):
        summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["stopped"] == "WalletEmpty: balance $0.000000"
    assert runlog.run_ended_event() is None


def test_refused_repair_retry_does_not_end_run(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = scripted("not json at all", WalletEmpty("balance $0.000000"))
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert runlog.run_ended_event() is None
```

In `tests/test_ledger.py`, append:

```python
def test_spent_since_tracks_token_cost_rows_after_a_watermark(ledger):
    start = ledger.last_tx_id()
    assert not ledger.spent_since(start)
    ledger.stake_bet(1, "b", 1)                      # not a token cost
    assert not ledger.spent_since(start)
    ledger.record_token_usage(1, "critic", "big", 1, 1)
    assert ledger.spent_since(start)
    assert not ledger.spent_since(start, agent="strategist")
    ledger.record_token_usage(1, "strategist", "big", 1, 1)
    assert ledger.spent_since(start, agent="strategist")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest tests/test_cycle.py tests/test_ledger.py -q`
Expected: FAIL. `last_tx_id` is missing, and the cap/worker/repair tests see `run_ended` written.

- [ ] **Step 4: Implement**

In `swarm50/ledger.py`, add after `cycle_spend`:

```python
    def last_tx_id(self) -> int:
        """Id of the newest transaction (0 on an empty ledger): a watermark for spent_since."""
        return self._scalar("SELECT MAX(id) FROM transactions")

    def spent_since(self, tx_id, agent=None) -> bool:
        """True if any token_cost row (optionally only for `agent`) was written after `tx_id`."""
        sql, params = "SELECT COUNT(*) FROM transactions WHERE type='token_cost' AND id > ?", [tx_id]
        if agent is not None:
            sql += " AND agent = ?"
            params.append(agent)
        return self._scalar(sql, *params) > 0
```

In `swarm50/cycle.py`, function `run`:
1. Directly under `balance_in = ledger.balance()` add:
   ```python
       start_tx = ledger.last_tx_id()
   ```
2. Replace the block from the comment `# the pre-call gate refused a call this cycle` down to and including
   the `runlog.append("run_ended", ...)` line with:
   ```python
           # Only a refused FIRST strategist call (no strategist spend since this run started) means the
           # wallet can't fund the run: that is "Death". A cap hit, a refused repair retry, or a refused
           # worker/critic call just ends this cycle early (spec §17.1).
           detail = f"{type(e).__name__}: {e}"
           counts["memos_proposed"] = len(proposed)
           if isinstance(e, WalletEmpty) and not ledger.spent_since(start_tx, agent="strategist"):
               runlog.append("run_ended", {"reason": "insolvent", "detail": detail}, cycle=cycle)
   ```

- [ ] **Step 5: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass (91 − 1 deleted + 5 new = 95).

- [ ] **Step 6: Commit**

```
git add swarm50/ledger.py swarm50/cycle.py tests/conftest.py tests/test_cycle.py tests/test_ledger.py
git commit -m "Fix false insolvency: only a refused first strategist call ends the run" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `refused` events no longer hide bets (spec §17.2)

**Files:**
- Modify: `swarm50/bets.py` (`EVENT_TYPES`)
- Modify: `swarm50/cycle.py` (`_apply_bet_actions`)
- Modify: `swarm50/workers.py` (`execute_work_orders`)
- Test: `tests/test_workers.py`, `tests/test_cycle.py`, `tests/test_bets.py`

**Interfaces:**
- Produces:
  - new bet event types `refused` (never changes a bet's status), `fee_charged` (payload
    `{"fee_usd": float}`) and `ad_result_entered` (payload
    `{"spend_usd": float, "attributed_sales_usd": float, "start_cycle": int, "end_cycle": int}`)
  - refusals carry the payload `{"rule": str, "status": str, ...}`

- [ ] **Step 1: Write the failing tests**

In `tests/test_workers.py`:
- In `test_order_on_unstaked_bet_is_blocked`, change the last assert to:
  ```python
      assert ev["event_type"] == "refused" and ev["payload"]["rule"] == "work_order_on_non_staked_bet"
  ```
- In `test_order_on_unknown_bet_is_blocked`, change the last assert to:
  ```python
      assert betlog.events("ghost")[-1]["event_type"] == "refused"
      assert betlog.bets()["ghost"]["status"] == "none"
  ```
- Append:
  ```python
  def test_refused_order_does_not_hide_a_queued_bet(ledger, betlog):
      betlog.append(1, "q", "proposed", memo(), "strategist")
      betlog.append(1, "q", "critiqued", {"verdict": "approve"}, "critic")
      assert "q" in betlog.queued()
      with patch("swarm50.workers.metered_call") as m:
          execute_work_orders(ledger, betlog, 2, [{"bet_id": "q", "task": "prep listing",
                                                   "deliverable_type": "text", "max_tokens": 10}])
      m.assert_not_called()
      assert "q" in betlog.queued()
  ```

In `tests/test_cycle.py`, in `test_kill_action_on_non_active_bet_is_blocked_not_raised`, replace the last
line with:
```python
    assert betlog.events("nonexistent")[-1]["event_type"] == "refused"
    assert betlog.bets()["nonexistent"]["status"] == "none"
```

In `tests/test_bets.py`, append:
```python
def test_refused_fee_and_ad_events_never_change_status(betlog):
    betlog.append(1, "a", "proposed", memo(), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    for t, p in (("refused", {"rule": "x", "status": "queued"}), ("fee_charged", {"fee_usd": 0.2}),
                 ("ad_result_entered", {"spend_usd": 3, "attributed_sales_usd": 0,
                                        "start_cycle": 1, "end_cycle": 3})):
        betlog.append(2, "a", t, p, "cfo")
        assert betlog.bets()["a"]["status"] == "queued"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_workers.py tests/test_cycle.py tests/test_bets.py -q`
Expected: FAIL (`refused` violates the CHECK constraint; events are still `blocked`).

- [ ] **Step 3: Implement**

In `swarm50/bets.py`, replace `EVENT_TYPES` with:
```python
EVENT_TYPES = ("proposed", "critiqued", "rebutted", "withdrawn", "final_verdict", "human_approved",
               "human_rejected", "staked", "return_recorded", "killed", "closed", "blocked", "malformed",
               "work_completed", "human_task_requested", "human_task_done",
               # v3: a refusal that must NOT change status; listing fees; owner-entered ad results
               "refused", "fee_charged", "ad_result_entered")
```
(`status_of` needs no change: event types not in `_STATUS` leave the status as it is.)

In `swarm50/cycle.py`, `_apply_bet_actions`: change `"blocked",` to `"refused",` in the
`betlog.append(...)` call and update its docstring's last sentence to: `Actions on a bet that isn't
open write a `refused` event (status unchanged) and never raise.`

In `swarm50/workers.py`, `execute_work_orders`: change `"blocked",` to `"refused",` in the refusal
`betlog.append(...)` and change the docstring's "writes a `blocked` event" to "writes a `refused` event".

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```
git add swarm50/bets.py swarm50/cycle.py swarm50/workers.py tests/test_workers.py tests/test_cycle.py tests/test_bets.py
git commit -m "Write refused events that leave bet status unchanged" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Unique bet IDs `c{cycle}-r{round}-{kind}{i}` (spec §16, §17.4)

**Files:**
- Modify: `swarm50/bets.py` (add `BetLog.next_id`)
- Modify: `swarm50/review.py` (`review_memos`)
- Test: `tests/test_bets.py`, `tests/test_review.py`, `tests/test_cycle.py`

**Interfaces:**
- Produces:
  - `BetLog.next_id(cycle: int, round_: int, kind: str) -> str`, where kind is `"m"` (memo), `"b"` (core
    build), `"a"` (adaptation) or `"w"` (wildcard)
  - `review_memos(ledger, betlog, cycle, memos, state, proposed=None, round_=1)`

- [ ] **Step 1: Update existing ID expectations, then write the failing tests**

Run (Git Bash or WSL; edits two files in place):
```
sed -i 's/"c1-1"/"c1-r1-m1"/g; s/"c1-2"/"c1-r1-m2"/g' tests/test_review.py tests/test_cycle.py
```
(PowerShell alternative: open both files and replace `"c1-1"` → `"c1-r1-m1"` and `"c1-2"` → `"c1-r1-m2"`.
Leave `"c0-1"` and `"c2-strategist"` alone.)

Append to `tests/test_bets.py`:
```python
def test_next_id_is_sequential_per_prefix_and_never_reuses(betlog):
    assert betlog.next_id(3, 1, "m") == "c3-r1-m1"
    betlog.append(3, "c3-r1-m1", "proposed", memo(), "strategist")
    assert betlog.next_id(3, 1, "m") == "c3-r1-m2"
    assert betlog.next_id(3, 2, "m") == "c3-r2-m1"
    assert betlog.next_id(3, 1, "b") == "c3-r1-b1"
    betlog.append(13, "c13-r1-m1", "proposed", memo(), "strategist")   # c13 must not count for c1
    assert betlog.next_id(1, 1, "m") == "c1-r1-m1"
```

Append to `tests/test_cycle.py`:
```python
def test_force_rerun_never_merges_bet_ids(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(memo())), result(CRIT_APPROVE),
                         result(strategist(memo(title="again"))), result(CRIT_APPROVE)]
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18), force=True)
    bets = betlog.bets()
    assert bets["c1-r1-m1"]["memo"]["title"] == "Sell a prompt pack"
    assert bets["c1-r1-m2"]["memo"]["title"] == "again"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_bets.py tests/test_review.py tests/test_cycle.py -q`
Expected: FAIL (`next_id` missing; reviews still create `c1-1`).

- [ ] **Step 3: Implement**

In `swarm50/bets.py`, add this method to `class BetLog` (after `append`):
```python
    def next_id(self, cycle, round_, kind) -> str:
        """Unique bet id `c{cycle}-r{round}-{kind}{i}` (spec §16). `i` continues after the highest id
        already used with the same prefix, so a --force rerun never merges into earlier bets."""
        prefix = f"c{cycle}-r{round_}-{kind}"
        used = [int(b[len(prefix):]) for b in self.bets()
                if b.startswith(prefix) and b[len(prefix):].isdigit()]
        return f"{prefix}{max(used, default=0) + 1}"
```

In `swarm50/review.py`, replace `review_memos` with:
```python
def review_memos(ledger, betlog, cycle, memos, state, proposed=None, round_=1) -> list[str]:
    """Runs the critic loop (approve / revise-rebuttal-final / reject) on each new memo in order.
    Returns the list of bet_ids created, in proposal order. `proposed`, if given, is mutated in
    place as each bet_id is proposed, so a caller sees partial progress if a later memo's critic
    loop raises (e.g. mid-cycle budget exhaustion)."""
    proposed = proposed if proposed is not None else []
    for memo in memos:
        bet_id = betlog.next_id(cycle, round_, "m")
        betlog.append(cycle, bet_id, "proposed", memo.model_dump(), "strategist")
        proposed.append(bet_id)
        _review_memo(ledger, betlog, cycle, bet_id, memo, state)
    return proposed
```

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```
git add swarm50/bets.py swarm50/review.py tests/test_bets.py tests/test_review.py tests/test_cycle.py
git commit -m "Give bets unique round-scoped ids so reruns never merge" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Queue commands raise `QueueError` instead of exiting (spec §17.5)

**Files:**
- Modify: `swarm50/queue.py`
- Test: `tests/test_queue.py` (new)

**Interfaces:**
- Produces: `swarm50.queue.QueueError(Exception)`, raised by `approve`, `record_return`, `close`,
  `cmd_show` and `_bet_cycle`. Only `main()` turns it into an exit.

- [ ] **Step 1: Write the failing tests** (`tests/test_queue.py`)

```python
import pytest

from swarm50 import queue
from tests.conftest import memo


def test_approve_unknown_bet_raises_instead_of_exiting(ledger, betlog):
    with pytest.raises(queue.QueueError, match="unknown bet nope"):
        queue.approve(ledger, betlog, "nope")


def test_approve_non_queued_bet_raises(ledger, betlog):
    betlog.append(1, "p", "proposed", memo(), "strategist")
    with pytest.raises(queue.QueueError, match="pending_critique, not queued"):
        queue.approve(ledger, betlog, "p")


def test_record_return_and_close_unknown_bet_raise(ledger, betlog):
    with pytest.raises(queue.QueueError):
        queue.record_return(ledger, betlog, "nope", 1.0)
    with pytest.raises(queue.QueueError):
        queue.close(ledger, betlog, "nope")


def test_cli_turns_queue_error_into_exit_message(monkeypatch, ledger):
    monkeypatch.setattr(queue, "Ledger", lambda: ledger)
    with pytest.raises(SystemExit) as exc:
        queue.main(["approve", "nope"])
    assert "unknown bet nope" in str(exc.value)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_queue.py -q`
Expected: FAIL (`QueueError` missing; `sys.exit` raises `SystemExit` from `approve`).

- [ ] **Step 3: Implement** (in `swarm50/queue.py`)

Add, after the imports:
```python
class QueueError(Exception):
    """A queue command can't proceed (unknown bet, wrong status). Only main() turns it into an exit."""
```

Replace every `sys.exit(f"unknown bet {bet_id}")` in `_bet_cycle`, `approve`, `record_return`, `close` and
`cmd_show` with `raise QueueError(f"unknown bet {bet_id}")`, and in `approve` replace
`sys.exit(f"{bet_id} is {bet['status']}, not queued")` with
`raise QueueError(f"{bet_id} is {bet['status']}, not queued")`.

In `main`, move everything after `betlog = BetLog(ledger)` into a new function and call it inside a try:
```python
def _dispatch(a, ledger, betlog):
    if a.cmd == "list":
        cmd_list(ledger, betlog)
    elif a.cmd == "show":
        cmd_show(ledger, betlog, a.bet_id)
    elif a.cmd == "approve":
        if approve(ledger, betlog, a.bet_id):
            print(f"staked {a.bet_id}; balance now {fmt_usd(ledger.balance())}")
        else:
            print(f"BLOCKED: {json.dumps(betlog.events(a.bet_id)[-1]['payload'], indent=1)}")
    elif a.cmd == "reject":
        reject(ledger, betlog, a.bet_id, a.reason)
        print(f"rejected {a.bet_id}")
    elif a.cmd == "record-return":
        record_return(ledger, betlog, a.bet_id, a.amount_usd, type=a.type, note=a.note)
        print(f"recorded {a.type} ${a.amount_usd} on {a.bet_id}; balance now {fmt_usd(ledger.balance())}")
    elif a.cmd == "close":
        close(ledger, betlog, a.bet_id, note=a.note)
        print(f"closed {a.bet_id}")
    elif a.cmd == "tasks":
        if a.tasks_cmd == "list":
            cmd_tasks_list(betlog)
        elif a.tasks_cmd == "done":
            cmd_tasks_done(betlog, a.task_id, a.note)
```
and end `main` with:
```python
    ledger = Ledger()
    betlog = BetLog(ledger)
    try:
        _dispatch(a, ledger, betlog)
    except QueueError as e:
        sys.exit(f"error: {e}")
```

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```
git add swarm50/queue.py tests/test_queue.py
git commit -m "Raise QueueError from queue commands; only the CLI exits" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `stop_reason`, no repair retry on truncation, configurable token limits (spec §17.6, §7.8)

**Files:**
- Modify: `swarm50/metered.py` (`Result`, `_call_api`, `_call_cli`, `_call_api_batch`)
- Modify: `swarm50/review.py` (limits, `_ask`, `_ask_parsed`, call sites)
- Modify: `config.yaml`, `tests/conftest.py` (`CONFIG`)
- Test: `tests/test_review.py`, `tests/test_metered.py`

**Interfaces:**
- Produces:
  - `Result.stop_reason: str | None` (last field, default `None`)
  - config keys `strategist_max_tokens` (default 6000) and `critic_max_tokens` (default 2000)
  - a truncated response yields a `malformed` payload with `{"truncated": True, "max_tokens": int, ...}`
    after **one** call

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review.py`:
```python
from swarm50.bets import BetLog
from swarm50.metered import Result, Usage


def test_truncated_response_is_not_retried(ledger, betlog, calls):
    cut = Result(text='{"cycle_reasoning": "r", "memos": [{"title": "half', usage=Usage(1, 1),
                 model="big", backend="api", reported_cost_usd=None, stop_reason="max_tokens")
    calls.side_effect = [cut]
    run_cycle(ledger, betlog, 1)
    assert calls.call_count == 1
    ev = betlog.events()[0]
    assert ev["event_type"] == "malformed" and ev["payload"]["truncated"] is True


def test_token_limits_come_from_config(make_ledger, calls):
    led = make_ledger(strategist_max_tokens=1234, critic_max_tokens=321)
    calls.side_effect = [result(strategist(memo())), result(CRIT_APPROVE)]
    run_cycle(led, BetLog(led), 1)
    assert calls.call_args_list[0].kwargs["max_tokens"] == 1234
    assert calls.call_args_list[1].kwargs["max_tokens"] == 321
```

Append to `tests/test_metered.py`:
```python
def test_api_result_carries_stop_reason(ledger):
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        resp = fake_response(input_tokens=1, output_tokens=1)
        resp.stop_reason = "max_tokens"
        cls.return_value.messages.create.return_value = resp
        assert metered_call(ledger, 1, "a", "worker", MSGS).stop_reason == "max_tokens"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_review.py tests/test_metered.py -q`
Expected: FAIL (`Result` has no `stop_reason`; limits are hard-coded).

- [ ] **Step 3: Implement**

`swarm50/metered.py`:
- In `class Result`, add as the last field:
  ```python
      stop_reason: str | None = None   # "end_turn", "max_tokens", ... when the backend reports it
  ```
- `_call_api` return line becomes:
  ```python
      return Result(text, _usage_from(resp.usage), getattr(resp, "model", model), "api", None, resp,
                    stop_reason=getattr(resp, "stop_reason", None))
  ```
- `_call_cli` return line becomes:
  ```python
      return Result(data.get("result", ""), _usage_from(data.get("usage")), used, "claude_cli", cost, data, note,
                    stop_reason=data.get("stop_reason"))
  ```
- In `_call_api_batch`, the `by_id[entry.custom_id] = Result(...)` call gains
  `stop_reason=getattr(msg, "stop_reason", None)` as its last keyword argument.

`swarm50/review.py`:
- Replace the two constants with:
  ```python
  STRATEGIST_MAX_TOKENS = 6000   # defaults; config strategist_max_tokens / critic_max_tokens override
  CRITIC_MAX_TOKENS = 2000


  def _limit(config, key, default) -> int:
      return int(config.get(key, default))
  ```
- Replace `_ask` and `_ask_parsed` with:
  ```python
  def _ask(ledger, cycle, agent, role, system, user, max_tokens):
      return metered_call(ledger, cycle, agent, role, [{"role": "user", "content": user}],
                          system=system, max_tokens=max_tokens)


  def _ask_parsed(ledger, cycle, agent, role, system, user, model_cls, max_tokens):
      """One call plus ONE repair retry that quotes the validation error. Returns (parsed, None) or
      (None, info). A response cut off at max_tokens is not retried: a repair can't fix truncation."""
      res = _ask(ledger, cycle, agent, role, system, user, max_tokens)
      text = res.text
      try:
          return parse_model(model_cls, text), None
      except ValueError as first:
          if res.stop_reason == "max_tokens":
              return None, {"schema": model_cls.__name__, "error": str(first), "response": text,
                            "truncated": True, "max_tokens": max_tokens}
          repair = (f"{user}\n\n## Validation error in your previous response\n{first}\n\n"
                    f"## Your previous response\n{text}")
          text2 = _ask(ledger, cycle, agent, role, system, repair, max_tokens).text
          try:
              return parse_model(model_cls, text2), None
          except ValueError as second:
              return None, {"schema": model_cls.__name__, "first_error": str(first), "first_response": text,
                            "error": str(second), "response": text2}
  ```
- In `_review_memo`, replace each `CRITIC_MAX_TOKENS` argument with
  `_limit(config, "critic_max_tokens", CRITIC_MAX_TOKENS)`, and the `STRATEGIST_MAX_TOKENS` argument with
  `_limit(config, "strategist_max_tokens", STRATEGIST_MAX_TOKENS)`.
- In `call_strategist`, replace `STRATEGIST_MAX_TOKENS` with
  `_limit(ledger.config, "strategist_max_tokens", STRATEGIST_MAX_TOKENS)`.

`config.yaml`: under `worker_max_tokens`, add:
```yaml
strategist_max_tokens: 6000      # spec §7.8; a cut-off response is never repair-retried
critic_max_tokens: 2000
```
`tests/conftest.py` `CONFIG`: add `"strategist_max_tokens": 6000, "critic_max_tokens": 2000,`.

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```
git add swarm50/metered.py swarm50/review.py config.yaml tests/conftest.py tests/test_review.py tests/test_metered.py
git commit -m "Expose stop_reason; skip repair on truncation; configurable token limits" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `refund` type, `external_id`, idempotent platform entries (spec §7.6, §16)

**Files:**
- Modify: `swarm50/exceptions.py` (add `LedgerSchemaOutdated`)
- Modify: `swarm50/ledger.py` (`TYPES`, `SCHEMA`, `MIGRATIONS`, unique index, schema guard,
  `record_platform_entry`, positive-amount guard in `record_return`)
- Test: `tests/test_ledger.py`

**Interfaces:**
- Produces:
  - `Ledger.record_platform_entry(cycle, type, amount_usd, external_id, bet_id=None, note=None) -> bool`,
    where `type` is `"revenue"` (amount ≥ 0) or `"refund"` (amount ≤ 0). It returns `False` without
    writing if `external_id` was already recorded. **Only ingest code (Plans 1d and 2) may call it.**
  - `swarm50.exceptions.LedgerSchemaOutdated`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_ledger.py`)

```python
def test_platform_entries_are_idempotent_by_external_id(ledger):
    assert ledger.record_platform_entry(5, "revenue", 8.75, "etsy:receipt:1", bet_id="c2-r1-b1")
    assert not ledger.record_platform_entry(5, "revenue", 8.75, "etsy:receipt:1")   # same sale again
    assert ledger.record_platform_entry(6, "refund", -8.75, "etsy:refund:1", bet_id="c2-r1-b1")
    assert ledger.balance() == 50 * MICRO                                            # +8.75 -8.75
    assert ledger._scalar("SELECT COUNT(*) FROM transactions WHERE external_id IS NOT NULL") == 2


def test_platform_entry_sign_and_type_are_validated(ledger):
    with pytest.raises(ValueError):
        ledger.record_platform_entry(1, "revenue", -1, "x:1")
    with pytest.raises(ValueError):
        ledger.record_platform_entry(1, "refund", 1, "x:2")
    with pytest.raises(ValueError):
        ledger.record_platform_entry(1, "deposit", 1, "x:3")


def test_record_return_rejects_non_positive_amounts(ledger):
    with pytest.raises(ValueError):
        ledger.record_return(1, "b", -5, "revenue")


def test_db_with_old_type_check_is_refused(tmp_path):
    from tests.conftest import CONFIG
    from swarm50.exceptions import LedgerSchemaOutdated
    from swarm50.ledger import Ledger
    db = tmp_path / "v2.db"
    with sqlite3.connect(db) as c:
        c.executescript("CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,"
                        " cycle INTEGER NOT NULL, type TEXT NOT NULL CHECK (type IN ('deposit', 'token_cost')),"
                        " amount_micro INTEGER NOT NULL);")
    with pytest.raises(LedgerSchemaOutdated):
        Ledger(CONFIG, db)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_ledger.py -q`
Expected: FAIL (`record_platform_entry` and `LedgerSchemaOutdated` missing).

- [ ] **Step 3: Implement**

`swarm50/exceptions.py`, append:
```python
class LedgerSchemaOutdated(Exception):
    """The DB predates a transaction type the code needs. No real run has started yet (spec §16), so
    the fix is a fresh state/ledger.db, never an in-place edit of an append-only table."""
```

`swarm50/ledger.py`:
- Import `sqlite3` is already present. Add `LedgerSchemaOutdated` to the `from .exceptions import ...` line.
- Replace `TYPES` with:
  ```python
  TYPES = ("deposit", "token_cost", "bet_stake", "bet_return", "revenue", "adjustment", "refund")
  ```
- In `SCHEMA`'s `CREATE TABLE`, change the last column line `backend             TEXT` to
  `backend             TEXT,` and add a new last line `external_id         TEXT`. Do **not** put the
  unique index in `SCHEMA`: older DBs only gain the column during `_migrate`, so the index is created
  there, after the migration. The final `_migrate` is:
  ```python
      def _migrate(self):
          have = {r["name"] for r in self.conn.execute("PRAGMA table_info(transactions)")}
          with self.conn:
              for col, typ in MIGRATIONS.items():
                  if col not in have:
                      self.conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typ}")
              self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS tx_external_id "
                                "ON transactions(external_id) WHERE external_id IS NOT NULL")
  ```
  (So `SCHEMA` gets the `external_id TEXT` column but **no** index line.)
- Add `"external_id": "TEXT",` to `MIGRATIONS`.
- In `__init__`, call `self._check_types()` right after `self.conn.executescript(SCHEMA)`:
  ```python
      def _check_types(self):
          row = self.conn.execute(
              "SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'").fetchone()
          if row and "CHECK" in row["sql"] and "'refund'" not in row["sql"]:
              raise LedgerSchemaOutdated("transactions table predates the 'refund' type; "
                                         "start a fresh state/ledger.db (no real run has started)")
  ```
- Add after `record_return`:
  ```python
      def record_platform_entry(self, cycle, type, amount_usd, external_id, bet_id=None, note=None) -> bool:
          """Revenue (>= 0) or refund (<= 0) reported by a platform API, written at most once per
          external_id (e.g. 'etsy:receipt:123'). Returns False, writing nothing, on a repeat.
          Ingest-only: no agent-facing code path may call this (spec §7.6)."""
          if type not in ("revenue", "refund"):
              raise ValueError(f"type must be revenue or refund, got {type!r}")
          amount = usd_to_micro(amount_usd)
          if (type == "revenue" and amount < 0) or (type == "refund" and amount > 0):
              raise ValueError(f"{type} amount has the wrong sign: {amount_usd}")
          try:
              self._insert(cycle, type, amount, external_id=external_id, bet_id=bet_id, note=note)
          except sqlite3.IntegrityError:
              return False
          return True
  ```
- In `record_return`, after the type check add:
  ```python
          if usd_to_micro(amount_usd) <= 0:
              raise ValueError(f"amount must be positive, got {amount_usd}")
  ```

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass (the existing `test_migration_from_previous_schema` still passes: its old table has
no CHECK, so it is migrated, not refused).

- [ ] **Step 5: Commit**

```
git add swarm50/exceptions.py swarm50/ledger.py tests/test_ledger.py
git commit -m "Add refund type and idempotent platform entries keyed by external_id" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Budget buckets and the hard run cap (spec §3.3, §7.8)

**Files:**
- Modify: `swarm50/exceptions.py` (add `RunCapExceeded`)
- Modify: `swarm50/ledger.py` (bucket map, `cycle_spend(cycle, bucket=None)`, `bucket_cap_micro`,
  `ai_spend`, `assert_can_spend(cycle, cost, agent=None)`, `record_token_usage` checks; remove
  `cycle_cap_micro`)
- Modify: `swarm50/metered.py` (pass `agent` to `assert_can_spend` in `metered_call` and `metered_batch_call`)
- Modify: `config.yaml`, `tests/conftest.py`
- Test: `tests/test_ledger.py`

**Interfaces:**
- Produces:
  - `swarm50.ledger.bucket_of(agent: str | None) -> str`, returning one of
    `"think" | "build" | "image" | "reply"`
  - `Ledger.cycle_spend(cycle, bucket=None) -> int`
  - `Ledger.bucket_cap_micro(cycle, bucket) -> int`
  - `Ledger.ai_spend() -> int`
  - `Ledger.assert_can_spend(cycle, cost_micro, agent=None)`
  - `swarm50.exceptions.RunCapExceeded(CycleCapExceeded)`
  - config keys `cycle_caps_usd: {think, build, image, reply}`, `discovery_cycles`,
    `discovery_cycle_think_cap_usd` and `run_ai_cap_usd`, replacing `cycle_token_cap_usd`
- Agent names later plans must use:
  - **think bucket:** `strategist`, `critic`, `analyst`
  - **build bucket:** `worker` and anything starting with `studio_`
  - **image bucket:** `image`
  - **reply bucket:** `reply`
  - any other name counts as think

- [ ] **Step 1: Update config, then write the failing tests**

`config.yaml`: replace the line `cycle_token_cap_usd: 0.75` with:
```yaml
cycle_caps_usd:                  # per-cycle AI spend caps by budget bucket (spec §3.3, §7.8)
  think: 0.75                    # strategist, critic, analyst
  build: 1.00                    # worker + studio_* roles
  image: 0.75
  reply: 0.15
discovery_cycles: 7              # cycles 1..7 use the discovery think cap
discovery_cycle_think_cap_usd: 1.50
run_ai_cap_usd: 75               # HARD cap on all AI + image spend for the whole run
```
and set `starting_balance_usd: 100` and `total_days: 90` (spec §7.8).

`tests/conftest.py` `CONFIG`: replace `"cycle_token_cap_usd": 0.75,` with:
```python
    "cycle_caps_usd": {"think": 0.75, "build": 1.00, "image": 0.75, "reply": 0.15},
    "discovery_cycles": 0,               # tests opt in; 0 keeps the plain 0.75 think cap on cycle 1
    "discovery_cycle_think_cap_usd": 1.50,
    "run_ai_cap_usd": 75,
```

Append to `tests/test_ledger.py`:
```python
from swarm50.exceptions import RunCapExceeded
from swarm50.ledger import bucket_of


def test_bucket_of_maps_agents():
    assert [bucket_of(a) for a in ("strategist", "critic", "analyst", "worker", "studio_builder",
                                   "image", "reply", "a", None)] == \
        ["think", "think", "think", "build", "build", "image", "reply", "think", "think"]


def test_buckets_are_isolated(ledger):
    ledger.record_token_usage(1, "strategist", "big", 0, 50_000)      # 50k out @ $15/M = $0.75: think full
    with pytest.raises(CycleCapExceeded):
        ledger.assert_can_spend(1, 1, agent="critic")
    ledger.assert_can_spend(1, 1_000_000, agent="worker")             # build has its own $1.00
    ledger.assert_can_spend(1, 750_000, agent="image")
    ledger.assert_can_spend(1, 150_000, agent="reply")
    assert ledger.cycle_spend(1, "think") == 750_000 and ledger.cycle_spend(1, "build") == 0
    assert ledger.cycle_spend(1) == 750_000


def test_discovery_cycles_use_the_higher_think_cap(make_ledger):
    led = make_ledger(discovery_cycles=7)
    led.assert_can_spend(3, 1_500_000, agent="strategist")
    with pytest.raises(CycleCapExceeded):
        led.assert_can_spend(3, 1_500_001, agent="strategist")
    with pytest.raises(CycleCapExceeded):
        led.assert_can_spend(8, 750_001, agent="strategist")          # operating mode again


def test_run_cap_is_hard_across_cycles_and_buckets(make_ledger):
    led = make_ledger(run_ai_cap_usd=1.0)
    for cycle in (1, 2):
        led.record_token_usage(cycle, "worker", "big", 0, 30_000)     # $0.45 each, $0.90 total
    with pytest.raises(RunCapExceeded):
        led.assert_can_spend(3, 100_001, agent="image")
    led.assert_can_spend(3, 100_000, agent="image")                   # exactly at the run cap


def test_record_token_usage_raises_after_writing_when_bucket_overrun(ledger):
    with pytest.raises(CycleCapExceeded):
        ledger.record_token_usage(2, "reply", "big", 0, 20_000)       # $0.30 > $0.15 reply cap
    assert ledger.cycle_spend(2, "reply") == 300_000                  # the real spend is still recorded
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_ledger.py -q`
Expected: FAIL (`bucket_of`/`RunCapExceeded` missing; `cycle_token_cap_usd` KeyError).

- [ ] **Step 3: Implement**

`swarm50/exceptions.py`, append:
```python
class RunCapExceeded(CycleCapExceeded):
    """The hard whole-run AI spend cap (run_ai_cap_usd) would be passed. Subclasses CycleCapExceeded so
    every existing handler stops the cycle cleanly; it never ends the run as insolvent."""
```

`swarm50/ledger.py`:
- Add `RunCapExceeded` to the exceptions import.
- Under `MICRO = 1_000_000` add:
  ```python
  AGENT_BUCKET = {"strategist": "think", "critic": "think", "analyst": "think",
                  "worker": "build", "image": "image", "reply": "reply"}


  def bucket_of(agent) -> str:
      """Budget bucket for an agent tag (spec §3.3). studio_* roles build; unknown agents think."""
      if agent in AGENT_BUCKET:
          return AGENT_BUCKET[agent]
      if agent and agent.startswith("studio_"):
          return "build"
      return "think"
  ```
- Delete the `cycle_cap_micro` property. Add in its place:
  ```python
      def bucket_cap_micro(self, cycle, bucket) -> int:
          if bucket == "think" and cycle <= int(self.config.get("discovery_cycles", 0)):
              return usd_to_micro(self.config["discovery_cycle_think_cap_usd"])
          return usd_to_micro(self.config["cycle_caps_usd"][bucket])

      @property
      def run_cap_micro(self) -> int:
          return usd_to_micro(self.config["run_ai_cap_usd"])
  ```
- Replace `cycle_spend` with:
  ```python
      def cycle_spend(self, cycle, bucket=None) -> int:
          """Token spend in `cycle`, in micro-dollars: all buckets, or only `bucket`."""
          rows = self.conn.execute("SELECT agent, -SUM(amount_micro) s FROM transactions "
                                   "WHERE type='token_cost' AND cycle=? GROUP BY agent", (cycle,))
          return sum(r["s"] for r in rows if bucket is None or bucket_of(r["agent"]) == bucket)

      def ai_spend(self) -> int:
          """All AI + image spend across the whole run, in micro-dollars."""
          return -self._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")
  ```
- Replace `assert_can_spend` with:
  ```python
      def assert_can_spend(self, cycle, cost_micro, agent=None):
          """Pre-flight check for a projected AI cost. Raises without writing."""
          bal = self.balance()
          if bal <= 0 or cost_micro > bal:
              raise WalletEmpty(f"balance {fmt_usd(bal)}, need {fmt_usd(cost_micro)}")
          bucket = bucket_of(agent)
          projected, cap = self.cycle_spend(cycle, bucket) + cost_micro, self.bucket_cap_micro(cycle, bucket)
          if projected > cap:
              raise CycleCapExceeded(f"cycle {cycle} {bucket}: {fmt_usd(projected)} > cap {fmt_usd(cap)}")
          if self.ai_spend() + cost_micro > self.run_cap_micro:
              raise RunCapExceeded(f"run AI spend {fmt_usd(self.ai_spend() + cost_micro)} "
                                   f"> cap {fmt_usd(self.run_cap_micro)}")
  ```
- In `record_token_usage`, replace the two lines that check `self.cycle_spend(cycle) > self.cycle_cap_micro`
  (the `if` and its `raise`) with:
  ```python
          bucket = bucket_of(agent)
          if self.cycle_spend(cycle, bucket) > self.bucket_cap_micro(cycle, bucket):
              raise CycleCapExceeded(f"cycle {cycle} {bucket}: {fmt_usd(self.cycle_spend(cycle, bucket))} "
                                     f"> cap {fmt_usd(self.bucket_cap_micro(cycle, bucket))}")
          if self.ai_spend() > self.run_cap_micro:
              raise RunCapExceeded(f"run AI spend {fmt_usd(self.ai_spend())} > cap {fmt_usd(self.run_cap_micro)}")
  ```

`swarm50/metered.py`:
- In `metered_call`: `ledger.assert_can_spend(cycle, worst_case_cost(...), agent)`, keeping the existing
  arguments to `worst_case_cost` and adding `agent` as the third argument to `assert_can_spend`.
- In `metered_batch_call`: `ledger.assert_can_spend(cycle, int(wc * BATCH_DISCOUNT), agent)`.

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass. The existing cap tests use agent `"a"` (think bucket, $0.75) and `discovery_cycles: 0`,
so their numbers are unchanged.

- [ ] **Step 5: Commit**

```
git add swarm50/exceptions.py swarm50/ledger.py swarm50/metered.py config.yaml tests/conftest.py tests/test_ledger.py
git commit -m "Add per-bucket cycle caps and a hard run-level AI spend cap" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Window score (spec §7.5)

**Files:**
- Create: `swarm50/score.py`
- Test: `tests/test_score.py` (new)

**Interfaces:**
- Consumes:
  - `revenue` and `refund` transactions (Task 6)
  - `fee_charged` and `ad_result_entered` bet events (Task 2)
- Produces:
  - `window_bounds(config, upto_cycle=None) -> tuple[int, int]` (the judged window by default; a
    trailing window ending at `upto_cycle` otherwise; length `score_window_cycles`, default 30)
  - `window_score(ledger, betlog, start, end) -> dict` with keys `start, end, net_sales, refunds,
    listing_fees, ad_spend, score` (all money in micro-dollars, refunds/fees/ads as positive numbers)

- [ ] **Step 1: Write the failing tests** (`tests/test_score.py`)

```python
from swarm50.ledger import MICRO
from swarm50.score import window_bounds, window_score
from tests.conftest import CONFIG


def test_window_bounds_default_to_the_judged_window_and_can_trail():
    cfg = {**CONFIG, "total_days": 90}
    assert window_bounds(cfg) == (61, 90)
    assert window_bounds(cfg, upto_cycle=34) == (5, 34)
    assert window_bounds(cfg, upto_cycle=10) == (1, 10)


def test_score_nets_refunds_listing_fees_and_ad_spend(ledger, betlog):
    ledger.record_platform_entry(60, "revenue", 9, "etsy:receipt:0")       # before the window
    ledger.record_platform_entry(61, "revenue", 10, "etsy:receipt:1")
    ledger.record_platform_entry(75, "revenue", 5, "gumroad:sale:1")
    ledger.record_platform_entry(80, "refund", -5, "gumroad:refund:1")
    betlog.append(59, "c1-r1-b1", "fee_charged", {"fee_usd": 0.2}, "cfo")   # before the window
    betlog.append(62, "c1-r1-b1", "fee_charged", {"fee_usd": 0.2}, "cfo")
    betlog.append(70, "c1-r1-b1", "ad_result_entered",
                  {"spend_usd": 4, "attributed_sales_usd": 6, "start_cycle": 59, "end_cycle": 62}, "human")
    s = window_score(ledger, betlog, 61, 90)
    assert s["net_sales"] == 15 * MICRO
    assert s["refunds"] == 5 * MICRO
    assert s["listing_fees"] == 200_000
    assert s["ad_spend"] == 2 * MICRO          # 2 of the 4 ad days (61, 62) fall inside the window
    assert s["score"] == 15 * MICRO - 5 * MICRO - 200_000 - 2 * MICRO


def test_empty_window_scores_zero(ledger, betlog):
    assert window_score(ledger, betlog, 61, 90)["score"] == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m pytest tests/test_score.py -q`
Expected: FAIL (`swarm50.score` missing).

- [ ] **Step 3: Implement** (`swarm50/score.py`)

```python
"""The window score the strategist is judged on (spec §7.5): net sales in the judged window minus
refunds, listing fees and ad spend in that window. AI spend is reported beside it, never inside it."""
from .ledger import usd_to_micro


def window_bounds(config, upto_cycle=None):
    """(start, end) cycles, inclusive. Default: the judged final window. With upto_cycle: the trailing
    window ending there, used as a guide before the judged window opens."""
    length = int(config.get("score_window_cycles", 30))
    end = config["total_days"] if upto_cycle is None else upto_cycle
    return max(1, end - length + 1), end


def _tx_sum(ledger, type_, start, end) -> int:
    return ledger._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type=? AND cycle BETWEEN ? AND ?",
                          type_, start, end)


def _prorated_ad_spend(payload, start, end) -> int:
    """Ad spend spread evenly over its cycles; the share inside [start, end], rounded up (never flatters)."""
    s, e = int(payload["start_cycle"]), int(payload["end_cycle"])
    total, days = usd_to_micro(payload["spend_usd"]), e - s + 1
    overlap = max(0, min(e, end) - max(s, start) + 1)
    return -(-total * overlap // days)


def window_score(ledger, betlog, start, end) -> dict:
    events = betlog.events()
    net_sales = _tx_sum(ledger, "revenue", start, end)
    refunds = -_tx_sum(ledger, "refund", start, end)
    listing_fees = sum(usd_to_micro(e["payload"]["fee_usd"]) for e in events
                       if e["event_type"] == "fee_charged" and start <= e["cycle"] <= end)
    ad_spend = sum(_prorated_ad_spend(e["payload"], start, end) for e in events
                   if e["event_type"] == "ad_result_entered")
    return {"start": start, "end": end, "net_sales": net_sales, "refunds": refunds,
            "listing_fees": listing_fees, "ad_spend": ad_spend,
            "score": net_sales - refunds - listing_fees - ad_spend}
```

- [ ] **Step 4: Run the full suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```
git add swarm50/score.py tests/test_score.py
git commit -m "Add the window score: net sales minus refunds, listing fees and ad spend" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Close out Plan 1a

**Files:** `docs/superpowers/plans/2026-10-05-roadmap.md` (status line only)

- [ ] **Step 1: Full suite and a manual smoke test of the CLIs on a throwaway DB**

Run:
```
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -c "import tempfile,pathlib; from swarm50.config import load_config; from swarm50.ledger import Ledger; l=Ledger(load_config(), pathlib.Path(tempfile.mkdtemp())/'t.db'); l.init_wallet(); print(l.balance(), l.bucket_cap_micro(1,'think'), l.bucket_cap_micro(8,'think'), l.run_cap_micro)"
```
Expected: all tests pass; prints `100000000 1500000 750000 75000000`.

- [ ] **Step 2: Mark 1a done in the roadmap and commit**

In `docs/superpowers/plans/2026-10-05-roadmap.md`, add under the calendar table: `**Status:** 1a complete (<date>).`

```
git add docs/superpowers/plans/2026-10-05-roadmap.md
git commit -m "Mark Plan 1a complete" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Not in Plan 1a (deliberately):** prompt and schema changes, removing reward arms and the trading cap,
and dry-run changes. They move together in Plan 1b, where the strategist is redesigned, so the
prompts are never half-updated.
