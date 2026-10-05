# Independent review of the pivot spec

- **Date:** 2026-10-05
- **Reviewed:** `2026-10-05-digital-products-pivot-design.md`
- **Method:** a fresh reviewer agent (Opus) with no access to the brainstorming conversation read
  the spec, the audit and the code, and red-teamed it. I then checked its least-supported claims
  against primary sources and the code. The reviewer's full report is in the appendix, unedited.

## Resolution
The owner decided: Line B now, with discovery from web research only (via Agent Reach's no-login
backends); kickoff proposed for 9-10 Oct (moved to a 31 Oct target with a 10-11 Oct setup weekend; see
spec section 18.1); the score subtracts ad spend and fees, and AI spend stays H3; about 10 min/day is
acceptable; hard provider spend limits: yes; Pinterest by weekly CSV. All findings marked "Agree" below
are folded into **spec v2**.

## Fact checks

| Claim | Result | Source |
|---|---|---|
| Threads keyword search only returns the user's own posts without app review | **Confirmed. I was wrong earlier** when I said the permission is granted instantly to testers. Public search needs Meta App Review for `threads_keyword_search` | Meta docs: "If your app has not been approved for the `threads_keyword_search` permission, the search will be performed only on posts owned by the authenticated user." |
| `views` may not be returned for other sellers' listings in `findAllListingsActive` | **Unverified either way.** The audit's "confirmed" overstated it; the source covers the field's behaviour, not who can see it | etsy/open-api discussion #1710 |
| Gumroad payout to a Pakistani bank isn't evidenced | **Refuted.** Gumroad's "Getting paid" page lists Pakistan, payout currency PKR | gumroad.com/help/article/13-getting-paid |
| Bet IDs collide across rounds/reruns | **Confirmed in code:** `review.py` sets `bet_id = f"c{cycle}-{i}"`; a `--force` rerun already reuses the same IDs today | `swarm50/review.py` (`review_memos`) |
| The cap starves workers and the product review | **Confirmed:** work orders run after the critic loop (`cycle.py`), and the pre-call gate reserves the worst case (4000 Fable output tokens ≈ $0.20 per call) | `cycle.py`, `metered.py`, `review.py` |

## My verdict on each finding

