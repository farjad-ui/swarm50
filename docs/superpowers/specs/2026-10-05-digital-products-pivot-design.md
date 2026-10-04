# swarm50 digital-products pivot: design spec

- **Date:** 2026-10-05
- **Status:** approved in brainstorming; awaiting owner review of this written spec
- **Companion:** `2026-10-05-assumption-audit.md` (the risk register this spec answers)
- **Replaces:** the category-neutral, trading-hypothesis design in `OVERNIGHT_BRIEF.md` M1/M2

## 1. Summary

swarm50 stops being a category-neutral betting experiment and becomes a small, mostly autonomous
**digital-products business** run by agents for 90 days on a $100 wallet. It runs two product lines
that share one wallet:

- **Line A, Marketplace:** practical, search-driven products on **Etsy**.
- **Line B, Conversation:** problem-solving products sold on **Gumroad**, marketed through a
  **Threads** brand account built around one niche the agents discover in week 1.

Pinterest drives traffic to both lines. The agents research demand, propose bets, build real files
(XLSX/PDF with AI-composited images), and draft listings and posts. The owner approves one daily batch
(about 2 minutes), and plain code publishes. The strategist is judged on **net revenue earned in the
final 30 cycles**, which rewards products people keep buying rather than fast money.

### Goals
1. A business that could keep running after day 90 if it works (signal: H3 in section 19).
2. Owner time of 5 minutes a day or less after setup (H5).
3. Every dollar and every outward action auditable in the append-only ledger and event logs.
4. Decisions grounded in observed demand, not model intuition.

### Non-goals
X/Twitter, video, AI avatars or personas, Reddit, LinkedIn, memberships, automated engagement
(replies, follows, likes, DMs), ad-platform automation, Notion automation. See section 24.

### Carried-over ground rules (unchanged)
- Ledger, bet log and run log are append-only (UPDATE/DELETE triggers). New tables get the same triggers.
- State is derived by folding events, never stored and mutated.
- Every AI call is **one system prompt plus one user message**. No multi-turn histories.
- `swarm50/metered.py` is the **only** module that touches any AI SDK (Anthropic, Google) or the
  `claude` CLI. Every AI call is budget-checked before it runs and debited after.
- No prompt text in `.py` files; prompts live in `prompts/*.md`, filled with `string.Template`.
- No agent-facing code path writes `deposit` or `adjustment` transactions.
- Python 3.11+, Windows and Linux, `pathlib`, UTF-8.

## 2. Decisions log (from brainstorming, 2026-10-05)

| # | Decision |
|---|---|
| 1 | Digital products only; trading and the other categories removed |
| 2 | Payouts in Pakistan: Etsy via Payoneer; Gumroad bank payout in PKR |
| 3 | Daily approval batch (~2 min): drafts → owner approves → code publishes |
| 4 | Run: **90 days, $100** starting balance |
| 5 | One objective (no reward arms): net revenue in the final 30 cycles. Convex arm and its 10× promise dropped |
| 6 | Channels: Etsy + Gumroad + Threads + Pinterest. No X, no video, no AI personas |
| 7 | Architecture: extend the current core with plain-code modules (ingest, research, renderer, publisher, approve) |
| 8 | Revenue recorded automatically from platform APIs (rule change, section 7.4) |
| 9 | Formats automated: XLSX and PDF. Notion manual, for proven winners only |
| 10 | Image model added (Google Gemini Flash Image); AI makes the art, code sets all text |
| 11 | Two product lines with different products and evidence (section 4) |
| 12 | Line B niche chosen by the agents in a discovery week, approved by the owner (section 6) |
| 13 | The strategist never sees raw external text; an analyst role turns it into graded briefs (section 5.3) |

## 3. Architecture

### 3.1 The daily cycle

