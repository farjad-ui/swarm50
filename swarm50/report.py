"""python -m swarm50.report writes a single self-contained report/index.html: inline CSS, inline SVG
charts, no external requests, no JS frameworks. Read-only against the DB. All model-generated text
(memo fields, critic objections, etc.) is untrusted and MUST be HTML-escaped before it is printed."""
import sys
from datetime import date, datetime
from html import escape as esc

from .bets import BetLog
from .config import ROOT, load_config
from .cycle import RunLog, cycle_number
from .ledger import MICRO, Ledger, fmt_usd
from .tasks import age_days, open_tasks

REPORT_DIR = ROOT / "report"


def _cycle_day(runlog, config):
    kickoff_ev = runlog.kickoff_event()
    if kickoff_ev is None:
        return None
    try:
        return cycle_number(runlog, date.today())
    except Exception:
        return None


def _total_token_spend_micro(ledger) -> int:
    return -ledger._scalar("SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")


def _balance_series(ledger):
    """[(ts, cumulative_balance_micro), ...] in transaction order."""
    rows = ledger.conn.execute(
        "SELECT ts, amount_micro FROM transactions ORDER BY id").fetchall()
    series = []
    running = 0
    for r in rows:
        running += r["amount_micro"]
        series.append((r["ts"], running))
    return series


def _spend_by(ledger, column):
    rows = ledger.conn.execute(
        f"SELECT {column} AS k, -SUM(amount_micro) AS s FROM transactions "
        f"WHERE type='token_cost' GROUP BY {column} ORDER BY {column}").fetchall()
    return [(r["k"], r["s"]) for r in rows]


def _bet_returns_micro(betlog):
    """bet_id -> total returned (bet_return + revenue), in micro."""
    from .ledger import usd_to_micro
    out = {}
    for bet_id, evs in _group_by_bet(betlog).items():
        total = 0
        for e in evs:
            if e["event_type"] == "return_recorded":
                total += usd_to_micro(e["payload"].get("amount_usd", 0))
        out[bet_id] = total
    return out


def _group_by_bet(betlog):
    by_id = {}
    for e in betlog.events():
        by_id.setdefault(e["bet_id"], []).append(e)
    return by_id


# ---- inline SVG helpers (no external libs) ----

def _svg_bars(pairs, width=560, height=180, bar_color="#4f7cff") -> str:
    """pairs: [(label, value_usd), ...]. Escapes labels."""
    if not pairs:
        return "<p>(no data)</p>"
    pad_left, pad_bottom, pad_top = 40, 30, 10
    plot_w, plot_h = width - pad_left - 10, height - pad_bottom - pad_top
    max_v = max(v for _, v in pairs) or 1
    n = len(pairs)
    bw = plot_w / n
    bars, labels = [], []
    for i, (label, v) in enumerate(pairs):
        h = (v / max_v) * plot_h
        x = pad_left + i * bw + bw * 0.1
        y = pad_top + (plot_h - h)
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.8:.1f}" height="{h:.1f}" '
                    f'fill="{bar_color}"><title>{esc(str(label))}: {fmt_usd(v)}</title></rect>')
        labels.append(f'<text x="{x + bw * 0.4:.1f}" y="{height - 10}" font-size="9" '
                      f'text-anchor="middle">{esc(str(label))[:10]}</text>')
    axis = (f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" stroke="#888"/>'
           f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - 10}" y2="{pad_top + plot_h}" stroke="#888"/>')
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">'
           f'{axis}{"".join(bars)}{"".join(labels)}</svg>')


