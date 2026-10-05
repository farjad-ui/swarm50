# swarm50 digital-products pivot: design spec (v3)

- **Status:** v3, approved in brainstorming. Awaiting the owner's read before implementation planning.
- **Companions:**
  - `2026-10-05-assumption-audit.md`: the risk register
  - `2026-10-05-spec-review.md`: the independent review
  - `2026-10-05-resource-research.md`: tools and community skills, each marked adopt, borrow or reject
- **Replaces:** the trading-hypothesis design in `OVERNIGHT_BRIEF.md` M1/M2

## 0. What changed in v3 (on top of v2)
1. **Product studio (§10):** specialist roles, a design system, independent QA, iteration up to 3 rounds,
   and shelving instead of shipping anything that fails.
2. **Budget A (§7.8):** $100 for fewer, better products: ~15 Line A core products plus ~15-20 adaptations,
   and 4 Line B products. A pre-registered top-up rule (§7.9).
3. **Explore vs exploit (§7.3):** the evidence bar scales with money at risk, a code-enforced shipping
   minimum, a research budget, a niche-diversity floor, phases, and a Thompson-sampling suggestion.
4. **Threads reply assistant (§12.4):** a narrow, auto-send exception to "everything outward is approved".
5. **One rendering engine (§10.3):** HTML/CSS through Playwright Chromium for PDFs, listing images,
   pins and Threads images; XlsxWriter plus LibreOffice for spreadsheets; a code-made listing video.
6. **Deterministic anti-slop gates (§10.5):** Vale with AI-tell rules, the impeccable design detector,
   contrast and print checks, and LibreOffice recalculation.
7. **Community skills vendored into role prompts (§8.3)** with licence attribution.
8. **Lessons ledger (§9):** for strategist coherence over 90 days.
9. **Threads image posts** via a GitHub Pages assets repo; 3 posts a day maximum.
10. **Gumroad email workflows** only after $100 earned and one payout (§4).
11. **Kickoff Sat 31 Oct 2026** (owner confirmed); setup weekend 10-11 Oct.

## 1. Summary
swarm50 becomes a small, mostly autonomous **digital-products business** run by agents for 90 days on a
$100 wallet. It has two product lines:
- **Line A, Marketplace:** practical, search-driven products on **Etsy**.
- **Line B, Conversation:** problem-solving products on **Gumroad**, marketed by a **Threads** brand account
  built around one niche the agents discover in week 1 from web research.

Pinterest traffic comes from a weekly CSV the owner uploads. The agents research demand, order products,
and run them through a **product studio** that designs, builds, tests and reviews them until they pass
(or shelves them). They draft listings and posts, and answer routine Threads comments. The owner
approves one daily batch (about 10 minutes, buyer messages included), and plain code publishes.

The strategist is judged on the **window score** (§7.5): net revenue in the final 30 cycles, after fees,
refunds, listing fees and ad spend.

### Goals
1. A business that could keep running after day 90 if it works (H3).
2. Owner time of about 10 minutes a day or less after setup (H5).
3. **No AI slop:** every shipped product passes functional, design and content gates (§10).
4. Every dollar and every outward action auditable in the append-only logs.
5. Decisions grounded in observed demand, with forecasts scored against reality (H1).

