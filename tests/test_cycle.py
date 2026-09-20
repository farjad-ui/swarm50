import sqlite3
from datetime import date
from unittest.mock import patch

import pytest

from swarm50.cycle import CycleError, RunLog, cycle_number, kickoff, run
from swarm50.exceptions import CycleCapExceeded
from tests.conftest import CONFIG, memo, result

CRIT_APPROVE = {"objections": [], "key_risk": "none", "verdict": "approve"}


def strategist(*memos, reason=None, bet_actions=None, work_orders=None):
    return {"cycle_reasoning": "r", "memos": list(memos), "no_bet_reason": reason,
           "bet_actions": bet_actions or [], "work_orders": work_orders or []}


@pytest.fixture
def runlog(ledger):
    return RunLog(ledger)


@pytest.fixture
def calls():
    with patch("swarm50.review.metered_call") as m:
        yield m


def test_kickoff_writes_once_and_refuses_twice(ledger, runlog):
    started = kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    assert started == "2026-09-18"
    assert runlog.kickoff_event()["payload"]["reward_arm"] == "linear"
    assert runlog.kickoff_event()["payload"]["config_hash"]
    with pytest.raises(CycleError):
        kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 19))


def test_cycle_number_derives_from_start_date(ledger, runlog):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    assert cycle_number(runlog, date(2026, 9, 18)) == 1
    assert cycle_number(runlog, date(2026, 9, 20)) == 3


def test_run_before_kickoff_refused(ledger, betlog, runlog):
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))


def test_full_mocked_cycle_writes_summary(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(memo())), result(CRIT_APPROVE)]
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["memos_proposed"] == 1
    assert summary["approved"] == 1
    assert summary["stopped"] is None
    assert runlog.has_run(1)
    assert betlog.bets()["c1-1"]["status"] == "queued"


def test_idempotency_refused_without_force(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(reason="nothing"))]
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))


def test_force_reruns_same_cycle(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(reason="nothing")), result(strategist(reason="nothing again"))]
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    summary2 = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18), force=True)
    assert summary2["stopped"] is None
    assert len(runlog.events("cycle_summary")) == 2


def test_refused_past_total_days(ledger, betlog, runlog):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18).replace(year=2027))


def test_insolvency_ends_run_permanently(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = CycleCapExceeded("cycle 1: over cap")
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["stopped"] == "CycleCapExceeded: cycle 1: over cap"
    assert runlog.run_ended_event()["payload"]["reason"] == "insolvent"
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 19))


def test_mid_cycle_exhaustion_is_not_insolvency(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(memo(), memo(title="second"))), CycleCapExceeded("over cap")]
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert summary["memos_proposed"] == 1
    assert summary["stopped"] == "CycleCapExceeded: over cap"
    assert runlog.run_ended_event() is None  # not a permanent death; only this cycle stopped early
    assert runlog.has_run(1)


def test_kill_bet_action_applied(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    betlog.append(1, "c0-1", "proposed", memo(), "strategist")
    betlog.append(1, "c0-1", "critiqued", CRIT_APPROVE, "critic")
    betlog.append(1, "c0-1", "human_approved", {}, "human")
    betlog.append(1, "c0-1", "staked", {"stake_usd": 5, "category": "digital_product"}, "cfo")
    assert betlog.bets()["c0-1"]["status"] == "active"

    calls.side_effect = [result(strategist(reason="hold steady",
                                           bet_actions=[{"bet_id": "c0-1", "action": "kill", "reason": "dead"}]))]
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert betlog.bets()["c0-1"]["status"] == "killed"


def test_kill_action_on_non_active_bet_is_blocked_not_raised(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = [result(strategist(reason="n",
                                           bet_actions=[{"bet_id": "nonexistent", "action": "kill", "reason": "x"}]))]
    run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    assert betlog.bets()["nonexistent"]["status"] == "blocked"


def test_error_path_leaves_db_usable(ledger, betlog, runlog, calls):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    calls.side_effect = RuntimeError("boom")
    with pytest.raises(CycleError):
        run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18))
    err = runlog.events("cycle_error")[0]
    assert "boom" in err["payload"]["error"] and "Traceback" in err["payload"]["traceback"]
    # the DB is still usable: another cycle (with --force, since cycle 1 wrote no summary but did
    # write a cycle_error; the run itself did not end) can proceed normally
    calls.side_effect = [result(strategist(reason="fine now"))]
    summary = run(ledger, betlog, runlog, CONFIG, today=date(2026, 9, 18), force=True)
    assert summary["stopped"] is None


def test_run_meta_append_only(ledger, runlog):
    kickoff(ledger, runlog, CONFIG, today=date(2026, 9, 18))
    for sql in ("UPDATE run_meta SET event_type='cycle_summary'", "DELETE FROM run_meta"):
        with pytest.raises(sqlite3.IntegrityError):
            runlog.conn.execute(sql)
