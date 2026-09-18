"""Workers: no tools, no network access of their own (they only ever see the one prompt built here).
A worker takes a work order and returns a text deliverable. Nothing a worker produces is ever
published or executed automatically -- it is written to artifacts/ for a human to review."""
from pathlib import Path

from .config import ROOT
from .ledger import MICRO
from .metered import metered_call
from .prompts import render_worker

ARTIFACTS_DIR = ROOT / "artifacts"
WORKER_MAX_TOKENS_DEFAULT = 3000


def _next_seq(artifacts_dir, bet_id) -> int:
    d = artifacts_dir / bet_id
    if not d.exists():
        return 1
    return len(list(d.glob("*_*.md"))) + 1


def _order_prompt(bet, order) -> str:
    memo = bet["memo"] or {}
    return (f"Bet: {memo.get('title', '(untitled)')}\n"
           f"Category: {memo.get('category', '?')}\n"
           f"Description: {memo.get('description', '')}\n\n"
           f"Task: {order['task']}\n"
           f"Deliverable type: {order['deliverable_type']}")


def execute_work_orders(ledger, betlog, cycle, work_orders, worker_max_tokens=WORKER_MAX_TOKENS_DEFAULT,
                        artifacts_dir=None):
    """Runs each work order whose bet's derived status is `active` (staked). Every other bet_id
    writes a `blocked` event and is skipped -- never raises. Returns the list of bet_ids that got
    a deliverable written."""
    artifacts_dir = artifacts_dir or ARTIFACTS_DIR
    bets = betlog.bets()
    completed = []
    for order in work_orders:
        bet_id = order["bet_id"]
        bet = bets.get(bet_id)
        if bet is None or bet["status"] != "active":
            betlog.append(cycle, bet_id, "blocked",
                         {"rule": "work_order_on_non_staked_bet", "status": bet["status"] if bet else "none",
                          "task": order["task"]}, "cfo")
            continue

        max_tokens = min(int(order.get("max_tokens") or worker_max_tokens), worker_max_tokens)
        result = metered_call(ledger, cycle, "worker", "worker",
                              [{"role": "user", "content": _order_prompt(bet, order)}],
                              system=render_worker(), max_tokens=max_tokens)

        out_dir = artifacts_dir / bet_id
        out_dir.mkdir(parents=True, exist_ok=True)
        seq = _next_seq(artifacts_dir, bet_id)
        path = out_dir / f"{seq}_{order['deliverable_type']}.md"
        path.write_text(result.text, encoding="utf-8")

        u = result.usage
        cost_micro = ledger.cost_micro(result.model, u.input_tokens, u.output_tokens,
                                       u.cache_creation_input_tokens, u.cache_read_input_tokens,
                                       u.web_search_requests)
        betlog.append(cycle, bet_id, "work_completed",
                     {"path": str(path), "seq": seq, "deliverable_type": order["deliverable_type"],
                      "task": order["task"], "input_tokens": result.usage.input_tokens,
                      "output_tokens": result.usage.output_tokens, "cost_usd": cost_micro / MICRO},
                     "worker")
        completed.append(bet_id)
    return completed
