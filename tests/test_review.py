from datetime import date
from unittest.mock import patch

import pytest

from swarm50 import queue
from swarm50.exceptions import CycleCapExceeded
from swarm50.review import run_cycle
from swarm50.state import build_state
from tests.conftest import memo, result

CRIT_APPROVE = {"objections": [{"point": "fine", "severity": "low"}], "key_risk": "none", "verdict": "approve"}
CRIT_REVISE = {"objections": [{"point": "stake too high", "severity": "high"}], "key_risk": "loss", "verdict": "revise"}
CRIT_REJECT = {**CRIT_REVISE, "verdict": "reject"}


def strategist(*memos, reason=None):
    return {"cycle_reasoning": "r", "memos": list(memos), "no_bet_reason": reason}


def types(betlog, bet_id):
    return [e["event_type"] for e in betlog.events(bet_id)]


@pytest.fixture
def calls():
    with patch("swarm50.review.metered_call") as m:
        yield m


def test_approve_path(ledger, betlog, calls):
    calls.side_effect = [result(strategist(memo())), result(CRIT_APPROVE)]
    summary = run_cycle(ledger, betlog, 1, today=date(2026, 9, 19))
    assert summary == {"proposed": ["c1-1"], "stopped": None, "no_bet_reason": None}
    assert types(betlog, "c1-1") == ["proposed", "critiqued"]
    assert betlog.bets()["c1-1"]["status"] == "queued"
    assert calls.call_count == 2
    # every call is exactly one system prompt + one user message
    for c in calls.call_args_list:
        assert len(c.args[4]) == 1 and c.args[4][0]["role"] == "user" and c.kwargs["system"]
    assert calls.call_args_list[0].args[3] == "strategist" and calls.call_args_list[1].args[3] == "critic"
    assert calls.call_args_list[0].args[4][0]["content"].startswith("date: 2026-09-19 | cycle: 1 | days remaining: 30")


def test_revise_rebuttal_final_path(ledger, betlog, calls):
    revised = memo(stake_usd=3, title="v2")
    calls.side_effect = [result(strategist(memo())), result(CRIT_REVISE),
                         result({"responses": [{"objection": "stake too high", "response": "lowered stake"}],
                                 "decision": "revise", "revised_memo": revised}),
                         result(CRIT_APPROVE)]
    run_cycle(ledger, betlog, 1)
    assert types(betlog, "c1-1") == ["proposed", "critiqued", "rebutted", "final_verdict"]
    assert betlog.bets()["c1-1"]["status"] == "queued"
    assert betlog.bets()["c1-1"]["memo"]["title"] == "v2"
    assert betlog.events("c1-1")[-1]["payload"]["verdict"] == "approve"
    assert [c.args[3] for c in calls.call_args_list] == ["strategist", "critic", "strategist", "critic"]
    # the rebuttal call carries the memo and the critique; the final call carries the revised memo and rebuttal
    assert "stake too high" in calls.call_args_list[2].args[4][0]["content"]
    final_user = calls.call_args_list[3].args[4][0]["content"]
    assert "v2" in final_user and "lowered stake" in final_user


def test_final_revise_counts_as_reject_and_withdraw(ledger, betlog, calls):
    calls.side_effect = [result(strategist(memo(), memo(title="second"))),
                         result(CRIT_REJECT),
                         result({"responses": [{"objection": "x", "response": "y"}],
                                 "decision": "revise", "revised_memo": memo()}),
                         result(CRIT_REVISE),  # final round: revise -> reject
                         result(CRIT_REJECT),
                         result({"responses": [{"objection": "x", "response": "fair point"}],
                                 "decision": "withdraw"})]
    run_cycle(ledger, betlog, 1)
    assert types(betlog, "c1-1") == ["proposed", "critiqued", "rebutted", "final_verdict"]
    assert betlog.events("c1-1")[-1]["payload"]["verdict"] == "reject"
    assert betlog.bets()["c1-1"]["status"] == "rejected"
    assert types(betlog, "c1-2") == ["proposed", "critiqued", "withdrawn"]
    assert betlog.bets()["c1-2"]["status"] == "withdrawn"


