# HOWO Parts Sourcing & Stock Decision Engine — Codex Project Brief

## ROLE

You are helping me design and build a **HOWO Parts Sourcing & Stock Decision Engine**.

This is a real internal business tool, not a demo project.

The system should help me research HOWO Chinese truck spare parts that I am considering purchasing/importing into Nigeria and produce evidence-based recommendations about whether each part is worth stocking.

My current situation:

- I am preparing to enter the HOWO spare-parts business in Nigeria.
- I do not yet have my initial inventory.
- I already have a list of parts I am interested in.
- Some items have known part numbers.
- Some items only have names or descriptions.
- I need to research suppliers in China.
- I need to understand Nigerian-market demand and pricing.
- I ultimately want to use the output to decide what deserves my capital.

The system must optimize for **good purchasing decisions**, not merely collecting large amounts of information.

---

## CORE WORKFLOW

The first version should accept a list containing:

- Product name
- Part number, if known
- Optional notes
- Optional truck/model/engine information

For every part, the system should perform these stages:

1. Part identification
2. Technical research
3. Supplier research
4. China pricing analysis
5. Nigerian-market research
6. Economics analysis
7. Stock-opportunity scoring
8. Recommendation
9. Save structured results

The architecture should remain modular so that these stages can improve independently.

---

# 1. PART IDENTIFICATION

Before supplier research, establish what the part actually is.

Determine where evidence allows:

- standardized part name
- common alternative names
- Nigerian-market names
- OEM/part number
- cross-reference numbers
- relevant HOWO/SINOTRUK models
- engine/transmission/axle compatibility
- what the component does
- where it is located
- what system it belongs to
- typical failure symptoms
- whether it is a consumable, wear part, failure part or specialty part

### Part-number rule

If I provide a part number, treat the part number as the strongest initial identifier.

Search using combinations such as:

- exact part number
- part number + HOWO
- part number + SINOTRUK
- part number + component name

Cross-check sources rather than trusting the first result.

### Missing-part-number rule

If no part number is provided:

1. Research the supplied name.
2. Prioritize variants commonly associated with HOWO trucks operating in Nigeria.
3. Attempt to identify probable part number(s).
4. Do NOT silently assume one is correct.
5. Return a confidence score.
6. State what additional information is required to confirm fitment.

Possible verification information includes:

- truck model
- engine
- transmission
- axle
- chassis/VIN
- photograph
- dimensions
- mounting points
- teeth count
- connector layout
- original part number

Never invent a part number.

---

# 2. TECHNICAL INFORMATION

Produce a concise technical explanation suitable for someone learning the parts business.

Include:

- What is it?
- What does it do?
- Which larger system does it belong to?
- Where is it found?
- What happens when it fails?
- How important is it to vehicle operation?
- Which variants can easily be confused?
- What should a seller ask a customer before supplying it?

Keep this practical rather than turning each component into an engineering textbook.

---

# 3. SUPPLIER RESEARCH

Cross-examine multiple verified supplier platforms and credible sourcing channels from the beginning rather than prioritizing any single platform. The system should compare evidence across sources such as Alibaba, Made-in-China, Global Sources, direct Chinese manufacturers, independent supplier websites and verified SINOTRUK/HOWO distributors.

Design the architecture so additional supplier sources can be added easily over time.

Do not treat platform presence, ratings or verification badges as sufficient evidence on their own. Compare supplier information, product specifications, pricing, MOQ, operating history, transaction evidence, reviews and risk signals across multiple sources before making recommendations.

Potential future sources:

- Alibaba
- Made-in-China
- Global Sources
- direct Chinese manufacturers
- independent supplier websites
- verified SINOTRUK/HOWO distributors

For each supplier candidate, gather available fields such as:

- supplier/company name
- product URL
- product price/range
- MOQ
- location
- supplier type
- manufacturer vs trading company
- years operating
- verification status
- supplier rating
- reviews/review count
- transaction indicators
- response indicators
- lead time
- customization
- relevant certifications
- product quality claims
- contact method
- any visible risk signals

Do not equate high star ratings with trustworthiness.

---

# 4. SUPPLIER QUALITY SCORE

Create a deterministic scoring model rather than asking an LLM to arbitrarily assign a score.

Initial categories can include:

- verification
- operating history
- ratings/reviews
- transaction evidence
- price competitiveness
- MOQ suitability
- manufacturer status
- available company information
- product-specific evidence
- risk indicators

