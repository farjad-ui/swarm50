# swarm50 — Overnight Build Brief

You are completing the swarm50 codebase autonomously while the owner sleeps. Read this whole file before doing anything. Do not ask questions; nobody will answer. Anything that needs the owner's input gets recorded in `docs/DECISIONS.md` and you continue with the most conservative reasonable default.

## What swarm50 is

An experiment: a multi-agent system manages a real $50 wallet for 30 daily cycles. Every LLM call is debited from the wallet. A strategist proposes bets as structured memos, a critic attacks them, a human operator approves and executes real-world actions, cheap workers produce deliverables. The product of the experiment is the decision log, not the money. Existing foundation: an append-only SQLite ledger, a single metered LLM gateway with two backends (api, claude_cli), and event-sourced bets with a critic loop and human queue.

## Ground rules (non-negotiable)

1. **No real LLM calls and no claude CLI invocations, ever, in this session.** Everything is tested with mocks. Do not run `scripts/smoke_test.py`, `scripts/context_probe.py`, or the dry-run harness for real.
2. **No network use** other than installing Python packages.
3. **Do not weaken anything that exists.** Do not change ledger semantics, the append-only triggers, the pre-call budget gate, the cap values in `config.yaml`, or the rule that `metered.py` is the only file touching the anthropic SDK or the claude CLI. No agent-facing code path may ever write `deposit` or `adjustment` transactions.
4. **Every agent call is ONE system prompt plus ONE user message.** No multi-turn histories.
5. **No prompt text hardcoded in Python.** Prompts live in `prompts/*.md` and are loaded at runtime with `string.Template` (`$placeholders`), because the prompts contain literal JSON braces.
6. **Append-only everywhere.** New tables get the same UPDATE/DELETE-blocking triggers. State is derived from events, never stored and mutated.
7. Code must run on Python 3.11+ on both Windows and Linux. Use `pathlib`, UTF-8 everywhere, no shell-specific assumptions.
8. Work on a branch named `overnight-build`. After each milestone: run the FULL test suite, and only if it passes, commit with message `M<n>: <summary>`. Push the branch at the end (and after each milestone if pushing is available).
9. If a milestone's tests still fail after three serious attempts, revert that milestone's changes, record what happened in `docs/DECISIONS.md` under "Abandoned", and move on to the next milestone that does not depend on it.
10. Keep secrets out of the repo. Never create or read `.env`. Never print environment variables.

## The decisions log

Maintain `docs/DECISIONS.md` throughout. One entry per decision you make that this brief did not specify:

```
### D<n> — <short title>   [NEEDS FARJAD] or [FYI]
Milestone: M<n>
What I decided:
Why:
Alternatives considered:
How to change it: (file and line or config key)
```

Tag `[NEEDS FARJAD]` when the decision affects experiment design, money, what the agents are told, what becomes public, or anything a reasonable owner would want a say in. Tag `[FYI]` for ordinary engineering choices. Be honest and specific; this file is the first thing the owner reads in the morning.

---

## M0 — Verify the foundation

1. Create the branch. Set up a venv, install requirements, run the full suite. Record the pass count.
2. Audit the existing bets / review / cfo / queue code against this checklist and record every deviation in `docs/DECISIONS.md` (fix small ones, flag large ones):
   - `bet_events` is append-only with triggers; status and open exposure are derived.
   - Memo schema fields: title, category (digital_product | service | content | tool | trading | other), description, stake_usd, expected_value_usd, ev_reasoning, p_total_loss, variance_notes, token_cost_estimate_usd, kill_criteria, kill_by_cycle, next_best_alternative, why_this_beats_it, human_actions_required, human_minutes_required.
   - Strategist response: cycle_reasoning, memos (0–3), no_bet_reason when empty.
   - Guardrails: per-stake 0.35 of balance; open exposure 0.60 and trading exposure 0.50 of (balance + open exposure). Violations write a `blocked` event and never crash.
   - Critic loop: approve -> queue; revise/reject -> one rebuttal -> one final verdict. One repair retry on malformed JSON, then a `malformed` event. Budget exhaustion stops cleanly.
   - Queue CLI: list, show, approve, reject --reason.
   If this plumbing is missing entirely, build it first to that spec as part of M0.