### Non-goals
X/Twitter, AI video, avatars or personas, Reddit (at runtime), LinkedIn, memberships, unsolicited
engagement (follows, likes, DMs, replying on other people's posts), ad-platform automation, Notion
automation, the Pinterest API, Threads keyword search.

### Ground rules
- Ledger, bet log, run log, research and metrics tables are append-only (UPDATE/DELETE triggers).
- State is derived by folding events, never stored and mutated.
- Every AI call is **one system prompt plus one user message**, with **no server-side tools**, so input
  size is known before the budget check.
- `swarm50/metered.py` is the only module that touches any AI SDK or the `claude` CLI.
- No prompt text in `.py` files; prompts live in `prompts/*.md` and are filled with `string.Template`.
- No agent-facing code path writes `deposit`, `adjustment`, `revenue` or `refund` transactions.
- **Nothing goes out without owner approval of its exact content**, with one narrow exception: the
  auto-send tier of the reply assistant (§12.4).
- Python 3.11+, Windows and Linux, `pathlib`, UTF-8.

## 2. Decisions log

| # | Decision |
|---|---|
| 1 | Digital products only |
| 2 | Payouts in Pakistan: Etsy via Payoneer; Gumroad bank payout in PKR (verified) |
| 3 | Daily owner approval batch; plain code publishes |
| 4 | 90 days, $100, plus a pre-registered top-up rule |
| 5 | One objective: the window score (§7.5); AI spend reported separately (H3) |
| 6 | Etsy + Gumroad + Threads; Pinterest by weekly CSV; no X, AI video or personas |
| 7 | Extend the existing core with plain-code modules |
| 8 | Revenue and refunds recorded automatically from platform APIs |
| 9 | XLSX + Google Sheets copy link, PDF (printable and hyperlinked); Notion manual and only for proven winners |
| 10 | Gemini Flash Image makes the art; code sets all text |
| 11 | Two product lines with different products and evidence |
| 12 | Line B niche discovered by the agents in week 1 from web research; owner approves |
| 13 | Web research through Agent Reach's no-login backends (Exa, Jina) |
| 14 | Test products: one owner approval on the finished draft |
| 15 | Product studio with iteration; fewer, better products (budget A) |
| 16 | Explore vs exploit rules (§7.3) |
| 17 | Threads reply assistant with a narrow auto-send tier |
| 18 | HTML/CSS + Playwright rendering; XlsxWriter + LibreOffice; code-made listing video |
| 19 | Community skills vendored into prompts, licences attributed |
| 20 | Hard provider spend limits; owner time about 10 min/day |
| 21 | Setup 10-11 Oct; kickoff Sat 31 Oct 2026 |

## 3. Architecture

### 3.1 The daily cycle
```
 code   1. INGEST      sales, refunds, fees, listing views/favorites, Threads insights + replies
 AI+cd  2. STUDIO      queued build orders run through the product studio (§10); passing products
                       become draft packages (files, 8-10 images, video, listing copy, scorecard)
 code   3. STATE       daily view (§9)
 AI     4. STRATEGIST  if due: build orders, scale-bet memos, research requests, post plan, lessons
 code   5. RESEARCH    Etsy probe; web via Agent Reach no-login backends
 AI     6. ANALYST     raw research -> graded brief
        (4-6 repeat up to 3 rounds in discovery mode; orders and memos only in the final round)
 AI     7. CRITIC      scale-bet memos and the niche thesis
 AI     8. SOCIAL      Threads posts (with images) and pin drafts
 human  9. APPROVE     `python -m swarm50.approve`
 code  10. PUBLISH     Etsy / Threads APIs; Gumroad + weekly pin CSV -> owner tasks
 ------ separately, every 2 hours during waking hours ------
 AI+cd     REPLIES     reply assistant (§12.4)
```

### 3.2 Modes and cadence
- **Discovery** (cycles 1-7): strategist every cycle, up to 3 rounds per cycle.
- **Operating** (cycles 8-90): strategist every `strategist_interval_cycles` (2, tuned by the sandbox run).
  The studio, social drafting, ingest and publishing run every cycle.

### 3.3 Budget buckets
`think` (strategist, analyst, critic) · `build` (studio AI roles) · `image` · `reply`. Each has a per-cycle
cap, and a refusal in one bucket never uses another's budget. Every AI dollar also counts toward the
hard run cap `run_ai_cap_usd`. Bucket membership is derived from the transaction's `agent` tag.

### 3.4 Modules
| Module | Role | Network |
|---|---|---|
| `metered.py` (changed) | `metered_image_call` (Google); `Result.stop_reason`; image blocks in user messages; bucket-aware gate; prompt caching | AI APIs |
| `research.py` (new) | Etsy probe; web fetch; analyst; notebook | Etsy (read), Exa, Jina |
| `studio/` (new) | roles, iteration loop, scorecards (§10) | none |
| `render/` (new) | `html.py` (Playwright PDF and PNG), `xlsx.py` (XlsxWriter), `office.py` (LibreOffice recalc and preview), `sheets.py` (Drive copy link), `video.py` (ffmpeg), `images.py` (Gemini backgrounds) | Drive only |
| `qa/` (new) | Vale, impeccable detector, contrast, `pypdf` print checks, formula tests, listing lint | none |
| `ingest.py` (new) | sales, refunds, fees, metrics, replies; privacy whitelist | Etsy, Gumroad, Threads (read) |
| `publish/` (new) | `etsy.py`, `threads.py`, `assets.py` (GitHub Pages), `pins_csv.py`; lint, limits, token refresh | Etsy, Threads, GitHub write |
| `replies.py` (new) | reply assistant | Threads |
| `approve.py` (new) | daily batch CLI and HTML preview | none |
| existing modules | updated per §16 and §17 | none |

## 4. Product lines

| | Line A: Marketplace | Line B: Conversation |
|---|---|---|
| Storefront | Etsy | Gumroad |
| Traffic | Etsy search + Pinterest CSV | Threads (with images) + Pinterest CSV |
| Fits | spreadsheets (Excel + Sheets), printables (A4 + Letter), **hyperlinked digital planners**, trackers | playbooks, swipe files, checklists + walkthroughs, profession-specific prompt packs, calculators with a guide, bundles |
| Price / volume | $5-17; ~15 core + ~15-20 adaptations | $15-49; 4 products: lead magnet → core → premium (+1 spare) |
| Niche shape | ≥4 niches during exploration | one niche (the approved thesis) |
| Evidence | Etsy probe (+ web) | web research (+ Etsy probe for adjacent demand) |
| Owner time per product | ~0 | ~10 min (Gumroad has no product API) |

**Gumroad funnel:**
- The free lead magnet collects emails from day 1, and the paid upgrade is linked inside the lead magnet.
- Gumroad's automated email sequences (Workflows) only unlock **after $100 earned and one payout**. At that
  point the owner sets up the agent-drafted 3-5 email sequence (an owner task; Gumroad has no API for it).

Line B may point to Etsy products; Line A never contacts Etsy buyers.

## 5. Research subsystem
- **Requests:** `request_id`, `source` (`etsy` | `web`), `query`, `purpose`, `hypothesis`. For Etsy the
  hypothesis is a **numeric threshold that code evaluates**; for web it is a sentence the analyst gives a
  verdict on.
- **Etsy probe:**
  - Calls: `findAllListingsActive` and `getShop`.
  - Code computes: the result count, price quartiles, favorites and listing age for the top 25, and views per
    day if Etsy returns them for other sellers' listings (K0). Otherwise it uses shops'
    `transaction_sold_count`.
  - Competitor titles and tags go to the analyst only, never to workers.
- **Web:**
  - Agent Reach's no-login backends: Exa search returns the top 5 URLs, and Jina Reader fetches each page's
    text, truncated to 6,000 characters.
  - Cookie backends and YouTube downloading are forbidden.
- **Analyst (Sonnet):** produces a `ResearchBrief`:
  - graded findings
  - recurring problems with the audience's own phrases
  - current alternatives and their gaps
  - contradicting evidence (required)
  - a verdict
  - a one-line conclusion
- **Quote limits, enforced by code:** at most 5 quotes per brief, each 120 characters or fewer, with URLs and
  @handles stripped. Quotes are shown to the strategist fenced and labelled as data.
- **Honest boundary:** short audience quotes do reach the strategist and, through it, the copy; that's
  intended. The defences are:
  1. no agent has a side-effecting tool
  2. quotes are capped and sanitised
  3. lint plus owner approval of the exact published content
- **Notebook:** an append-only `research` table. The daily view shows an index of the last 40 briefs, and
  `reread` brings up to 3 full briefs back.

## 6. Discovery week (cycles 1-7)
| Cycles | Stage | Expectation |
|---|---|---|
| 1-2 | Broad scan | 12-15 candidate niches; shallow scans |
| 3-5 | Deep dive | Top 3 candidates; hypotheses, including attempts to disprove the favourite |
| 6 | Niche thesis | A separate thesis call |
| 7 | Owner approval | One page in the batch |

**Line A runs in parallel** and starts building in cycle 2. Pre-kickoff research (K1, using last30days
and Google Trends at build time) seeds its first candidates.

**The `NicheThesis`**, checked by `critic_thesis.md`:
- audience
- ranked problems, each citing research IDs
- jobs to be done and current alternatives
- the gap and our position
- the product ladder
- content pillars with example hooks
- milestones for days 30, 60 and 90
- risky assumptions, each with the cheapest test
- kill criteria
- why not the runners-up

Line B can't build until the thesis is approved. Day 45 re-checks it.

## 7. Money model

### 7.1 Wallet
$100, written once at kickoff.

### 7.2 Kinds of spending
| | Core product | Adaptation | Wildcard | Scale bet |
|---|---|---|---|---|
| What | new product, full studio | audience, regional or theme version of a product that passed | a core product on a hunch | ads, promoted listings, more variants of a winner |
| Evidence | Line A: one passing Etsy probe. Line B: one web brief graded at least moderate | the parent passed the studio | a written hunch and reason; at most 1 in 5 cores | parent has 3+ sales from distinct buyers |
| Process | build order → studio → one owner approval → listing fee staked → publish | same, with a light studio | same as core | memo → critic → owner → stake |
| Typical AI cost | ~$1.00 (Line A), ~$2.50 (Line B) | ~$0.35 | ~$1.00 | critic loop ~$0.10 |

**Colour and size options are variations inside one Etsy listing, never separate listings.**

### 7.3 Explore vs exploit
1. **The evidence bar scales with money at risk** (table above). At most 3 research requests per
   candidate niche before deciding.
2. **Shipping minimum, enforced in code.** From cycle 2 to 30, at least 2 Line A build orders per week.
   If a week falls short, the daily view shows **SHIP DUE**, and the strategist's next response must
   contain a build order (validated by its schema).
3. **Research budget.** Research is capped at 35% of think spend in operating mode. No query or niche
   is re-researched within 7 cycles unless new metrics arrive. **Research yield** (the share of verdicts
   that changed a decision) is tracked in the daily view.
4. **Phases.**

| Phase | Cycles | Line A | Line B |
|---|---|---|---|
| Explore | 2-30 | ~10 cores across ≥4 niches, at most 3 per niche | thesis approved → free lead magnet → Threads tests |
| Exploit | 31-60 | adaptations of products with traction, plus 3-4 cores near the winners | ~$15 core product only if the lead magnet gets downloads and clicks |
| Harvest | 61-90 | adaptations and listing refreshes; **no new cores after cycle 65** | ~$49 premium only after the core has 3+ sales |

5. **Allocation suggestion (Thompson sampling).** Code samples each niche's favorite rate and sale rate
   from Beta distributions (stdlib `random.betavariate`) and shows "suggested next build: niche X" in the
   daily view. The strategist may override it, with a reason.
6. **No Line A kills before cycle 45** except for policy reasons. Listings cost $0.20 per 4 months, and
   Etsy needs 60-90 days to rank a new listing.

### 7.4 Scale bets
- **The critic's input** includes the parent product's code-computed metrics and the cited briefs' numbers.
- **Ads** have no API, so an approved scale bet becomes an owner task to set them up. When a scale bet
  closes, the owner enters the actual ad spend and the attributed sales; that entry is the only ad return
  the critic and the score ever see. Unspent budget comes back as `bet_return`.
- **Run ad cap:** $20.

### 7.5 Window score
Computed by code over cycles 61-90:

`score = Σ net sales (gross − platform transaction/processing fees) − Σ refunds − Σ listing fees charged in the window − Σ ad spend in the window`

AI spend is shown next to the score, not in it (H3). The daily view shows the score from cycle 61 and a
trailing-30-cycle equivalent before that.

### 7.6 Revenue and refunds
- **Automatic recording:** `ingest.py` writes `revenue` net of transaction and processing fees, and `refund`
  transactions. Listing fees aren't deducted here because they already sit in stakes.
- **No double counting:** each sale or refund is keyed on `external_id`, which has a unique index.
- **Sanity hold:** if more than $100 would be credited in one day, ingest writes nothing and creates an owner
  task to confirm.
- **Gumroad mapping:** the owner's task-done note must include the Gumroad product ID. Sales of unmapped
  products are refused and flagged.
- **Manual entries:** `record-return` stays for edge cases.

### 7.7 Overhead and the true P&L
The owner records `overhead` events: Payoneer's $29.95/yr fee (under $6,000 received, Pakistan), the ~3%
withdrawal fee, FX, and payout timing. The report shows a **true P&L** line next to the agents' wallet.

### 7.8 Budget and caps (budget A)
| Item | Estimate |
|---|---|
| Discovery week | ~$8 |
| Operating strategist (~42 runs) | ~$10 |
| Scale-bet critic loops | ~$2 |
| Analyst | ~$5 |
| Line A core products, ~15 × ~$1.00 (studio + images + video) | ~$15 |
| Line A adaptations, ~18 × ~$0.35 | ~$6 |
| Line B products, 4 × ~$2.50 | ~$10 |
| Threads posts and pins | ~$2 |
| Reply assistant | ~$6 |
| **AI + images, before caching and batch savings** | **~$64** |
| After prompt caching (target) | ~$55 |
| Listing fees and renewals | ~$7 |
| Ads (only after 3 sales) | ≤ $20 |

With zero sales, about $29-38 remains (no scale bets are possible without sales). **The sandbox run measures
real costs, and the caps are tuned before kickoff.** Studio work may move to the Batch API (50% off) once
it's verified.

| Key | Value |
|---|---|
| `starting_balance_usd` / `total_days` | 100 / 90 |
| `max_stake_pct` / `max_open_exposure_pct` | 0.35 / 0.60 |
| `cycle_think_cap_usd` | 0.75 (discovery 1.50) |
| `cycle_build_cap_usd` | 1.00 |
| `cycle_image_cap_usd` | 0.75 |
| `cycle_reply_cap_usd` | 0.15 |
| `run_ai_cap_usd` | 75 (hard) |
| `strategist_interval_cycles` | 2 |
| `strategist_max_tokens` / `thesis_max_tokens` | 6000 / 6000 |
| `studio_max_rounds` | 3 |
| `builds_per_cycle` | 1 core, or up to 3 adaptations |
| `ship_floor_per_week` | 2 (cycles 2-30) |
| `research_share_cap` | 0.35 |
| `scale_min_sales` / `run_ad_cap_usd` | 3 / 20 |
| `web_max_pages` / `web_max_chars_per_page` | 5 / 6000 |
| `ingest_daily_credit_alert_usd` | 100 |
| `etsy_listings_per_day` | 2 in week 1, then 5 |
| `threads_posts_per_day` / `auto_replies_per_day` | 3 / 20 |
| `draft_ttl_days` | 3 |
| `publishing_enabled` | false until kickoff |
| `operator_away_until` | null |
| roles | strategist `claude-fable-5-1`; critic, analyst, studio roles and replies `claude-sonnet-5`; image Gemini Flash Image (ID and price confirmed at build) |
| formats | `spreadsheet` · `printable_pdf` · `digital_planner` · `guide_pdf` · `notion_template` · `bundle` · `lead_magnet` |

### 7.9 Top-up rule (in the preregistration)
If the day-45 gate shows traction, by a threshold the owner sets before kickoff, the owner may deposit up to
**$50 more** (only a human can ever write a deposit). **The agents aren't told about this rule in advance.**
H2 and H3 are reported against total deposits.

## 8. Prompts

### 8.1 Objective (`prompts/objective.md`)
```
Your objective
Build products that people keep buying. At the end of cycle $total_days you are judged by
one number: net revenue earned during the final 30 cycles, after platform fees, refunds,
listing fees and ad spend in that window. The wallet balance is not the measure, and money
that arrives early but stops does not count. Spending that builds lasting demand is how you
score; spending that only produces a one-off spike is not.
```

### 8.2 Role prompts
- **Thinking:** `strategist.md`, `thesis.md`, `analyst.md`, `critic.md`, `critic_final.md`, `critic_thesis.md`, `rebuttal.md`
- **Studio:** `studio_product_lead.md`, `studio_builder_xlsx.md`, `studio_builder_pdf.md`, `studio_qa.md`,
  `studio_design_review.md`, `studio_content_edit.md`, `studio_art_director.md`, `studio_buyers_eye.md`
- **Listings:** `listing_copy.md`
- **Social:** `social_post.md`, `pin.md`, `reply.md`
- **Strategist prompt keeps:** the factual statement that the run ends if the wallet can't pay for a call.
- **It adds:** two lines, modes, build orders with forecasts and evidence, the explore/exploit rules,
  `notes_to_self` and lessons.
- **Prompt caching:** long shared prefixes (design system, rubrics) are cached.

### 8.3 Vendored community skills
Relevant rules are copied into the role prompts, with licences and attribution in `prompts/vendor/LICENSES.md`.

| Source | Licence | Goes into |
|---|---|---|
| taste-skill (anti-defaults, design read, dials, image direction) | MIT | product lead, builders, art director |
| impeccable (design vocabulary; its detector runs as a QA gate, §10.5) | Apache 2.0 | builders' revision instructions |
| ui-ux-pro-max (palettes, font pairings, type scales, chart guidance) | MIT | design system data, filtered by anti-defaults |
| humanizer + stop-slop (AI-writing patterns) | MIT | content editor, listing copy, social |
| threads-skills (13 hook formulas by goal, reply drafter, Threads humanizer) | MIT | social post, reply, profile setup |
| Nano Banana prompt-craft rules (materials, framing, ratio) | open source | art director |
| Planner generators (hyperlink navigation patterns) | open source | planner templates |
| Etsy listing helpers (alt text, category path, digital checklist) | open source | listing copy, product brief |

## 9. Daily view (state block)
About 3,000 tokens:
```
cycle 34 of 90 | operating | phase: exploit | next strategist: c35 | balance $81.40 | exposure $6.20
AI $28.10 of $75 cap (planned pace $29.80) | today: think $0 build $0.92 image $0.41 reply $0.06
SCORE      trailing-30 equivalent $14.20 (window starts c61)
SHIP       Line A this week: 1 of 2  -> SHIP DUE
LINES      A: 12 live, 4 sales, net $36.10 | B: lead magnet 61 downloads, core 2 sales, net $28.00
ALLOCATION suggested next build: niche "freelance invoicing" (sampled sale rate 0.031)
LESSONS    L4 "Planner buyers favorite but don't buy below 8 photos" (ev: c12-r1-b1, c19-r1-b1) ...
THESIS (B) ...  RESEARCH  last 40 briefs | research share 28% | yield 41%
PRODUCTS   id, line, format, title, age, views, favs, sales, net, 7d, forecast vs actual, studio score
CHANNELS   threads 7d: posts, views, clicks, replies (auto 31 / queued 4); last pin CSV c31
WAITING    drafts, scale bets, tasks | REJECTED 14d | SHELVED (studio fails + reasons)
NOTES      last 3 strategist runs | OPERATOR recent task notes
```

**Lessons ledger:** the strategist writes lessons as `{lesson, evidence_ids, confidence}` events (in an
append-only log). Active lessons appear in the daily view, and every 7th cycle the strategist confirms or
retires each one. This follows the long-horizon benchmark finding that agents lose coherence and fail to
learn from experience.

## 10. Product studio

### 10.1 Pipeline
```
build order -> PRODUCT LEAD brief -> BUILDER spec (inside the design system) -> RENDER
  -> QA: deterministic gates (§10.5) + QA engineer's independent test cases
  -> DESIGN REVIEW (vision) + CONTENT EDIT
  -> pass? --no--> BUILDER revises with every failing item (max 3 rounds, may span 2 cycles) -> shelved if still failing
     --yes--> ART DIRECTOR (images) -> LISTING COPY -> VIDEO -> BUYER'S EYE -> draft package + scorecard -> owner
```
**Adaptations** skip the brief and reuse the parent's design decisions, but still pass QA, the design
review and the content edit.

### 10.2 Roles (Sonnet unless noted)
| Role | Job | Pass condition |
|---|---|---|
| Product lead | Brief: buyer, job to be done, competitor **feature** checklist (features only, never their text), one clear differentiator, the **design read** (taste-skill), testable acceptance criteria, page or sheet outline | the critic doesn't review it; the QA engineer tests against it |
| Builder | XLSX or HTML spec within the design system | renders cleanly |
| QA engineer | Writes test cases **from the brief, independently of the builder**: formula scenarios with expected outputs, validation, protected cells, the Sheets import, A4 and Letter, links | all tests pass |
| Design reviewer (vision) | Scores rendered pages 1-5 on hierarchy, grid, spacing, typography, colour and contrast, consistency, print-friendliness, premium vs template | average ≥ 4, no criterion < 3 |
| Content editor | humanizer + stop-slop rubric; specificity; would an expert in the niche find it useful; invented facts | no blocking items; usefulness ≥ 4 |
| Art director (vision + Gemini) | Image prompts from the brand style and prompt-craft rules; **3 versions of each hero background**; picks the best and rejects artefacts | a selection is made |
| Buyer's eye (vision) | Listing plus previews against the competitor feature checklist and the differentiator claim | matches the checklist; the differentiator is real |

### 10.3 Rendering
- **PDFs** (printables, guides, planners):
  - Jinja2 HTML/CSS templates, rendered by Playwright Chromium (`@page` sizes, `printBackground`).
  - **Separate A4 and US Letter files.**
  - Margins of at least 0.5 inch.
  - Planners get Monday-start and Sunday-start versions.
  - **Hyperlinked digital planners** use internal anchor links, with year → month → week → day navigation.
- **Spreadsheets:**
  - XlsxWriter builds the workbook: dashboard first, then assumptions, then detail; charts, validation,
    conditional formats, freeze panes, print setup, an instructions tab, sample data.
  - LibreOffice in headless mode recalculates every formula and renders preview images.
  - The Drive API produces a **Google Sheets copy link**.
- **Images:**
  - The same HTML/CSS engine renders Playwright screenshots of the template plus a Gemini background:
    - **8-10 Etsy photos** at 2000×2000, including lifestyle compositions, **device mockups** (the real
      product on a tablet or laptop via CSS 3D transforms), a "what's inside" grid and feature callouts
    - Gumroad covers
    - Pinterest pins at 1000×1500
    - Threads images
  - AI makes the art; code sets every word.
- **Listing video:** ffmpeg turns the rendered pages into a 5-15 second page-flip slideshow. It isn't AI
  video; it shows the real product.

### 10.4 Design system (built once during implementation; the owner approves it at setup)
- **Type:** 6-8 curated Google Font pairings from ui-ux-pro-max, **excluding overused AI defaults** (Inter,
  Poppins and others on impeccable's and taste-skill's lists), on a modular type scale.
- **Colour:** palettes from ui-ux-pro-max by niche type, each passing WCAG AA contrast.
- **Page templates:** cover, section, worksheet, checklist, table, tracker, planner spreads; a 12-column
  print grid.
- **Spreadsheet style kit:** header, banding and derived-cell styles; number formats; a chart palette.
- **Image composition templates:** 5-6.
- **Icons:** Lucide or Tabler (ISC/MIT).
- **Calibration:** 3 hand-reviewed reference products calibrate the design reviewer and content editor
  (`scripts/calibrate_reviewers.py`) before kickoff.

### 10.5 Deterministic gates (run before any AI review; a failure means revise)
1. **Vale** with AI-tell rules (vale-ai-tells / slop-linter) on all product text, listings and posts.
2. The **impeccable detector** (`npx impeccable --json`) on every rendered HTML page and image template,
   with print-relevant rules only.
3. **WCAG AA contrast** on every text/background pair, including text over images.
4. **`pypdf` print checks:** page size, embedded fonts, minimum 9pt text, page count, links resolve.
5. **LibreOffice recalculation:** no error values, and the QA test cases' expected outputs match.
6. **Listing lint:**
   - the title's first 40 characters carry the main phrase; under 15 words; no pipes
   - 13 multi-word tags
   - every attribute filled
   - trademark denylist
   - near-duplicate check against our live listings
7. The "About this product: created with AI assistance" line is present.

A product whose review was refused by the budget **cannot enter the batch**; it retries the next cycle.

## 11. Images
- Gemini Flash Image, called through `metered_image_call`, in the image bucket.
- **Rules:** no real people or likeness; no logos or trademarks; no model-drawn text; safe for work.
- **Etsy rules (since 2026-07-09):** the first photo shows what the buyer gets; the AI-generative box is
  ticked (via the API if it's exposed, otherwise a 10-second owner task).
- **Threads images:** the publisher uploads them to the **GitHub Pages assets repo** (a free public URL).
  Etsy-hosted URLs are reused where they exist.

## 12. Owner workflow (about 10 min/day; H5)

### 12.1 `python -m swarm50.approve`
- The HTML preview shows each draft package with its **scorecard**, plus scale bets, the thesis, tasks and
  queued replies.
- In the terminal: `y` / `n` (with a reason) / `s` (skip; expires after 3 days). It never exits on a stale item.
- `approve_session` timing feeds H5. `--pause` / `--resume` control publishing.

### 12.2 Owner tasks
- Gumroad product creation (the note must include the product ID)
- ad setup and scale-bet close entries
- the weekly Pinterest CSV upload (~5 min)
- Gumroad Workflow setup (after the first payout)
- the AI checkbox, if needed
- Notion duplication
- sanity-hold confirmations

### 12.3 Buyer support
The batch ends with a fixed item: check Etsy messages and Gumroad emails, and reply within 24 hours.

### 12.4 Threads reply assistant
- **Schedule:** every 2 hours during waking hours. It reads new comments on our own posts.
- **One Sonnet call per comment** (~$0.004), with no tools. Output: `{category, reply_text, product_id|null}`.
  The model never writes a URL; code builds links only from our own product list.

| Tier | Covers | Handling |
|---|---|---|
| Auto-send | thanks and acknowledgements; answers from the product's **owner-approved FAQ sheet**; the product or free link when someone asks for it | sent after lint; at most 1 per person per thread; at most 20 a day |
| Owner batch | complaints, refunds, criticism, money, health or legal topics, low classifier confidence | queued |
| Never | arguments, replying on others' posts, DMs, follows, likes, keyword bait | blocked in code |

- **Guardrails:**
  - comment text is treated as data
  - replies are 300 characters or fewer
  - no @mentions beyond the person being answered
  - the banned-phrase list applies
  - obvious spam (strangers posting links) is hidden automatically
- **Disclosure:** the profile bio says the account is AI-run, and replies say so plainly if anyone asks.
- **Posts:** threads-skills hook formulas, chosen by goal; at most 3 a day; **no engagement bait** ("comment X
  for the link" posts get about half the reach). The link goes in the post or our own first reply.

## 13. Publisher and safety
1. Publish only items with `draft_approved` whose `content_hash` matches. The one exception is reply-assistant
   auto-sends, which pass the reply lint instead.
2. Lint as in §10.5, plus: links only to our own Etsy, Gumroad and assets URLs; no @mentions; at most 3
   hashtags; banned phrases (fake urgency, invented testimonials, income claims).
3. Daily limits from config.
4. Idempotent: `published` events store the platform ID.
5. A failure becomes `publish_failed`, is retried once the next day, then becomes an owner task. A failure never crashes a cycle.
6. Kill switch: `publishing_enabled: false` or `approve --pause` (this also pauses replies).
7. Credentials in `.env`; refreshed tokens in `state/tokens.json` (git-ignored, never synced).
8. Tokens refresh automatically (Threads tokens last 60 days; Etsy uses refresh tokens).
9. A killed bet's Etsy listing is deactivated through the API; Gumroad becomes an owner task.
10. `--force` reruns are refused once publishing is enabled.

## 14. Ingest
- **Etsy:** receipts become revenue (net, using payment-account ledger entries if available; otherwise
  estimated and flagged); refunds and cases become `refund`; views and favorites go to metrics.
- **Gumroad:** `GET /v2/sales` → revenue and refunds; the referrer is reduced to a bare domain.
- **Threads:** own-post insights, and new replies for the reply assistant.
- **Privacy whitelist, applied at parse time:**
  - kept: amounts, currency, IDs, timestamps, listing ID, country, a salted buyer-ID hash (for counting distinct buyers)
  - dropped: names, emails, addresses, messages
  - raw receipts are never stored
  - reply authors are kept only as a salted hash plus the public handle, needed to reply
- Append-only `metrics` table.

## 15. Operations
- **Scheduler:** `scripts/install_schedule.ps1` registers the daily cycle and the 2-hourly reply job.
- **Missed cycles** are shown in the report; there's no catch-up.
- **Away mode:** ingest only, and replies drop to the owner-batch tier.
- **Backups:** daily SQLite backups; the last 14 are kept.
- **Device and network:** one always-on personal device on the home connection; no VPN. The K3 fallback is
  another device on the same connection.

## 16. Data model
- **`transactions`:**
  - types add `refund`
  - adds `external_id` (unique index)
  - every AI row carries an `agent` tag (strategist, critic, analyst, studio roles, image, reply)
  - images are priced per image
- **`bet_events`:**
  - new types: `build_ordered`, `studio_round`, `studio_passed`, `shelved`, `refused` (doesn't change status),
    `draft_created`, `draft_approved`, `draft_rejected`, `published`, `publish_failed`, `unpublished`,
    `fee_charged`, `ad_result_entered`
  - `blocked` stays for guardrail stake refusals only
- **Bet IDs:** `c{cycle}-r{round}-{kind}{i}`, where kind is `b` (core), `a` (adaptation), `w` (wildcard) or `m` (memo).
- **`run_meta`:** thesis events, `approve_session`, `ingest_run`, `ingest_hold`, `overhead`, `lesson`, `reply_sent`, `reply_queued`.
- **New tables:** `research`, `metrics`.
- **Schemas:**
  - `StrategistResponse`: build orders, research requests, reread, notes, lessons, post plan
  - `BuildOrder`: line, format, kind, parent, niche, keywords, price, evidence, forecasts
  - `Memo` (scale bets)
  - `ResearchBrief`
  - `NicheThesis`
  - studio specs and scorecards
  - `ReplyDecision`
  - `Result.stop_reason`
- No real database exists yet, so none of this needs a data migration.

## 17. Fixes to existing code (built first, each with a failing test first)
1. **False insolvency** (`cycle.py:176`): the run only ends when the strategist's first call is refused for `WalletEmpty`.
2. **Refusals hiding bets** (`bets.py:31`): use the new `refused` event type.
3. **10-event window** (`state.py:54`): replaced by the daily view.
4. **Bet ID collisions** (`review.py`): new ID scheme.
5. **`queue.approve` calls `sys.exit`:** return an error instead.
6. **Truncation:** expose `stop_reason`; skip the repair retry when output hit `max_tokens`.

## 18. Setup, dates and gates

### 18.1 Dates
- **Setup weekend: Sat-Sun 10-11 Oct 2026.**
- **Kickoff: Sat 31 Oct 2026**, or the first Saturday after the gates pass. That puts cycles 61-90 on 30 Dec-28 Jan.
- **Re-target rule:** if kickoff slips past Sat 21 Nov, Line A doesn't target New Year-specific products
  in the judging window.

### 18.2 One-time owner setup
| # | Task | Time |
|---|---|---|
| 0 | Confirm employment terms allow a private online business | before any account |
| 1 | Etsy developer account + API key (**do first**; 24h-3 weeks) | 15 min |
| 2 | Etsy shop, ID check, Payoneer (within 30 days), policies, **opt out of Offsite Ads** | 60-90 min |
| 3 | Instagram Professional + Threads + Meta app; Threads Tester; token with post, reply and insight permissions | 30 min |
| 4 | Gumroad account + PKR payout | 20 min |
| 5 | Pinterest business account | 10 min |
| 6 | Anthropic + Google AI Studio keys; Drive API OAuth; Exa key; Jina free key → `.env` | 30 min |
| 7 | **Hard spend limits:** Anthropic workspace limit; Google budget alert plus a Gemini requests-per-day quota | 15 min |
| 8 | Install LibreOffice, Node.js (for impeccable), Vale and ffmpeg; `playwright install chromium` | 30 min |
| 9 | Create a GitHub Pages assets repo (public) | 10 min |
| 10 | Agent Reach, no-login backends only (review `install.md` first) | 15 min |
| 11 | Approve the design system and brand board | 20 min |

**Stated downside:** an Etsy suspension is tied to the owner's identity and is effectively permanent.

### 18.3 Pre-kickoff gates
| Gate | Pass | If it fails |
|---|---|---|
| K0 data check | Etsy `views` available for competitors, or the fallback is adopted | use the fallback |
| K1 market probe | ≥2 Line A niches meet the owner's thresholds (Etsy probe + last30days + Trends) | rethink product type |
| K2 blind check | the owner would pay $10 for ≥2 of 3 sandbox products next to bestsellers; the Sheets import works; the reviewer calibration matches the owner's judgement on the reference products | adjust the studio and rerun |
| K3 7-day unattended run (publishing off) | ≥6 of 7 cycles complete | another device on the same connection |
| K4 shop health + live smoke test | Etsy ID and Payoneer verified; 3 seed listings live 7 days without flags; one API draft listing activated then deactivated; one Threads post and **one reply** published and confirmed | fix first; fall back to Gumroad-first |
| K7 employment | permitted | don't proceed under the owner's name |

**In-run gates:**
- **K5, day 45:** traction threshold. Failing it means a reset ordered by the owner; passing it allows the top-up (§7.9).
- **K6, day 21:** Threads views per post. Failing it means 3 posts a week and effort shifted to Etsy.

## 19. Hypotheses (replace `docs/PREREGISTRATION.md`)
- **H1 Calibration:** the strategist's day-14 and day-30 view forecasts, scored against actual views.
- **H2 Cost of thinking:** AI plus image spend as a share of total deposits by day 90 (estimate ~55-64%).
- **H3 Sustainability:** the window score is greater than AI plus image spend over cycles 61-90.
  Confound: the window covers the New Year peak.
- **H4 Lines:** Line A vs Line B on window score per dollar and per owner-minute.
- **H5 Owner time:** mean logged session time of about 10 minutes a day or less.
- **H6 Studio:** the share of products shelved, the mean revision rounds, and whether studio scores predict
  favorites and sales.

## 20. Dry run and sandbox
- `scripts/dry_run.py`: N day-1 strategist calls, with measured cost per call.
- **Sandbox cycle** (`cycle run --sandbox`): one real cycle with publishing forced off on a throwaway DB.
  It runs the full studio on 3 products, renders images and video, and builds the preview. It feeds K2,
  and its **measured costs set the cadence and the caps.**
- `scripts/calibrate_reviewers.py`: the reviewers' scores against the owner's scores on the reference products.

## 21. Testing
1. §17 fixes first, each with a failing test.
2. **Offline module tests:**
   - research and ingest against saved responses
   - the publisher against mocked `httpx`
   - rendering real files locally (Playwright, XlsxWriter, LibreOffice; skipped when those tools are absent)
   - QA gates catching seeded defects: a broken formula, low contrast, an AI-tell phrase, an overused font,
     a missing tag
3. **Safety:**
   - unapproved items refused
   - hash mismatches refused
   - lint, limits, idempotency, the kill switch, token refresh, `--force` refusal
   - reply tiers, including URL stripping and "never" actions blocked
4. **Money:**
   - score, refunds, `external_id`, sanity hold, Gumroad mapping
   - bucket isolation, run cap, the scale-bet gate, the ship floor, the research share cap
5. **Privacy:** no names, emails or `@` reach the database or prompts from ingest fixtures.
6. No real network in tests. The sandbox, dry run, calibration and K0/K4 are the only real-call paths, run by hand.
7. The existing 91 tests stay green.

## 22. Build order
1. **K0:** Etsy `views` check
2. §17 fixes
3. Schemas, config, money model, buckets, run cap, score, ID scheme
4. Research subsystem + analyst + notebook
5. Discovery mode + thesis call + lessons ledger + allocation suggestion
6. Design system + HTML/PDF rendering (Playwright) + planners
7. XLSX building (XlsxWriter) + LibreOffice recalc and preview + Sheets copy link
8. Deterministic QA gates (Vale, impeccable, contrast, `pypdf`, listing lint)
9. Studio roles + iteration loop + vendored prompts + calibration script
10. Image pipeline + art director + listing video
11. Approve CLI + preview + pin CSV
12. Etsy publisher + ingest + privacy whitelist
13. Threads publisher + assets repo + insights + reply assistant
14. Gumroad ingest + mapping
15. Daily view, report (true P&L, score, burn rate, studio stats), scheduler, away mode, backups
16. Docs: README, RULES, KICKOFF_CHECKLIST, PREREGISTRATION
17. Sandbox cycle + dry run + calibration → set the caps and cadence

## 23. To verify during the build
- **K0:** Etsy `views` on other sellers' listings.
- **Etsy:** whether the API exposes the AI checkbox; fee ledger entries; refund data.
- **Threads:** reply and insight permissions in tester mode; link-click insight fields.
- **Agent Reach:** invocation from Python; free-tier limits on Windows.
- **Google:** the Drive copy-link flow and how faithfully formulas convert to Sheets.
- **Chromium:** internal PDF links are preserved and work in GoodNotes.
- **impeccable CLI:** behaviour on static HTML files on Windows; which rules apply to print.
- **Gumroad:** cover URLs are public; Workflow unlock conditions.
- **Gemini:** image model ID and price.
- **Vendored skills:** confirm each source's licence file is reproduced at the time of copying.

## 24. Out of scope (parked)
X/Twitter · AI video, avatars and personas · Reddit at runtime (last30days is used at build time only) ·
LinkedIn · Gumroad memberships · Medium/Substack · unsolicited engagement · ad-platform automation ·
Notion automation · the Pinterest API · Threads keyword search · Agent Reach cookie backends ·
BERTopic · AI image-scoring models · Langfuse.
