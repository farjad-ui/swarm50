from unittest.mock import patch

import pytest

from swarm50 import queue, tasks
from swarm50.metered import Result, Usage
from swarm50.workers import execute_work_orders
from tests.conftest import memo


def worker_result(text, input_tokens=10, output_tokens=20):
    return Result(text=text, usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
                 model="big", backend="api", reported_cost_usd=None)


def _stake_bet(betlog, bet_id="a", cycle=1, **memo_overrides):
    betlog.append(cycle, bet_id, "proposed", memo(**memo_overrides), "strategist")
    betlog.append(cycle, bet_id, "critiqued", {"verdict": "approve"}, "critic")
    betlog.append(cycle, bet_id, "staked", {"stake_usd": 5, "category": "digital_product"}, "cfo")


def test_order_on_unstaked_bet_is_blocked(ledger, betlog):
    betlog.append(1, "a", "proposed", memo(), "strategist")  # never staked
    with patch("swarm50.workers.metered_call") as m:
        completed = execute_work_orders(ledger, betlog, 1,
                                        [{"bet_id": "a", "task": "write copy",
                                          "deliverable_type": "text", "max_tokens": 500}])
    m.assert_not_called()
    assert completed == []
    ev = betlog.events("a")[-1]
    assert ev["event_type"] == "blocked" and ev["payload"]["rule"] == "work_order_on_non_staked_bet"


def test_order_on_unknown_bet_is_blocked(ledger, betlog):
    with patch("swarm50.workers.metered_call") as m:
        execute_work_orders(ledger, betlog, 1,
                            [{"bet_id": "ghost", "task": "x", "deliverable_type": "text", "max_tokens": 10}])
    m.assert_not_called()
    assert betlog.bets()["ghost"]["status"] == "blocked"


def test_artifact_written_and_event_recorded(ledger, betlog, tmp_path):
    _stake_bet(betlog)
    with patch("swarm50.workers.metered_call") as m:
        m.return_value = worker_result("Here is your listing copy.")
        completed = execute_work_orders(ledger, betlog, 1,
                                        [{"bet_id": "a", "task": "write listing copy",
                                          "deliverable_type": "listing_copy", "max_tokens": 500}],
                                        artifacts_dir=tmp_path)
    assert completed == ["a"]
    path = tmp_path / "a" / "1_listing_copy.md"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "Here is your listing copy."
    ev = betlog.events("a")[-1]
    assert ev["event_type"] == "work_completed" and ev["actor"] == "worker"
    assert ev["payload"]["path"] == str(path)
    assert ev["payload"]["output_tokens"] == 20
    assert ev["payload"]["cost_usd"] > 0


def test_second_order_on_same_bet_increments_seq(ledger, betlog, tmp_path):
    _stake_bet(betlog)
    with patch("swarm50.workers.metered_call") as m:
        m.return_value = worker_result("v1")
        execute_work_orders(ledger, betlog, 1, [{"bet_id": "a", "task": "t1",
                                                 "deliverable_type": "text", "max_tokens": 100}],
                            artifacts_dir=tmp_path)
        m.return_value = worker_result("v2")
        execute_work_orders(ledger, betlog, 1, [{"bet_id": "a", "task": "t2",
                                                 "deliverable_type": "text", "max_tokens": 100}],
                            artifacts_dir=tmp_path)
    assert (tmp_path / "a" / "1_text.md").read_text() == "v1"
    assert (tmp_path / "a" / "2_text.md").read_text() == "v2"


def test_worker_max_tokens_cap_applied(ledger, betlog, tmp_path):
    _stake_bet(betlog)
    with patch("swarm50.workers.metered_call") as m:
        m.return_value = worker_result("ok")
        execute_work_orders(ledger, betlog, 1,
                            [{"bet_id": "a", "task": "t", "deliverable_type": "text", "max_tokens": 999999}],
                            worker_max_tokens=3000, artifacts_dir=tmp_path)
    assert m.call_args.kwargs["max_tokens"] == 3000  # capped, not the requested 999999


def test_worker_max_tokens_uses_lesser_of_order_and_cap(ledger, betlog, tmp_path):
    _stake_bet(betlog)
    with patch("swarm50.workers.metered_call") as m:
        m.return_value = worker_result("ok")
        execute_work_orders(ledger, betlog, 1,
                            [{"bet_id": "a", "task": "t", "deliverable_type": "text", "max_tokens": 50}],
                            worker_max_tokens=3000, artifacts_dir=tmp_path)
    assert m.call_args.kwargs["max_tokens"] == 50


# ---- human task lifecycle ----

def test_approval_requests_a_task_per_human_action(ledger, betlog):
    betlog.append(1, "a", "proposed", memo(human_actions_required=["create listing", "set price"]), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    queue.approve(ledger, betlog, "a")
    open_ = tasks.open_tasks(betlog)
    assert len(open_) == 2
    descriptions = {t["description"] for t in open_.values()}
    assert descriptions == {"create listing", "set price"}


def test_task_done_lifecycle(ledger, betlog):
    betlog.append(1, "a", "proposed", memo(human_actions_required=["publish"]), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    queue.approve(ledger, betlog, "a")
    task_id = next(iter(tasks.open_tasks(betlog)))
    tasks.mark_done(betlog, task_id, note="done, listed at $5")
    assert tasks.open_tasks(betlog) == {}
    all_ = tasks.all_tasks(betlog)
    assert all_[task_id]["done"] is True and all_[task_id]["done_note"] == "done, listed at $5"


def test_mark_done_unknown_task_raises(betlog):
    with pytest.raises(KeyError):
        tasks.mark_done(betlog, "nope-t1")


def test_no_human_actions_requests_no_tasks(ledger, betlog):
    betlog.append(1, "a", "proposed", memo(human_actions_required=[]), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    queue.approve(ledger, betlog, "a")
    assert tasks.open_tasks(betlog) == {}
