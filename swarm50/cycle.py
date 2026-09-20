"""python -m swarm50.cycle kickoff | run [--force]

Sequence for `run`: load state -> strategist -> apply bet_actions -> critic loop on new memos ->
execute work_orders via workers -> write a cycle_summary event.
"""
import argparse
import hashlib
import json
import sys
import traceback
from datetime import date, datetime, timezone

from .bets import BetLog
from .config import load_config
from .exceptions import CycleCapExceeded, WalletEmpty
from .ledger import Ledger, MICRO, fmt_usd
from .review import call_strategist, review_memos
from .workers import execute_work_orders

RUN_EVENT_TYPES = ("kickoff", "cycle_summary", "cycle_error", "run_ended")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS run_meta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    cycle        INTEGER,
    event_type   TEXT    NOT NULL CHECK (event_type IN {RUN_EVENT_TYPES!r}),
    payload_json TEXT    NOT NULL
);
CREATE TRIGGER IF NOT EXISTS run_meta_no_update BEFORE UPDATE ON run_meta
    BEGIN SELECT RAISE(ABORT, 'run_meta is append-only'); END;
CREATE TRIGGER IF NOT EXISTS run_meta_no_delete BEFORE DELETE ON run_meta
    BEGIN SELECT RAISE(ABORT, 'run_meta is append-only'); END;
"""


def config_hash(config) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


class RunLog:
    """Append-only, non-bet run-level events: kickoff, cycle_summary, cycle_error, run_ended."""

    def __init__(self, ledger):
        self.conn = ledger.conn
        self.conn.executescript(SCHEMA)

    def append(self, event_type, payload, cycle=None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO run_meta (ts, cycle, event_type, payload_json) VALUES (?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), cycle, event_type, json.dumps(payload, default=str)))
        return cur.lastrowid

    def events(self, event_type=None) -> list[dict]:
        sql, params = "SELECT * FROM run_meta", ()
        if event_type is not None:
            sql, params = sql + " WHERE event_type=?", (event_type,)
        sql += " ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json"))
            out.append(d)
        return out

    def kickoff_event(self):
        evs = self.events("kickoff")
        return evs[0] if evs else None

    def run_ended_event(self):
        evs = self.events("run_ended")
        return evs[0] if evs else None

    def cycle_summaries(self) -> dict:
        """cycle -> its cycle_summary event (last one written, in the ordinary case there is one)."""
        out = {}
        for e in self.events("cycle_summary"):
            out[e["cycle"]] = e
        return out

    def has_run(self, cycle) -> bool:
        return cycle in self.cycle_summaries()


class CycleError(Exception):
    pass


def kickoff(ledger, runlog, config, today=None) -> str:
    """Writes the one-time kickoff event and initialises the wallet. Refuses to run twice."""
    if runlog.kickoff_event() is not None:
        raise CycleError("kickoff has already run; refusing to run twice")
    today = today or date.today()
    ledger.init_wallet()
    runlog.append("kickoff", {"start_date": today.isoformat(),
                              "reward_arm": config.get("reward_arm", "linear"),
                              "config_hash": config_hash(config)})
    return today.isoformat()


def cycle_number(runlog, today) -> int:
    kickoff_ev = runlog.kickoff_event()
    if kickoff_ev is None:
        raise CycleError("run before kickoff: run `python -m swarm50.cycle kickoff` first")
    start = date.fromisoformat(kickoff_ev["payload"]["start_date"])
    return (today - start).days + 1


def _apply_bet_actions(betlog, cycle, bet_actions):
    """kill -> a `killed` event (stake is NOT returned automatically; only a human return-recorded
    does that). hold is a no-op (nothing to write; its effect is simply not killing).
    Actions on a bet that isn't open write a `blocked` event and never raise."""
    bets = betlog.bets()
    for a in bet_actions:
        bet_id = a["bet_id"]
        if a["action"] != "kill":
            continue  # "hold" needs no event; the bet's status is unchanged
        bet = bets.get(bet_id)
        if bet is None or bet["status"] != "active":
            betlog.append(cycle, bet_id, "blocked",
                         {"rule": "bet_action_on_non_active_bet", "action": a["action"],
                          "status": bet["status"] if bet else "none", "reason": a.get("reason", "")},
                         "cfo")
            continue
        betlog.append(cycle, bet_id, "killed", {"reason": a.get("reason", "")}, "cfo")


