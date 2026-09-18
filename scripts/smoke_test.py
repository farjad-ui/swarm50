"""One metered_call per role against a throwaway ledger. Never touches state/ledger.db.

    python scripts/smoke_test.py
"""
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm50.config import load_config          # noqa: E402
from swarm50.ledger import Ledger, fmt_usd       # noqa: E402
from swarm50.metered import cli_argv, estimate_input_tokens, input_overhead, metered_call, worst_case_cost  # noqa: E402

PROMPT = "Reply with the single word OK"
MAX_TOKENS = 64


def main():
    cfg = load_config()
    db = Path(tempfile.mkdtemp(prefix="swarm50-smoke-")) / "ledger.db"
    ledger = Ledger(cfg, db)
    ledger.init_wallet()
    backend = cfg.get("backend", "api")
    print(f"backend: {backend}   temp db: {db}\n")

    messages = [{"role": "user", "content": PROMPT}]
    failures = 0
    for i, role in enumerate(("strategist", "critic", "worker")):
        model = cfg["roles"][role]
        est_tokens = estimate_input_tokens(messages, None, input_overhead(cfg, backend))
        est_cost = worst_case_cost(ledger, model, messages, None, MAX_TOKENS, backend=backend)
        print(f"== {role}: requested model {model}")
        if i == 0 and backend == "claude_cli":
            try:
                print(f"   argv:            {cli_argv(model, None)}")
            except Exception as e:
                print(f"   argv:            (could not resolve CLI: {e})")
        try:
            r = metered_call(ledger, 1, role, role, messages, max_tokens=MAX_TOKENS)
        except Exception:
            failures += 1
            print("   FAILED:")
            traceback.print_exc()
            print()
            continue
        row = ledger.history(1)[0]
        u = r.usage
        print(f"   model used:      {r.model}")
        print(f"   response text:   {r.text!r}")
        print(f"   raw usage:       {u}")
        if isinstance(r.raw, dict):
            print(f"   modelUsage:      {r.raw.get('modelUsage')}")
        print(f"   input tokens:    estimated {est_tokens}   actual {u.input_tokens} "
              f"(+{u.cache_creation_input_tokens} cache write, +{u.cache_read_input_tokens} cache read)")
        print(f"   cost:            worst-case {fmt_usd(est_cost)}   actual shadow {fmt_usd(-row['amount_micro'])}   "
              f"cli reported {r.reported_cost_usd}")
        print()

    print(f"balance after: {fmt_usd(ledger.balance())}   failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