| # | Finding | Verdict | Note |
|---|---|---|---|
| C1 | Budget under-estimated; cap starves workers | **Partly agree** | Starving the steps that build products is real. The cost level is uncertain: my model assumed ~$0.30/day in actual spend, and the reviewer's $0.45-0.65 is plausible on heavy days. **The dry run must measure it.** Reserve budget for workers and the product review; consider running the strategist every 2-3 days in operating mode |
| C2 | Score undefined and gameable | **Agree** | Define net in code (sales − fees − ad spend in the window); `scale_min_sales` ≥ 3; cap ad spend for the run |
| C3 | Bet pipeline too heavy for $0.20 listings | **Agree, highest-value change** | Line A test products: a build allowance with one approval (the finished draft). Memo, critic and stake for scale bets only |
| C4 | Line B: weakest path, broken research source | **Agree on the research source** (confirmed). **Disagree on payout** (verified). Image hosting: Gumroad cover images may be public URLs; verify | **Owner decision:** defer Line B behind Line A, or keep it and budget for Meta App Review of keyword search |
| I1 | Analyst boundary leaks; web search breaks the gate and single-turn rule | **Agree** | Quote fields reach the strategist by design; web search results bill as input tokens and can return `pause_turn`. Cap the quotes; rewrite the boundary claim honestly; drop or tightly cap `web` |
| I2 | The critic can't check what it's asked to | **Agree** | Code validates evidence IDs; give the critic the cited numbers; give the product review the rendered pages as images |
| I3 | Strategist output will truncate | **Agree** | Separate thesis call; configurable max_tokens; no repair retry on a `max_tokens` stop |
| I4 | Bet ID collisions | **Agree, latent bug today** | `c{cycle}-r{round}-{i}`; memos only in the final round |
| I5 | Money-accounting holes | **Agree** | Refund type written only by ingest; net excludes listing fees (already in the stake); Gumroad product↔bet mapping; provider spend limits; a sanity hold on large auto-credits |
| I6 | Publishers and K1 data never tested live before kickoff | **Agree** | First build task: verify competitor `views`; live draft-listing plus Threads-post smoke test in K4 |
| I7 | Agent-driven Etsy shop risk | **Agree** | Near-duplicate lint, trademark denylist, never pass competitor tags to workers, opt out of Offsite Ads, state the identity-level suspension downside |
| I8 | Buyer privacy at ingest | **Agree** | Whitelist fields when parsing; never store raw receipts; referrer reduced to a domain; test for it |
| I9 | Machine, network, employer | **Partly** | Owner has decided: OneDrive sync is off, no move. Valid: `state/tokens.json` must never sync; the K3 "VPS" fallback contradicts the same-network rule (prefer an always-on home device) |
| I10 | Strategist acts on noise | **Agree** | No Line A kills before ~day 45 except for policy reasons |
| I11 | Scored window depends on the kickoff date | **Agree** | Fix the kickoff date in the prereg, with a re-target rule if it slips |
| M1 | strategist.md "run ends permanently" | **Disagree** | It's a true statement of fact, kept deliberately; the "no threat" test covers the objective only |
| M2-M4 | double state to critic, image transaction type, `sys.exit` in queue | **Agree** | Small and cheap |
| M5 | H1 trivially true | **Agree** | Replace with calibration: per-product day-14/30 view predictions scored by code |
| M6 | Buyers expect Google Sheets copy links | **Agree, good market point** | Possibly automatable via the Drive API (upload, convert, link-share, `/copy`); verify; include in K2 |
| M7 | Overhead may exceed revenue | **Agree** | Show the true P&L prominently |

## Cut list: my position
- **Accept:** multi-round discovery → one round with a discovery prompt; `brand_kit` → set in config;
  `revision` → reject and re-order; memo/critic/stake for Line A tests; NicheThesis → a one-page
  markdown thesis plus one approval event.
- **Accept if Line B is deferred:** the `web` source, Threads research, Gumroad ingest, Threads image posts.
- **Owner call:** Pinterest API. The manual alternative (Pinterest's own bulk CSV pin upload, built
  weekly from Etsy image URLs) removes the 11-26-day review and the OAuth video at about 5 owner-minutes a week.
- **Owner call:** operating-mode strategist cadence (daily vs every 2-3 days).

## Questions for the owner (merged from the review)
1. **Line B now or later?** If now, accept a Meta App Review (screencast, privacy policy, likely
   business verification) for keyword search, or run Line B discovery on web search alone.
2. **Kickoff date** to fix in the prereg, and the re-target rule if it slips past early December.
3. **Score definition:** subtract ad spend and fees in the window? (Recommended: yes; AI spend stays H3.)
4. **Owner time:** is about 10 min/day (honest, including buyer messages and Gumroad tasks) acceptable?
5. **Hard spend limits** on the Anthropic and Google accounts so $100 is a real ceiling.

---

## Appendix: reviewer's full report

# Red-team review: swarm50 digital-products pivot spec (2026-10-05)

## Executive summary
1. **Verdict: build with changes, and cut about 40% of the scope first.** The safety core is sound: plain-code publishing, hash-matched approvals, revenue that only comes from platform APIs, and the append-only ledger. The business and agent layers around it are oversized for a $100, 90-day, one-person run.
2. The budget does not add up. A daily Fable strategist, Fable rebuttals, an analyst with web search and images will probably eat $60-75 of the $100, not the ~$45 the spec implies. The per-cycle cap also starves the step that actually makes products (workers run last).
3. The scoring objective is undefined at its edges ("net" of what?) and easy to game. One sale unlocks a 35% ad bet, and spending before cycle 61 costs nothing toward the score.
4. Applying the memo → critic → stake → next-day work order → draft approval pipeline to $0.20 listings gives 2+ days of latency, two owner approvals per product and critic costs bigger than the stake. That makes the 2-minute day impossible.
5. Line B (Threads → Gumroad) is the most expensive line to build and the least likely to earn. Its research source (Threads keyword search) and its image hosting both look broken as specified. Ship Line A end-to-end first and gate Line B behind it.

