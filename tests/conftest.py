import pytest

from swarm50.bets import BetLog
from swarm50.ledger import Ledger
from swarm50.metered import Result, Usage

CONFIG = {
    "starting_balance_usd": 50,
    "cycle_token_cap_usd": 0.75,
    "max_stake_pct": 0.35,
    "max_open_exposure_pct": 0.60,
    "max_trading_exposure_pct": 0.50,
    "end_date": "2026-10-19",
    "web_search_per_request_usd": 0.01,
    "backend": "api",
    "cli_input_overhead_tokens": 600,
    "models": {"big": {"input_per_mtok_usd": 3.0, "output_per_mtok_usd": 15.0,
                       "cache_write_5m_per_mtok_usd": 3.75, "cache_read_per_mtok_usd": 0.30}},
    "roles": {"strategist": "big", "critic": "big", "worker": "big"},
}

MEMO = {
    "title": "Sell a prompt pack", "category": "digital_product", "description": "d",
    "stake_usd": 5.0, "expected_value_usd": 12.0, "ev_reasoning": "r", "p_total_loss": 0.4,
    "variance_notes": "v", "token_cost_estimate_usd": 0.5, "kill_criteria": "k", "kill_by_cycle": 6,
    "next_best_alternative": "n", "why_this_beats_it": "w", "human_actions_required": ["publish"],
    "human_minutes_required": 15,
}


def memo(**overrides) -> dict:
    return {**MEMO, **overrides}


def result(obj) -> Result:
    """A mocked metered_call return value carrying `obj` (dict or raw string) as the response text."""
    import json
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return Result(text=text, usage=Usage(input_tokens=1, output_tokens=1), model="big", backend="api",
                  reported_cost_usd=None)


@pytest.fixture
def make_ledger(tmp_path):
    def _make(**overrides):
        led = Ledger({**CONFIG, **overrides}, tmp_path / "ledger.db")
        led.init_wallet()
        return led
    return _make


@pytest.fixture
def ledger(make_ledger):
    return make_ledger()


@pytest.fixture
def betlog(ledger):
    return BetLog(ledger)
