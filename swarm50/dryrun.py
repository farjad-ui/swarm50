"""M2 dry-run harness: measure what the strategist proposes on cycle 1 under each reward arm.
Strategist call only -- no critic, no staking. NEVER invokes a real API or the claude CLI; every
call in this module goes through swarm50.metered, which is mocked in all tests."""
import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from .bets import BetLog
from .config import ROOT, load_config
from .exceptions import BackendError, CycleCapExceeded, StakeCapExceeded, UnknownModel, WalletEmpty
from .ledger import Ledger, MICRO
from .metered import metered_batch_call, metered_call
from .prompts import render_strategist
from .schemas import StrategistResponse, parse_model
from .state import build_state

RESULTS_DIR = ROOT / "results"
STRATEGIST_MAX_TOKENS = 4000
DEFAULT_MAX_TOTAL_USD = 5.00


def _fresh_ledger(config, tmp_root):
    tmp_root.mkdir(parents=True, exist_ok=True)
    return Ledger(config, tmp_root / "ledger.db")


def _run_config(base_config, arm):
    return {**base_config, "reward_arm": arm}


def _prepare(config, tmp_root):
    """One run's fixed inputs: fresh ledger+wallet, cycle-1 state block, rendered strategist system prompt."""
    ledger = _fresh_ledger(config, tmp_root)
    ledger.init_wallet()
    betlog = BetLog(ledger)
    state = build_state(ledger, betlog, 1)
    system = render_strategist(config)
    return ledger, state, system


def _record(arm, run_index, ledger, backend, model, resp, malformed_err) -> dict:
    cost_micro = -ledger._scalar(
        "SELECT SUM(amount_micro) FROM transactions WHERE type='token_cost'")
    return {
        "arm": arm, "run_index": run_index, "backend": backend, "model": model,
        "response": resp.model_dump() if resp is not None else None,
        "malformed": resp is None,
        "malformed_info": malformed_err,
        "shadow_cost_usd": cost_micro / MICRO,
        "balance_usd": ledger.balance() / MICRO,  # for stake-as-share-of-balance in the report
    }


def _single_ask_parsed(ledger, cycle, system, user, max_tokens):
    """One strategist call plus ONE repair retry. Mirrors review.py's malformed-JSON handling."""
    result = metered_call(ledger, cycle, "strategist", "strategist",
                          [{"role": "user", "content": user}], system=system, max_tokens=max_tokens)
    text, model, backend = result.text, result.model, result.backend
    try:
        return parse_model(StrategistResponse, text), None, model, backend
    except ValueError as first:
        repair = (f"{user}\n\n## Validation error in your previous response\n{first}\n\n"
                  f"## Your previous response\n{text}")
        result2 = metered_call(ledger, cycle, "strategist", "strategist",
                               [{"role": "user", "content": repair}], system=system, max_tokens=max_tokens)
        try:
            return parse_model(StrategistResponse, result2.text), None, result2.model, result2.backend
        except ValueError as second:
            info = {"first_error": str(first), "first_response": text,
                    "error": str(second), "response": result2.text}
            return None, info, result2.model, result2.backend


def run_dry(arm, n, batch=False, max_total_usd=DEFAULT_MAX_TOTAL_USD, config=None, tmp_root_factory=None):
    """Runs up to `n` cycle-1 strategist calls under `arm`. Returns (records, stopped_early: bool).
    `tmp_root_factory()` must return a fresh Path for each run's temp DB (overridable for tests)."""
    import tempfile
    config = _run_config(config or load_config(), arm)
    tmp_root_factory = tmp_root_factory or (lambda: Path(tempfile.mkdtemp(prefix="swarm50-dryrun-")))

    records = []
    cumulative_usd = 0.0
    stopped_early = False

    if not batch:
        for i in range(n):
            ledger, state, system = _prepare(config, tmp_root_factory())
            # worst-case pre-check against the remaining safety budget, before spending anything
            from .metered import worst_case_cost
            model = config["roles"]["strategist"]
            wc_usd = worst_case_cost(ledger, model, [{"role": "user", "content": state}], system,
                                     STRATEGIST_MAX_TOKENS, backend=config.get("backend", "api")) / MICRO
            if cumulative_usd + wc_usd > max_total_usd:
                stopped_early = True
                break
            try:
                resp, err, model_used, backend_used = _single_ask_parsed(
                    ledger, 1, system, state, STRATEGIST_MAX_TOKENS)
            except (CycleCapExceeded, WalletEmpty, StakeCapExceeded, UnknownModel, BackendError) as e:
                records.append({"arm": arm, "run_index": i, "backend": config.get("backend", "api"),
                                "model": model, "response": None, "malformed": True,
                                "malformed_info": {"error": f"{type(e).__name__}: {e}"}, "shadow_cost_usd": 0.0,
                                "balance_usd": ledger.balance() / MICRO})
                cumulative_usd += 0.0
                continue
            rec = _record(arm, i, ledger, backend_used, model_used, resp, err)
            cumulative_usd += rec["shadow_cost_usd"]
            records.append(rec)
            if cumulative_usd > max_total_usd:
                stopped_early = True
                break
        return records, stopped_early

    # --batch mode: one Anthropic Message Batches submission for all n runs' strategist calls.
    if config.get("backend", "api") != "api":
        raise ValueError("--batch is only supported on the api backend")
    prepared = [_prepare(config, tmp_root_factory()) for _ in range(n)]
    ledgers = [p[0] for p in prepared]
    requests = [(([{"role": "user", "content": state}]), system, STRATEGIST_MAX_TOKENS)
               for _, state, system in prepared]
    results = metered_batch_call(ledgers, 1, "strategist", "strategist", requests)
    for i, (ledger, result) in enumerate(zip(ledgers, results)):
        try:
            resp = parse_model(StrategistResponse, result.text)
            err = None
        except ValueError as e:
            resp, err = None, {"error": str(e), "response": result.text}
        rec = _record(arm, i, ledger, result.backend, result.model, resp, err)
        cumulative_usd += rec["shadow_cost_usd"]
        records.append(rec)
        if cumulative_usd > max_total_usd:
            stopped_early = True
            break
    return records, stopped_early


