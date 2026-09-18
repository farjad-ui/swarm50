"""Append-only bet event log in the ledger's SQLite DB. Status and exposure are DERIVED from events."""
import json
from datetime import datetime, timezone

from .ledger import usd_to_micro

EVENT_TYPES = ("proposed", "critiqued", "rebutted", "withdrawn", "final_verdict", "human_approved",
               "human_rejected", "staked", "return_recorded", "killed", "closed", "blocked", "malformed")
ACTORS = ("strategist", "critic", "cfo", "human")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS bet_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    cycle        INTEGER NOT NULL,
    bet_id       TEXT    NOT NULL,
    event_type   TEXT    NOT NULL CHECK (event_type IN {EVENT_TYPES!r}),
    payload_json TEXT    NOT NULL,
    actor        TEXT    NOT NULL CHECK (actor IN {ACTORS!r})
);
CREATE TRIGGER IF NOT EXISTS bet_events_no_update BEFORE UPDATE ON bet_events
    BEGIN SELECT RAISE(ABORT, 'bet_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS bet_events_no_delete BEFORE DELETE ON bet_events
    BEGIN SELECT RAISE(ABORT, 'bet_events is append-only'); END;
"""

# event_type -> status it leaves the bet in (critiqued / final_verdict depend on the payload verdict)
_STATUS = {"proposed": "pending_critique", "rebutted": "pending_final", "human_approved": "approved",
           "human_rejected": "rejected", "staked": "active", "withdrawn": "withdrawn", "killed": "killed",
           "closed": "closed", "blocked": "blocked", "malformed": "malformed"}


def status_of(events) -> str:
    """Fold one bet's events (oldest first) into its current status."""
    status = "none"
    for e in events:
        t, p = e["event_type"], e["payload"]
        if t == "critiqued":
            status = "queued" if p.get("verdict") == "approve" else "pending_rebuttal"
        elif t == "final_verdict":
            status = "queued" if p.get("verdict") == "approve" else "rejected"
        elif t in _STATUS:
            status = _STATUS[t]
        # return_recorded leaves status unchanged
    return status


class BetLog:
    def __init__(self, ledger):
        self.conn = ledger.conn
        self.conn.executescript(SCHEMA)

    def append(self, cycle, bet_id, event_type, payload, actor) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO bet_events (ts, cycle, bet_id, event_type, payload_json, actor) VALUES (?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), cycle, bet_id, event_type,
                 json.dumps(payload, default=str), actor))
        return cur.lastrowid

    def events(self, bet_id=None, limit=None):
        """Oldest first. With limit, the LAST `limit` events."""
        sql, params = "SELECT * FROM bet_events", ()
        if bet_id is not None:
            sql, params = sql + " WHERE bet_id=?", (bet_id,)
        sql += " ORDER BY id DESC" + (" LIMIT ?" if limit else "")
        rows = self.conn.execute(sql, params + ((limit,) if limit else ())).fetchall()
        out = []
        for r in reversed(rows):
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out

    def bets(self) -> dict:
        """bet_id -> {status, cycle, memo, stake_micro}, all derived by folding events."""
        by_id = {}
        for e in self.events():
            by_id.setdefault(e["bet_id"], []).append(e)
        out = {}
        for bet_id, evs in by_id.items():
            memo, stake_micro, category = None, 0, None
            for e in evs:
                t, p = e["event_type"], e["payload"]
                if t == "proposed":
                    memo = p
                elif t == "rebutted" and p.get("revised_memo"):
                    memo = p["revised_memo"]
                elif t == "staked":
                    stake_micro = usd_to_micro(p["stake_usd"])
                    category = p.get("category")
            out[bet_id] = {"status": status_of(evs), "cycle": evs[0]["cycle"], "memo": memo,
                           "category": (memo or {}).get("category", category),
                           "stake_micro": stake_micro, "last_event": evs[-1]["event_type"]}
        return out

    def with_status(self, *statuses) -> dict:
        return {k: v for k, v in self.bets().items() if v["status"] in statuses}

    def open_bets(self) -> dict:
        return self.with_status("active")

    def queued(self) -> dict:
        return self.with_status("queued")

    def open_exposure_micro(self, category=None) -> int:
        return sum(b["stake_micro"] for b in self.open_bets().values()
                   if category is None or b["category"] == category)

    def recent_blocked(self, limit=5):
        rows = self.conn.execute(
            "SELECT * FROM bet_events WHERE event_type='blocked' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]
