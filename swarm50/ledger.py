"""Append-only SQLite ledger. All money is INTEGER micro-dollars (1 USD = 1_000_000)."""
import sqlite3
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .config import DB_PATH, load_config
from .exceptions import CycleCapExceeded, StakeCapExceeded, UnknownModel, WalletEmpty

MICRO = 1_000_000
TYPES = ("deposit", "token_cost", "bet_stake", "bet_return", "revenue", "adjustment")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    cycle         INTEGER NOT NULL,
    type          TEXT    NOT NULL CHECK (type IN {TYPES!r}),
    amount_micro  INTEGER NOT NULL,
    agent         TEXT,
    model         TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    bet_id        TEXT,
    note          TEXT,
    cache_write_tokens  INTEGER,
    cache_read_tokens   INTEGER,
    web_search_requests INTEGER,
    backend             TEXT
);
CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON transactions
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON transactions
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
"""

# Columns added after the first schema; ALTER TABLE ADD COLUMN is the whole migration.
MIGRATIONS = {
    "cache_write_tokens": "INTEGER",
    "cache_read_tokens": "INTEGER",
    "web_search_requests": "INTEGER",
    "backend": "TEXT",
}


def usd_to_micro(usd) -> int:
    """Exact USD -> micro-dollars via Decimal(str()) so 0.1 never becomes 0.1000000000000000055."""
    return int((Decimal(str(usd)) * MICRO).to_integral_value(ROUND_HALF_UP))


def fmt_usd(micro: int) -> str:
    sign = "-" if micro < 0 else ""
    micro = abs(micro)
    return f"{sign}${micro // MICRO}.{micro % MICRO:06d}"


class Ledger:
    def __init__(self, config=None, db_path=DB_PATH):
        self.config = config or load_config()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self):
        have = {r["name"] for r in self.conn.execute("PRAGMA table_info(transactions)")}
        with self.conn:
            for col, typ in MIGRATIONS.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typ}")

    # ---- limits from config, in micro-dollars ----
    @property
    def cycle_cap_micro(self) -> int:
        return usd_to_micro(self.config["cycle_token_cap_usd"])

    def max_stake_micro(self) -> int:
        return int(Decimal(str(self.config["max_stake_pct"])) * self.balance())

    def _prices(self, model):
        prices = self.config["models"].get(model)
        if prices is None:
            raise UnknownModel(model)
        return prices

    def cost_micro(self, model, input_tokens, output_tokens,
                   cache_write_tokens=0, cache_read_tokens=0, web_search_requests=0) -> int:
        p = self._prices(model)
        per_mtok = (input_tokens * usd_to_micro(p["input_per_mtok_usd"])
                    + output_tokens * usd_to_micro(p["output_per_mtok_usd"])
                    + cache_write_tokens * usd_to_micro(p["cache_write_5m_per_mtok_usd"])
                    + cache_read_tokens * usd_to_micro(p["cache_read_per_mtok_usd"]))
        tokens = -(-per_mtok // MICRO)  # ceil: never under-charge
        return tokens + web_search_requests * usd_to_micro(self.config["web_search_per_request_usd"])

    # ---- reads ----
    def _scalar(self, sql, *params) -> int:
        return self.conn.execute(sql, params).fetchone()[0] or 0

    def balance(self) -> int:
        return self._scalar("SELECT SUM(amount_micro) FROM transactions")

    def cycle_spend(self, cycle) -> int:
        return -self._scalar(
            "SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost' AND cycle=?", cycle)

    def history(self, limit=10):
        rows = self.conn.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def cache_savings(self):
        """(would_have_cost, did_cost) in micro for all cached reads, at full input vs cache-read rate."""
        full = actual = 0
        for r in self.conn.execute("SELECT model, SUM(cache_read_tokens) t FROM transactions "
                                   "WHERE type='token_cost' AND cache_read_tokens > 0 GROUP BY model"):
            p = self.config["models"].get(r["model"])
            if p is None:
                continue  # model since removed from config; can't price it
            full += -(-r["t"] * usd_to_micro(p["input_per_mtok_usd"]) // MICRO)
            actual += -(-r["t"] * usd_to_micro(p["cache_read_per_mtok_usd"]) // MICRO)
        return full, actual

    # ---- enforcement ----
    def assert_can_spend(self, cycle, cost_micro):
        """Pre-flight check for a projected token cost. Raises without writing."""
        bal = self.balance()
        if bal <= 0 or cost_micro > bal:
            raise WalletEmpty(f"balance {fmt_usd(bal)}, need {fmt_usd(cost_micro)}")
        projected = self.cycle_spend(cycle) + cost_micro
        if projected > self.cycle_cap_micro:
            raise CycleCapExceeded(
                f"cycle {cycle}: {fmt_usd(projected)} > cap {fmt_usd(self.cycle_cap_micro)}")

    # ---- writes (INSERT only) ----
    def _insert(self, cycle, type, amount_micro, **cols):
        cols.update(ts=datetime.now(timezone.utc).isoformat(), cycle=cycle,
                    type=type, amount_micro=amount_micro)
        keys = ", ".join(cols)
        marks = ", ".join("?" * len(cols))
        with self.conn:
            self.conn.execute(f"INSERT INTO transactions ({keys}) VALUES ({marks})",
                              tuple(cols.values()))

    def init_wallet(self):
        if self._scalar("SELECT COUNT(*) FROM transactions WHERE type='deposit' AND note='init_wallet'"):
            return
        self._insert(0, "deposit", usd_to_micro(self.config["starting_balance_usd"]), note="init_wallet")

    def record_token_usage(self, cycle, agent, model, input_tokens, output_tokens,
                           cache_creation_input_tokens=0, cache_read_input_tokens=0,
                           web_search_requests=0, backend=None, note=None) -> int:
        """Debit real usage. The API was already called, so the cost is always recorded;
        limit breaches are raised AFTER the write so the ledger never lies."""
        cost = self.cost_micro(model, input_tokens, output_tokens,
                               cache_creation_input_tokens, cache_read_input_tokens, web_search_requests)
        self._insert(cycle, "token_cost", -cost, agent=agent, model=model,
                     input_tokens=input_tokens, output_tokens=output_tokens,
                     cache_write_tokens=cache_creation_input_tokens,
                     cache_read_tokens=cache_read_input_tokens,
                     web_search_requests=web_search_requests, backend=backend, note=note)
        if self.balance() <= 0:
            raise WalletEmpty(f"balance {fmt_usd(self.balance())}")
        if self.cycle_spend(cycle) > self.cycle_cap_micro:
            raise CycleCapExceeded(
                f"cycle {cycle}: {fmt_usd(self.cycle_spend(cycle))} > cap {fmt_usd(self.cycle_cap_micro)}")
        return cost

    def stake_bet(self, cycle, bet_id, amount_usd, note=None) -> int:
        stake = usd_to_micro(amount_usd)
        if stake > self.max_stake_micro():
            raise StakeCapExceeded(f"stake {fmt_usd(stake)} > max {fmt_usd(self.max_stake_micro())}")
        self._insert(cycle, "bet_stake", -stake, bet_id=bet_id, note=note)
        return stake

    def record_return(self, cycle, bet_id, amount_usd, type="bet_return") -> int:
        if type not in ("bet_return", "revenue"):
            raise ValueError(f"type must be bet_return or revenue, got {type!r}")
        amount = usd_to_micro(amount_usd)
        self._insert(cycle, type, amount, bet_id=bet_id)
        return amount


def status(ledger):
    q = ledger.conn.execute
    total = ledger._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")
    print(f"balance:           {fmt_usd(ledger.balance())}")
    print(f"total token spend: {fmt_usd(-total)}")
    full, actual = ledger.cache_savings()
    print(f"cache savings:     {fmt_usd(full - actual)}  "
          f"(cached reads cost {fmt_usd(actual)}, would have been {fmt_usd(full)} at full input price)")
    print("\nspend by agent:")
    for r in q("SELECT agent, -SUM(amount_micro) s FROM transactions "
               "WHERE type='token_cost' GROUP BY agent ORDER BY s DESC"):
        print(f"  {r['agent']:<16}{fmt_usd(r['s'])}")
    print("\nspend by cycle:")
    for r in q("SELECT cycle, -SUM(amount_micro) s FROM transactions "
               "WHERE type='token_cost' GROUP BY cycle ORDER BY cycle"):
        print(f"  {r['cycle']:<16}{fmt_usd(r['s'])}")
    print("\nlast 10 transactions:")
    for t in reversed(ledger.history(10)):
        extra = " ".join(str(t[k]) for k in ("agent", "model", "bet_id", "note") if t[k])
        print(f"  #{t['id']:<4} {t['ts'][:19]}  c{t['cycle']:<3} {t['type']:<10} "
              f"{fmt_usd(t['amount_micro']):>14}  {extra}")


if __name__ == "__main__":
    if sys.argv[1:] != ["status"]:
        sys.exit("usage: python -m swarm50.ledger status")
    status(Ledger())