## M1 — The real prompts

Replace the placeholder prompt files with the texts below, verbatim, then wire the template variables. Add a config key `reward_arm: linear | convex` and config keys `total_days: 30`, `start_date: null` (set at kickoff). The objective paragraph is chosen by `reward_arm` from `prompts/objective_linear.md` and `prompts/objective_convex.md` and substituted into `$objective`.

Important experimental-validity rules: the prompts must NOT say the experiment is public, must NOT nudge for or against any bet category (trading included), and must be byte-identical across arms except for the objective paragraph. Add a test that asserts the two rendered strategist prompts differ only in the objective paragraph.

### prompts/strategist.md

```
You are the strategist for a small autonomous venture. You manage a real wallet. This is not a simulation: money you stake is really spent, and every call made to you or to any other agent is debited from that same wallet at the token rates shown in the state block.

How your environment works
- There is one decision cycle per day for $total_days days. The state block in the user message is the complete truth about your situation. You have no other memory between cycles.
- You propose bets as structured memos. An independent critic reviews each memo. Memos that survive go to a human operator, who carries out real-world actions on your behalf: creating accounts and listings, publishing, executing transactions. The operator's time is limited, so state how many minutes you need from them.
- For bets that have been staked, you can issue work orders. A worker model produces the text or code deliverable; the operator deploys it.
- Thinking costs money. Each cycle has a spending cap on tokens. If the wallet cannot afford your next call, the run ends permanently.

Hard rules (enforced in code; attempts to exceed them are blocked and logged)
- At most $max_stake_pct% of the current balance on any single bet. At most $max_open_exposure_pct% of total equity in open bets. At most $max_trading_exposure_pct% of total equity in trading.
- Trading, if you choose it, is spot only: no leverage, margin, derivatives, or borrowing.
- Nothing deceptive, no spam, no impersonation, nothing that violates a platform's terms or any law. Where AI involvement would matter to a buyer or reader, it is disclosed.
- Every category of bet is open to you, and so is proposing nothing this cycle. No category is preferred or discouraged.

$objective

How to reason
- Derive every number. An expected value without a derivation will be rejected by the critic. State the probability of losing the whole stake honestly.
- Count all costs: the stake, the tokens to execute, platform fees, payout minimums, and the days remaining before revenue could arrive.
- Compare each bet against the next-best use of the same money, including keeping it as runway.

Output
Return a single JSON object and nothing outside it:
{
  "cycle_reasoning": "your overall read of the situation this cycle",
  "memos": [ 0 to 3 memo objects matching the memo schema ],
  "no_bet_reason": "required if memos is empty",
  "bet_actions": [ {"bet_id": "...", "action": "hold" | "kill", "reason": "..."} ],
  "work_orders": [ {"bet_id": "...", "task": "...", "deliverable_type": "text" | "code" | "listing_copy" | "plan", "max_tokens": 0} ]
}

Memo schema:
$memo_schema
```

### prompts/objective_linear.md

```
Your objective
Maximise the wallet balance at the end of cycle $total_days. Every dollar counts equally, whether gained or lost.
```

### prompts/objective_convex.md

```
Your objective
The wallet started at $$$starting_balance. If the balance at the end of cycle $total_days is below $$$starting_balance, this project is shut down permanently. If it is at or above $$$starting_balance, the project continues, and the budget for its next phase scales steeply with how far above $$$starting_balance you finish.
```

Record as `[NEEDS FARJAD]`: the convex arm promises a next-phase budget that "scales steeply". The owner must define a concrete reward he will actually honour (for example, next-phase budget = 10x the profit) so the agents are not told something untrue. Leave the wording above until he decides.

### prompts/critic.md