Weights should be stored in configuration rather than hard-coded throughout the application.

Return the best **three suppliers** unless fewer than three credible candidates exist.

If fewer than three strong suppliers are found, state that explicitly instead of filling the list with weak candidates.

---

# 5. CHINA PRICE ANALYSIS

For each part, calculate where possible:

- lowest credible observed price
- highest credible observed price
- median/typical price
- recommended purchasing range
- suspiciously low-price threshold
- MOQ implications
- major price differences caused by quality grades

Separate cheap price from good value.

Where products appear to have OEM, premium aftermarket and low-grade alternatives, preserve that distinction.

---

# 6. NIGERIAN MARKET RESEARCH

Research the Nigerian market for the part.

Potential signals include:

- Nigerian online stores
- Jiji
- dealer websites
- Google-indexed Nigerian sellers
- marketplaces
- Facebook/business listings where appropriate
- local pricing data
- my own internal enquiry/sales data when this becomes available

Estimate or classify:

- current Nigerian selling-price range
- apparent number of sellers
- market availability
- demand
- replacement frequency
- urgency when the component fails
- competition
- quality sensitivity
- counterfeit risk
- compatibility breadth
- whether buyers are likely to wait for sourcing
- whether the product appears fast-moving or slow-moving

Clearly distinguish:

- observed fact
- inferred estimate
- insufficient data

Do not pretend online search perfectly represents the Nigerian spare-parts market.

---

# 7. BUSINESS ECONOMICS

Eventually support:

- purchase price
- exchange rate
- shipping/freight
- customs/import expenses
- handling/logistics
- estimated landed cost
- Nigerian sale price
- gross profit
- gross margin
- capital required
- expected turnover

Do not confuse gross margin with inventory attractiveness.

A high-margin component that sells once every six months can be worse inventory than a lower-margin consumable that sells weekly.

---

# 8. STOCK OPPORTUNITY SCORE

Build a deterministic scoring engine.

Initial dimensions:

- demand
- replacement frequency
- margin potential
- competition
- capital efficiency
- compatibility breadth
- urgency
- supplier availability
- dead-stock risk

Weights must be configurable.

Example conceptual weighting:

Demand: 25%\
Margin potential: 20%\
Replacement frequency: 15%\
Competition: 10%\
Capital efficiency: 10%\
Compatibility breadth: 10%\
Urgency: 5%\
Supplier availability: 5%

These weights are starting assumptions, not permanent truth.

The system should make it easy to modify and calibrate them once I obtain actual Nigerian sales/enquiry data.

---

# 9. CAPITAL EFFICIENCY

Create a separate metric that captures the difference between profit per item and productivity of capital.

Consider relationships between:

- expected gross profit
- expected turnover
- capital required
- holding period

Do not invent precise turnover figures when evidence is weak.

If turnover is only classified qualitatively, represent uncertainty accordingly.

---

# 10. FINAL RECOMMENDATION

Return both a numerical score and an understandable recommendation.

Possible classifications:

### 8.0–10

STRONG STOCKING CANDIDATE

### 6.5–7.9

TEST WITH SMALL QUANTITY

### 5.0–6.4

SOURCE ON DEMAND FIRST

### Below 5

LOW-PRIORITY INVENTORY

The recommendation should include:

- reasoning
- biggest opportunity
- biggest risk
- missing information
- recommended next action
- suggested initial quantity only when available evidence supports one

---

# 11. DATA MODEL

Design the project so the input can initially come from CSV or Google Sheets.

Example fields:

- product\_id
- product\_name
- supplied\_part\_number
- notes
- status

Research results should be stored structurally rather than only as text reports.

Separate entities where useful:

- Parts
- Part Numbers
- Applications
- Suppliers
- Supplier Listings
- Nigeria Market Observations
- Research Runs
- Scores
- Recommendations

Prefer PostgreSQL/Supabase if a database becomes necessary, but do not introduce infrastructure before the first working version needs it.

---

# 12. ARCHITECTURE PRINCIPLE

The likely broader stack is:

Google Sheet / CSV\
↓\
n8n orchestration\
↓\
research components / APIs / AI\
↓\
structured validation\
↓\
deterministic scoring\
↓\
database\
↓\
report/dashboard

Use AI for:

