"""Renders the compact plain-text state block the strategist sees."""
from datetime import date

from .ledger import MICRO, fmt_usd
from .tasks import age_days, open_tasks


def _days_remaining(config, today) -> int | None:
    end = config.get("end_date")
    if end is None:
        return None
    if isinstance(end, str):
        end = date.fromisoformat(end)
    return (end - today).days


def _role_rates(config) -> str:
    parts = []
    for role, model in config.get("roles", {}).items():
        p = config.get("models", {}).get(model, {})
        parts.append(f"{role}={model} (${p.get('input_per_mtok_usd', '?')}/Mtok in,"
                     f" ${p.get('output_per_mtok_usd', '?')}/Mtok out)")
    return ", ".join(parts)


def build_state(ledger, betlog, cycle, today=None) -> str:
    today = today or date.today()
    days = _days_remaining(ledger.config, today)
    total_tokens = -ledger._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")
    cfg = ledger.config
    lines = [
        f"date: {today.isoformat()} | cycle: {cycle} | days remaining: {days if days is not None else 'n/a'}",
        f"balance: {fmt_usd(ledger.balance())} | token spend this cycle: {fmt_usd(ledger.cycle_spend(cycle))}"
        f" | total token spend: {fmt_usd(total_tokens)} | open exposure: {fmt_usd(betlog.open_exposure_micro())}",
        f"token rates by role: {_role_rates(cfg)}",
        f"caps: max_stake_pct={float(cfg['max_stake_pct']) * 100:g}% "
        f"max_open_exposure_pct={float(cfg['max_open_exposure_pct']) * 100:g}% "
        f"max_trading_exposure_pct={float(cfg['max_trading_exposure_pct']) * 100:g}%",
        "open bets:",
    ]
    open_bets = betlog.open_bets()
    overdue_ids = []
    if not open_bets:
        lines.append("  (none)")
    for bet_id, b in open_bets.items():
        m = b["memo"] or {}
        kill_by = m.get("kill_by_cycle")
        overdue = isinstance(kill_by, int) and cycle > kill_by
        if overdue:
            overdue_ids.append(bet_id)
        suffix = "  *** OVERDUE: past kill_by_cycle, hold or kill explicitly this cycle ***" if overdue else ""
        lines.append(f"  {bet_id}  {b['status']}  stake {fmt_usd(b['stake_micro'])}  {m.get('category', '?')}"
                     f"  kill_by_cycle {m.get('kill_by_cycle', '?')}  {m.get('title', '')!r}{suffix}")
    if overdue_ids:
        lines.insert(4, f"*** {len(overdue_ids)} bet(s) past kill_by_cycle and awaiting an explicit "
                        f"hold or kill this cycle: {', '.join(overdue_ids)} ***")
    lines.append("last 10 bet events:")
    events = betlog.events(limit=10)
    if not events:
        lines.append("  (none)")
    for e in events:
        verdict = e["payload"].get("verdict") or e["payload"].get("decision") or e["payload"].get("rule") or ""
        lines.append(f"  c{e['cycle']} {e['bet_id']} {e['event_type']} ({e['actor']}) {verdict}".rstrip())
    lines.append("open human tasks:")
    tasks = open_tasks(betlog)
    if not tasks:
        lines.append("  (none)")
    for tid, t in sorted(tasks.items()):
        lines.append(f"  {tid}  {t['bet_id']}  age {age_days(t, today)}d  {t['description']!r}")
    lines.append("recently blocked:")
    blocked = betlog.recent_blocked(5)
    if not blocked:
        lines.append("  (none)")
    for e in blocked:
        p = e["payload"]
        lines.append(f"  c{e['cycle']} {e['bet_id']} {p.get('rule')}: {p.get('value_micro', 0) / MICRO:.2f}"
                     f" > limit {p.get('limit_micro', 0) / MICRO:.2f} USD  {p.get('memo', {}).get('title', '')!r}")
    return "\n".join(lines)
