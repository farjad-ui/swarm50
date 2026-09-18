"""python scripts/dry_run.py --arm linear|convex --n 10 [--batch] [--max-total-usd 5.00]

DO NOT RUN FOR REAL: this makes real metered_call()s, which by the ground rules of this project must
never hit a real Anthropic API key or the claude CLI outside of a mocked test. All logic lives in
swarm50/dryrun.py so it can be unit-tested with mocks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm50.dryrun import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