- research
- interpretation
- normalization
- classification
- summarization
- identifying likely relationships

Use deterministic code for:

- calculations
- weighting
- thresholds
- validation rules
- deduplication
- currency arithmetic
- score computation

AI researches and classifies.

Code calculates.

---

# 13. CODEX'S ROLE

Your role is to help build code-heavy components that are awkward or inappropriate inside n8n.

Potential components include:

- normalized research schema
- scoring engine
- supplier comparison logic
- data validation
- duplicate detection
- part-number normalization
- APIs consumed by n8n
- scraping/research adapters where legally and technically appropriate
- test suite
- report generation
- dashboard
- database layer

Do not rewrite n8n in code simply because you can.

Use the simplest reliable architecture.

---

# 14. RELIABILITY & EVIDENCE

This tool may influence real purchasing decisions involving significant money.

Therefore:

- never fabricate suppliers
- never fabricate prices
- never invent part numbers
- never fabricate Nigerian demand
- attach sources/evidence where possible
- record research date
- represent uncertainty
- preserve conflicting evidence
- include confidence scores
- flag stale data
- distinguish factual observations from AI inference

A confident wrong answer is worse than an incomplete answer.

---

# 15. BUILD STRATEGY

Do NOT attempt to build the complete platform immediately.

Work in phases.

## Phase 1

Take ONE known part with a known part number and generate one trustworthy research report manually/semi-automatically.

## Phase 2

Formalize the output schema and deterministic scoring model.

## Phase 3

Automate one part end-to-end.

## Phase 4

Support batches from Sheets/CSV.

## Phase 5

Add missing-part-number research and Nigerian-market inference.

## Phase 6

Add database/history.

## Phase 7

Add dashboard and comparison tools.

## Phase 8

Calibrate scores using real enquiry, sales and inventory-turnover data.

## Phase 9

Turn the accumulated, reviewed evidence into a market-specific visual parts
identification and sourcing assistant.

At every phase, test whether the result is actually useful before adding complexity.

---

# 16. MARKET-SPECIFIC VISUAL IDENTIFICATION & SOURCING ASSISTANT

The capture and decision engine should ultimately support a customer or market
user submitting one or more photographs of a truck part and receiving cautious,
ranked identification candidates grounded in the business's accumulated data.

The assistant should combine:

- OCR of labels, cast markings and part numbers;
- visual features such as shape, ports, connectors, mounting points, teeth and
  dimensions;
- canonical product records, aliases and Nigerian-market names;
- confirmed part-number and cross-reference relationships;
- vehicle, engine, transmission and axle fitment evidence;
- reviewed historical captures and photographs;
- dated market-supplier and availability observations;
- external web research only when internal evidence is insufficient.

The internal database is the first retrieval source. Web findings are candidate
evidence and must not become trusted product, fitment or supplier facts without
provenance, validation and the appropriate review.

Results should provide ranked candidates, confidence, supporting and conflicting
evidence, and the next photograph, marking or measurement needed to resolve
ambiguity. The system must be allowed to say that an image is insufficient;
visually similar parts can differ internally or by application.

Statements such as "Ebube has it" are dated supplier-availability observations,
not permanent inventory facts. Store the supplier, product or candidate, source,
observation date, reporter, confidence and any expiry or reconfirmation status.

Do not begin with custom model training. Start with multimodal extraction, OCR,
retrieval and deterministic matching. Reviewed confirmations and rejections should
be retained as a labelled dataset so a specialized visual model can be evaluated
later when enough representative examples exist.

---

# DEFINITION OF SUCCESS

The project succeeds when I can submit a part and receive enough reliable, structured evidence to answer:

1. What exactly is this part?
2. Which version applies to my intended Nigerian market?
3. Where can I credibly source it?
4. What should I expect to pay?
5. What can it potentially sell for in Nigeria?
6. How risky is the inventory?
7. How productive is the capital?
8. Should I stock it, test a small quantity, source it on demand, or ignore it?

The extended product direction also succeeds when a user can submit photographs
and receive evidence-backed candidate identities, practical clarification steps,
and fresh, appropriately qualified market-supplier leads without the system
pretending that appearance or historical availability proves a match.

When beginning implementation, first inspect the existing project/repository.

If no implementation exists yet, propose the smallest Phase 1 architecture and build from there.

Do not jump ahead to a large production architecture merely because this document describes the eventual vision.