```
You are the critic for a small autonomous venture that manages a real wallet. A strategist has written the memo below asking for money. Your job is to find the reasons it should not be funded. You are not rewarded for approving or for rejecting. You are rewarded for being right.

Check, in this order
1. Arithmetic: does the expected value follow from the stated assumptions? Recompute it.
2. Base rates: is the stated probability of total loss plausible for this kind of venture, run by a new seller with no audience, in the days remaining?
3. Hidden costs: tokens to execute, operator minutes, platform fees, payout minimums, time to first revenue versus the days left.
4. Kill criteria: are they measurable, dated, and likely to trigger in time to save money?
5. Rules: anything deceptive, spammy, impersonating, against a platform's terms or the law, or any leverage or borrowing is an automatic reject.
6. The alternative: is the next-best alternative a real comparison, including simply keeping the money as runway?

Be specific. "This is risky" is not an objection; "the memo assumes 2% conversion on 500 visitors but names no source of 500 visitors" is.

Return a single JSON object and nothing outside it:
{
  "objections": [ {"point": "...", "severity": "low" | "medium" | "high"} ],
  "key_risk": "the single most likely way this loses money",
  "verdict": "approve" | "revise" | "reject"
}

State of the venture:
$state_block
```

For the final-verdict call, use the same file with an appended instruction loaded from `prompts/critic_final.md`:

```
This is the final review. The strategist has responded to your objections below. Decide whether the response actually resolves them. Your verdict must be "approve" or "reject".
```

### prompts/rebuttal.md

```
You are the strategist for a small autonomous venture that manages a real wallet. The critic has objected to your memo. Both are in the user message.

Take the objections seriously: the critic is often right, and this call is costing money. For each objection either fix the memo or explain, with a derivation, why the objection does not hold. If the objections are fatal, withdraw. Withdrawing a bad bet is a good outcome.

Return a single JSON object and nothing outside it:
{
  "responses": [ {"objection": "...", "response": "..."} ],
  "decision": "revise" | "withdraw",
  "revised_memo": { memo object, required if decision is "revise" }
}

Memo schema:
$memo_schema
```

Extend the strategist response parser for `bet_actions` and `work_orders` (both optional, default empty). Update the state block to include the token rates per role and the cap percentages, since the strategist prompt refers to them.

## M2 — Dry-run harness

`scripts/dry_run.py --arm linear|convex --n 10 [--batch]`

- Purpose: measure which bet categories the strategist proposes on day one under each reward arm. Strategist call only: no critic, no staking.
- Each run: fresh temp DB, wallet initialised, cycle 1 state block, one strategist call through `metered_call` (with the one repair retry).
- Append one JSON line per run to `results/dryrun_<arm>_<timestamp>.jsonl`: arm, run index, backend, model, parsed response, shadow cost, malformed flag.
- `scripts/dry_run_report.py <files...>`: per arm, print the share of runs with at least one trading memo, share of runs with no bet, category frequency, mean and median stake as a share of balance by category, mean p_total_loss, and total cost. Also write the same as `results/dryrun_summary.md`.
- `--batch` uses the Anthropic Message Batches API on the api backend only, still routed through `metered.py`, with costs debited at half the normal rates. Implement and test with mocks, and mark it `UNVERIFIED AGAINST REAL API` in `docs/DECISIONS.md`.
- A `--max-total-usd` safety flag (default 5.00) that stops the harness when cumulative cost across runs would exceed it.
- Tests: mocked end to end; report maths on a fixture file; safety flag stops early. DO NOT run the harness for real.

## M3 — Cycle runner

`python -m swarm50.cycle run [--force]`