```
 code   1. INGEST     sales, fees, listing views/favorites, Threads/Pinterest insights -> ledger + metrics
 code   2. STATE      daily view: products, lines, research index, thesis, notes, waiting items
 AI     3. STRATEGIST memos, bet actions, work orders, research requests, notes to self
 code   4. RESEARCH   run requests (Etsy probe, Threads search, Pinterest trends); raw data saved
 AI     5. ANALYST    raw research -> graded brief (no tools except web search for source=web)
        (3-5 repeat up to N rounds in discovery mode; one round in operating mode)
 AI     6. CRITIC     memo loop (unchanged) + scale-bet evidence check (product review runs in step 8)
 AI     7. WORKERS    structured specs: spreadsheet, pdf, listing copy, posts, pins, revisions
 code   8. RENDER     specs -> XLSX/PDF + images (AI art composited by code); quality gates
 human  9. APPROVE    `python -m swarm50.approve`: money, drafts, thesis, tasks, inbox reminder
 code  10. PUBLISH    approved, fingerprint-matched items -> Etsy / Threads / Pinterest APIs;
                      Gumroad -> owner task; fees debited against the bet's stake
```

Steps 1-8 run unattended (scheduled, section 15). Step 9 is the owner's daily batch. Step 10 runs
right after approval.

### 3.2 Modes
- **Discovery mode:** cycles 1 to `discovery_cycles` (7). Up to `discovery_rounds_per_cycle` (3)
  strategist → research → analyst rounds per cycle, with a higher token cap (section 7.6).
- **Operating mode:** every later cycle. One round.

### 3.3 New and changed modules

| Module | Role | Network |
|---|---|---|
| `swarm50/metered.py` (changed) | adds `metered_image_call` (Google) and web-search support for analyst calls | AI APIs only |
| `swarm50/research.py` (new) | runs research requests; stores raw results; calls the analyst | Etsy, Threads, Pinterest (read) |
| `swarm50/ingest.py` (new) | pulls sales, fees and metrics; writes revenue and metric snapshots | Etsy, Gumroad, Threads, Pinterest (read) |
| `swarm50/render/` (new) | `xlsx.py`, `pdf.py`, `images.py`; quality gates | none (image calls go through `metered.py`) |
| `swarm50/publish/` (new) | `etsy.py`, `threads.py`, `pinterest.py`; lint, limits, token refresh | platform write APIs |
| `swarm50/approve.py` (new) | daily batch CLI and HTML preview; logs session time | none |
| `swarm50/cycle.py` (changed) | modes, rounds, ingest → … → summary; insolvency fix | none |
| `swarm50/state.py` (changed) | new daily view (section 9) | none |
| `swarm50/schemas.py` (changed) | new memo fields, research, specs, thesis | none |
| `swarm50/bets.py` (changed) | new event types; `refused` doesn't change status | none |
| `swarm50/workers.py` (changed) | structured specs; revisions get the prior spec | none |

Workers, the critic and the analyst have **no tools** (except the analyst's web search for
`source=web`). Only `research.py`, `ingest.py` and `publish/` make platform calls, and they're plain code.

## 4. Product lines

| | Line A: Marketplace | Line B: Conversation |
|---|---|---|
| Storefront | Etsy | Gumroad |
| Traffic | Etsy search + Pinterest | Threads + Pinterest |
| Buyer trigger | A search: they know what they want | A post that names their problem; trust |
| Fits | spreadsheets, printables, planners, trackers | playbooks, swipe files, checklists + walkthroughs, profession-specific prompt packs, calculators with a guide, bundles |
| Price / volume | $5-17, many products | $15-49, few products; free lite version → paid upgrade |
| Niche shape | many niches allowed | **one niche** (the approved thesis, section 6) |
| Demand evidence | Etsy probe + Pinterest trends | Threads search + web + Pinterest trends |
| Owner time per product | ~0 (Etsy API) | ~10 min (Gumroad has no product API) |

- Every memo declares `line`. Stakes, costs and revenue are tracked per line (H4).
- Etsy forbids marketing to its buyers off-platform without consent: Line B may point to Etsy
  products; Line A never collects or contacts Etsy buyers.

## 5. Research subsystem

