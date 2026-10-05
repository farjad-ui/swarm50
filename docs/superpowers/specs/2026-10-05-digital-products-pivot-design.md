# swarm50 digital-products pivot: design spec (v2)

- **Status:** v2. It folds in the owner's decisions on the independent review and the fixes agreed in
  `2026-10-05-spec-review.md`. Awaiting the owner's read of v2.
- **Companions:** `2026-10-05-assumption-audit.md` (risk register), `2026-10-05-spec-review.md` (independent review)
- **Replaces:** the category-neutral, trading-hypothesis design in `OVERNIGHT_BRIEF.md` M1/M2

## 0. What changed in v2
1. **Test products are built directly:** one owner approval, on the finished draft. Memo → critic → stake
   is kept only for scale bets (section 7).
2. **Budget buckets:** building, thinking and images each have their own per-cycle cap. Building runs
   first. A hard run-level cap on AI plus images is added, and the spend table is re-derived (section 7.8).
3. **The score is defined in code** (net after fees, refunds, listing fees and ad spend in the window).
   Scale bets need 3 sales from distinct buyers; ad spend has a run cap (sections 7.4, 7.5).
4. **Bugs:** unique bet IDs; a `refund` transaction type; buyer-data whitelist at ingest (sections 14, 16, 17).
5. **Line B research uses the web only,** fetched by code through Agent Reach's no-login backends.
   Threads keyword search is dropped (it needs Meta App Review). Section 5.
6. **Pinterest API dropped:** the owner uploads a weekly bulk CSV of pins instead (section 12).
7. **Dates:** setup weekend Sat-Sun 10-11 Oct 2026; kickoff target Sat 31 Oct 2026, with a re-target
   rule (section 18).
8. Owner time target is about 10 min/day (H5); hard spend limits on the AI provider accounts (section 18).
9. Also folded in from the review: honest analyst boundary and quote caps; code-validated evidence;
   a product review that sees rendered pages; a separate thesis call; Etsy shop-safety lint;
   no Line A kills before day 45; H1 becomes a calibration test; Google Sheets copy-link delivery;
   a true P&L line.

## 1. Summary

swarm50 becomes a small, mostly autonomous **digital-products business** run by agents for 90 days on a
$100 wallet, with two product lines sharing that wallet:

- **Line A, Marketplace:** practical, search-driven products on **Etsy**.
- **Line B, Conversation:** problem-solving products sold on **Gumroad**, marketed by a **Threads** brand
  account built around one niche the agents discover in week 1 from web research.

Pinterest traffic comes from a weekly CSV of pins the owner uploads. The agents research demand,
order products, build real files (XLSX/PDF with AI-composited images), and draft listings and posts.
The owner approves one daily batch (about 10 min including buyer messages), and plain code publishes.
The strategist is judged on the **window score** (section 7.5): net revenue in the final 30 cycles after
fees, refunds, listing fees and ad spend.

### Goals
1. A business that could keep running after day 90 if it works (H3).
2. Owner time of about 10 minutes a day or less after setup (H5).
3. Every dollar and outward action auditable in the append-only ledger and event logs.
4. Decisions grounded in observed demand, with forecasts scored against reality (H1).

### Non-goals
X/Twitter, video, AI avatars or personas, Reddit, LinkedIn, memberships, automated engagement, ad-platform
automation, Notion automation, the Pinterest API, Threads keyword search. See section 24.

### Carried-over ground rules (unchanged)
- Ledger, bet log and run log are append-only (UPDATE/DELETE triggers). New tables get the same triggers.
- State is derived by folding events, never stored and mutated.
- Every AI call is **one system prompt plus one user message**. No multi-turn histories and **no
  server-side tools** (no in-call web search), so every call's input is known before the budget check.
- `swarm50/metered.py` is the **only** module that touches any AI SDK (Anthropic, Google) or the `claude` CLI.
- No prompt text in `.py` files; prompts live in `prompts/*.md`, filled with `string.Template`.
- No agent-facing code path writes `deposit`, `adjustment`, `revenue` or `refund` transactions.
- Python 3.11+, Windows and Linux, `pathlib`, UTF-8.

## 2. Decisions log