def _svg_line(series, width=560, height=180, line_color="#4f7cff") -> str:
    """series: [(ts, value_micro), ...]."""
    if not series:
        return "<p>(no data)</p>"
    pad_left, pad_bottom, pad_top, pad_right = 55, 20, 10, 10
    plot_w, plot_h = width - pad_left - pad_right, height - pad_bottom - pad_top
    vals = [v / MICRO for _, v in series]
    lo, hi = min(vals + [0]), max(vals + [0.01])
    span = (hi - lo) or 1
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = pad_left + (i / max(n - 1, 1)) * plot_w
        y = pad_top + plot_h - ((v - lo) / span) * plot_h
        pts.append(f"{x:.1f},{y:.1f}")
    axis = (f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" stroke="#888"/>'
           f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - pad_right}" y2="{pad_top + plot_h}" '
           f'stroke="#888"/>')
    labels = (f'<text x="4" y="{pad_top + 5}" font-size="9">${hi:.2f}</text>'
             f'<text x="4" y="{pad_top + plot_h}" font-size="9">${lo:.2f}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">'
           f'{axis}{labels}<polyline points="{" ".join(pts)}" fill="none" stroke="{line_color}" '
           f'stroke-width="2"/></svg>')


# ---- sections ----

def _headline(ledger, betlog, runlog, config) -> str:
    day = _cycle_day(runlog, config)
    total_spend = _total_token_spend_micro(ledger)
    starting = config.get("starting_balance_usd", 0)
    share_pct = (total_spend / MICRO / starting * 100) if starting else 0
    tiles = [
        ("Day", day if day is not None else "not started"),
        ("Balance", fmt_usd(ledger.balance())),
        ("Total token spend", fmt_usd(total_spend)),
        ("Share of budget on thinking", f"{share_pct:.1f}%"),
        ("Open exposure", fmt_usd(betlog.open_exposure_micro())),
    ]
    cells = "".join(f'<div class="tile"><div class="tile-label">{esc(str(k))}</div>'
                    f'<div class="tile-value">{esc(str(v))}</div></div>' for k, v in tiles)
    return f'<section class="headline">{cells}</section>'


def _balance_chart(ledger) -> str:
    return f'<section><h2>Balance over time</h2>{_svg_line(_balance_series(ledger))}</section>'


def _spend_charts(ledger) -> str:
    by_role = _spend_by(ledger, "agent")
    by_cycle = _spend_by(ledger, "cycle")
    return ('<section><h2>Token spend by role</h2>'
           f'{_svg_bars([(k or "?", v / MICRO) for k, v in by_role])}</section>'
           '<section><h2>Token spend by cycle</h2>'
           f'{_svg_bars([(f"c{k}", v / MICRO) for k, v in by_cycle])}</section>')


def _bets_table(betlog) -> str:
    bets = betlog.bets()
    returns = _bet_returns_micro(betlog)
    if not bets:
        return "<section><h2>Bets</h2><p>(no bets yet)</p></section>"
    rows = []
    for bet_id, b in sorted(bets.items()):
        m = b["memo"] or {}
        ret = returns.get(bet_id, 0)
        pnl = ret - b["stake_micro"]
        rows.append(
            f"<tr><td>{esc(bet_id)}</td><td>{esc(b['status'])}</td>"
            f"<td>{esc(str(m.get('category', '?')))}</td>"
            f"<td>{esc(fmt_usd(b['stake_micro']))}</td>"
            f"<td>{esc(fmt_usd(ret))}</td>"
            f"<td>{esc(fmt_usd(pnl))}</td>"
            f"<td>{esc(str(m.get('title', '')))}</td></tr>")
    return ("<section><h2>Bets</h2><table><thead><tr>"
           "<th>bet_id</th><th>status</th><th>category</th><th>stake</th><th>returns</th>"
           "<th>P&amp;L</th><th>title</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>")


def _blocked_section(betlog) -> str:
    blocked = [e for e in betlog.events() if e["event_type"] == "blocked"]
    if not blocked:
        return "<section><h2>Blocked actions</h2><p>(none)</p></section>"
    rows = []
    for e in blocked:
        p = e["payload"]
        rows.append(f"<tr><td>{esc(e['bet_id'])}</td><td>{esc(str(p.get('rule', '')))}</td>"
                    f"<td>{esc(str(p.get('reason', p.get('memo', {}).get('title', ''))))}</td></tr>")
    return ("<section><h2>Blocked actions</h2><table><thead><tr><th>bet_id</th><th>rule</th>"
           "<th>reasoning / detail</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>")