def test_malformed_gets_one_retry_then_event(ledger, betlog, calls):
    calls.side_effect = [result("I think we should... (no json)"),
                         result({"cycle_reasoning": "r", "memos": [{"title": "broken"}]})]
    summary = run_cycle(ledger, betlog, 1)
    assert calls.call_count == 2
    repair_user = calls.call_args_list[1].args[4][0]["content"]
    assert "Validation error" in repair_user and "no JSON object found" in repair_user
    evs = betlog.events()
    assert len(evs) == 1 and evs[0]["event_type"] == "malformed" and evs[0]["actor"] == "strategist"
    assert "schema validation failed" in evs[0]["payload"]["error"]
    assert summary["proposed"] == []


def test_no_bet_is_valid_and_reason_required(ledger, betlog, calls):
    calls.side_effect = [result(strategist(reason="nothing worth it")), ]
    assert run_cycle(ledger, betlog, 1)["no_bet_reason"] == "nothing worth it"
    assert betlog.events() == []
    calls.side_effect = [result(strategist()), result(strategist())]  # empty memos, no reason -> malformed
    run_cycle(ledger, betlog, 2)
    assert types(betlog, "c2-strategist") == ["malformed"]


def test_budget_exhaustion_mid_loop_stops_cleanly(ledger, betlog, calls):
    calls.side_effect = [result(strategist(memo(), memo(title="second"))), result(CRIT_REVISE),
                         CycleCapExceeded("cycle 1: over cap")]
    summary = run_cycle(ledger, betlog, 1)
    assert summary["stopped"] == "CycleCapExceeded: cycle 1: over cap"
    assert summary["proposed"] == ["c1-1"]
    assert types(betlog, "c1-1") == ["proposed", "critiqued"]  # left in its last state
    assert betlog.bets()["c1-1"]["status"] == "pending_rebuttal"
    assert "c1-2" not in betlog.bets()
    assert calls.call_count == 3


def test_human_approve_stakes_and_reject_records(ledger, betlog, calls):
    calls.side_effect = [result(strategist(memo(stake_usd=5), memo(stake_usd=20, title="too big"))),
                         result(CRIT_APPROVE), result(CRIT_APPROVE)]
    run_cycle(ledger, betlog, 1)
    assert queue.approve(ledger, betlog, "c1-1")
    assert types(betlog, "c1-1") == ["proposed", "critiqued", "human_approved", "staked"]
    assert ledger.balance() == 45_000_000
    assert not queue.approve(ledger, betlog, "c1-2")  # 20 > 35% of 45
    assert types(betlog, "c1-2") == ["proposed", "critiqued", "human_approved", "blocked"]
    assert ledger.balance() == 45_000_000
    queue.reject(ledger, betlog, "c1-2", "no")
    assert betlog.bets()["c1-2"]["status"] == "rejected"


def test_state_block(ledger, betlog):
    betlog.append(1, "a", "proposed", memo(), "strategist")
    betlog.append(1, "a", "staked", {"stake_usd": 5}, "cfo")
    betlog.append(2, "b", "blocked", {"rule": "max_stake_pct", "value_micro": 20_000_000,
                                      "limit_micro": 15_750_000, "memo": memo(title="big one")}, "cfo")
    s = build_state(ledger, betlog, 3, today=date(2026, 10, 1))
    assert "days remaining: 18" in s
    assert "open exposure: $5.000000" in s
    assert "a  active  stake $5.000000  digital_product  kill_by_cycle 6  'Sell a prompt pack'" in s
    assert "c2 b blocked (cfo) max_stake_pct" in s
    assert "max_stake_pct: 20.00 > limit 15.75 USD  'big one'" in s
