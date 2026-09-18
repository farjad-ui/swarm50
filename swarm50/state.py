"""Renders the compact plain-text state block the strategist sees."""
from datetime import date

from .ledger import MICRO, fmt_usd


def _days_remaining(config, today) -> int | None:
    end = config.get("end_date")
    if end is None:
        return None
    if isinstance(end, str):
        end = date.fromisoformat(end)
    return (end - today).days


def build_state(ledger, betlog, cycle, today=None) -> str:
    today = today or date.today()
    days = _days_remaining(ledger.config, today)
    total_tokens = -ledger._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")
    lines = [
        f"date: {today.isoformat()} | cycle: {cycle} | days remaining: {days if days is not None else 'n/a'}",
        f"balance: {fmt_usd(ledger.balance())} | token spend this cycle: {fmt_usd(ledger.cycle_spend(cycle))}"
        f" | total token spend: {fmt_usd(total_tokens)} | open exposure: {fmt_usd(betlog.open_exposure_micro())}",
        "open bets:",
    ]
    open_bets = betlog.open_bets()
    if not open_bets:
        lines.append("  (none)")
    for bet_id, b in open_bets.items():
        m = b["memo"] or {}
        lines.append(f"  {bet_id}  {b['status']}  stake {fmt_usd(b['stake_micro'])}  {m.get('category', '?')}"
                     f"  kill_by_cycle {m.get('kill_by_cycle', '?')}  {m.get('title', '')!r}")
    lines.append("last 10 bet events:")
    events = betlog.events(limit=10)
    if not events:
        lines.append("  (none)")
    for e in events:
        verdict = e["payload"].get("verdict") or e["payload"].get("action") or e["payload"].get("rule") or ""
        lines.append(f"  c{e['cycle']} {e['bet_id']} {e['event_type']} ({e['actor']}) {verdict}".rstrip())
    lines.append("recently blocked:")
    blocked = betlog.recent_blocked(5)
    if not blocked:
        lines.append("  (none)")
    for e in blocked:
        p = e["payload"]
        lines.append(f"  c{e['cycle']} {e['bet_id']} {p.get('rule')}: {p.get('value_micro', 0) / MICRO:.2f}"
                     f" > limit {p.get('limit_micro', 0) / MICRO:.2f} USD  {p.get('memo', {}).get('title', '')!r}")
    return "\n".join(lines)
