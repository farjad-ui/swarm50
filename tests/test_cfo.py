from swarm50 import cfo
from swarm50.ledger import MICRO
from swarm50.schemas import Memo
from tests.conftest import memo


def _stake(ledger, betlog, bet_id, **m) -> bool:
    return cfo.try_stake(ledger, betlog, 1, bet_id, Memo.model_validate(memo(**m)))


def _blocked(betlog, bet_id):
    evs = betlog.events(bet_id)
    assert [e["event_type"] for e in evs] == ["blocked"]
    assert evs[0]["actor"] == "cfo" and evs[0]["payload"]["memo"]["title"]
    return evs[0]["payload"]


def test_max_stake_pct_blocks(ledger, betlog):
    assert _stake(ledger, betlog, "ok", stake_usd=17.5)          # exactly 35% of $50
    assert not _stake(ledger, betlog, "big", stake_usd=11.38)    # 35% of $32.50 is $11.375
    p = _blocked(betlog, "big")
    assert (p["rule"], p["value_micro"], p["limit_micro"]) == ("max_stake_pct", 11_380_000, 11_375_000)
    assert ledger.balance() == 32_500_000                        # nothing staked


def test_max_open_exposure_pct_blocks(ledger, betlog):
    assert _stake(ledger, betlog, "a", stake_usd=10)   # balance 40, exposure 10
    assert _stake(ledger, betlog, "b", stake_usd=10)   # balance 30, exposure 20; limit 60% of 50 = 30
    assert not _stake(ledger, betlog, "c", stake_usd=10.5)  # per-stake cap 35% of 30 = 10.5 passes; 30.5 > 30
    p = _blocked(betlog, "c")
    assert (p["rule"], p["value_micro"], p["limit_micro"]) == ("max_open_exposure_pct", 30_500_000, 30 * MICRO)
    assert betlog.open_exposure_micro() == 20 * MICRO and ledger.balance() == 30 * MICRO


def test_max_trading_exposure_pct_blocks(ledger, betlog):
    assert _stake(ledger, betlog, "a", stake_usd=10, category="trading")
    assert _stake(ledger, betlog, "b", stake_usd=10, category="trading")  # trading exposure 20, limit 25
    assert not _stake(ledger, betlog, "c", stake_usd=5.5, category="trading")  # 25.5 > 25 (open 25.5 <= 30 ok)
    p = _blocked(betlog, "c")
    assert (p["rule"], p["value_micro"], p["limit_micro"]) == ("max_trading_exposure_pct", 25_500_000, 25 * MICRO)
    assert _stake(ledger, betlog, "d", stake_usd=5.5, category="service")  # same stake, non-trading: fine
    assert betlog.open_exposure_micro("trading") == 20 * MICRO


def test_staked_event_and_ledger_agree(ledger, betlog):
    assert _stake(ledger, betlog, "a", stake_usd=5)
    ev = betlog.events("a")[-1]
    assert ev["event_type"] == "staked" and ev["payload"]["stake_usd"] == 5
    assert ledger.history(1)[0]["type"] == "bet_stake" and ledger.history(1)[0]["bet_id"] == "a"
