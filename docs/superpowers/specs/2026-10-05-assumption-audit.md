# Assumption audit: digital-products pivot

Date: 2026-10-05. Scope: the pivot design agreed in brainstorming (90 days, $100, Etsy + Gumroad from
Pakistan, AI-made XLSX/PDF templates with AI-composited images, Threads + Pinterest, daily ~2-min
human approval, judged on net revenue in the last 30 cycles).

Grades: A multiple direct recent sources, B one direct or several secondary, C analogy/seller blogs,
D expert opinion, F assertion. Importance/confidence: H/M/L. **Danger zone = importance H, confidence L or grade C-F.**

## Register

### Market
| # | We assume that... | Imp | Conf | Grade | Evidence / note |
|---|---|---|---|---|---|
| M1 | buyers still pay for niche templates even though free AI can make a basic one | H | M | B- | 2026 pricing study of 91 Etsy spreadsheet listings: market active, but simple templates commoditised (invoices median $2.99, 92% under $5); specialised ones hold ~$17 |
| M2 | Etsy search delivers buyers to a zero-review new shop within 30-45 days | **H** | **L** | **C** | seller blogs: first sale 2-4+ weeks, "about 15 listings", Etsy tests listings 60-90 days. Survivorship-biased sources |
| M3 | niche XLSX/PDF products at $9-17 find buyers | H | M | B- | same pricing study; niche-specific listings price higher |
| M4 | the mandatory AI disclosure doesn't crush conversion | M | L | D | unknown; mandatory anyway, so it's a fact to measure, not a choice |
| M5 | an automated, openly-AI brand account on Threads builds reach from zero in 90 days | M | L | D | algorithm guides only; no comparable case |
| M6 | Pinterest traffic lifts Etsy rank | M | M | C | Etsy SEO guides; Pinterest now labels AI images "AI modified" and lets users see fewer of them in art/home decor etc. |
| M7 | the free-to-paid Gumroad funnel converts 3-8% | M | L | C | creator self-reports |
| M8 | demand is stable across the run | M | M | B | **No: a November kickoff puts the judging window (cycles 61-90) in January, the annual peak for budget/planner templates.** Opportunity, but confounds H3 |
| M9 | PLR (private-label-rights) floods don't reach the niche segments we'd target | M | M | B- | pricing study shows the floods sit in generic categories |

### Capability
| # | We assume that... | Imp | Conf | Grade | Evidence / note |
|---|---|---|---|---|---|
| C1 | **the strategist can pick niches with real demand** | **H** | **L** | **F** | **It has no market data at all**: only training-era knowledge, no Etsy search, no competitor counts. The critic demands "demand evidence" the system can't supply |
| C2 | Haiku workers plus the renderer make products good enough to earn good reviews | **H** | **L** | **D** | untested; one bad early review is costly for a new shop |
| C3 | the formula engine plus allowlist catches broken spreadsheets | M | M | C | standard approach; Google Sheets import quirks unverified |
| C4 | AI backgrounds plus composited real previews look premium | M | M | C | common seller practice; untested in our pipeline |
| C5 | platform APIs behave as documented (Etsy create/upload/views, Threads tester tokens, Pinterest) | H | M | B | docs plus developer reports; Etsy listing `views` confirmed (updated daily) |
| C6 | Etsy's API exposes the AI-disclosure checkbox | L | L | F | fallback: 10-second human task |
| C7 | the 12-milestone build lands in about 3-4 weeks without publishing bugs | M | M | C | |
| C8 | lint plus critic plus human stop policy violations (trademarks, claims) | H | M | B | three independent layers |

### Execution
| # | We assume that... | Imp | Conf | Grade | Evidence / note |
|---|---|---|---|---|---|
| E1 | the Etsy shop opens and stays unsuspended from Pakistan | **H** | **M** | **C** | top triggers for PK sellers: missing the 30-day Payoneer verification deadline, "inconsistent network data" (IP/VPN changes), AI non-disclosure. **Single point of failure** |
| E2 | **the daily cycle actually runs every day** | **H** | **L** | **F** | **Not designed.** Nothing schedules `cycle run`; it needs the machine on, online and powered (load-shedding) |
| E3 | operator time stays about 2 min/day | M | L | D | ignores buyer messages, Etsy cases, ad and Gumroad tasks |
| E4 | buyer messages get answered | **H** | **L** | **F** | **Not designed.** Etsy has no messaging API; unanswered "file won't open" messages turn into cases and 1-star reviews |
| E5 | storage is safe | H | H | A | **Resolved 2026-10-05:** owner confirmed OneDrive cloud sync has been off for a while, so no sync conflicts and no upload to the employer tenant. Daily `ledger.db` backup still applies |
| E6 | the owner's employment terms allow a private online business | **H** | **?** | **F** | unverified; some public-sector conduct rules require permission for private trade |
| E7 | the $100 is the whole cash need | M | H | A | **No:** Payoneer charges a $29.95/yr fee for Pakistani accounts receiving under $6,000/yr (from Feb 2026), about 3% on withdrawals plus an FX markup; Etsy holds new-seller funds 45-90 days (reserve 25-75%) |
| E8 | token and image prices stay stable for 90 days | L | M | B | |
| E9 | the $0.75 thinking and $0.50 image caps suffice on build days | L | M | C | |
| E10 | the operator reviews carefully rather than rubber-stamping | M | L | D | approval fatigue undoes the main safety layer |
| E11 | tax on small Payoneer receipts is negligible at this scale | L | M | C | revisit if it becomes a business |
| E12 | products get spread sensibly across niches | M | L | D | nothing stops 20 products in 15 unrelated niches: no brand, no cross-sell |