## Findings by severity

### CRITICAL

**C1. The thinking budget is under-estimated, and the cap starves the money-making step** (§7.6, §3.1; `review.py:12`, `cycle.py:168-176`, `ledger.py:133-141`)
- **What is wrong:**
  - A Fable strategist call costs about $0.04 input plus 2.5-4k output tokens at $50/Mtok, so roughly $0.17-0.24.
  - Every critic "revise" or "reject" triggers a Fable rebuttal, which is another ~$0.15-0.20. Repair retries double either call.
  - Realistic operating days therefore cost $0.45-0.65, which is $37-54 over 83 days, plus ~$10 for discovery.
  - "Analyst ~$3" is wrong. Discovery alone allows 8 requests × 3 rounds × 7 days = 168 analyst calls at about $0.02-0.03 each, before web search.
  - The caps don't bound the run either: 7×$1.50 + 83×$0.75 + 90×$0.50 = $118 > $100.
  - The pre-call gate reserves the worst case (4000 tokens × $50/Mtok = $0.20 per Fable call). So by the 2nd-3rd memo the $0.75 cap trips. Workers run after the review loop (`cycle.py:168`) and `critic_product` runs after workers, so the steps that produce sellable files are the ones refused.
- **Why it matters:**
  - H2 will land around 60%+, not 37%.
  - No money is left for scale bets.
  - Products silently fail to get built on busy days.
- **What to change:**
  1. Run the operating-mode strategist every 3 days. Ingest stays daily. Etsy data moves slowly anyway.
  2. Alternatively, put Sonnet on operating cycles and keep Fable for discovery and a weekly review.
  3. Give workers, rendering and `critic_product` their own reserved per-cycle budget, or run work orders for already-staked products before reviewing new memos.
  4. Add a run-level burn-rate line to the daily view ("spent $X of a planned $Y by today").
  5. Re-derive the §7.6 spend table from these numbers.

**C2. "Net revenue in the final 30 cycles" is undefined and gameable** (§1, §7.2, §8 `objective.md`)
- **What is wrong:**
  - "Net" isn't defined. If ad spend inside cycles 61-90 isn't subtracted, $30 of Etsy Ads that buys $20 of sales raises the score while losing $10.
  - Spending before cycle 61 has zero score cost. A capable strategist will burn the wallet on inventory and ads early, then coast.
  - `scale_min_sales: 1` means one sale (possibly the owner or a friend) unlocks a stake of up to 35% of the balance.
  - Etsy Ads results aren't available through the API, so neither code nor the critic can see "observed ad return" (§7.2).
- **What to change:**
  1. Define the score in code: sales − platform fees − listing fees − ad spend, all within the window. Report AI spend in the window next to it (that is H3).
  2. Show the score-to-date in the daily view from cycle 61.
  3. Set `scale_min_sales` ≥ 3 from distinct buyers.
  4. Cap total ad spend for the run (e.g. $20).
  5. Require the owner to type ad spend and attributed sales from the Etsy dashboard when a scale bet closes, and make that the only "ad return" the critic sees.

**C3. The bet/stake machinery is the wrong shape for $0.20 listings** (§3.1, §7.2-7.3; `workers.py:42`, `queue.py`)
- **What is wrong:**
  - Work orders only run on `active` (staked) bets (`workers.py:42`), and staking happens at owner approval. So each product goes:
    1. Cycle N: memo, then critic (and maybe Fable rebuttal plus final critic).
    2. Owner stakes it.
    3. Cycle N+1: strategist issues work orders; worker, renderer, images and `critic_product` run.
    4. Owner approves the drafts.
    5. Publish.
  - That is two approvals and two or more days per product. The critic loop (about $0.05-0.45) costs more than the $0.20-3 stake it guards. The real cost of a product (tokens plus ~$0.30 of images) isn't in the stake at all.
  - On top of that, 3 Threads posts + 5 pins + 2-5 listings a day, each with 8-10 images and a 10-page PDF, can't be honestly reviewed in 2 minutes. The audit's E10 (rubber-stamping) becomes the default.
