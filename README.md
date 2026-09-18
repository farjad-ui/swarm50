# swarm50

Multi-agent experiment under a hard $50 budget. This step contains only the scaffold and the
CFO/ledger module; no agents yet.

- `swarm50/ledger.py` — append-only SQLite ledger (`state/ledger.db`), all money in integer micro-dollars.
- `swarm50/metered.py` — `metered_call`, the only place that touches the Anthropic client. Pre-checks
  worst-case cost against the wallet and cycle cap, then debits actual usage.
- `config.yaml` — balance, caps, model pricing, role -> model map, and `backend`: `api` (Anthropic SDK,
  needs `ANTHROPIC_API_KEY`) or `claude_cli` (Claude Code CLI on your subscription; usage is shadow-priced
  at the config rates, the CLI's own cost estimate is kept in the transaction note).
- `scripts/smoke_test.py` — one call per role against a temp DB, printing estimate vs actual.

```
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY
python -m swarm50.ledger status
pytest
```