| # | Decision | When |
|---|---|---|
| 1 | Digital products only; trading and the other categories removed | brainstorm |
| 2 | Payouts in Pakistan: Etsy via Payoneer; Gumroad bank payout in PKR (verified on Gumroad's payout page) | brainstorm |
| 3 | Daily owner approval batch; plain code publishes | brainstorm |
| 4 | 90 days, $100 | brainstorm |
| 5 | One objective, the window score (no reward arms) | brainstorm + v2 definition |
| 6 | Etsy + Gumroad + Threads; Pinterest by manual weekly CSV; no X, video, personas | brainstorm + v2 |
| 7 | Extend the current core with plain-code modules | brainstorm |
| 8 | Revenue and refunds recorded automatically from platform APIs | brainstorm + v2 |
| 9 | XLSX/PDF automated (+ Google Sheets copy link); Notion manual | brainstorm + v2 |
| 10 | Gemini Flash Image: AI makes the art, code sets all text | brainstorm |
| 11 | Two product lines with different products and evidence | brainstorm |
| 12 | Line B niche chosen by the agents in discovery week; owner approves | brainstorm |
| 13 | Line B discovery from the web only, via Agent Reach no-login backends (Exa search, Jina Reader) | v2 |
| 14 | Test products: one owner approval on the finished draft | v2 |
| 15 | Score = net after fees, refunds, listing fees, ad spend; AI spend stays H3 | v2 |
| 16 | Owner time about 10 min/day | v2 |
| 17 | Hard spend limits on the Anthropic and Google accounts | v2 |
| 18 | Setup 10-11 Oct; kickoff target 31 Oct (owner proposed 9-10 Oct; moved, see section 18) | v2 |

## 3. Architecture

### 3.1 The daily cycle (v2 order)

```
 code   1. INGEST     sales, refunds, fees, listing views/favorites, Threads own-post insights
 AI+cd  2. BUILD      queued build orders: worker spec -> render -> images -> product review -> draft
                      (build bucket, runs before any thinking so it can't be starved)
 code   3. STATE      daily view (section 9)
 AI     4. STRATEGIST if due: build orders, scale-bet memos, research requests, post plan, notes
 code   5. RESEARCH   Etsy probe; web via Agent Reach no-login backends; raw data saved
 AI     6. ANALYST    raw research -> graded brief (one ordinary call, no tools)
        (4-6 repeat up to 3 rounds in discovery mode; build orders and memos only in the final round)
 AI     7. CRITIC     scale-bet memos and the niche thesis only
 AI     8. DRAFTS     Threads posts, pin drafts (worker)
 human  9. APPROVE    `python -m swarm50.approve`: drafts, scale bets, thesis, tasks, inbox
 code  10. PUBLISH    approved, fingerprint-matched items -> Etsy / Threads APIs; Gumroad -> owner task;
                      weekly pin CSV -> owner task
```

### 3.2 Modes and cadence
- **Discovery mode:** cycles 1-7. Strategist every cycle, up to 3 rounds per cycle.
- **Operating mode:** strategist every `strategist_interval_cycles` (default 2; set from dry-run
  measurements before kickoff). Ingest, build, drafts and publish run every cycle.

### 3.3 Budget buckets (per cycle; section 7.8)
`build` (worker, renderer-triggered AI, product review) · `think` (strategist, analyst, critic) ·
`image`. Each bucket has its own cap; a refused call in one bucket never consumes another's budget. All
AI spend also counts against the hard run cap `run_ai_cap_usd`.

### 3.4 Modules

| Module | Role | Network |
|---|---|---|
| `metered.py` (changed) | adds `metered_image_call` (Google); `Result.stop_reason`; image blocks in user messages (for the product review); bucket-aware budget check | AI APIs |
| `research.py` (new) | runs requests; Etsy probe; web fetch via Agent Reach no-login backends; calls the analyst | Etsy (read), Exa, Jina |
| `ingest.py` (new) | sales, refunds, fees, metrics; field whitelist | Etsy, Gumroad, Threads (read) |
| `render/` (new) | `xlsx.py`, `pdf.py`, `sheets.py` (Drive copy link), `images.py`; quality gates | Google Drive (sheets only) |
| `publish/` (new) | `etsy.py`, `threads.py`, `pins_csv.py`; lint, limits, token refresh | Etsy, Threads write |
| `approve.py` (new) | daily batch CLI and HTML preview; session timing | none |
| `cycle.py`, `state.py`, `schemas.py`, `bets.py`, `workers.py`, `queue.py` (changed) | sections 3, 9, 16, 17 | none |

## 4. Product lines

| | Line A: Marketplace | Line B: Conversation |
|---|---|---|
| Storefront | Etsy | Gumroad |
| Traffic | Etsy search + Pinterest CSV | Threads + Pinterest CSV (when a public image URL exists) |
| Buyer trigger | A search | A post that names their problem; trust |
| Fits | spreadsheets, printables, planners, trackers | playbooks, swipe files, checklists + walkthroughs, profession-specific prompt packs, calculators with a guide, bundles |
| Price / volume | $5-17, many products | $15-49, few products; free lite version → paid upgrade |
| Niche shape | many niches allowed | **one niche** (the approved thesis) |
| Demand evidence | Etsy probe (+ web) | web research (+ Etsy probe for adjacent demand) |
| Owner time per product | ~0 | ~10 min (Gumroad has no product API) |

- Every build order and memo declares `line`; stakes, costs and revenue are tracked per line (H4).
- Line B may point to Etsy products; Line A never collects or contacts Etsy buyers (Etsy rules).

## 5. Research subsystem

### 5.1 Requests
```json
{"request_id": "c3-r1-q2", "source": "etsy|web", "query": "freelance invoice tracker",
 "purpose": "test: is demand recent or legacy?",
 "hypothesis": {"metric": "median_views_per_day_recent", "op": ">=", "value": 5}}
```
- `purpose` is required. For `etsy`, the hypothesis is a **numeric threshold evaluated by code**, not by
  the analyst. For `web`, the hypothesis is a sentence and the analyst returns a verdict.
- Max `research_max_requests_per_round` (8).

### 5.2 Sources (all executed by plain code)

| Source | How | Code computes | Text to analyst |
|---|---|---|---|
| `etsy` | `findAllListingsActive` (keywords), API key only; `getShop` for incumbents | result count; price quartiles; top-25 favorites and listing age; **views/day if Etsy returns `views` for other sellers' listings** (verified first, section 22), otherwise shop `transaction_sold_count` as the demand signal; hypothesis verdict | titles, tags (analyst only; never passed to workers) |
| `web` | Agent Reach **no-login backends only**: Exa search → top `web_max_pages` URLs → Jina Reader page text, each truncated to `web_max_chars_per_page` | page count, domains | page texts |

Forbidden: Agent Reach's cookie-based backends (X, Reddit, XiaoHongShu; the tool warns of account bans,
and Reddit's free tier bans commercial use) and YouTube downloading.

Raw responses go to `state/research/<request_id>.json`. Because web text is fetched by code and
truncated, the analyst call's input size is known before the budget check, and there are no server
tools, no `pause_turn` and no second turn.

### 5.3 Analyst role (Sonnet)
One call per request that carries stranger-written text. `ResearchBrief`:
- `findings`: `{claim, evidence_grade: strong|moderate|anecdotal, support}`, where `support` is a list
  of numbers or quotes
- `recurring_problems`: `{problem, frequency, intensity, example_phrases}`
- `current_alternatives`, `their_gaps`
- `contradicting_evidence` (required; may be empty with a reason)
- `hypothesis_verdict` (web only): `supported | weakened | inconclusive` + reasoning
- `one_line_conclusion`

**Quote caps, enforced by code after parsing:** at most 5 quotes per brief, each ≤120 characters, with URLs
and @handles stripped. Shown to the strategist inside a fenced block labelled as data.

**Honest boundary:** short audience quotes do reach the strategist, and from there listing copy and
posts. That's intended: the audience's own words are what sells. The defences are that (1) no agent has
a side-effecting tool, (2) quotes are capped and sanitised, (3) publishing passes lint and owner approval
of exact content.

### 5.4 Research notebook
Append-only `research` table (id, ts, cycle, request_id, source, query, purpose, hypothesis,
raw_path, numbers_json, brief_json, verdict, cost_micro). The daily view shows the last 40 (id, query,
verdict, one-line conclusion). `reread: [request_id]` brings up to 3 full briefs into the next round.

## 6. Discovery week (cycles 1-7)

| Cycles | Stage | Expectation |
|---|---|---|
| 1-2 | Broad scan | 12-15 candidate niches; shallow web and Etsy scans; filter fast |
| 3-5 | Deep dive | Top 3; explicit hypotheses; targeted scans, including attempts to disprove the favourite |
| 6 | Niche thesis | **separate thesis call** (own prompt, own schema, `thesis_max_tokens`) |
| 7 | Owner approval | one page in the batch |

Line A runs in parallel: build orders are allowed from cycle 2.

**`NicheThesis`** (checked by `critic_thesis.md`): `audience` (who; where they gather) · `problems`
(ranked; each cites research ids) · `jobs_and_alternatives` · `gap_and_position` · `product_ladder` (free
→ ~$15 → ~$49) · `content_pillars` (3-4, with example hooks) · `milestones` (days 30/60/90) ·
`risky_assumptions` (each with the cheapest test) · `kill_criteria` · `why_not_runners_up`.

`run_meta` events: `thesis_proposed`, `thesis_critiqued`, `thesis_approved`, `thesis_rejected`. Line B
can't build or publish until a thesis is approved. Day 45 re-checks it; a change needs a new thesis and
owner approval.

## 7. Money model

### 7.1 Wallet
$100, written once at kickoff.

### 7.2 Two kinds of spending

| | **Build order** (test product) | **Scale bet** |
|---|---|---|
| What | a new product or variant: files, images, listing | ads, promoted listings, more variants of a proven product |
| Process | strategist issues → code validates → build → draft → **one owner approval** → listing fee staked → publish | memo → critic loop → owner approval → stake |
| Gate | allowance + evidence ids must exist | parent has ≥ `scale_min_sales` (3) sales from distinct buyers; run ad cap |
| Stake | Etsy listing fee ($0.20/listing), charged at approval | up to the 35% cap; ads ≤ `run_ad_cap_usd` total ($20) |

### 7.3 Build orders
- **Allowance:** `build_allowance_per_cycle` (1) new products per cycle. A strategist running every 2
  cycles may queue up to 2. One product is built per cycle.
- **Each build order carries:** `line`, `format`, niche, working title, target keywords, price,
  `demand_evidence` (research ids), and **forecasts**: expected listing views at day 14 and day 30
  (scored by code for H1).
- **Code validation:** evidence ids must exist, belong to a source relevant to the line, and be no
  older than 21 cycles. Otherwise the order is `refused`.
- Bet ID `c{cycle}-r{round}-b{i}`, status `building` → `draft_ready` → (approved: staked + published) or
  (rejected: closed). Rejected drafts are re-ordered by the strategist if wanted; there's no revision loop.
- Line A: **no kills before cycle 45** except for policy reasons. Listings cost $0.20 per 4 months, and
  Etsy needs 60-90 days to settle rank.

### 7.4 Scale bets
- Memo (`bet_type: scale`, `parent_bet_id`) → critic → (rebuttal → final) → owner → stake (existing caps).
- The critic's user message includes the parent's **code-computed metrics** (views, favorites, sales,
  conversion) and the cited briefs' numbers.
- Ads have no API: approval creates an owner task to set the ad budget. **Closing** a scale bet requires
  the owner to enter actual ad spend and the attributed sales from the Etsy dashboard; that entry is the
  only "ad return" the critic and the score ever see. The unspent budget comes back as `bet_return`.

### 7.5 The window score (what the strategist is judged on)
Computed by code for cycles 61-90:

```
score = Σ net sales            (gross − platform transaction & processing fees)
      − Σ refunds
      − Σ listing fees charged in the window
      − Σ ad spend in the window (owner-entered at scale-bet close, prorated by day)
```

AI spend is excluded from the score and reported next to it (H3). The daily view shows the score so far
from cycle 61 and a trailing-30-cycle equivalent before that, as a guide.

### 7.6 Revenue and refunds (automatic)
- `ingest.py` writes `revenue` (net of platform transaction and processing fees; listing fees are
  excluded because they're already in stakes, so nothing is double-counted) and `refund` (negative)
  transactions, keyed on `external_id` (`etsy:receipt:<id>`, `gumroad:sale:<id>`, `…:refund:<id>`) with a
  unique index.
- **Sanity hold:** if ingest would credit more than `ingest_daily_credit_alert_usd` ($100) in one day, it
  writes nothing, raises an owner task, and waits for confirmation.
- **Gumroad mapping:** when the owner marks a Gumroad creation task done, the note must include the
  Gumroad product ID. Ingest refuses (and flags) sales of unmapped products.
- Manual `record-return` stays for ad refunds and edge cases.

### 7.7 Business overhead and the true P&L
Payoneer annual fee ($29.95/yr under $6,000 received, PK), the ~3% withdrawal fee, FX, payout timing (Etsy
holds new-seller funds 45-90 days), and any provider charges outside the wallet are recorded by the owner
as `overhead` events. The report shows a prominent **true P&L** line (revenue − refunds − all spend −
overhead) next to the agents' wallet, so a "winning" agent run isn't mistaken for a profitable business.

### 7.8 Budgets, caps and config

| Key | Value | Note |
|---|---|---|
| `starting_balance_usd` / `total_days` | 100 / 90 | |
| `max_stake_pct` / `max_open_exposure_pct` | 0.35 / 0.60 | unchanged |
| `max_trading_exposure_pct`, `reward_arm` | removed | |
| `cycle_think_cap_usd` | 0.75 (discovery: 1.50) | strategist, analyst, critic |
| `cycle_build_cap_usd` | 0.35 | worker, product review |
| `cycle_image_cap_usd` | 0.50 | images |
| `run_ai_cap_usd` | 60 | **hard**: no AI call of any kind once all AI + image spend reaches it |
| `strategist_interval_cycles` | 2 | operating mode; tuned from the dry run |
| `strategist_max_tokens` / `thesis_max_tokens` | 6000 / 6000 | configurable (was hard-coded 4000) |
| `worker_max_tokens` | 8000 | |
| `build_allowance_per_cycle` | 1 | |
| `scale_min_sales` | 3 | distinct buyers |
| `run_ad_cap_usd` | 20 | |
| `research_max_requests_per_round` | 8 | |
| `web_max_pages` / `web_max_chars_per_page` | 5 / 6000 | bounds analyst input |
| `ingest_daily_credit_alert_usd` | 100 | |
| `publishing_enabled` | false until kickoff | kill switch |
| `etsy_listings_per_day` | 2 in week 1, then 5 | shop-safety ramp |
| `threads_posts_per_day` | 3 | |
| `draft_ttl_days` | 3 | |
| `operator_away_until` | null | |
| `backend` | api | |
| roles | strategist `claude-fable-5-1`, critic `claude-sonnet-5`, analyst `claude-sonnet-5`, worker `claude-haiku-4-5-20251001`, image Gemini Flash Image (ID and price confirmed at build) | |

**Expected 90-day spend (re-derived; the dry run must confirm it):**

| Item | Estimate |
|---|---|
| Discovery (7 cycles, up to 3 rounds) | ~$8 |
| Operating strategist (every 2 cycles, ~42 calls at ~$0.25) | ~$10 |
| Scale-bet critic loops | ~$3 |
| Analyst briefs | ~$5 |
| Workers + product review | ~$8 |
| Images (~25 products × ~$0.35 + post images) | ~$10 |
| **AI + images subtotal** | **~$44** (hard cap $60) |
| Listing fees | ~$5 |
| Ads (only after 3 sales; run cap) | ≤ $20 |

With zero sales no scale bets can happen, so about $51 is left (about $35 if AI spend hits the $60 cap).
The daily view shows burn rate: "AI spent $X of the $60 cap; planned pace by today $Y".

**Category to format:** `spreadsheet | printable_pdf | guide_pdf | notion_template | bundle | lead_magnet`.

## 8. Prompts
- `prompts/objective.md` (replaces both arm files):
  ```
  Your objective
  Build products that people keep buying. At the end of cycle $total_days you are judged by
  one number: net revenue earned during the final 30 cycles, after platform fees, refunds,
  listing fees and ad spend in that window. The wallet balance is not the measure, and money
  that arrives early but stops does not count. Spending that builds lasting demand is how you
  score; spending that only produces a one-off spike is not.
  ```
- `prompts/strategist.md` updated: two lines; modes and cadence; build orders with allowance,
  forecasts and evidence; scale bets and their gate; research requests with hypotheses; no Line A
  kills before cycle 45; `notes_to_self`. It keeps the factual statement that the run ends if the wallet
  can't pay for a call (a fact, not an incentive). It drops trading wording.
- New: `analyst.md`, `thesis.md` (the separate thesis call), `critic_thesis.md`, `critic_product.md`.
- `worker.md` updated for structured specs, the brand from config and the disclosure line.
- The critic gets the state once (in the user message only), and multi-memo cycles use prompt caching.
- Tests: the objective has no shutdown threat or bonus promise; every prompt renders without unfilled placeholders.

## 9. Daily view (state block)
Target about 3,000 tokens, trimmed by fixed rules:

```
cycle 34 of 90 | mode: operating | next strategist: cycle 35 | balance $81.40 | exposure $6.20
AI spend $21.10 of $60 cap (planned pace $22.70) | today: think $0.00 build $0.06 image $0.31
SCORE        window starts cycle 61 | trailing-30 equivalent so far: $14.20
LINES        A: 9 live, 4 sales, net $36.10, spend $14.20 | B: 3 live, 2 sales, net $41.00, spend $9.80
THESIS (B)   "Systems for freelance bookkeepers": pillars …; day-30 milestone: met
PRODUCTS     id, line, format, title, live-on, age, views, favorites, sales, net, 7d,
             forecast vs actual (day 14/30), kill-eligible from cycle 45
CHANNELS     threads 7d: posts, views, link clicks; pinterest: last CSV uploaded cycle 31
RESEARCH     last 40 briefs: id | query | verdict | one-line conclusion
WAITING      drafts, scale bets, thesis, owner tasks (age)
REJECTED 14d id, title, reason (critic key risk / owner reason / code refusal)
NOTES        your notes from the last 3 strategist runs
OPERATOR     recent task-done notes
```

Only totals and code-computed numbers from platforms. Never buyer names, emails or messages.

## 10. Workers and renderer

### 10.1 Worker deliverables (strict JSON, one repair retry, then `malformed`)
| Type | Content | Output |
|---|---|---|
| `spreadsheet_spec` | sheets, columns, sample rows, formulas, dropdowns, limited conditional formats, instructions tab | XLSX (`openpyxl`) **and** a Google Sheets copy link (Drive API: upload, convert, link-share, `/copy` URL), if that check passes at build; otherwise XLSX plus an import guide |
| `pdf_spec` | markdown sections + layout directives + art prompts | PDF (`fpdf2`) |
| `listing_copy` | Etsy title ≤140, 13 tags ≤20, description, price | validated; disclosure appended; lint (section 13) |
| `social_post` | Threads text ≤500, target product, pillar | link with channel tag |
| `pin` | title ≤100, description ≤500, target product | row in the weekly CSV, image = the product's public listing image |

Removed in v2: `brand_kit` (palette, fonts and style prompt live in `config.yaml`, set once by the owner)
and `revision` (reject and re-order instead). Workers never receive competitor titles or tags.

### 10.2 Quality gates (before the batch)
1. **XLSX:** fill sample rows, evaluate every formula with a Python formula engine (`formulas` or
   `pycel`); any error fails. Formula allowlist: SUM, SUMIFS, COUNTIFS, IF, IFERROR, AVERAGE, MIN, MAX,
   ROUND, INDEX, MATCH, date functions.
2. **PDF:** renders, within page count, no overflow.
3. **Product review** (`critic_product.md`, Sonnet with vision): the user message carries the listing
   copy plus **rendered images** of the cover and up to 4 pages or sheet previews. Question: does the file
   deliver what the listing promises, and is there any claim that isn't true.
4. A product whose product review was refused by the budget **cannot enter the batch**; it retries next cycle.
5. Every file contains an "About this product: created with AI assistance" line.

## 11. Images
- Gemini Flash Image via `metered_image_call` (~$0.02-0.04/image), image bucket.
- **AI makes the art, code sets the words.** No text is drawn by the model.

| Image | AI | Code |
|---|---|---|
| Etsy cover (first photo) | styled backdrop | real product preview as a card with shadow; title in brand fonts |
| Etsy "what's inside" | matching backdrop | real page grid |
| PDF design | cover art, section-header illustrations | all body text and tables |
| Gumroad cover (Line B) | backdrop | product preview + title (the owner uploads it with the product) |

- Rules: no real people or likeness, no logos or trademarks, no model-drawn text, safe for work.
- Etsy (since 2026-07-09): the first photo shows what the buyer gets; the AI-generative box is ticked
  (via the API if exposed, otherwise a 10-second owner task).
- **Threads:** text-first. An image post is allowed only for a product with a public listing image URL
  (Etsy-hosted, or a Gumroad cover URL if verified public at build).
- About 8-10 images per product. Brand palette, fonts and style prompt from config.

## 12. Owner workflow (about 10 min/day; H5)

### 12.1 `python -m swarm50.approve`
- Writes `artifacts/review/<date>.html` (drafts with images, copy and posts; scale bets with metrics;
  thesis; tasks) and opens it.
- Terminal walk: `y` / `n` (reason) / `s` (skip; expires after `draft_ttl_days`). It never exits on a
  stale item; it reports the item and continues (fixes the `sys.exit` behaviour in `queue.py`).
- Approval writes `draft_approved` with the `content_hash`.
- `approve_session` events (start, end, items) feed H5. `--pause` / `--resume` flip publishing.

### 12.2 Owner tasks
Gumroad product creation (note must include the Gumroad product ID) · ad settings and scale-bet close
entries · **weekly Pinterest CSV upload** (code generates `artifacts/pins/<week>.csv` from approved pin
drafts; about 5 min/week) · AI checkbox if needed · Notion duplication · sanity-hold confirmations.

### 12.3 Buyer support
The batch ends with a fixed item: "Check Etsy messages and Gumroad emails; reply within 24h."

## 13. Publisher and safety rules
1. Publish only items with `draft_approved` whose `content_hash` matches the rendered artifact.
2. Lint: disclosure present; links only to our own Etsy/Gumroad URLs; no @mentions; ≤3 hashtags; length
   limits; banned phrases (fake urgency, invented testimonials, income claims); **trademark denylist** in
   titles and tags (e.g. Notion, Canva, GoodNotes, Cricut, Excel, Etsy, unless used descriptively as "for
   Google Sheets" style compatibility, per a list in config); **near-duplicate check** against our live
   listings (title/tag Jaccard and spec-hash similarity above a threshold → refused).
3. Daily limits from config.
4. Idempotent: `published` stores the platform ID.
5. `publish_failed` → retry once next day → owner task. Never crash a cycle.
6. Kill switch: `publishing_enabled: false` or `approve --pause`.
7. Credentials come from `.env`; refreshed tokens are kept in `state/tokens.json` (git-ignored; never synced
   to any cloud folder).
8. Automatic token refresh (Threads 60-day tokens; Etsy refresh tokens).
9. A `killed` bet: Etsy listing deactivated via the API; Gumroad → owner task.
10. No replies, follows, likes or DMs.
11. `--force` cycle reruns are refused once `publishing_enabled` is true.

## 14. Ingest
- **Etsy:** shop receipts → revenue (net via payment-account ledger entries if available; otherwise gross
  minus configured fees, with `estimated=1`); refunds and cases → `refund`; listings → `views` and favorites.
- **Gumroad:** `GET /v2/sales` → revenue (price − `gumroad_fee`), refunded sales → `refund`, `referrer`
  reduced to a bare domain.
- **Threads:** own-post insights (views, likes, replies, link clicks where available).
- **Privacy whitelist, applied at parse time:** amounts, currency, platform IDs, timestamps, listing ID,
  country, and a salted hash of the buyer ID (only for counting distinct buyers). Names, emails, addresses
  and messages are dropped before anything is written. Raw receipt or sale JSON is never stored.
- Append-only `metrics` table (ts, cycle, bet_id, platform, views, favorites, clicks, sales).

## 15. Operations
- **Scheduler:** `scripts/install_schedule.ps1` registers a daily Windows Task Scheduler job.
- **Missed cycles:** a day without a `cycle_summary` is a missed cycle, shown in the report. No catch-up.
- **Away mode:** while `operator_away_until` is in the future, cycles run ingest only.
- **Backups:** after each cycle, `ledger.db` is copied via the SQLite backup API to
  `state/backups/ledger-YYYYMMDD.db`; the last 14 are kept.
- **Device and network:** one always-on personal device on the home connection; no VPN. The K3 fallback is
  another device on the **same** connection, not a VPS.

## 16. Data model changes
- `transactions`: types add `refund`; add `external_id TEXT` + a unique index where not null; AI spend
  rows tagged by `agent` (strategist, critic, analyst, worker, product_review, image); bucket membership
  comes from `agent`. Images are recorded as `token_cost` rows priced per image.
- `bet_events` new types: `build_ordered`, `refused` (doesn't change status), `draft_created`,
  `draft_approved`, `draft_rejected`, `published`, `publish_failed`, `unpublished`, `fee_charged`,
  `ad_result_entered`. `blocked` stays for guardrail stake refusals only.
- **Bet IDs:** `c{cycle}-r{round}-{kind}{i}` with kind `b` (build) or `m` (memo); build orders and memos
  only in a cycle's final round.
- `run_meta` new types: `thesis_proposed`, `thesis_critiqued`, `thesis_approved`, `thesis_rejected`,
  `approve_session`, `ingest_run`, `ingest_hold`, `overhead`.
- New append-only tables: `research`, `metrics`.
- Schemas: `StrategistResponse` (+`build_orders`, `research_requests`, `reread`, `notes_to_self`,
  `post_plan`); `BuildOrder`; `Memo` (scale bets: +`line`, `bet_type`, `parent_bet_id`, `format`,
  `demand_evidence`, `channels`, `price_usd`; −`category`); `ResearchRequest`; `ResearchBrief`;
  `NicheThesis` (its own response); spec types; `Result.stop_reason`.
- No real database exists yet, so no data migration is needed.

## 17. Fixes to existing code (built first, each with a failing test first)
1. **False insolvency** (`cycle.py:176`): `run_ended` only when the strategist's first call of a cycle
   is refused with `WalletEmpty`. Cap refusals never end the run.
2. **Refusals hiding bets** (`bets.py:31`): refusals write `refused`, which `status_of` ignores.
3. **10-event window** (`state.py:54`): replaced by the daily view.
4. **Bet ID collisions** (`review.py`, `bet_id = f"c{cycle}-{i}"`): new ID scheme; a `--force` rerun
   today already merges into the previous run's bets.
5. **`queue.approve` exits the process** on a non-queued bet (`queue.py`): return an error instead.
6. **Truncation:** expose `stop_reason`; when it is `max_tokens`, skip the repair retry (repair can't fix
   truncation) and log `malformed` with the reason.

## 18. Setup, dates and kickoff gates

### 18.1 Dates
- **Setup weekend, Sat-Sun 10-11 Oct 2026:** the owner opens accounts, applies for keys, sets spend
  limits, and signs the preregistration.
- **Kickoff target, Sat 31 Oct 2026**, or the first Saturday after all pre-kickoff gates pass. The owner
  proposed 9-10 Oct; it's moved because none of the automation exists yet (14 build steps), the Etsy API
  key takes 24h to 3 weeks, and K3/K4 each need 7 days (they overlap with the build).
- With a 31 Oct kickoff, cycles 61-90 fall on **30 Dec-28 Jan**, covering the New Year peak for planners
  and budgets (an advantage, and a confound recorded in H3).
- **Re-target rule (written into the prereg):** if kickoff slips past **Sat 21 Nov 2026** (window would
  start after about 20 Jan), Line A must not target New-Year-specific products (2027 planners, resolution
  trackers) for its judging-window bets, and H3's seasonality note is updated.

### 18.2 One-time owner setup
| # | Task | Owner time | Waiting time |
|---|---|---|---|
| 0 | Confirm employment terms allow a private online business | n/a | before any account |
| 1 | Etsy developer account + API key (clear app description) | 15 min | 24h-3 weeks; **do first** |
| 2 | Etsy shop, ID verification, Payoneer (within 30 days), policies; **opt out of Offsite Ads** | 60-90 min | days |
| 3 | Instagram Professional + Threads + Meta app; add self as Threads Tester; token | 30 min | none |
| 4 | Gumroad account + payout settings (PKR bank) | 20 min | review after first sales |
| 5 | Pinterest business account (no developer app) | 10 min | none |
| 6 | Anthropic + Google AI Studio keys → `.env`; Google Drive API OAuth (for Sheets copy links) | 25 min | none |
| 7 | **Hard spend limits:** Anthropic Console workspace monthly limit; Google Cloud budget alert **plus a request-per-day quota cap** on the Gemini API (Google budgets only alert) | 15 min | none |
| 8 | Install Agent Reach, no-login backends only (review its `install.md` before running it) | 15 min | none |

**Downside to state plainly:** an Etsy suspension is tied to the owner's identity and is effectively
permanent, so the real risk is losing Etsy as a channel for life, not $100. The shop-safety rules
(section 13, the ramp, no VPN) exist for this reason.

### 18.3 Pre-kickoff gates
| Gate | Pass | If it fails |
|---|---|---|
| K0 data check (first build task) | Etsy returns `views` for other sellers' listings, or the fallback (favorites + shop sold counts) is adopted | switch the probe to the fallback |
| K1 market probe (Line A) | ≥2 candidate niches meet the owner's thresholds; Line B is gated by thesis approval | rethink product type |
| K2 blind product check | the owner would pay $10 for ≥2 of 3 sandbox products next to competitor bestsellers; the XLSX opens correctly in Google Sheets | workers → Sonnet; rerun |
| K3 7-day unattended run (publishing off) | ≥6 of 7 cycles complete | another always-on device on the same connection |
| K4 shop health + live smoke test | Etsy ID + Payoneer verified; 3 seed listings live 7 days without flags; **one listing created as a draft via the API, activated, then deactivated; one Threads post published and confirmed** | fix before kickoff; Gumroad-first fallback |
| K7 employment | permitted | don't proceed under the owner's name |

In-run gates (prereg): **K5 day 45** (shop views ≥ threshold or ≥1 sale, otherwise an owner-ordered reset of
Line A's focus and/or the thesis) and **K6 day 21** (Threads median views/post ≥ threshold, otherwise cut
to 3 posts/week and shift effort to Etsy).

## 19. Hypotheses (replace `docs/PREREGISTRATION.md` H1-H3)
- **H1 Calibration:** the strategist's day-14 and day-30 view forecasts for its products are scored
  against actual views (mean absolute log error and direction). Prediction set by the owner.
  This replaces "revenue falls short of EV", which would be trivially true at low sales.
- **H2 Cost of thinking:** AI plus image spend exceeds 30% of the $100 by day 90 (estimate ~44%).
- **H3 Sustainability:** the window score exceeds AI plus image spend in cycles 61-90. Confound: with a
  31 Oct kickoff the window covers the New Year peak.
- **H4 Lines:** Line A vs Line B on window score per dollar spent and per owner-minute.
- **H5 Owner time:** mean logged approval-session time after setup is about 10 minutes a day or less.

## 20. Dry run and sandbox
- `scripts/dry_run.py`: arms removed; N day-1 strategist calls (discovery mode, research mocked or live),
  reporting formats, lines, build orders and research requested, **and the measured cost per call**.
- **Sandbox cycle** (`cycle run --sandbox`): one real cycle with publishing forced off on a throwaway DB;
  real files, images and preview (~$1-2). Feeds K2. **Its measured costs set `strategist_interval_cycles`
  and the bucket caps before kickoff.**

## 21. Testing
1. Section 17 fixes first, each with a failing test.
2. New modules offline: research/ingest against saved sample responses; publisher against mocked `httpx`;
   real local file rendering; broken formula fails; images with stub bytes.
3. Safety: unapproved refused; hash mismatch refused; lint including trademark and near-duplicate;
   limits; idempotency; kill switch; token refresh; `--force` refused while publishing.
4. Money: score calculation; refunds; external_id uniqueness; sanity hold; Gumroad mapping refusal;
   bucket isolation; run cap; scale-bet gate (3 distinct buyers).
5. Privacy: no names, emails or `@` reach the DB or prompts from ingest fixtures.
6. Analyst: quote caps and sanitising enforced; Etsy hypotheses evaluated by code.
7. No real network in tests. The sandbox, dry run and K0/K4 checks are the only real-call paths, run by hand.
8. The existing 91 tests stay green (prompt tests updated per section 8).

## 22. Build order
1. **K0 data check:** call Etsy `findAllListingsActive` with the owner's API key; confirm whether `views`
   comes back for other sellers' listings
2. Fixes to existing code (section 17)
3. Schemas, prompts, config, money model, budget buckets, run cap, score (sections 7, 8, 16)
4. Research subsystem: Etsy probe, Agent Reach web fetch, analyst, notebook (section 5)
5. Discovery mode + separate thesis call (section 6)
6. Renderer XLSX/PDF/Sheets + quality gates + product review with images (section 10)
7. Image pipeline (section 11)
8. Approve CLI + preview + pin CSV export (section 12)
9. Etsy publisher + ingest + privacy whitelist (sections 13, 14)
10. Threads publisher + insights ingest
11. Gumroad ingest + product mapping
12. Daily view, report (true P&L, score, burn rate), operations (sections 9, 15)
13. Docs: README, RULES, KICKOFF_CHECKLIST, PREREGISTRATION (sections 18, 19)
14. Sandbox cycle + dry-run update → set cadence and caps (section 20)

## 23. To verify during the build
- K0: Etsy `views` on other sellers' listings (otherwise favorites + `transaction_sold_count`).
- Etsy API: the AI-generative checkbox; payment-account ledger entries for exact fees; refund/case data.
- Threads own-post insights fields (link clicks).
- Agent Reach: how to invoke the Exa and Jina backends from plain Python (CLI or direct HTTP), free-tier
  limits, and Windows behaviour.
- Google Drive API copy-link flow for Sheets (OAuth scope, conversion fidelity of formulas and validation).
- Gumroad cover image URLs: public or not (for Threads image posts and pins).
- Formula engine choice; Gemini image model ID and price.
- Audit `teomro/etsy` before the owner installs it as a planning-time MCP (not a runtime dependency).

## 24. Out of scope (parked)
X/Twitter · video, avatars, personas · Reddit (commercial use banned on the free tier) · LinkedIn ·
Gumroad memberships · Medium/Substack · automated engagement · ad-platform automation · Notion
automation · **Pinterest API** (weekly CSV instead) · **Threads keyword search** (needs Meta App
Review; revisit if Line B works) · Agent Reach cookie-based backends and YouTube downloading.