def _tasks_section(betlog) -> str:
    tasks = open_tasks(betlog)
    if not tasks:
        return "<section><h2>Open human tasks</h2><p>(none)</p></section>"
    rows = [f"<tr><td>{esc(tid)}</td><td>{esc(t['bet_id'])}</td><td>{age_days(t)}d</td>"
           f"<td>{esc(t['description'])}</td></tr>" for tid, t in sorted(tasks.items())]
    return ("<section><h2>Open human tasks</h2><table><thead><tr><th>task_id</th><th>bet_id</th>"
           "<th>age</th><th>description</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>")


def _event_line(e) -> str:
    p = e["payload"]
    detail = (p.get("verdict") or p.get("decision") or p.get("rule") or p.get("reason")
             or p.get("title") or "")
    return (f"<div class='ev'><span class='ev-cycle'>c{esc(str(e['cycle']))}</span> "
           f"<span class='ev-bet'>{esc(e['bet_id'])}</span> "
           f"<span class='ev-type'>{esc(e['event_type'])}</span> "
           f"<span class='ev-actor'>({esc(e['actor'])})</span> "
           f"<span class='ev-detail'>{esc(str(detail))}</span></div>")


def _decision_log(betlog) -> str:
    events = betlog.events()
    if not events:
        return "<section><h2>Decision log</h2><p>(no events yet)</p></section>"
    lines = "".join(_event_line(e) for e in events)
    return (f"<section><h2>Decision log</h2><details><summary>{len(events)} events "
           f"(memo &rarr; critique &rarr; rebuttal &rarr; verdict &rarr; human decision) "
           f"-- click to expand</summary><div class='log'>{lines}</div></details></section>")


CSS = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 0; padding: 24px;
       background: #0b0e14; color: #e6e6e6; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.05rem; margin-top: 2rem; }
section { margin-bottom: 1.5rem; }
.headline { display: flex; flex-wrap: wrap; gap: 12px; }
.tile { background: #161b26; border-radius: 8px; padding: 12px 16px; min-width: 140px; }
.tile-label { font-size: 0.75rem; color: #9aa4b2; text-transform: uppercase; letter-spacing: 0.03em; }
.tile-value { font-size: 1.3rem; font-weight: 600; margin-top: 4px; }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { border-bottom: 1px solid #263042; padding: 6px 8px; text-align: left; }
th { color: #9aa4b2; font-weight: 600; }
svg text { fill: #9aa4b2; }
.log { max-height: 480px; overflow-y: auto; font-size: 0.8rem; font-family: ui-monospace, monospace; }
.ev { padding: 2px 0; border-bottom: 1px solid #1c2330; }
.ev-cycle { color: #6b7280; } .ev-bet { color: #4f7cff; } .ev-type { font-weight: 600; }
.ev-actor { color: #9aa4b2; } .ev-detail { color: #c9d1d9; }
details summary { cursor: pointer; color: #9aa4b2; }
"""


def render(ledger, betlog, runlog, config) -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    body = "".join([
        f"<h1>swarm50 report</h1><p style='color:#9aa4b2;font-size:0.8rem'>generated {esc(generated)}</p>",
        _headline(ledger, betlog, runlog, config),
        _balance_chart(ledger),
        _spend_charts(ledger),
        _bets_table(betlog),
        _blocked_section(betlog),
        _tasks_section(betlog),
        _decision_log(betlog),
    ])
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
           f"<title>swarm50 report</title><style>{CSS}</style></head><body>{body}</body></html>")


def write_report(ledger=None, betlog=None, runlog=None, config=None, out_dir=None):
    config = config or load_config()
    ledger = ledger or Ledger(config)
    betlog = betlog or BetLog(ledger)
    runlog = runlog or RunLog(ledger)
    out_dir = out_dir or REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render(ledger, betlog, runlog, config)
    path = out_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def main(argv=None):
    path = write_report()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
