import json
from unittest.mock import patch

import pytest

from swarm50.dryrun import (load_records, render_summary_md, report_main, run_dry, summarize,
                            write_jsonl)
from tests.conftest import CONFIG, memo, result

STRAT_TRADING = {"cycle_reasoning": "r", "memos": [memo(category="trading", stake_usd=5)], "no_bet_reason": None}
STRAT_NO_BET = {"cycle_reasoning": "r", "memos": [], "no_bet_reason": "nothing worth it"}
STRAT_DIGITAL = {"cycle_reasoning": "r", "memos": [memo(category="digital_product", stake_usd=10)],
                 "no_bet_reason": None}


@pytest.fixture
def tmp_root_factory(tmp_path):
    counter = {"i": 0}

    def factory():
        counter["i"] += 1
        return tmp_path / f"run{counter['i']}"
    return factory


def test_run_dry_single_mode_no_critic_no_staking(tmp_root_factory):
    with patch("swarm50.dryrun.metered_call") as m:
        m.side_effect = [result(STRAT_TRADING), result(STRAT_NO_BET)]
        records, stopped = run_dry("linear", 2, config=CONFIG, tmp_root_factory=tmp_root_factory)
    assert stopped is False
    assert len(records) == 2
    assert m.call_count == 2  # one call per run, no repair needed, no critic
    assert records[0]["response"]["memos"][0]["category"] == "trading"
    assert records[1]["response"]["memos"] == []
    assert all(r["arm"] == "linear" and not r["malformed"] for r in records)


def test_run_dry_repairs_malformed_once(tmp_root_factory):
    with patch("swarm50.dryrun.metered_call") as m:
        m.side_effect = [result("not json"), result(STRAT_DIGITAL)]
        records, stopped = run_dry("linear", 1, config=CONFIG, tmp_root_factory=tmp_root_factory)
    assert m.call_count == 2
    assert records[0]["malformed"] is False
    assert records[0]["response"]["memos"][0]["category"] == "digital_product"


def test_run_dry_still_malformed_after_repair(tmp_root_factory):
    with patch("swarm50.dryrun.metered_call") as m:
        m.side_effect = [result("nope"), result("still nope")]
        records, stopped = run_dry("linear", 1, config=CONFIG, tmp_root_factory=tmp_root_factory)
    assert records[0]["malformed"] is True
    assert "error" in records[0]["malformed_info"]


def test_max_total_usd_stops_early(tmp_root_factory):
    # each call costs the same tiny amount; force a minuscule cap so it stops after 1 run
    with patch("swarm50.dryrun.metered_call") as m:
        m.side_effect = [result(STRAT_DIGITAL)] * 5
        records, stopped = run_dry("linear", 5, config=CONFIG, max_total_usd=0.0,
                                   tmp_root_factory=tmp_root_factory)
    assert stopped is True
    assert len(records) == 0  # worst-case pre-check already exceeds a $0 budget


def test_batch_mode_routes_through_metered_batch_call(tmp_root_factory):
    with patch("swarm50.dryrun.metered_batch_call") as m:
        m.return_value = [result(STRAT_TRADING), result(STRAT_DIGITAL)]
        records, stopped = run_dry("convex", 2, batch=True, config=CONFIG, tmp_root_factory=tmp_root_factory)
    assert m.call_count == 1
    assert len(records) == 2
    assert records[0]["response"]["memos"][0]["category"] == "trading"
    assert records[1]["response"]["memos"][0]["category"] == "digital_product"


def test_batch_mode_rejects_non_api_backend(tmp_root_factory):
    with pytest.raises(ValueError):
        run_dry("linear", 1, batch=True, config={**CONFIG, "backend": "claude_cli"},
               tmp_root_factory=tmp_root_factory)


def test_write_and_load_jsonl(tmp_path):
    records = [{"arm": "linear", "run_index": 0, "backend": "api", "model": "big",
               "response": STRAT_TRADING, "malformed": False, "malformed_info": None,
               "shadow_cost_usd": 0.01, "balance_usd": 50.0}]
    path = write_jsonl(records, "linear", out_dir=tmp_path)
    assert path.exists() and path.name.startswith("dryrun_linear_") and path.suffix == ".jsonl"
    loaded = load_records([path])
    assert loaded == records


# ---- report maths on a fixture ----

FIXTURE = [
    {"arm": "linear", "run_index": 0, "response": {"memos": [
        {"category": "trading", "stake_usd": 5, "p_total_loss": 0.4}]},
     "malformed": False, "shadow_cost_usd": 0.02, "balance_usd": 50.0},
    {"arm": "linear", "run_index": 1, "response": {"memos": []},
     "malformed": False, "shadow_cost_usd": 0.01, "balance_usd": 50.0},
    {"arm": "linear", "run_index": 2, "response": None, "malformed": True, "shadow_cost_usd": 0.005,
     "balance_usd": 50.0},
    {"arm": "convex", "run_index": 0, "response": {"memos": [
        {"category": "trading", "stake_usd": 20, "p_total_loss": 0.6},
        {"category": "digital_product", "stake_usd": 5, "p_total_loss": 0.1}]},
     "malformed": False, "shadow_cost_usd": 0.03, "balance_usd": 50.0},
]


def test_summarize_maths():
    s = summarize(FIXTURE)
    lin = s["linear"]
    assert lin["n_runs"] == 3 and lin["n_valid"] == 2 and lin["n_malformed"] == 1
    assert lin["share_with_trading_memo"] == 0.5   # 1 of 2 valid runs
    assert lin["share_no_bet"] == 0.5
    assert lin["category_frequency"] == {"trading": 1}
    assert lin["mean_stake_share_of_balance_by_category"]["trading"] == pytest.approx(5 / 50)
    assert lin["mean_p_total_loss"] == pytest.approx(0.4)
    assert lin["total_cost_usd"] == pytest.approx(0.02 + 0.01 + 0.005)

    con = s["convex"]
    assert con["category_frequency"] == {"trading": 1, "digital_product": 1}
    assert con["mean_p_total_loss"] == pytest.approx((0.6 + 0.1) / 2)


def test_render_summary_md_has_both_arms():
    text = render_summary_md(summarize(FIXTURE))
    assert "## Arm: linear" in text and "## Arm: convex" in text


def test_report_main_writes_summary_file(tmp_path, monkeypatch, capsys):
    jsonl = tmp_path / "dryrun_linear_x.jsonl"
    with open(jsonl, "w") as f:
        for r in FIXTURE:
            f.write(json.dumps(r) + "\n")
    monkeypatch.setattr("swarm50.dryrun.RESULTS_DIR", tmp_path / "results")
    report_main([str(jsonl)])
    out = tmp_path / "results" / "dryrun_summary.md"
    assert out.exists()
    assert "## Arm: linear" in out.read_text()
