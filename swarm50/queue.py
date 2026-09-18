"""Human queue: python -m swarm50.queue list | show <bet_id> | approve <bet_id> | reject <bet_id> --reason ..."""
import argparse
import json
import sys

from . import cfo
from .bets import BetLog
from .ledger import Ledger, fmt_usd
from .schemas import Memo


def _bet_cycle(betlog, bet_id) -> int:
    evs = betlog.events(bet_id)
    if not evs:
        sys.exit(f"unknown bet {bet_id}")
    return evs[-1]["cycle"]


def approve(ledger, betlog, bet_id) -> bool:
    """Record human approval, then run the guardrails and stake. Returns True if staked."""
    bet = betlog.bets().get(bet_id)
    if bet is None:
        sys.exit(f"unknown bet {bet_id}")
    if bet["status"] != "queued":
        sys.exit(f"{bet_id} is {bet['status']}, not queued")
    cycle = _bet_cycle(betlog, bet_id)
    betlog.append(cycle, bet_id, "human_approved", {}, "human")
    return cfo.try_stake(ledger, betlog, cycle, bet_id, Memo.model_validate(bet["memo"]))


def reject(ledger, betlog, bet_id, reason):
    betlog.append(_bet_cycle(betlog, bet_id), bet_id, "human_rejected", {"reason": reason}, "human")


def cmd_list(ledger, betlog):
    queued = betlog.queued()
    if not queued:
        print("queue is empty")
    for bet_id, b in queued.items():
        m = b["memo"]
        print(f"{bet_id:<10} c{b['cycle']:<3} {m['category']:<16} stake ${m['stake_usd']:<8} EV ${m['expected_value_usd']:<8} {m['title']}")


def cmd_show(ledger, betlog, bet_id):
    evs = betlog.events(bet_id)
    if not evs:
        sys.exit(f"unknown bet {bet_id}")
    print(f"{bet_id}  status: {betlog.bets()[bet_id]['status']}\n")
    for e in evs:
        print(f"--- {e['event_type']} ({e['actor']}, cycle {e['cycle']}, {e['ts'][:19]})")
        p = e["payload"]
        if e["event_type"] == "proposed":
            _print_memo(p)
        elif e["event_type"] in ("critiqued", "final_verdict"):
            print(f"verdict: {p['verdict']}   key risk: {p['key_risk']}")
            for o in p["objections"]:
                print(f"  [{o['severity']}] {o['point']}")
        elif e["event_type"] in ("rebutted", "withdrawn"):
            print(f"action: {p['action']}\nreason: {p['reason']}")
            if p.get("memo"):
                print("revised memo:")
                _print_memo(p["memo"])
        else:
            print(json.dumps(p, indent=1))
        print()


def _print_memo(m):
    for k, v in m.items():
        print(f"  {k}: {v}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m swarm50.queue")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("show").add_argument("bet_id")
    sub.add_parser("approve").add_argument("bet_id")
    r = sub.add_parser("reject")
    r.add_argument("bet_id")
    r.add_argument("--reason", required=True)
    a = ap.parse_args(argv)

    ledger = Ledger()
    betlog = BetLog(ledger)
    if a.cmd == "list":
        cmd_list(ledger, betlog)
    elif a.cmd == "show":
        cmd_show(ledger, betlog, a.bet_id)
    elif a.cmd == "approve":
        if approve(ledger, betlog, a.bet_id):
            print(f"staked {a.bet_id}; balance now {fmt_usd(ledger.balance())}")
        else:
            print(f"BLOCKED: {json.dumps(betlog.events(a.bet_id)[-1]['payload'], indent=1)}")
    elif a.cmd == "reject":
        reject(ledger, betlog, a.bet_id, a.reason)
        print(f"rejected {a.bet_id}")


if __name__ == "__main__":
    main()