## Danger zone (importance H, weak evidence)
C1 no market data, E2 nothing runs the cycle, E4 no buyer support, E6 employment terms, C2 product quality, M2 cold-start search traffic, E1 shop suspension.

## Pre-mortem: day 90, it failed

The shop drew about 40 views a week and made one sale. The strategist built 22 products across 14
niches, choosing them from training-era intuition (wedding budgets, ADHD planners, the most
saturated categories on Etsy) because it never saw a single search result or competitor count. The
critic kept approving "plausible" memos because it had no data either. Eleven cycles never ran: the
laptop was off, the power was out, or the operator was travelling, and nothing caught up. Early on,
a buyer's "the file won't open in Google Sheets" message went unanswered for a week, so a 1-star review
sat at the top of the shop. Week 6 brought a OneDrive "conflicted copy" of `ledger.db`. Thinking
plus images ate about 40% of the budget, and the Payoneer annual fee turned up in the books as a
surprise.

- Wrong assumption: that production was the bottleneck. **Demand discovery was.**
- Missed signal: the critic's repeated "no demand evidence" objections, approved anyway.
- What we were unwilling to consider: that agents without market data are guessing.
- Who would have caught it: any experienced Etsy seller ("do keyword research first, answer your messages").

New assumptions surfaced by the pre-mortem: E2, E4, E10, E12, M8.

## Kill-shot tests (pre-committed)

| Test | Settles | When | Pass | If it fails |
|---|---|---|---|---|
| K1 market-probe dry run | C1, M1, M3 | pre-kickoff | at least 2 candidate niches where the top listings created in the last 12 months average at least the agreed views/day and median price is $8 or more | rethink product type before staking anything |
| K2 blind product check | C2, C4 | sandbox cycle | the operator would pay $10 for at least 2 of 3 sandbox products, judged side by side with 3 competitor bestsellers | switch workers to Sonnet (about +$0.04/order) and rerun |
| K3 7-day unattended run | E2 | pre-kickoff, publishing off | at least 6 of 7 cycles complete on their own | move to an always-on device or small VPS |
| K4 shop health | E1 | pre-kickoff | Etsy ID and Payoneer verified; 3 seed listings live 7 days without flags | resolve with Etsy before kickoff; Gumroad-first fallback |
| K5 day-45 gate | M2 | cycle 45 | cumulative shop views at least the agreed number, or at least 1 sale | operator-ordered niche reset (written into the prereg) |
| K6 day-21 Threads gate | M5 | cycle 21 | median views/post at least the agreed number | cut to 3 posts/week; redirect the image budget to Pinterest/Etsy |
| K7 employment check | E6 | before any account is opened | permitted, or permission obtained | don't proceed under your own name until resolved |

Thresholds marked "agreed" are set by the owner in `docs/PREREGISTRATION.md`.

## Verdict: proceed with sequencing

Adjustments to fold into the spec:
1. **Market research for the strategist:** an Etsy keyword probe (public listing search: counts,
   price spread, views, favorites, listing age) requested via `research_requests`, run by code,
   results shown in the next state block. Web search runs inside analyst calls rather than
   strategist calls, so the strategist never sees raw external text (superseded in the spec,
   section 5.3); also Threads keyword search and Pinterest trends.
2. **Operations:** Windows Task Scheduler runs the cycle daily; missed cycles are logged; an
   `operator_away` mode lets cycles run cheap without drafting; daily `ledger.db` backup.
3. **Storage:** no move needed (OneDrive sync is off); daily `ledger.db` backup plus the git remote cover it.
4. **Buyer support:** the daily batch includes an Etsy inbox and Gumroad email check (target 24h response); count it in H5.
5. **Shop safety ramp:** 2 listings/day in week 1, then 5; Payoneer verification on the kickoff checklist; same machine and network, no VPN.
6. **Money:** report Payoneer/FX/withdrawal costs as business overhead next to the agent wallet (owner decides whether they're charged to it).
7. **Prereg:** note the January seasonality confound; add gates K5/K6 with pre-committed actions.
8. **Niche focus:** show the strategist a per-niche product rollup so scattering is visible to it and to the critic.

## Sources
- [Spreadsheet Template Market Index 2026](https://tabletemplates.com/research/)
- [Payoneer fees in Pakistan 2026](https://pakera.pk/payoneer-fees-pakistan-2026/)
- [Payoneer 3% withdrawal fee, Express Tribune](https://tribune.com.pk/story/2543768/payoneer-imposes-3-withdrawal-fee-on-pakistani-users-raising-concerns-among-freelancers)
- [Etsy listing views field discussion](https://github.com/etsy/open-api/discussions/1710)
- [Pinterest Gen AI labels](https://newsroom.pinterest.com/news/introducing-gen-ai-labels/)
- [Pinterest AI controls, TechCrunch](https://techcrunch.com/2025/04/30/pinterest-launches-new-tools-to-fight-ai-slop)
- [Etsy suspension rules 2026](https://www.shieldmyshop.com/blog/2026-03-26-etsy-suspension-2026-new-rules-what-changed)
- [Etsy payment holds for new sellers](https://www.insightagent.app/guides/etsy-payment-holds-new-sellers-guide)
