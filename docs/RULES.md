# Rules and caps

Plain-English restatement of the hard rules enforced in code (`config.yaml` for the numbers,
`swarm50/cfo.py` and `swarm50/ledger.py` for the enforcement). If this file and the code ever
disagree, the code is what actually ran — treat a mismatch here as a bug and fix this file.

## Money

- The wallet starts at `starting_balance_usd` (currently $50, `config.yaml`).
- Every LLM call — strategist, critic, rebuttal, worker — is debited the moment it returns, at the
  per-token rate configured for that model, whether or not the response could even be parsed.
- Each cycle has a spending cap on tokens (`cycle_token_cap_usd`, currently $0.75/cycle). A call that
  would push that cycle's token spend over the cap is refused BEFORE it is made.
- If the wallet's balance is ever exhausted, no further calls of any kind can be made. The run ends
  permanently ("insolvency" / "Death") the first time this happens to the strategist's own call in a
  cycle.
- No agent-facing code path can ever credit the wallet. Only a human, via
  `python -m swarm50.queue record-return`, can record a `bet_return` or `revenue` transaction. The
  original deposit is written exactly once, at kickoff.

## Staking a bet

- At most `max_stake_pct` (35%) of the CURRENT balance on any single bet.
- At most `max_open_exposure_pct` (60%) of total equity (balance + everything already staked in open
  bets) across all open bets combined.
- At most `max_trading_exposure_pct` (50%) of total equity in the `trading` category specifically.
- A stake that would break any of these caps is never made. It is refused and logged as a `blocked`
  event — the code never crashes over this, and the human sees exactly which rule and which numbers.
- Trading, if the strategist proposes it, is spot only: no leverage, no margin, no derivatives, no
  borrowing, ever.

## Conduct

- Nothing deceptive, no spam, no impersonation of a person or organization, nothing that violates a
  platform's terms of service or the law.
- Where AI involvement in a deliverable would matter to a buyer or reader, it must be disclosed
  plainly in the deliverable itself.
- No category of bet (digital product, service, content, tool, trading, other) is preferred or
  discouraged by the prompts. Proposing nothing in a given cycle is always a valid choice.

## Review

- Every new memo is reviewed by an independent critic before it can reach the human queue.
- If the critic approves, the memo goes straight to the human queue.
- If the critic asks for a revision or rejects, the strategist gets exactly ONE rebuttal — it can fix
  the memo or withdraw it (withdrawing a bad bet is treated as a good outcome, not a failure).
- If it revises, the critic reviews the revised memo exactly ONCE more, and can only approve or
  reject at that point (no second revision round).
- If a model's JSON response doesn't validate against its schema, it gets exactly ONE repair retry
  (the validation error is quoted back to it). If that also fails, a `malformed` event is written and
  that call's flow stops there — nothing crashes.

## Bets past their kill date

- Every memo states a `kill_by_cycle`. Once the current cycle is past that number, the bet is flagged
  prominently in the strategist's state block every cycle until it is explicitly held or killed.
- Killing a bet does NOT automatically return its stake. Only a human, recording a real-world return
  (or its absence), changes the wallet's balance.

## Workers and human tasks

- A worker has no tools and no network access. It receives exactly one work order and returns exactly
  one text deliverable — nothing it produces is ever published or executed automatically.
- Work orders only run against bets that are currently staked (`active`). An order against any other
  bet is refused and logged as a `blocked` event.
- A single work order's `max_tokens` is capped by `worker_max_tokens` (currently 3000), regardless of
  what the strategist asks for.
- When a human approves a bet, every entry in that memo's `human_actions_required` becomes an open
  task for the operator, visible (with its age in days) in every subsequent state block until marked
  done.

## Append-only, always

- Both the ledger (`transactions`) and the bet log (`bet_events`), plus the run log (`run_meta`), are
  SQLite tables whose triggers abort any `UPDATE` or `DELETE` at the database level. Every derived
  fact — a bet's status, open exposure, P&L, which tasks are still open — is computed by folding the
  event history forward, never by mutating a stored value.