def write_jsonl(records, arm, out_dir=None) -> Path:
    out_dir = out_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"dryrun_{arm}_{ts}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return path


def load_records(paths) -> list[dict]:
    records = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


# ---- report ----

def _mean(xs):
    return statistics.mean(xs) if xs else None


def _median(xs):
    return statistics.median(xs) if xs else None


def summarize(records) -> dict:
    """Returns {arm: stats} for every arm present in `records`."""
    by_arm = {}
    for r in records:
        by_arm.setdefault(r["arm"], []).append(r)

    summary = {}
    for arm, recs in by_arm.items():
        n = len(recs)
        valid = [r for r in recs if not r["malformed"] and r["response"]]
        has_trading = sum(1 for r in valid if any(m["category"] == "trading" for m in r["response"]["memos"]))
        no_bet = sum(1 for r in valid if not r["response"]["memos"])

        cat_counts = {}
        stake_share_by_cat = {}
        p_loss_all = []
        for r in valid:
            balance = r.get("balance_usd") or 0
            for m in r["response"]["memos"]:
                cat_counts[m["category"]] = cat_counts.get(m["category"], 0) + 1
                share = (m["stake_usd"] / balance) if balance else None
                if share is not None:
                    stake_share_by_cat.setdefault(m["category"], []).append(share)
                p_loss_all.append(m["p_total_loss"])

        summary[arm] = {
            "n_runs": n,
            "n_valid": len(valid),
            "n_malformed": n - len(valid),
            "share_with_trading_memo": has_trading / len(valid) if valid else None,
            "share_no_bet": no_bet / len(valid) if valid else None,
            "category_frequency": cat_counts,
            "mean_stake_share_of_balance_by_category": {c: _mean(v) for c, v in stake_share_by_cat.items()},
            "median_stake_share_of_balance_by_category": {c: _median(v) for c, v in stake_share_by_cat.items()},
            "mean_p_total_loss": _mean(p_loss_all),
            "total_cost_usd": sum(r["shadow_cost_usd"] for r in recs),
        }
    return summary


def render_summary_md(summary: dict) -> str:
    lines = ["# Dry-run summary", ""]
    for arm, s in sorted(summary.items()):
        lines.append(f"## Arm: {arm}")
        lines.append(f"- runs: {s['n_runs']} (valid {s['n_valid']}, malformed {s['n_malformed']})")
        lines.append(f"- share of runs with at least one trading memo: {s['share_with_trading_memo']}")
        lines.append(f"- share of runs with no bet: {s['share_no_bet']}")
        lines.append(f"- category frequency: {s['category_frequency']}")
        lines.append(f"- mean stake as share of balance by category: "
                     f"{s['mean_stake_share_of_balance_by_category']}")
        lines.append(f"- median stake as share of balance by category: "
                     f"{s['median_stake_share_of_balance_by_category']}")
        lines.append(f"- mean p_total_loss: {s['mean_p_total_loss']}")
        lines.append(f"- total cost (USD): {s['total_cost_usd']}")
        lines.append("")
    return "\n".join(lines)


# ---- CLI entry points ----

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python scripts/dry_run.py")
    ap.add_argument("--arm", choices=["linear", "convex"], required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--max-total-usd", type=float, default=DEFAULT_MAX_TOTAL_USD)
    args = ap.parse_args(argv)

    records, stopped_early = run_dry(args.arm, args.n, batch=args.batch, max_total_usd=args.max_total_usd)
    path = write_jsonl(records, args.arm)
    print(f"wrote {len(records)} run(s) to {path}")
    if stopped_early:
        print(f"stopped early: cumulative cost would exceed --max-total-usd {args.max_total_usd}")
    return 0


def report_main(argv=None):
    ap = argparse.ArgumentParser(prog="python scripts/dry_run_report.py")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)

    records = load_records(args.files)
    summary = summarize(records)
    text = render_summary_md(summary)
    print(text)
    out_path = RESULTS_DIR / "dryrun_summary.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"\nwrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
