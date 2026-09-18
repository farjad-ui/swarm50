from swarm50.cycle import RunLog
from swarm50.report import render, write_report
from tests.conftest import CONFIG, memo


def test_renders_on_empty_db(ledger, betlog):
    runlog = RunLog(ledger)
    html = render(ledger, betlog, runlog, CONFIG)
    assert "<!doctype html>" in html.lower()
    assert "swarm50 report" in html
    assert "(no bets yet)" in html
    assert "(none)" in html  # blocked / tasks sections


def test_renders_on_fixture_db_with_bets_and_events(ledger, betlog):
    runlog = RunLog(ledger)
    betlog.append(1, "a", "proposed", memo(stake_usd=5), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    betlog.append(1, "a", "staked", {"stake_usd": 5, "category": "digital_product"}, "cfo")
    betlog.append(1, "a", "return_recorded", {"amount_usd": 8, "type": "revenue"}, "human")
    betlog.append(2, "b", "proposed", memo(stake_usd=30, category="trading"), "strategist")
    betlog.append(2, "b", "blocked", {"rule": "max_stake_pct", "value_micro": 30_000_000,
                                      "limit_micro": 17_500_000, "memo": memo(title="too big")}, "cfo")
    html = render(ledger, betlog, runlog, CONFIG)
    assert "$5.000000" in html or "5.000000" in html
    assert "max_stake_pct" in html
    assert "trading" in html
    assert "Balance over time" in html
    assert "Token spend by role" in html
    assert "Decision log" in html


def test_html_escaping_with_hostile_memo_title(ledger, betlog):
    runlog = RunLog(ledger)
    hostile = "<script>alert('xss')</script>"
    betlog.append(1, "a", "proposed", memo(title=hostile), "strategist")
    betlog.append(1, "a", "critiqued", {"verdict": "approve"}, "critic")
    betlog.append(1, "a", "staked", {"stake_usd": 5, "category": "digital_product"}, "cfo")
    html = render(ledger, betlog, runlog, CONFIG)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_headline_share_of_budget_on_thinking(ledger, betlog):
    runlog = RunLog(ledger)
    html = render(ledger, betlog, runlog, CONFIG)
    assert "Share of budget on thinking" in html
    assert "0.0%" in html  # nothing spent yet


def test_write_report_creates_index_html(ledger, betlog, tmp_path):
    runlog = RunLog(ledger)
    path = write_report(ledger, betlog, runlog, CONFIG, out_dir=tmp_path)
    assert path.name == "index.html"
    assert path.exists()
    assert "<!doctype html>" in path.read_text(encoding="utf-8").lower()


def test_blocked_memo_title_in_blocked_section_is_escaped(ledger, betlog):
    runlog = RunLog(ledger)
    hostile = "<img src=x onerror=alert(1)>"
    betlog.append(1, "b", "proposed", memo(title=hostile), "strategist")
    betlog.append(1, "b", "blocked", {"rule": "max_stake_pct", "memo": memo(title=hostile)}, "cfo")
    html = render(ledger, betlog, runlog, CONFIG)
    assert "<img src=x" not in html
    assert "&lt;img" in html
