# Resource research: tools and methods for each stage of swarm50

Purpose: for every stage of the pivot design, what we're trying to do, what's available (open source
or free tier), and whether we adopt it, borrow from it, or reject it. "Adopt" means it becomes part of
the system, "borrow" means we reuse its ideas or data but not its code, and "reject" means we
considered it and don't use it.

## Stage 1: Line A market and niche research
**Goal:** find Etsy niches with recent demand and beatable competition, cheaply and in code.

| Resource | Verdict | Why |
|---|---|---|
| Etsy Open API v3 `findAllListingsActive` + `getShop` | **Adopt** (already in the spec) | official; listing views/favorites/age; shop sold counts as fallback (K0) |
| [etsy-python-sdk](https://github.com/amitray007/etsy-python-sdk) (amitray007) | **Adopt if it passes evaluation** | maintained (updated Aug 2026); OAuth2 with automatic token refresh; full v3 coverage. Fallback: a thin `httpx` client |
| [teomro/etsy](https://github.com/teomro/etsy) `scan_niche` | **Borrow** the demand-velocity and saturation logic | MIT, official API; tiny project (3 commits), so we port ideas rather than depend on it |
| Google Trends MCP ([trendzeist-mcp](https://pypi.org/project/trendzeist-mcp/)) | **Planning time only** | free, but unofficial and rate-limited; good for checking seasonality before kickoff, too flaky for runtime |
| eRank free plan | Optional, by hand | no API; the owner can sanity-check keywords |
| Apify Etsy scrapers | **Reject** | scraping Etsy puts the shop at risk |

## Stage 2: Line B audience and pain-point research
**Goal:** find what a niche struggles with, in its own words, from public web sources.

| Resource | Verdict | Why |
|---|---|---|
| [Agent Reach](https://github.com/Panniantong/agent-reach), no-login backends | **Adopt** | MIT, 91k stars. Exa search + Jina Reader, fetched by our code |
| Exa free tier | **Adopt** | $10/month of credits (~1,400 searches/month) plus $20 at signup; 5 queries/second |
| Jina Reader | **Adopt** with a free key | 20 requests/minute with no key; 500/minute and 10M free tokens with a free key |
| [BERTopic](https://bertopic.com/what-is-bertopic/) topic modelling | **Reject** for v1 | built for thousands of documents and needs heavy ML dependencies; we read tens of pages, so the analyst model is enough |
| Reddit via OpenCLI (Agent Reach's desktop backend), read-only | **Adopt** (v3.1, owner decision) | throwaway account in a dedicated Chrome profile; suspension and the user-agreement breach are owner-accepted risks; soft failure, never on the critical path |
| Agent Reach cookie backends (X, XiaoHongShu) | **Reject** | the project warns of account bans |

## Stage 3: Strategy, memory and allocation
**Goal:** a strategist that stays coherent over 90 days and learns from results.

| Finding / resource | Verdict | What changes |
|---|---|---|
| Long-horizon business benchmarks ([Vending-Bench](https://www.mindstudio.ai/blog/what-is-vending-bench-ai-business-benchmark), [E-Commerce Bench](https://arxiv.org/html/2608.30730)): agents lose coherence over long runs and fail to turn experience into better decisions; the best performers adapt over repeated interactions | **Adopt the lesson** | add a **lessons ledger**: the strategist records explicit lessons with evidence ids; the daily view shows active lessons; a weekly review prunes them. This complements `notes_to_self` |
| Thompson sampling (bandit allocation) | **Adopt, in ~20 lines of stdlib** (`random.betavariate`) | code computes a per-niche "where to build next" suggestion from favorite and sale rates and shows it in the daily view. The strategist may override it, with a reason |
| Forecast calibration (H1) | **Adopt, in plain code** | day-14/30 view forecasts scored with log error; no library needed |

## Stage 4: Making products
**Goal:** functional, well-designed XLSX and PDF products, plus listing imagery, with as little layout
invention by the AI as possible.

| Resource | Verdict | Why / what changes |
|---|---|---|
| [XlsxWriter](https://xlsxwriter.com/xlsxwriter-vs-openpyxl/) | **Adopt** (replaces openpyxl for writing) | the strongest library for *generating* workbooks: charts, validation, conditional formats, freeze panes, print setup |
| LibreOffice headless | **Adopt** (replaces the `formulas`/`pycel` idea) | genuinely recalculates every formula and renders sheets to PDF/PNG for the vision review; free; runs on Windows. The pattern is the same one Anthropic's xlsx skill uses (`recalc.py`) |
| Google Drive API (Sheets copy link) | **Adopt** (already in the spec) | bestselling templates ship in both Excel and Google Sheets |
| HTML/CSS templates (Jinja2) + **Playwright Chromium** print-to-PDF | **Adopt** (replaces fpdf2) | full modern CSS; `@page` page sizes; models write HTML/CSS far better than fpdf2 layout code; **internal links** make **hyperlinked digital planners** (GoodNotes) possible, a large Etsy category |
| The same Playwright engine for listing images, pins and Threads images | **Adopt** (replaces Pillow composition) | one design system everywhere; CSS 3D transforms give **device mockups** (the real product on a tablet or laptop) over Gemini backgrounds |
| [WeasyPrint](https://templated.io/blog/generate-pdfs-in-python-with-libraries/), Typst, ReportLab | **Reject** | WeasyPrint needs GTK on Windows; Typst is excellent but models know HTML/CSS far better; ReportLab means coordinate drawing |
| Python mockup generators | **Reject** | Playwright + CSS covers it within our own design system |
| Code-generated listing video (ffmpeg page-flip slideshow) | **Recommend** (owner decision) | Etsy rewards listing video in its quality score; this is not AI video, just the real pages animated |

**Buyer expectations found** (encode in product briefs):
- **Spreadsheets:** a dashboard with charts, automatic formulas, sample data, an instructions tab, and both Excel and Google Sheets versions.
- **Printables:** separate A4 and US Letter PDFs (never "scale to fit"); at least 0.5" margins on full pages; Monday- and Sunday-start versions for planners.

## Stage 5: Quality control and anti-slop
**Goal:** nothing generic, broken or ugly reaches the owner, let alone a buyer.

| Resource | Verdict | Why / what changes |
|---|---|---|
| [Vale](https://github.com/vale-cli/vale) + [vale-ai-tells](https://github.com/tbhb/vale-ai-tells) / [slop-linter](https://github.com/thrash-d/slop-linter) rules | **Adopt** | deterministic, free linting of all prose (product text, listings, posts) for AI tells, before any AI review. Cheap, and it can't be talked out of its rules |
| Rubric-based AI judges (the G-Eval pattern) | **Adopt** the pattern in our reviewer prompts | written criteria, a score per criterion, thresholds |
| [promptfoo](https://deepeval.com/blog/top-5-llm-evaluation-frameworks) / DeepEval | **Borrow the idea**; a ~50-line `scripts/calibrate_reviewers.py` is enough | calibrate the design and content reviewers against good and bad reference examples before kickoff |
| WCAG contrast check | **Adopt** (a 10-line formula, stdlib) | every palette and text-on-image pair must pass AA |
| `pypdf` print checks | **Adopt** | page size, embedded fonts, minimum font size, page count |
| LAION aesthetic predictor / image-quality models | **Reject** | heavy ML dependencies; [documented biases](https://arxiv.org/html/2601.09896v1); Claude vision with a rubric is enough |
| [anthropics/skills](https://github.com/anthropics/skills) | **Borrow** for building the design system | the example skills (canvas-design, theme-factory, brand-guidelines) are Apache 2.0, so themes and principles can be reused. The document skills (xlsx/pdf) are source-available, **not** open source: reference only, never copied into the repo |
| Lucide / Tabler icons; Google Fonts | **Adopt** | ISC/MIT icons; OFL fonts, bundled locally |

## Stage 6: Listings and Etsy SEO
**Goal:** listings that match search intent and earn clicks.

**Findings** ([Etsy SEO 2026](https://printify.com/blog/etsy-seo-how-to-get-noticed-on-etsy/), [listing photos](https://www.listifyai.net/blog/etsy-listing-photos-size-requirements-2026)):
- **Titles:** the first 40 characters are all mobile shoppers see. Use a natural phrase under 15 words, with no pipes or bullet separators.
- **Tags and attributes:** use all 13 tags as multi-word buyer phrases, choose the deepest category, and fill every attribute.
- **Listing quality score** is driven by click-through rate, favorite rate, add-to-cart rate and conversion, so **images drive ranking**.
- **Photos:** use 2000×2000 px images.
  - Listings with 7–10 photos convert about **2×** better than those with 1–3; Etsy now allows 20.
  - Lifestyle mockups get **35–50% more clicks** than flat images.
  - One reported switch from screenshots to mockups doubled conversion (1.8% → 3.6%).

**What changes:**
- **Images per product:** about **8–10** listing images, built from the Playwright templates and AI backgrounds.
- **Listing lint** enforces:
  - the title rules
  - all 13 tags
  - every attribute filled
  - no trademarks

## Stage 7: Social (Threads)
**Findings** ([Threads strategy, 10K+ posts analysed](https://www.teract.ai/resources/threads-content-strategy-2026), [algorithm](https://posteverywhere.ai/blog/how-the-threads-algorithm-works)):
- **2–3 posts a day is the ceiling.** Posting more triggers spam detection.
- **Posts with images get about 3.2× the engagement** of text-only posts.
- **Freshness and replies weigh heavily.** Saves and shares count for more than likes.

**What changes:**
- The spec's "text-first" stance is reversed. Line B posts need images, which needs **public image hosting**: a free public **GitHub Pages** assets repo, written by the publisher (or Gumroad cover URLs, if they turn out to be public).
- The daily post cap is set to **3**.
- The reply assistant is in.
- No engagement bait.

## Stage 8: The Gumroad funnel
**Finding** ([Gumroad workflows](https://insightraider.com/en/answers/how-to-build-an-email-list-with-gumroad)): Workflows (automated email sequences, e.g. free → paid upgrade) are free, but **Gumroad only allows sending emails after $100 earned and one payout**.

**What changes:**
- The free lead magnet collects emails from day 1.
- An agent-drafted 3–5 email sequence is set up by the owner (no API) once the first payout happens.
- Until then, the paid upgrade is linked from inside the lead magnet itself.

## Stage 9: Publishing and platform clients
| Resource | Verdict |
|---|---|
| Etsy | `etsy-python-sdk` (if it passes evaluation) or `httpx` |
| Threads | thin `httpx` client (post, replies, insights) |
| Gumroad | `httpx` (`GET /v2/sales`) |
| Pinterest | **bulk CSV** with columns Title, Media URL, Pinterest board, Thumbnail, Description, Link, Publish date (`YYYY-MM-DD HH:MM`), Keywords; ≤200 pins per file; publish dates spread across the week so one weekly upload posts daily ([format](https://pinsmachine.com/blog/pinterest-csv-bulk-upload-the-fastest-way-to-pin-100-images-in-one-shot)) |

## Stage 10: Efficiency and cost
| Resource | Verdict |
|---|---|
| Anthropic prompt caching | **Adopt.** The design system, rubrics and role prompts are long and repeated; cached reads cost 10% of normal input. `metered_call` already supports `cache=True` |
| Anthropic Batch API (50% off) | **Later.** Non-urgent studio work could run as overnight batches; the code path exists but is unverified, so turn it on after the sandbox |
| [Langfuse](https://langfuse.com/) tracing | **Reject** for v1. The ledger, event logs and HTML report already trace every call and cost; Langfuse adds a Docker service for little gain |

## Part 2: community skills and repos

How they get used, given that our runtime agents are single prompts, not Claude Code sessions:
- **Runtime (vendor):** we copy the relevant rules and rubrics into our role prompts (`prompts/*.md`),
  keeping each project's licence and attribution in `prompts/vendor/LICENSES.md`. Every project below
  is MIT or Apache 2.0, which allows this. Prompt caching makes the long prompts cheap.
- **Build time:** I use them while building the design system, templates and rubrics, and for
  pre-kickoff niche research.

| Repo | Licence / stars | What it gives us | Use |
|---|---|---|---|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache 2.0, ~77k | **61 deterministic detector rules for AI-slop design** that run on HTML files with a local browser, **no AI and no API key**, with JSON output (overused fonts like Inter, purple gradients, grey text on colour, untinted pure black, cramped padding, line length, skipped heading levels, overflow) | **Adopt as a QA gate:** our products are HTML rendered by Chromium, so the detector runs on every product and image template. Web-only rules (touch targets, easing) are filtered out. Also its design vocabulary (polish, distill, bolder, quieter) for the builder's revision instructions |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (installed) | MIT | anti-default discipline (no AI-purple, no Inter + slate, no three equal cards); a one-line "design read" before designing; variance/density dials; `imagegen-frontend-web` image-direction rules; minimalist/soft/brutalist style variants | **Vendor** into the product-lead and builder prompts: a design read per product, dials set by niche, anti-defaults. Image-direction rules into the art director |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (installed) | MIT | **datasets**: colour palettes by product type, font pairings (with Google Fonts licences), typography scales, chart guidance, style catalogue (~3,000 rows, with provenance) | **Adopt the data** as the seed of our design system, **filtered by impeccable/taste anti-defaults** (e.g. drop Inter and Poppins pairings) |
| [blader/humanizer](https://github.com/blader/humanizer) | MIT, ~54k | 26 AI-writing patterns in 6 groups, with before/after examples, from Wikipedia's "Signs of AI writing"; a final "obviously AI" audit pass | **Vendor** into the content-editor rubric and the copy prompts |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | MIT, ~2.8k | phrase, structure and sentence-level AI tells | **Vendor** alongside humanizer; it overlaps with the Vale rules, which enforce the deterministic part |
| [sergebulaev/threads-skills](https://github.com/sergebulaev/threads-skills) | MIT, 52 stars, **exact fit** | Threads post writer with **13 hook formulas mapped to goals** (replies, reposts, likes, quotes); reply drafter; Threads-specific humanizer scored on 2026 AI vocabulary; content planner; profile optimizer | **Vendor** into the social-post worker, the reply assistant and the profile setup. (Its Publora publishing is not used; we have our own publisher) |
| [sergebulaev/x-skills](https://github.com/sergebulaev/x-skills) | MIT | hook extraction from viral posts; reply drafting | Borrow reply-drafting patterns |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | ~39k | researches Reddit, X, YouTube, HN, GitHub and the web over the last 30 days, ranked by engagement | **Build time and pre-kickoff only** (K1 niche research, Line B candidate niches). Not at runtime, because Reddit bans commercial API use |
| [kudrykv/latex-yearly-planner](https://github.com/rahulpnath/latex-yearly-planner) family, [mohanrex/digital-planner-generator](https://github.com/mohanrex/digital-planner-generator), [georgiastuart/planner-generator-python](https://github.com/georgiastuart/planner-generator-python) | open source | proven **hyperlinked planner** structures (year → month → week → day tabs, index pages, back-links) for GoodNotes and e-ink | **Borrow** the navigation patterns for our HTML planner templates |
| [nexscope-ai/eCommerce-Skills](https://github.com/nexscope-ai/eCommerce-Skills) `etsy-digital-products` | open source | digital-product checklist: files, licences, delivery setup, launch checklist | **Borrow** the checklists into the product brief and listing lint |
| [silennsong/etsy-listing-helper](https://github.com/silennsong/etsy-listing-helper) | open source | listing structure: title ≤140, 13 tags, official category path, attributes, photo alt text | **Borrow**: alt text and category-path handling for the listing worker |
| Nano Banana prompt libraries ([YouMind-OpenLab](https://github.com/YouMind-OpenLab/awesome-nano-banana-pro-prompts), [antifragile0](https://github.com/antifragile0/Awesome-Nano-Banana-Prompts)) | open source | thousands of tested Gemini image prompts with previews; craft rules (name materials, not adjectives; pin framing with lens terms like "overhead flat lay" or "85mm"; fix the aspect ratio) | **Borrow** the craft rules and 10-20 product/flat-lay recipes into the art director's prompt |
| Analyst-grade spreadsheet skill notes ([gist](https://gist.github.com/gregkonush/e2b64bd48a7c20fd00483be033a6eddc), [collection](https://github.com/bighardperson/computer-science-skills-collection/blob/main/skills/spreadsheets/SKILL.md)) | open | dashboard first, then assumptions, then detail; helper cells instead of monster formulas; distinct header and derived-cell styles | **Borrow** into the spreadsheet builder and the design system |
| [OthmanAdi/planning-with-files](https://github.com/othmanadi/planning-with-files) | open source | memory kept on disk and re-injected every turn | Already covered by our event log and daily view; the lessons ledger borrows its "findings" idea |

**Rejected:** MengTo/skills (157 skills, web/interactive only, nothing for print); paid PromptBase
"Etsy niche finder" skills (prompts without data); `jiji262/claude-design-skill` (adapted from an
internal Anthropic prompt, so its licensing is unclear).

## New owner setup items (all free)
- LibreOffice
- the Playwright Chromium download (one command)
- Vale
- a GitHub Pages assets repo
- an Exa API key
- a Jina free key
- Node.js, to run the impeccable detector CLI (`npx impeccable`)
