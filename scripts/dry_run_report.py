"""python scripts/dry_run_report.py results/dryrun_linear_*.jsonl results/dryrun_convex_*.jsonl

Reads dry-run JSONL files (from scripts/dry_run.py) and prints/writes results/dryrun_summary.md.
Pure post-processing: makes no LLM calls at all.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm50.dryrun import report_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(report_main())