def run(ledger, betlog, runlog, config, today=None, force=False) -> dict:
    """Runs one cycle end to end. Raises CycleError for refusals (already ran, past total_days,
    run before kickoff, run already ended). Any other exception is caught, recorded as a
    `cycle_error` run_meta event with the traceback, and re-raised so the CLI exits non-zero --
    but never leaves partial DB state that would break the next run (every write here is either
    an independent append-only event, or nothing).
    """
    if runlog.run_ended_event() is not None:
        raise CycleError(f"run has ended: {runlog.run_ended_event()['payload']}")
    today = today or date.today()
    cycle = cycle_number(runlog, today)
    total_days = config["total_days"]
    if cycle > total_days:
        raise CycleError(f"cycle {cycle} is past total_days {total_days}; the run is over")
    if runlog.has_run(cycle) and not force:
        raise CycleError(f"cycle {cycle} already ran; pass --force to rerun it")

    balance_in = ledger.balance()
    counts = {"memos_proposed": 0, "approved": 0, "rejected": 0, "blocked": 0, "malformed": 0}
    proposed = []
    try:
        resp, err, state = call_strategist(ledger, betlog, cycle, today)
        if resp is None:
            betlog.append(cycle, f"c{cycle}-strategist", "malformed", err, "strategist")
            counts["malformed"] += 1
        else:
            _apply_bet_actions(betlog, cycle, [a.model_dump() for a in resp.bet_actions])
            if resp.memos:
                review_memos(ledger, betlog, cycle, resp.memos, state, proposed=proposed)
                counts["memos_proposed"] = len(proposed)
                for bet_id in proposed:
                    status = betlog.bets()[bet_id]["status"]
                    if status in ("rejected", "withdrawn"):
                        counts["rejected"] += 1
                    elif status == "malformed":
                        counts["malformed"] += 1
                    elif status == "queued":
                        counts["approved"] += 1
            execute_work_orders(ledger, betlog, cycle, [w.model_dump() for w in resp.work_orders],
                                config.get("worker_max_tokens", 3000))
    except (CycleCapExceeded, WalletEmpty) as e:
        # the pre-call gate refused a call this cycle -- if it was the very first one (the
        # strategist call), this run is permanently over ("Death"); otherwise it just ends the
        # cycle early with whatever partial progress was already written.
        detail = f"{type(e).__name__}: {e}"
        counts["memos_proposed"] = len(proposed)
        if counts["memos_proposed"] == 0 and counts["malformed"] == 0:
            runlog.append("run_ended", {"reason": "insolvent", "detail": detail}, cycle=cycle)
        balance_out = ledger.balance()
        summary = {**counts, "balance_in_usd": balance_in / MICRO, "balance_out_usd": balance_out / MICRO,
                  "token_spend_usd": (balance_in - balance_out) / MICRO if balance_in >= balance_out else 0.0,
                  "stopped": detail}
        runlog.append("cycle_summary", summary, cycle=cycle)
        return summary
    except Exception as e:
        tb = traceback.format_exc()
        runlog.append("cycle_error", {"error": str(e), "traceback": tb}, cycle=cycle)
        raise CycleError(f"cycle {cycle} failed: {e}") from e

    balance_out = ledger.balance()
    summary = {**counts, "balance_in_usd": balance_in / MICRO, "balance_out_usd": balance_out / MICRO,
              "token_spend_usd": ledger.cycle_spend(cycle) / MICRO, "stopped": None}
    runlog.append("cycle_summary", summary, cycle=cycle)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m swarm50.cycle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("kickoff")
    r = sub.add_parser("run")
    r.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    config = load_config()
    ledger = Ledger(config)
    runlog = RunLog(ledger)
    betlog = BetLog(ledger)

    try:
        if args.cmd == "kickoff":
            started = kickoff(ledger, runlog, config)
            print(f"kicked off {started}; wallet initialised at {fmt_usd(ledger.balance())}")
        elif args.cmd == "run":
            summary = run(ledger, betlog, runlog, config, force=args.force)
            print(json.dumps(summary, indent=1))
            if summary.get("stopped"):
                return 1
    except CycleError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