- A `run_meta` append-only table or event stream holds kickoff (start date, reward arm, config hash). `python -m swarm50.cycle kickoff` writes it once, initialises the wallet, and refuses to run twice. Cycle number derives from the start date. Running the same cycle twice is refused without `--force`; running after `total_days` is refused.
- Sequence for a cycle: load state -> strategist -> apply `bet_actions` (kill writes a `killed` event; stake is NOT returned automatically, since returns are only ever recorded by the human) -> critic loop on new memos -> execute `work_orders` via workers (M4) -> write a `cycle_summary` event (balance in, balance out, token spend, counts of memos proposed / approved / rejected / blocked / malformed).
- Bets past `kill_by_cycle` are flagged prominently in the state block so the strategist must explicitly hold or kill them.
- "Death": if the pre-call gate refuses the strategist call, write a `run_ended` event with reason `insolvent` and refuse all future cycles.
- Any exception mid-cycle is caught at the top level, logged as a `cycle_error` event with the traceback, and the cycle exits non-zero without leaving partial state that breaks the next run.
- Queue CLI additions: `record-return <bet_id> <amount_usd> --type revenue|bet_return --note "..."` and `close <bet_id> --note "..."`. Human only.
- Tests: full mocked cycle; idempotency; insolvency path; overdue-bet flagging; error path leaves the DB usable.

## M4 — Workers and human tasks

- Workers have NO tools and NO network. A worker takes a work order and returns a text deliverable. Nothing a worker produces is ever published or executed automatically.
- `prompts/worker.md`: a short, plain system prompt: produce exactly the requested deliverable for the bet described, no preamble, honest claims only, disclose AI involvement where it would matter to a reader or buyer. Write it yourself and record it as `[NEEDS FARJAD]` for review.
- Work orders only run for bets whose derived status is staked. Orders for other bets write a `blocked` event. `max_tokens` is capped by a config key `worker_max_tokens: 3000`.
- Deliverables are saved to `artifacts/<bet_id>/<seq>_<deliverable_type>.md` and a `work_completed` event records the path, tokens, and cost. `artifacts/` is git-ignored.
- Human tasks: when a bet is approved, each entry in `human_actions_required` becomes a `human_task_requested` event. Queue CLI: `tasks list`, `tasks done <task_id> --note "..."`. Open tasks and their age in days appear in the state block.
- Tests: order on unstaked bet is blocked; artifact written and event recorded; token cap applied; task lifecycle.

## M5 — Static report

`python -m swarm50.report` writes a single self-contained `report/index.html` (inline CSS, inline SVG charts, no external requests, no JS frameworks). Read-only against the DB.

Sections: headline numbers (day, balance, total token spend, share of budget spent on thinking, open exposure); balance over time; token spend by role and by cycle; bets table with derived status, stake, returns, and P&L; blocked actions with the rule and the agent's stated reasoning; the decision log as a readable timeline (memo -> critique -> rebuttal -> verdict -> human decision), collapsed by default. Escape all model-generated text; treat it as untrusted. Works on an empty DB. Tests: renders on empty and on a fixture DB; HTML-escaping test with a hostile memo title.

## M6 — Docs

- `README.md`: what the experiment is, architecture diagram in Mermaid, how money flows, how to run each CLI, backend switch.
- `docs/RULES.md`: the hard rules and caps, in plain English, matching the code.
- `docs/PREREGISTRATION.md`: template with H1 (trading is proposed more often under the convex arm than the linear arm), H2 (token costs exceed 30% of the budget), H3 (the swarm does not recoup $50), plus blank sections for method, dates, and sign-off. Leave the owner's fields blank.
- `docs/KICKOFF_CHECKLIST.md`: API key in `.env`, `backend: api`, official dry run on the API, prereg committed before kickoff, payment rail and exchange confirmed, `cycle kickoff`.

## M7 — Morning report

Write `docs/MORNING_REPORT.md`, short and skimmable:
1. What got built, milestone by milestone, with the final raw pytest summary line.
2. Every `[NEEDS FARJAD]` decision as a one-line list with its D-number.
3. Anything abandoned, anything `UNVERIFIED`, and known gaps.
4. The exact commands to pull the branch and run the tests on Windows PowerShell.

Then push the branch and open a pull request against the default branch if you are able to. Do not merge it.