### 5.1 Requests
The strategist output gains `research_requests` (max `research_max_requests_per_round`, default 8):

```json
{"request_id": "r34-2", "source": "etsy|threads|pinterest_trends|web",
 "query": "freelance invoice tracker", "purpose": "test: is demand recent or legacy?",
 "hypothesis": "recent listings (<12 months) still get at least 5 views/day"}
```

`purpose` and `hypothesis` are required. Research is for testing ideas, not browsing.

### 5.2 Sources (all executed by code)

| Source | Call | Code computes | Raw text to analyst |
|---|---|---|---|
| `etsy` | `findAllListingsActive` (keywords), API key only | result count; price quartiles; for the top 25: views/day since creation, favorites, listing age; age distribution | titles, tags |
| `threads` | `keyword_search` (own-account tester token; 2,200/day limit) | post count by recency | post texts, sampled |
| `pinterest_trends` | `/trends/keywords/{region}/top/{type}` (available once Pinterest access is granted) | growth WoW/MoM/YoY, seasonal flag | none |
| `web` | analyst call with Anthropic web search (max 5 uses) | none | the analyst searches itself |

Raw responses are saved to `state/research/<request_id>.json`. Numbers computed by code go straight
into the result; any text written by strangers goes **only** to the analyst.

### 5.3 Analyst role (new, Sonnet)
One call per request (sources with no stranger text skip it). The output schema (`ResearchBrief`):
- `findings`: list of `{claim, evidence_grade: strong|moderate|anecdotal, support: [quotes or numbers]}`
- `recurring_problems`: `{problem, frequency, intensity, example_phrases}`
- `current_alternatives` and `their_gaps`
- `contradicting_evidence` (required, may be empty with a reason)
- `hypothesis_verdict`: `supported | weakened | inconclusive`, with reasoning
- `one_line_conclusion`

The analyst prompt treats all quoted material as data and instructs it to ignore instructions found
inside that material. **The strategist never sees raw external text**, only briefs and numbers
computed by code. (This replaces the earlier idea of web search on strategist calls.)

### 5.4 Research notebook
- New append-only table `research` (id, ts, cycle, request_id, source, query, purpose, hypothesis,
  raw_path, numbers_json, brief_json, cost_micro).
- The daily view shows an **index** of the last 40 briefs (id, query, verdict, one-line conclusion).
- The strategist can ask to re-read up to 3 briefs in full per round via `reread: [request_id]`.

## 6. Discovery week (cycles 1-7)

| Cycles | Stage | Expectation |
|---|---|---|
| 1-2 | Broad scan | 12-15 candidate niches, shallow scans across sources; filter fast |
| 3-5 | Deep dive | Top 3 candidates; explicit hypotheses; targeted scans, including attempts to disprove the favourite |
| 6 | Niche thesis | `NicheThesis` object in the strategist response, compared against the runners-up |
| 7 | Owner approval | Thesis shown as one page in the approval batch |

Line A runs in parallel: Etsy test bets are allowed from cycle 2.

**`NicheThesis` schema** (the critic checks each section via `prompts/critic_thesis.md`):
`audience` (who; where they gather on Threads) · `problems` (ranked; each cites research ids) ·
`jobs_and_alternatives` · `gap_and_position` (why us, why now, against which competitors) ·
`product_ladder` (free lead magnet → ~$15 core → ~$49 premium) · `content_pillars` (3-4, with example
hooks in the audience's words) · `milestones` (days 30/60/90) · `risky_assumptions` (each with the
cheapest test) · `kill_criteria` · `why_not_runners_up`.

Events: `run_meta` types `thesis_proposed`, `thesis_critiqued`, `thesis_approved`, `thesis_rejected`.
Until a thesis is approved, Line B may not stake or publish. The day-45 gate re-checks it. A change
needs a new thesis and owner approval.

## 7. Money model

### 7.1 Wallet
$100, written once at kickoff. AI calls are debited per call, as now.

### 7.2 Bet types (`bet_type` on every memo)

