# How to run swarm50

Steps in order, from a fresh checkout to a live 30-day run. Commands are Windows PowerShell; Linux/macOS
differences are noted inline. The detailed reasoning behind each pre-kickoff step is in
`docs/KICKOFF_CHECKLIST.md`.

## 1. Set up (no money spent)

```powershell
git checkout main
git pull
python -m venv .venv
.venv\Scripts\Activate.ps1            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env           # Linux/macOS: cp .env.example .env
```

Open `.env` and set `ANTHROPIC_API_KEY=sk-ant-...`. `.env` is git-ignored; never commit it.

Check the install:

```powershell
pytest                                # expect: 90 passed
python -m swarm50.ledger status
```

## 2. Set config (`config.yaml`)

| Key | Set to | Why |
|---|---|---|
| `backend` | `api` | Real runs go through the Anthropic API so ledger costs match real spend. |
| `reward_arm` | `linear` or `convex` | Must match what you preregister. `convex` tells the agents next-phase budget = 10x profit, so only use it if you will honour that. |
| `total_days` | `30` | Length of the run. |
| `end_date` | kickoff date + `total_days` - 1 | **Set this by hand.** The strategist's "days remaining" is computed from `end_date`, not from the kickoff date. If you kick off on a different day than planned, update it before kickoff. |

Leave `start_date: null`; kickoff records the real start date.

## 3. Real dry run (small, capped spend)

The only pre-kickoff step that makes real API calls. Each harness run stops before cumulative cost
passes `--max-total-usd` (default $5.00).

```powershell
python scripts/dry_run.py --arm linear --n 10
python scripts/dry_run.py --arm convex --n 10
python scripts/dry_run_report.py (Get-ChildItem results\dryrun_*.jsonl)   # Linux/macOS: results/dryrun_*.jsonl
```

Read `results/dryrun_summary.md`. If the proposals, costs, or prompts look wrong, fix them now.
Add `--batch` for half-price Batches API runs, but that path has never been tested against the real API
(`docs/DECISIONS.md` D6), so try it once deliberately before relying on it.

## 4. Preregister

Fill every `_[owner: ...]_` field in `docs/PREREGISTRATION.md`, then commit and push it **before**
kickoff:

```powershell
git add docs/PREREGISTRATION.md
git commit -m "Preregister hypotheses before kickoff"
git push
```

## 5. Confirm the money rail (outside the code)

Decide which account stakes leave from and returns land in, and which platform or exchange each kind of
bet uses. The code never moves money; `record-return` only logs money you already moved.

## 6. Kick off (irreversible)

```powershell
python -m swarm50.cycle kickoff
```

Writes the one `deposit`, locks the start date, reward arm, and config hash. It refuses to run twice.

## 7. Daily loop, for `total_days` days

```powershell
python -m swarm50.cycle run                      # once per day; refuses a repeat without --force
python -m swarm50.queue list                     # memos waiting for you
python -m swarm50.queue show <bet_id>
python -m swarm50.queue approve <bet_id>         # stakes it if guardrails pass, creates your tasks
python -m swarm50.queue reject <bet_id> --reason "..."
python -m swarm50.queue tasks list               # real-world actions the agents need from you
python -m swarm50.queue tasks done <task_id> --note "..."
python -m swarm50.queue record-return <bet_id> <amount_usd> --type revenue|bet_return --note "..."
python -m swarm50.queue close <bet_id> --note "..."
python -m swarm50.report                         # rebuilds report/index.html
```

Open `report/index.html` in a browser any time for balance, spend, bets, blocked actions, and the full
decision timeline.

## When it stops

- After `total_days` cycles, `cycle run` refuses to run.
- If the wallet can't afford the strategist's call, the run ends permanently (`run_ended`, reason
  `insolvent`).
- If a cycle errors, it logs a `cycle_error` event with the traceback and exits non-zero; the database
  stays usable, so fix the cause and run again.