- **What to change:**
  1. Line A test bets: drop the memo, critic and stake. Give the strategist a daily build allowance (e.g. ≤1 new product a day, a listing-count cap) and let it issue work orders directly. The owner approves only the finished draft (one approval).
  2. Keep memo, critic and stake for scale bets only.
  3. Cut social volume (see the cut list).
  4. Re-baseline H5 at about 10 minutes a day, honestly, including buyer messages and Gumroad tasks.

**C4. Line B costs the most and has the weakest path to revenue** (§4, §5.2, §6, §11)
- **What is wrong:**
  - **Research source:** as I understand Meta's docs, without approval for the advanced `threads_keyword_search` permission, keyword search returns only the authenticated user's own posts. Verify on day 1. If that's right, the "Threads" research source returns nothing in tester mode, and discovery and the thesis rest on web search alone.
  - **Distribution:** a zero-follower, openly AI account that only broadcasts, with automated engagement banned and no owner time for manual replies, is close to the worst case for Threads growth.
  - **Images:** §11 says Threads images reuse Etsy-hosted URLs. Line B products live on Gumroad and have no Etsy images, so Line B posts have no public image host.
  - **Owner time:** Gumroad needs ~10 minutes of owner time per product. Gumroad Discover won't surface a new seller. Gumroad payouts to a Pakistani bank are asserted in Decision 2 but not evidenced.
  - **Build cost:** discovery mode, the 10-section `NicheThesis`, `critic_thesis`, the thesis events and the day-45 re-check all exist mainly for this line.
- **What to change:**
  1. Ship v1 as Line A only, plus the Threads publisher in text-only mode.
  2. Turn on Line B (Gumroad ingest, thesis) only if (a) Threads keyword search is verified to return public posts and (b) Gumroad PK payout is verified with a $1 test sale.
  3. If kept, replace the thesis machinery with a one-page owner-approved markdown thesis stored as one `run_meta` event.

### IMPORTANT

**I1. The analyst boundary leaks by design, and web search breaks the metered-gateway rule** (§5.2-5.3, §1 ground rules; `metered.py:75-81, 108-115`)
- **What is wrong:**
  - `ResearchBrief` has `support: [quotes]` and `example_phrases`. NicheThesis requires hooks "in the audience's words". So stranger text does reach the strategist (via `reread`) and then workers and posts. The §21.4 "hostile text never reaches the strategist" test contradicts the schema.
  - Anthropic web search adds search-result content as input tokens. That is often 10-30k tokens per search, so up to ~$0.20 per analyst call. `worst_case_cost` can't predict it, so the pre-call gate can be overrun after the fact.
  - Long server-tool turns can return `pause_turn`, and continuing one is a second turn, which breaks "one system + one user message".
  - `_call_api` has no `tools` parameter and ignores `stop_reason`.
- **What to change:**
  1. Cut the `web` source from v1.
  2. Length-cap quote fields (e.g. ≤120 chars, ≤5 per brief), strip URLs and @handles, and show them fenced as data.
  3. Rewrite §5.3 and §21.4 honestly: the real defences are "no agent has side-effecting tools" plus human approval.
  4. For `etsy` requests, make the hypothesis a numeric threshold that code evaluates. Don't let an analyst who has seen the hypothesis grade it.

**I2. The critic is asked to check things it is never given** (§7.2, §10.2.3, §6; `review.py:43-45`)
- **What is wrong:**
  - `_review_memo` passes only `state` and the memo. "Cited evidence is real" can't be checked from a 40-row index of one-line conclusions.
  - "Real" means the ID exists, which is a job for code, not an LLM.
  - `critic_product` would see the JSON spec, not the rendered PDF or cover, so it can't judge overflow, ugliness or whether the file matches the listing.