| | Test bet | Scale bet |
|---|---|---|
| Buys | listings for a new product or variant | ads, promoted pins, variants of a proven product |
| Stake | typically $0.20-3 | up to the 35% cap |
| Code gate | existing caps | `parent_bet_id` must have ≥ `scale_min_sales` (1) recorded sales |
| Critic | niche specificity; cited evidence is real | stake sized from **observed** conversion and ad return |

All memos need `demand_evidence: [research_id, ...]`. The critic rejects memos that cite nothing
relevant.

### 7.3 Spending a stake
- The full stake is debited at owner approval, so the wallet can only understate the money left.
- The publisher records listing fees against the stake (bet event `fee_charged`, no extra ledger debit).
- Ads have no API: a scale bet creates an owner task ("set Etsy Ads to $3/day for 10 days").
- Closing a scale bet asks the owner for the unspent amount, recorded as `bet_return`.

### 7.4 Revenue (rule change)
`ingest.py` records `revenue` transactions automatically from platform APIs. It never comes from an
agent. Each sale is recorded **net** (gross and fees in the note), once, keyed on a new
`external_id` column (`platform:receipt_id`) with a unique index. Agents still can never credit
anything. Manual `record-return` stays for ad refunds and edge cases.

### 7.5 Business overhead (outside the agent wallet, reported)
Payoneer annual fee ($29.95/yr under $6,000 received, PK, from Feb 2026), the ~3% withdrawal fee, FX
markup and payout timing (Etsy holds new sellers' funds 45-90 days). These are recorded by the owner
as `overhead` entries in the report, not debited from the agents' wallet unless the owner decides
otherwise. This keeps the experiment's wallet about agent decisions while the report shows the true
business picture.

### 7.6 Caps and config

| Key | Value | Note |
|---|---|---|
| `starting_balance_usd` | 100 | |
| `total_days` | 90 | |
| `max_stake_pct` / `max_open_exposure_pct` | 0.35 / 0.60 | unchanged |
| `max_trading_exposure_pct` | removed | |
| `reward_arm` | removed | single objective |
| `cycle_token_cap_usd` | 0.75 | operating mode |
| `discovery_cycle_token_cap_usd` | 1.50 | discovery mode (3 rounds × strategist + analysts) |
| `cycle_image_cap_usd` | 0.50 | separate from thinking |
| `worker_max_tokens` | 8000 | was 3000; a 10-page guide needs it |
| `scale_min_sales` | 1 | |
| `discovery_cycles` / `discovery_rounds_per_cycle` | 7 / 3 | |
| `research_max_requests_per_round` | 8 | |
| `publishing_enabled` | false until kickoff | kill switch |
| `etsy_listings_per_day` | 2 in week 1, then 5 | shop-safety ramp |
| `threads_posts_per_day` / `pins_per_day` | 3 / 5 | |
| `draft_ttl_days` | 3 | silence never means yes |
| `operator_away_until` | null | section 15 |
| `backend` | api | the CLI backend has no web search or image support |
| roles | strategist `claude-fable-5-1`, critic `claude-sonnet-5`, analyst `claude-sonnet-5`, worker `claude-haiku-4-5-20251001`, image: Gemini Flash Image (exact model ID and price confirmed at build) | |

**Expected 90-day spend before revenue:** thinking ~$27, extra discovery ~$5, analyst ~$3, images
~$10, listings ~$5, ad tests up to ~$30 (only after sales). With zero sales, no scale bets can happen,
so the floor is about $50 left.

**Category to format:** Memo `category` becomes `format`:
`spreadsheet | printable_pdf | guide_pdf | notion_template | bundle | lead_magnet`.

## 8. Prompts

- `prompts/objective.md` replaces `objective_linear.md` and `objective_convex.md`:

  ```
  Your objective
  Build products that people keep buying. At the end of cycle $total_days you are judged
  by one number: the net revenue earned during the final 30 cycles. The wallet balance is
  not the measure, and money that arrives early but stops does not count. Spending that
  builds lasting demand is how you score; spending that only produces a one-off spike is not.
  ```
- `prompts/strategist.md` updated: two lines; discovery vs operating mode; research requests with
  hypotheses; demand evidence required; test vs scale bets; thesis in discovery; `notes_to_self`.
  It keeps: real money, costs of thinking, hard rules, honesty and disclosure, derive every number.
  It drops: trading wording, the "no category is preferred" sentence (formats are now explicitly the
  product space).
- New: `prompts/analyst.md`, `prompts/critic_thesis.md`, `prompts/critic_product.md`.
- `prompts/worker.md` updated for structured specs, the brand kit and the disclosure line.
- Test change: the old "arms differ only in the objective" test becomes "the objective contains no
  shutdown threat or bonus promise" plus "the prompts render without unfilled placeholders".

## 9. Daily view (state block)

Target about 3,000 tokens, trimmed by fixed rules:

```
cycle 34 of 90 | mode: operating | judging window starts cycle 61 | balance $81.40
open exposure $6.20 | tokens today $0.00 / total $10.12 | images total $3.40 | caps ...
LINES        A marketplace: 9 live, 4 sales, net $36.10, spend $14.20 | B conversation: 3 live, 2 sales ...
THESIS (B)   "Systems for freelance bookkeepers": pillars ..., day-30 milestone: met / missed
PRODUCTS     every active one (id, line, format, title, live-on, age, views, favorites, sales, net, 7d, kill_by)
CHANNELS     threads 7d: posts, views, link clicks; pinterest: status/impressions
RESEARCH     last 40 briefs: id | query | verdict | one-line conclusion
WAITING      bets awaiting approval, drafts, thesis, owner tasks (age)
REJECTED 14d id, title, the critic's key risk / the owner's reason
NOTES        your notes from the last 3 cycles
OPERATOR     recent task-done notes
```

Only totals and code-computed numbers from platforms. No buyer names, emails or messages ever.

## 10. Workers and renderer

### 10.1 Worker deliverables (strict JSON schemas, one repair retry, then `malformed`)
| Type | Content | Renderer output |
|---|---|---|
| `spreadsheet_spec` | sheets, columns, sample rows, formulas, dropdowns, limited conditional formats, instructions tab | XLSX (`openpyxl`) |
| `pdf_spec` | markdown sections + layout directives (tables, grids, checkboxes, page breaks) + art prompts | PDF (`fpdf2`) |
| `listing_copy` | Etsy title ≤140, 13 tags ≤20, description, price | validated; disclosure appended |
| `social_post` | Threads text ≤500, target product, content pillar | link with channel tag |
| `pin` | title ≤100, description ≤500, art prompt, target product | 1000×1500 image |
| `revision` | change request against an earlier artifact | the worker receives the prior spec plus the change |
| `brand_kit` | palette, two Google Fonts (bundled), style prompt | `artifacts/brand.json`, owner-approved once |

### 10.2 Quality gates (before the approval batch)
1. **XLSX:** fill the sample rows, evaluate every formula with a Python formula engine (`formulas` or
   `pycel`, chosen at build); any error value fails the build. Formulas are limited to an allowlist:
   SUM, SUMIFS, COUNTIFS, IF, IFERROR, AVERAGE, MIN, MAX, ROUND, INDEX, MATCH, date functions.
2. **PDF:** renders, stays within the memo's page count, no text overflow.
3. **Critic product review** (`critic_product.md`, ~$0.02): does the file deliver what the listing
   promises; are there any claims that aren't true.
4. Every file contains an "About this product" line: created with AI assistance.

## 11. Images

- **Model:** Google Gemini Flash Image via `metered_image_call` (~$0.02-0.04/image; batch half price
  later). Pricing per image is in config.
- **AI makes the art, code sets the words.** No text is drawn by the model.

| Image | AI | Code |
|---|---|---|
| Etsy cover | styled backdrop with space for the product | real product preview (PDF page via `pypdfium2` / drawn spreadsheet table) as a card with shadow; title in brand fonts |
| Etsy "what's inside" | matching backdrop | real page grid |
| Pinterest pin | bold background | headline, preview, call to action |
| Threads image | background art | hook text |
| PDF design | cover art, section-header illustrations, backgrounds | all body text and tables |

- Image rules enforced in the prompt template and the lint: no real people or celebrity likeness, no
  logos or trademarks, no model-drawn text, safe for work.
- Etsy policy (in force since 2026-07-09): the first photo shows what the buyer gets; the "I used
  AI-generative technology" box is ticked (via the API if exposed, otherwise a 10-second owner task).
- Threads images are posted by public URL: the publisher reuses Etsy-hosted listing image URLs.
  Pinterest accepts base64 uploads.
- About 8-10 images per product; ~$10 for the run. Separate $0.50/cycle cap.

## 12. Owner workflow

### 12.1 `python -m swarm50.approve`
- Writes `artifacts/review/<date>.html`: every pending money item, draft (images, copy, posts),
  thesis and task side by side. It opens the page in the browser.
- The terminal walks each item: `y` / `n` (reason) / `s` (skip; it expires after `draft_ttl_days`).
- Approval of a draft writes `draft_approved` with the draft's `content_hash`.
- It logs `approve_session` (start, end, items) to `run_meta`; this is the H5 measurement.
- `approve --pause` / `--resume` flips publishing without editing config.

### 12.2 Owner tasks (existing task lifecycle)
Gumroad product creation, ad settings, the scale-bet unspent amount, the AI checkbox if needed, the
Pinterest video review, Notion duplication.

### 12.3 Buyer support
The approval batch ends with a fixed checklist item: "Check Etsy messages and Gumroad emails; reply
within 24h." Etsy has no messaging API. Time spent is part of the logged session.

## 13. Publisher and safety rules
1. Publishes only items with a `draft_approved` event whose `content_hash` matches the rendered artifact.
2. Pre-publish lint: disclosure present; links only to our own Etsy/Gumroad URLs; no @mentions; ≤3
   hashtags; platform length limits; banned phrases (fake urgency, invented testimonials, income claims).
3. Daily limits from config, below the platforms' limits.
4. Idempotent: `published` events store the platform ID; retries never double-post.
5. Failures write `publish_failed`, retry once the next day, then become an owner task. Never crash a cycle.
6. Kill switch: `publishing_enabled: false` or `approve --pause`.
7. Credentials come from `.env`; refreshed tokens are kept in `state/tokens.json` (git-ignored). Never in
   prompts, logs or the report.
8. Token refresh is automatic: Threads long-lived tokens (60 days, shorter than the run); Etsy refresh
   tokens (90 days).
9. A `killed` bet: Etsy listings are deactivated through the API; Gumroad becomes an owner task.
10. Automate what we say, never what we do to others: no replies, follows, likes or DMs.

## 14. Ingest
Runs at the start of each cycle (and on demand: `python -m swarm50.ingest`).
- **Etsy:** shop receipts → revenue (net via the payment-account ledger entries endpoint if
  available; otherwise gross minus the configured fee schedule with `estimated=1` in the note);
  listings → `views` (updated daily) and favorites.
- **Gumroad:** `GET /v2/sales` → revenue (price minus `gumroad_fee`), `referrer` for channel attribution.
- **Threads:** own-post insights (views, likes, replies, link clicks where available).
- **Pinterest:** pin analytics once Standard access is granted.
- New append-only table `metrics` (ts, cycle, bet_id, platform, views, favorites, clicks, sales).
- Attribution limits: Gumroad reports referrers; Etsy's API doesn't attribute traffic sources, so Etsy
  channel attribution is limited to what listing views and Pinterest analytics show.

## 15. Operations
- **Scheduler:** `scripts/install_schedule.ps1` registers a Windows Task Scheduler job: daily
  `python -m swarm50.cycle run` at a set hour (ingest runs inside it).
- **Missed cycles:** the cycle number still comes from the date. A day with no `cycle_summary` is a
  missed cycle, shown in the report. There is no catch-up and no double cycle.
- **Away mode:** while `operator_away_until` is in the future, cycles run ingest only (no strategist
  call, no drafts), saving money while nobody can approve.
- **Backups:** after each cycle, `ledger.db` is copied via the SQLite backup API to
  `state/backups/ledger-YYYYMMDD.db`; the last 14 are kept.
- **Network consistency:** run from the same machine and network; no VPN (an Etsy fraud-flag trigger).

## 16. Data model changes
- `transactions`: add `external_id TEXT` (migration) plus a unique index on `external_id` where not null.
- `bet_events` new types: `refused` (doesn't change status), `draft_created`, `draft_approved`,
  `draft_rejected`, `published`, `publish_failed`, `unpublished`, `fee_charged`. `blocked` stays for
  guardrail stake refusals only (it does change status).
- `run_meta` new types: `thesis_proposed`, `thesis_critiqued`, `thesis_approved`, `thesis_rejected`,
  `approve_session`, `ingest_run`, `overhead`.
- New append-only tables: `research`, `metrics` (same no-update/no-delete triggers).
- Schemas: `Memo` (+`line`, `bet_type`, `parent_bet_id`, `format`, `demand_evidence`, `channels`,
  `price_usd`; −`category`), `StrategistResponse` (+`research_requests`, `reread`, `notes_to_self`,
  `niche_thesis`), new `ResearchRequest`, `ResearchBrief`, `NicheThesis`, spec types (section 10.1),
  `WorkOrder.deliverable_type` extended.
- No real database exists yet (no kickoff has happened), so the schema changes need no data migration.

## 17. Fixes from the code review (built first, each with a failing test first)
1. **False insolvency** (`cycle.py:176`): `run_ended`/`insolvent` only when the strategist's
   **first** call of the cycle is refused with `WalletEmpty`. `CycleCapExceeded` never ends the run.
2. **Refusals hiding bets** (`bets.py:31`): bet-action and work-order refusals write `refused`, which
   `status_of` ignores, so a queued bet stays in the queue.
3. **10-event window** (`state.py:54`): replaced by the daily view in section 9.

## 18. Setup and kickoff gates

### 18.1 One-time owner setup (slowest approvals first)
| # | Task | Owner time | Waiting time |
|---|---|---|---|
| 0 | Confirm employment terms allow a private online business (audit E6) | n/a | before any account |
| 1 | Etsy developer account + API key (clear app description) | 15 min | 24-48h, sometimes 1-3 weeks |
| 2 | Pinterest business account + developer app; record the OAuth/pin video in Trial; apply for Standard | 30 min | 11-26+ days |
| 3 | Etsy shop, ID verification, Payoneer (verify within 30 days), shop policies | 60-90 min | days |
| 4 | Instagram Professional + Threads + Meta app; add self as Threads Tester; token | 30 min | none |
| 5 | Gumroad account + payout settings (PKR bank) | 20 min | review after the first sales |
| 6 | Anthropic + Google AI Studio keys with billing → `.env` | 15 min | none |

### 18.2 Kickoff gates (pre-committed; from the audit)
| Gate | Pass | If it fails |
|---|---|---|
| K1 market probe (Line A) | ≥2 candidate niches meet the owner's thresholds (views/day of listings created in the last 12 months; median price ≥ $8). Line B is gated separately by thesis approval (section 6) | rethink product type before staking |
| K2 blind product check | the owner would pay $10 for ≥2 of 3 sandbox products next to competitor bestsellers | workers → Sonnet; rerun |
| K3 7-day unattended run (publishing off) | ≥6 of 7 cycles complete | always-on device / small VPS |
| K4 shop health | Etsy ID + Payoneer verified; 3 seed listings live 7 days without flags | resolve first; Gumroad-first fallback |
| K7 employment | permitted | don't proceed under the owner's name |

In-run gates (written into the prereg): **K5 day 45** (shop views ≥ threshold or ≥1 sale, otherwise
an owner-ordered reset of Line A's product focus and/or the Line B thesis) and **K6 day 21** (Threads median
views/post ≥ threshold, otherwise cut to 3 posts/week and move the image budget to Pinterest/Etsy).

## 19. Hypotheses (replace the current `docs/PREREGISTRATION.md` H1-H3)
- **H1 Overconfidence:** in most test bets, actual revenue falls short of the memo's stated expected value.
- **H2 Cost of thinking:** AI plus image spend exceeds 30% of the $100 by day 90 (model predicts ~37%).
- **H3 Sustainability:** net revenue in cycles 61-90 exceeds AI plus image spend in the same window.
  **Confound to state up front:** a November kickoff puts cycles 61-90 in January, the annual peak for
  planners and budgets.
- **H4 Lines:** compare Line A and Line B on net revenue per dollar staked and per owner-minute.
- **H5 Owner time:** mean logged approval-session time after setup is 5 minutes a day or less.

The owner sets the thresholds and the K-gate numbers before kickoff.

## 20. Dry run and sandbox
- `scripts/dry_run.py`: arms removed; runs N day-1 strategist calls (discovery mode, research mocked
  or live) and reports formats, lines, stake sizes and research requested. `--batch` and
  `--max-total-usd` stay.
- **Sandbox cycle** (new, `python -m swarm50.cycle run --sandbox`): one real cycle with publishing
  forced off, on a throwaway DB. It produces real files, images and the preview page (~$1-2). This
  feeds K2.

## 21. Testing
1. The section 17 fixes first, each with a failing test before the fix.
2. Every new module offline: research and ingest against saved sample API responses; publisher
   against mocked `httpx`; the renderer producing real files locally; a broken formula fails the
   build; images with stub bytes.
3. A test for each publisher safety rule: unapproved refused, hash mismatch refused, lint, limits,
   idempotency, kill switch, token refresh.
4. Analyst boundary test: hostile text inside raw research never reaches the strategist prompt.
5. No real network calls in any test. The sandbox cycle and dry run are the only real-call paths, run by hand.
6. The existing 91 tests stay green (prompt tests updated per section 8).

## 22. Build order
1. Review fixes (section 17)
2. Pinterest connector + OAuth in Trial (unblocks the owner's video for the longest review)
3. Schemas, prompts, config, money model (sections 7, 8, 16)
4. Research subsystem + analyst + notebook (section 5)
5. Discovery mode + thesis (section 6)
6. Renderer XLSX/PDF + quality gates (section 10)
7. Image pipeline + brand kit (section 11)
8. Approve CLI + preview (section 12)
9. Etsy publisher + ingest (sections 13, 14)
10. Threads publisher + ingest
11. Gumroad ingest
12. Daily view, report updates, operations: scheduler, away mode, backups (sections 9, 15)
13. Docs: README, RULES, KICKOFF_CHECKLIST, PREREGISTRATION (section 19)
14. Sandbox cycle + dry-run update (section 20)

## 23. To verify during the build
- Whether Etsy's API exposes the AI-generative checkbox (otherwise an owner task).
- Etsy payment-account ledger endpoint for exact fees (otherwise fees are estimated and flagged).
- Fields returned by Threads `keyword_search`, and whether insights include link clicks.
- The access tier needed for Pinterest trending keywords.
- Formula engine choice (`formulas` vs `pycel`) against the allowlist and Google Sheets import.
- The exact Gemini image model ID and per-image price.
- Audit `teomro/etsy` before the owner installs it as a planning-time MCP (it's not a runtime dependency).

## 24. Out of scope (parked as possible later scale bets)
X/Twitter (pay-per-use, "Automated" label, weak small-account reach) · video and AI avatars or
personas (owner decision) · Reddit (free tier bans commercial use) · LinkedIn (page posting needs
approval; a personal profile would put AI content under the owner's name) · Gumroad memberships (no
posting API) · Medium/Substack (search payoff takes longer than 90 days) · automated replies and
engagement · ad-platform automation · Notion automation.
