import sqlite3

import pytest

from swarm50.ledger import MICRO
from tests.conftest import memo


def test_status_and_exposure_derive_from_events(betlog):
    betlog.append(1, "a", "proposed", memo(stake_usd=5), "strategist")
    assert betlog.bets()["a"]["status"] == "pending_critique"
    betlog.append(1, "a", "critiqued", {"verdict": "revise", "objections": [], "key_risk": ""}, "critic")
    assert betlog.bets()["a"]["status"] == "pending_rebuttal"
    betlog.append(1, "a", "rebutted",
                  {"responses": [], "decision": "revise", "revised_memo": memo(stake_usd=4, title="v2")},
                  "strategist")
    assert betlog.bets()["a"]["status"] == "pending_final"
    assert betlog.bets()["a"]["memo"]["title"] == "v2"  # latest revision wins
    betlog.append(1, "a", "final_verdict", {"verdict": "approve"}, "critic")
    assert betlog.bets()["a"]["status"] == "queued" and "a" in betlog.queued()
    betlog.append(1, "a", "human_approved", {}, "human")
    betlog.append(1, "a", "staked", {"stake_usd": 4}, "cfo")
    assert betlog.bets()["a"]["status"] == "active"
    assert betlog.open_exposure_micro() == 4 * MICRO

    betlog.append(2, "b", "proposed", memo(category="trading"), "strategist")
    betlog.append(2, "b", "critiqued", {"verdict": "approve"}, "critic")
    betlog.append(2, "b", "staked", {"stake_usd": 6}, "cfo")
    betlog.append(2, "b", "return_recorded", {"amount_usd": 1}, "cfo")
    assert betlog.bets()["b"]["status"] == "active"  # returns don't close a bet
    assert betlog.open_exposure_micro() == 10 * MICRO
    assert betlog.open_exposure_micro("trading") == 6 * MICRO

    betlog.append(3, "a", "killed", {"why": "kill criteria hit"}, "cfo")
    assert betlog.bets()["a"]["status"] == "killed"
    assert betlog.open_exposure_micro() == 6 * MICRO
    betlog.append(3, "b", "closed", {}, "cfo")
    assert betlog.open_exposure_micro() == 0 and betlog.open_bets() == {}


def test_terminal_events(betlog):
    for bet, ev, payload in (("w", "withdrawn", {"responses": [], "decision": "withdraw"}), ("r", "human_rejected", {}),
                             ("x", "final_verdict", {"verdict": "reject"}), ("m", "malformed", {}),
                             ("k", "blocked", {"rule": "max_stake_pct"})):
        betlog.append(1, bet, "proposed", memo(), "strategist")
        betlog.append(1, bet, ev, payload, "human" if ev == "human_rejected" else "cfo")
    statuses = {k: v["status"] for k, v in betlog.bets().items()}
    assert statuses == {"w": "withdrawn", "r": "rejected", "x": "rejected", "m": "malformed", "k": "blocked"}
    assert betlog.queued() == {}


def test_events_ordering_and_limit(betlog):
    for i in range(12):
        betlog.append(1, f"b{i}", "proposed", memo(), "strategist")
    last = betlog.events(limit=10)
    assert [e["bet_id"] for e in last] == [f"b{i}" for i in range(2, 12)]  # oldest first, last 10
    assert [e["bet_id"] for e in betlog.events("b3")] == ["b3"]


def test_bet_events_append_only_and_constrained(betlog):
    betlog.append(1, "a", "proposed", memo(), "strategist")
    for sql in ("UPDATE bet_events SET actor='human'", "DELETE FROM bet_events"):
        with pytest.raises(sqlite3.IntegrityError):
            betlog.conn.execute(sql)
    with pytest.raises(sqlite3.IntegrityError):
        betlog.append(1, "a", "not_a_type", {}, "cfo")
    with pytest.raises(sqlite3.IntegrityError):
        betlog.append(1, "a", "closed", {}, "nobody")