- **What to change:**
  1. Code rejects memos whose `demand_evidence` IDs don't exist or don't match the memo's line.
  2. Pass the cited briefs' code-computed numbers into the critic's user message.
  3. Give `critic_product` the rendered pages as image blocks. That is still one user message.
  4. Specify that a product whose `critic_product` call was refused by the cap cannot enter the batch.

**I3. Strategist output will truncate** (§5.1, §6, §16; `review.py:12, 21-34`)
- **What is wrong:**
  - `STRATEGIST_MAX_TOKENS = 4000` is hard-coded. The new response carries reasoning, up to 3 memos with new fields, 8 research requests, rereads, bet actions, work orders, notes, and in cycle 6 a 10-section thesis with citations.
  - Truncation produces invalid JSON. The repair retry re-sends the truncated text and truncates again. The result is `malformed`, ~$0.40 burned and a lost cycle.
- **What to change:**
  1. Make the thesis its own call with its own schema.
  2. Raise and configure the strategist's max_tokens.
  3. Expose `stop_reason` on `Result` and skip the repair retry when it is `max_tokens` (repair can't fix truncation).

**I4. Bet IDs collide across discovery rounds and reruns** (§3.2; `review.py:99`, `cycle.py` `--force`)
- **What is wrong:** `bet_id = f"c{cycle}-{i}"`. Round 2 of a discovery cycle, or any `--force` rerun, writes a second `c3-1` that merges into the first bet's event history. Once publishing and ingest key on bet_id, this cross-wires listings and revenue.
- **What to change:** Use `c{cycle}-r{round}-{i}` (or a short uuid). Allow memos only in the final round. Drop `--force` once publishing exists.

**I5. Money-accounting holes** (§7.3-7.5, §14)
- **What is wrong:**
  1. Refunds, cases and chargebacks aren't modelled. `adjustment` is banned for agent-facing code and there is no negative-revenue type, so an Etsy case refund leaves phantom money in the wallet.
  2. Revenue is credited at receipt time while Etsy holds new-seller funds for 45-90 days. Agents can re-spend money that doesn't exist yet, so the owner's real card outlay (Anthropic, Google, Etsy bill) can exceed $100.
  3. Listing fees are charged against the stake and also show up in Etsy's payment-account ledger entries. If "net" uses those entries, the fees are counted twice.
  4. Gumroad products are created by hand, and nothing maps a Gumroad product ID to a bet_id, so H4 per-line attribution breaks.
  5. Nothing caps provider-side spend. Google billing budgets only alert, and a mis-set per-image price in config makes the gate pass everything.
- **What to change:**
  1. Add a `refund` transaction type that only ingest can write.
  2. Define net as sale − transaction/processing fees only (listing fees live in stakes).
  3. Make the owner enter the Gumroad product ID in the task-done note, and have ingest refuse unmapped sales.
  4. Set an Anthropic workspace spend limit and Google budget alerts.
  5. Hold any single-day auto-credit above a sanity bound (e.g. $100) for owner confirmation.

**I6. The publishers and the K1 data source are never tested live before kickoff** (§18.2, §20, §21.5, §23)
- **What is wrong:**
  - All tests are mocked, and the sandbox forces publishing off. The first real Etsy OAuth/PKCE flow, multipart file/image upload, Threads container-then-publish and token refresh would happen on day 1 of the scored run.
  - K1 depends on `views` being returned for *other sellers'* listings in `findAllListingsActive`. The audit's "confirmed" source may concern own listings only.
- **What to change:**
  1. Add a live publish smoke test to K4: one Etsy listing created through the API in draft state, then activated; one Threads post.
  2. Make "verify `views` on competitor listings" the first build task, before K1.
  3. If `views` isn't available, fall back to favorites plus shop-level `transaction_sold_count` from `getShop`, which is arguably a better demand signal anyway.

**I7. Agent-driven risks to the Etsy shop** (§13.2, §10.1, §5.2)
- **What is wrong:**
  - The rational strategist maximises listing count (cheap, and "15+ listings" lore says it helps). That leads to near-duplicate re-skins, which is Etsy spam and search-manipulation territory.
  - Competitor titles and tags flow into research. Common Etsy tags are trademarks (Notion, Canva, GoodNotes, Cricut).
  - New shops are opted into Offsite Ads by default (15% fee on attributed sales), which is invisible to the strategist.
  - An Etsy suspension is tied to the owner's identity and effectively permanent, so the downside is losing Etsy for life, not $100.
- **What to change:**
  1. Lint for near-duplicates (title/tag Jaccard and spec-hash similarity against live listings).
  2. Keep a trademark denylist in the tags/title lint.
  3. Never pass competitor titles or tags to workers.
  4. Add an Offsite Ads opt-out to setup.
  5. State the identity-level downside in §18.

**I8. Buyer privacy at ingest isn't specified** (§9, §14)
- **What is wrong:** Etsy receipts carry buyer name, address and often email, and Gumroad sales carry email. The spec forbids these in the view, but research raw responses are saved to disk, and nothing says ingest won't persist raw receipt payloads or ledger notes.
- **What to change:**
  1. Whitelist fields at parse time (amounts, IDs, timestamps, listing ID, country at most).
  2. Never write raw receipt or sale JSON.
  3. Reduce Gumroad `referrer` to a bare domain (it's attacker-controllable text).
  4. Add a test asserting no `@` or name fields reach the DB.

**I9. The machine, the network and the employer** (§15, §18 K3/K7, audit E5)
- **What is wrong:**
  - The repo sits under `OneDrive - Higher Education Commission`. Sync is off today, but `state/tokens.json` (Etsy and Meta refresh tokens) and buyer data would go to the employer tenant if sync is ever re-enabled.
  - If this is an employer laptop, or it moves between office and home networks, it breaks both the "same machine and network" rule and likely K7.
  - The K3 fallback ("small VPS") puts API traffic on a foreign IP, which contradicts §15's network-consistency rule.
- **What to change:**
  1. Move the repo off the OneDrive path now.
  2. Decide the always-on device before the shop opens.
  3. Reword the K3 fallback (a home mini-PC on the same connection, or accept the VPS and note the risk).

**I10. The strategist will act on noise, and Etsy needs time** (§9, §7.2, `kill_by_cycle`)
- **What is wrong:** With tens of views per week, per-product numbers are meaningless. A daily strategist with kill/hold actions will churn listings, and Etsy needs about 60-90 days to settle a new listing's rank.
- **What to change:** No kills on Line A listings before ~day 45 except for policy reasons (listings cost $0.20 per 4 months). The decision that matters is what to build next. Pairs with the every-3-days cadence in C1.

**I11. The scored window depends on the kickoff date** (§19 H3, audit M8)
- **What is wrong:** A 3-4 week build plus Pinterest's 11-26-day review plus K3 (7 days) plus K4 (7 days) realistically puts kickoff in mid-to-late November, so cycles 61-90 fall in mid-January to mid-February. A two-week slip moves the window past the planner peak. Listings made in late November also won't rank for the January peak.
- **What to change:** Fix the kickoff date in the prereg now, with an explicit "if later than X, re-target away from planner/budget niches" rule.

### MINOR

- **M1.** `prompts/strategist.md:7` still says "the run ends permanently". The §8 "no shutdown threat" test only checks `objective.md`. Extend the test to every rendered strategist prompt, or soften the line.
- **M2.** The critic gets the ~3k-token state twice: in the system prompt via `render_critic(state)` (`prompts.py:43`) and in the user message (`review.py:45`). Drop one, and pass `cache=True` for multi-memo cycles. `metered_call` supports it but nothing uses it.
- **M3.** The separate image cap needs a new transaction type. `cycle_spend` sums all `token_cost` (`ledger.py:111-113`), and `TYPES` is a CHECK constraint (`ledger.py:12`). Easy now since no DB exists, but the spec doesn't mention it. It also needs a mode-aware cap for discovery.
- **M4.** `queue.approve` calls `sys.exit` on a non-queued bet (`queue.py:23,25`). Inside the new batch walker, one stale item ends the session. Return errors instead.
- **M5.** H1 ("revenue falls short of EV") is trivially true at near-zero sales. Replace it with a calibration test of the research subsystem: each product preregisters day-14 and day-30 view predictions, and code scores them from `metrics`. That is the learning actually worth $100.
- **M6.** Most top-selling Etsy spreadsheets ship as Google Sheets copy links, and buyers on mobile or Mac struggle with XLSX. Make the Sheets import check part of K2, and consider a "make a copy" PDF.
- **M7.** Business overhead (Payoneer $29.95/yr, 3% withdrawal fee, FX, a possible Etsy setup fee; verify for PK) probably exceeds plausible revenue. Show the true P&L line prominently so a "winning" agent run isn't mistaken for a profitable business.

## What is good and should not be touched
- Plain code publishes only items with `draft_approved` whose `content_hash` matches (§13.1). Idempotent `published` events, kill switch, retry once and then raise an owner task.
- Revenue only from platform APIs, never from agents, keyed on a unique `external_id` (§7.4).
- "AI makes the art, code sets the words" (§11). This is the right call for quality and for Etsy's first-photo rule.
- The full stake is debited at approval, so the wallet understates money left (§7.3).
- The append-only and fold-to-derive discipline. New tables get the same triggers.
- Research requests must carry a hypothesis, and numbers are computed by code (§5.1-5.2).
- XLSX formula evaluation with an allowlist (§10.2.1).
- The §17 fixes are accurate. I verified them against the code: `cycle.py:176` insolvency on any cap hit, the `blocked` status in `bets.py:29-31` hiding queued bets, and the 10-event window at `state.py:53`. Build them first as planned.
- Pre-committed K-gates, with K7 (employment) before any account. The shop-safety ramp, no VPN, no automated engagement, away mode, and no catch-up cycles.

## Cut list (v1)
1. **Pinterest API entirely** (publisher, trends, analytics, OAuth video). If wanted, have the owner bulk-upload a weekly CSV of pins built from Etsy image URLs.
2. **Line B pipeline** (Gumroad ingest, thesis machinery, Threads research) until the C4 checks pass. Keep a text-only Threads publisher if the owner wants a channel test.
3. **Multi-round discovery mode.** One round per cycle with a discovery prompt and a higher cap. K1 already does pre-kickoff market discovery for Line A.
4. **The `web` research source** (I1).
5. **Memo, critic, stake and owner approval for Line A test bets** (C3). Keep them for scale bets.
6. **The `brand_kit` worker deliverable.** The owner picks a palette and two fonts in config once.
7. **The `revision` deliverable type.** Reject and re-order instead.
8. **Threads image posts.** Text-only removes the hosting problem.
9. **A daily operating-mode strategist.** Run it every 3 days.
10. **The `NicheThesis` 10-section schema plus `critic_thesis`**, if Line B is kept at all. One page of markdown and one approval event instead.

## Questions only the owner can answer
1. **Kickoff date:** what date are you committing to, and if it slips past early December, do you accept a judging window after the January peak, or should niches be re-targeted?
2. **Device and employer:** is the machine that will run this personal, and does it stay on one home network? Have you got written clearance under your employer's conduct rules (K7) before opening Etsy under your name?
3. **Score definition:** should "net revenue" subtract ad spend and listing fees in the window? Should AI spend in the window count too, or stay a separate H3?
4. **Time and goal:** will you really give about 10 minutes a day, including buyer messages and Gumroad tasks? If Line A alone answers "can agents run a small shop", are you willing to defer Line B?
5. **Payout reality:** have you confirmed Gumroad pays out to a Pakistani bank (or by another route you can actually receive), and are you willing to put hard spend limits on the Anthropic and Google accounts so the $100 is a real ceiling, not just a number in the ledger?
