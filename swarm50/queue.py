"""Human queue: python -m swarm50.queue list | show <bet_id> | approve <bet_id> | reject <bet_id> --reason ..."""
import argparse
import json
import sys

from . import cfo, tasks
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
    memo = Memo.model_validate(bet["memo"])
    if memo.human_actions_required:
        tasks.request_tasks(betlog, cycle, bet_id, memo.human_actions_required)
    return cfo.try_stake(ledger, betlog, cycle, bet_id, memo)


def reject(ledger, betlog, bet_id, reason):
    betlog.append(_bet_cycle(betlog, bet_id), bet_id, "human_rejected", {"reason": reason}, "human")


def record_return(ledger, betlog, bet_id, amount_usd, type="bet_return", note=None):
    """Human only: records real-world money coming back on a bet. Never mutates the stake event;
    it's simply a new ledger credit plus a `return_recorded` bet event."""
    if bet_id not in betlog.bets():
        sys.exit(f"unknown bet {bet_id}")
    cycle = _bet_cycle(betlog, bet_id)
    ledger.record_return(cycle, bet_id, amount_usd, type=type)
    betlog.append(cycle, bet_id, "return_recorded",
                 {"amount_usd": amount_usd, "type": type, "note": note}, "human")


def close(ledger, betlog, bet_id, note=None):
    """Human only: marks a bet closed (no more activity expected). Does not touch its returns."""
    if bet_id not in betlog.bets():
        sys.exit(f"unknown bet {bet_id}")
    betlog.append(_bet_cycle(betlog, bet_id), bet_id, "closed", {"note": note}, "human")


def cmd_tasks_list(betlog):
    open_ = tasks.open_tasks(betlog)
    if not open_:
        print("no open tasks")
    for tid, t in sorted(open_.items()):
        print(f"{tid:<16} c{t['cycle']:<3} {t['bet_id']:<10} age {tasks.age_days(t)}d   {t['description']}")


def cmd_tasks_done(betlog, task_id, note):
    tasks.mark_done(betlog, task_id, note)
    print(f"marked {task_id} done")


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
            print(f"decision: {p['decision']}")
            for r in p.get("responses", []):
                print(f"  objection: {r['objection']}\n  response: {r['response']}")
            if p.get("revised_memo"):
                print("revised memo:")
                _print_memo(p["revised_memo"])
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
    rr = sub.add_parser("record-return")
    rr.add_argument("bet_id")
    rr.add_argument("amount_usd", type=float)
    rr.add_argument("--type", choices=["revenue", "bet_return"], default="bet_return")
    rr.add_argument("--note", default=None)
    c = sub.add_parser("close")
    c.add_argument("bet_id")
    c.add_argument("--note", default=None)
    t = sub.add_parser("tasks")
    tsub = t.add_subparsers(dest="tasks_cmd", required=True)
    tsub.add_parser("list")
    td = tsub.add_parser("done")
    td.add_argument("task_id")
    td.add_argument("--note", default=None)
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
    elif a.cmd == "record-return":
        record_return(ledger, betlog, a.bet_id, a.amount_usd, type=a.type, note=a.note)
        print(f"recorded {a.type} ${a.amount_usd} on {a.bet_id}; balance now {fmt_usd(ledger.balance())}")
    elif a.cmd == "close":
        close(ledger, betlog, a.bet_id, note=a.note)
        print(f"closed {a.bet_id}")
    elif a.cmd == "tasks":
        if a.tasks_cmd == "list":
            cmd_tasks_list(betlog)
        elif a.tasks_cmd == "done":
            cmd_tasks_done(betlog, a.task_id, a.note)


if __name__ == "__main__":
    main()
