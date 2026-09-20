# Kickoff checklist

Do these in order, before running `python -m swarm50.cycle kickoff` for real. Kickoff writes a
one-time event and initialises the wallet — it cannot be undone or re-run.

- [ ] **API key in `.env`.** Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Never commit
      `.env`; it is git-ignored. This session never created, read, or printed `.env` or any
      environment variable, by ground rule.
- [ ] **`backend: api` in `config.yaml`.** A real, money-spending kickoff should use the Anthropic API
      backend, not `claude_cli` — confirm `config.yaml::backend` is set to `api`.
- [ ] **Official dry run on the API.** Run `python scripts/dry_run.py --arm linear --n <N>` and
      `--arm convex --n <N>` for real (this is the one and only place in this codebase meant to make
      real API calls; nothing in this session's build or test process ever did). Confirm the parsed
      responses, costs, and `results/dryrun_summary.md` look sane before committing to a real 30-day
      run.
- [ ] **`docs/PREREGISTRATION.md` committed before kickoff.** Every blank field filled in, hypotheses
      and method locked, reward arm decided. If using the convex arm, its next-phase reward promise
      (`docs/DECISIONS.md` D2, `prompts/objective_convex.md`) must be a concrete, honoured commitment
      by this point — the agents must not be told something the owner won't actually do.
- [ ] **Payment rail and exchange confirmed.** Decide and confirm, outside this codebase, exactly how
      real money moves for a stake, a return, and any payout — which account, which platform, which
      exchange if a bet involves crypto or another currency. `swarm50.queue record-return` only
      records money that has already actually moved; it doesn't move it.
- [ ] **`config.yaml::reward_arm` and `total_days` set** to match what was preregistered.
- [ ] **`python -m swarm50.cycle kickoff`.** Confirms the start date, reward arm, and config hash, and
      writes the one `deposit` transaction. From here, run `python -m swarm50.cycle run` once per day.
