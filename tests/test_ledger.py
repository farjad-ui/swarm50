import sqlite3

import pytest

from swarm50.exceptions import CycleCapExceeded, StakeCapExceeded, UnknownModel, WalletEmpty
from swarm50.ledger import MICRO

# 1000 in @ $3/MTok + 500 out @ $15/MTok = 3000 + 7500 micro
KNOWN_COST = 10_500


def test_balance_is_sum_of_transactions(ledger):
    ledger.record_token_usage(1, "a", "big", 1000, 500)
    ledger.stake_bet(1, "b1", 5)
    ledger.record_return(2, "b1", 7.25, "revenue")
    assert ledger.balance() == 50 * MICRO - KNOWN_COST - 5 * MICRO + 7_250_000


def test_init_wallet_is_idempotent(ledger):
    ledger.init_wallet()
    ledger.init_wallet()
    assert ledger.balance() == 50 * MICRO
    assert len(ledger.history()) == 1


def test_cost_math_is_exact_micro_dollars(ledger):
    assert ledger.record_token_usage(1, "a", "big", 1000, 500) == KNOWN_COST
    assert ledger.cycle_spend(1) == KNOWN_COST
    assert ledger.balance() == 50 * MICRO - KNOWN_COST


def test_unknown_model(ledger):
    with pytest.raises(UnknownModel):
        ledger.record_token_usage(1, "a", "nope", 1, 1)
    assert len(ledger.history()) == 1  # nothing written


def test_wallet_empty(make_ledger):
    led = make_ledger(starting_balance_usd=0.005)  # 5000 micro < KNOWN_COST
    with pytest.raises(WalletEmpty):
        led.record_token_usage(1, "a", "big", 1000, 500)
    assert led.balance() == 5000 - KNOWN_COST  # real spend still recorded
    with pytest.raises(WalletEmpty):
        led.assert_can_spend(1, 1)


def test_cycle_cap_exceeded(ledger):
    # 100k in + 40k out = $0.30 + $0.60 = $0.90 > $0.75 cap
    with pytest.raises(CycleCapExceeded):
        ledger.record_token_usage(3, "a", "big", 100_000, 40_000)
    with pytest.raises(CycleCapExceeded):
        ledger.assert_can_spend(4, 750_001)
    ledger.assert_can_spend(4, 750_000)  # exactly at cap is fine


def test_stake_cap_exceeded(ledger):
    ledger.stake_bet(1, "ok", 17.5)  # exactly 35% of $50
    with pytest.raises(StakeCapExceeded):
        ledger.stake_bet(1, "too-much", 11.38)  # 35% of remaining $32.50 is $11.375


def test_cost_math_with_cache_and_search(ledger):
    # 1000 in @3 + 500 out @15 + 2000 cache write @3.75 + 4000 cache read @0.30 + 3 searches @ $0.01
    # = 3000 + 7500 + 7500 + 1200 + 30000 micro
    assert ledger.record_token_usage(1, "a", "big", 1000, 500, 2000, 4000, 3) == 49_200
    row = ledger.history(1)[0]
    assert (row["cache_write_tokens"], row["cache_read_tokens"], row["web_search_requests"]) == (2000, 4000, 3)
    # 4000 reads would have cost 12000 at full input price; cost 1200 -> saved 10800
    assert ledger.cache_savings() == (12_000, 1_200)


OLD_SCHEMA = """
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, cycle INTEGER NOT NULL,
    type TEXT NOT NULL, amount_micro INTEGER NOT NULL, agent TEXT, model TEXT,
    input_tokens INTEGER, output_tokens INTEGER, bet_id TEXT, note TEXT);
INSERT INTO transactions (ts, cycle, type, amount_micro, note)
    VALUES ('2026-01-01T00:00:00+00:00', 0, 'deposit', 50000000, 'init_wallet');
"""


def test_migration_from_previous_schema(tmp_path):
    from tests.conftest import CONFIG
    from swarm50.ledger import Ledger
    db = tmp_path / "old.db"
    with sqlite3.connect(db) as c:
        c.executescript(OLD_SCHEMA)
    led = Ledger(CONFIG, db)
    cols = {r[1] for r in led.conn.execute("PRAGMA table_info(transactions)")}
    assert {"cache_write_tokens", "cache_read_tokens", "web_search_requests", "backend"} <= cols
    led.init_wallet()  # still idempotent against the old deposit row
    assert led.balance() == 50 * MICRO
    led.record_token_usage(1, "a", "big", 1000, 500, 2000, 4000, 3)
    assert led.balance() == 50 * MICRO - 49_200
    Ledger(CONFIG, db)  # re-opening an already-migrated DB is a no-op


def test_table_is_append_only(ledger):
    for sql in ("UPDATE transactions SET amount_micro = 0", "DELETE FROM transactions"):
        with pytest.raises(sqlite3.IntegrityError):
            ledger.conn.execute(sql)
