# Section source map

Which source feeds which part of the account plan. Nothing in the document may be written
without a source named here. The writing rules live in `output_standard.md`; both are mandatory.

## Source classes

Every block in `account_plan.json` carries a `source_class`. The class decides what happens
when evidence is missing, and it is the single most important field in the file.

| Class | Means | When there is nothing |
|---|---|---|
| `crm` | From the Aircover deal record's `crm` block | Leave blank, note the field in the appendix |
| `calls` | From an agent result or a transcript, with a meeting and a date | Blank, or a hypothesis under the validate list. Never a guess |
| `external` | From a fetched public source, with a name and a retrieval date | Omit the claim. An uncited external claim is a defect |
| `internal` | Only a human in the selling org knows this | Render an INPUT NEEDED block with the specific question |
| `derived` | Computed from metadata, for example attendee counts | Show the computation basis |

A block that mixes classes labels each claim, not the block. "They are consolidating on one
API platform (Q2 earnings call, retrieved 2026-08-22) and the platform team confirmed the
migration is funded (Kwan, 2026-07-14)" is two claims with two sources, and that is correct.

## Contents
1. Account resolution and header
2. Plan section 1, Executive summary and account snapshot
3. Plan section 2, Customer landscape and market insights
4. Plan section 3, Relationship and stakeholder mapping
5. Plan section 4, Existing opportunities, footprint and adoption
6. Plan section 5, License and contract management
7. Plan section 6, Cross functional GTM strategy
8. Plan section 7, Strategic next steps and mutual action plan
9. Plan section 8, Competitive landscape
10. Appendix, evidence coverage
11. Evidence rules that apply everywhere

---

## 1. Account resolution and header

| Field | Source |
|---|---|
| Account name | `crm.<source>.fields.account_name` where present, else the person's confirmed name. Not `prospect_org`, which is a domain |
| Domains in scope | Confirmed list of `prospect_org` values. Never auto merged |
| Opportunities in scope | Confirmed list of `deal_key` values (`prospect_org/deal_id`) |
| Account owner | `get_deal.customer_owner`, most common across in-scope deals. Conflicts between deals are shown, not resolved silently |
| Plan date, author | Runtime date and the person |

**The account is a set of deal_keys, not a deal.** Every downstream step loops that set. A
single `get_deal` call answers for one opportunity only, and an account plan built from one
opportunity is the failure this skill exists to prevent.

## 2. Plan section 1, Executive summary and account snapshot

| Block | Source | Notes |
|---|---|---|
| Account details: name, industry, revenue, HQ | `external` for industry, revenue, HQ. `crm` for name | Revenue from filings or IR only, never an aggregator estimate presented as fact |
| Strategic narrative: why this account matters | `internal`, informed by `crm` totals and `calls` | This is a judgment about the selling org's strategy. Draft it from the evidence, mark it for the person to confirm, never assert it as found |
| Current relationship health | `crm` for spend and open pipeline, `calls` for recent wins and sentiment, `derived` for meeting cadence | State the meeting cadence trend and the date of the most recent customer meeting |

Written last, after every other section exists. The summary asserts nothing the body does not
carry. Cap it at one page.

`snapshot_metrics` render as tiles on the At a glance page, not in this section. Each value is
a number, an amount or a date, 12 characters or fewer ("3", "$441,000", "12 days ago"). A
qualifier such as "1 with CRM data" belongs in relationship health, where it can be explained.

## 3. Plan section 2, Customer landscape and market insights

The highest fabrication risk in the document. The uploaded outline ships example challenges
(legacy SDLC, AI readiness, fragmented developer ecosystem, automation and velocity, AI and
API governance). **Those are a checklist to test, not content to paste.**

Every candidate challenge resolves to exactly one of three states:

1. **Evidenced.** A customer said it. Quote, speaker, title, meeting date.
2. **Externally supported.** A public source says it about this company. Source name, date.
3. **Hypothesis.** Neither. Goes under "Hypotheses to validate" with the discovery question
   that would confirm or kill it, and never appears anywhere else in the document.

A hypothesis that migrates into the executive summary as a finding is the defect this
section is designed to prevent.

| Block | Source | Notes |
|---|---|---|
| Business priorities, top 3 to 5 initiatives | `external` primary (earnings calls, annual report, investor day), `calls` corroborating | Quote the initiative in the company's own words where possible. Tie each to the executive who owns it if named |
| Challenges and unconsidered needs | `calls` primary (MEDDPICC Identify Pain, VoC pain points), `external` secondary | Three-state rule above. Cost of doing nothing only where the customer stated a consequence |
| KPIs and performance | `calls` (MEDDPICC Metrics) and `external` | A KPI the customer named beats an industry-standard KPI you assumed |
| Industry trends | `external` only | Must affect this company, not the sector generically. A trend with no line to this account is filler |
| SWOT strengths | `external`, `calls` | The customer's competitive moat, financial position, operational strengths |
| SWOT weaknesses | `external`, `calls` | The customer's business weaknesses, not their failure to buy from us. See the banned patterns in `output_standard.md` §4 |
| SWOT opportunities | `external` | External tailwinds, expansion targets, M&A |
| SWOT threats | `external` | Disruptors, regulation, market shifts |

SWOT is the customer's SWOT. Every quadrant entry carries a source tag. An empty quadrant is
better than a quadrant of plausible-sounding sector commentary.

## 4. Plan section 3, Relationship and stakeholder mapping

| Block | Source | Notes |
|---|---|---|
| Known stakeholders | `derived` from `customer_attendees` across every in-scope meeting, plus `calls` for title and role | Attendance comes from meeting metadata, never from agents. Agents see who spoke |
| Title and function | `calls` where stated on a call, else `external` from a public profile, else blank | Mark which |
| Role: champion, influencer, evaluator, blocker, detractor | `calls` only, with evidence | Default is "attendee, role unconfirmed". Do not promote a frequent attendee to champion. A detractor is someone evidenced favouring a competing option, including the internal build; carry them into plan section 8 |
| Last touched, meeting count, opportunities touched | `derived` | Per person, across the whole account |
| Who we do not know yet: role gaps | `derived` from MEDDPICC decision process plus Punchcard security, procurement, and legal dimensions | Roles the account requires where nobody has a name at all. Distinct from the row below, which needs a name. Each carries why it is needed stated as a consequence, opportunities at risk, a route in or "Not identified", and an owner |
| Named but unengaged | `calls` | People referenced in transcripts who never attended a meeting. Capture the name or the function, the meeting where they were mentioned, and what they were mentioned for. This is what the outline means by unknown personas |
| Coverage analysis | `derived` | Functions covered, seniority levels covered, single-threaded opportunities, opportunities with no customer-side attendee in the last 90 days |
| Engagement strategy, exec to exec | `internal` | INPUT NEEDED block. No transcript contains the selling org's exec pairing plan |
| Org chart | `internal` or `external` | Only draw reporting lines that were stated. An inferred hierarchy presented as an org chart is fabrication |

Two rules that catch most errors here:

- **A blocker must be evidenced blocking.** Someone who asked hard questions is an evaluator.
- **Unknown is a finding.** "Security sign-off is required and the reviewer has never been
  named" belongs in the document, in the unengaged table, with the meeting reference.

## 5. Plan section 4, Existing opportunities, footprint and adoption

| Block | Source | Notes |
|---|---|---|
| Open opportunities table | `crm` per deal_key: name, type, stage, amount, close date, owner | One row per opportunity. Totals must equal the sum of the rows |
| Associated initiative or use case | `calls` | Ties each opportunity to the business initiative from plan section 2 |
| Current footprint: products, tiers, seats, ARR, term | `crm` where the fields exist, else `internal` | Seat counts and tier names are rarely in the deal record. INPUT NEEDED rather than inference |
| Adoption and usage: active users, utilization, feature adoption | `internal` | **Aircover holds no product telemetry.** This never comes from calls. Ask for it, or leave the block as INPUT NEEDED with the specific metrics required |
| Organizational footprint: business units, teams, regions | `calls` (Close Plan Usage Footprint, VoC) plus `internal` | Distinguish units evidenced as using the product from units merely mentioned |
| Value and business impact delivered | `calls` (MEDDPICC Metrics, VoC outcomes) | Customer-stated outcomes only. A rep asserting value on a call is not customer evidence |
| Use cases in play | `calls`, constrained to `config.use_cases.vocabulary` | Write the selected values only. A use case counts as in play when a customer-side speaker describes doing it, never when a rep pitched it |
| Use cases available and not in play | `derived` | **Computed by the builder** by subtracting the selected values from the vocabulary. Never write this list by hand: a hand-written one omits whatever you did not think of, which is the expansion you were looking for |
| Expansion signals and whitespace | `calls` and `derived` | Teams appearing on calls with no entitlement, usage nearing limits if stated, adjacent use cases raised, units with zero engagement |

The whitespace read is the point of plan section 4. Say plainly which parts of the organization
have never appeared on a call.

## 6. Plan section 5, License and contract management

| Block | Source | Notes |
|---|---|---|
| Active licenses, consumption vs capacity | `internal` | Not in Aircover |
| Contract terms, key dates, TCV, non-standard clauses | `crm` where present, else `internal` | Renewal dates drive the plan, so ask for them explicitly rather than leaving the block empty |
| Historical spend, 2 to 3 year ARR lookback | `internal` or `crm` closed-won history | If closed-won opportunities are in scope, build the lookback from them and say so |

Mostly INPUT NEEDED on a first run. That is the correct output, not a failure.

## 7. Plan section 6, Cross functional GTM strategy

Entirely `internal`. ADR, customer education, CSE and PS, partner, post sales, and executive
strategy are decisions the selling team makes, and no transcript contains them.

Render each as a named INPUT NEEDED block with a prompt shaped by what the evidence shows.
Where the evidence points somewhere, say so as a recommendation and label it:

> Recommendation, for the account team to confirm: two of the four business units on the
> platform have never had a CS touchpoint (appendix, coverage table). A post sales plan for
> those two units is the largest uncovered surface in the account.

A recommendation the person can accept or reject beats an empty box, and beats a fabricated
plan by a wider margin still.

## 8. Plan section 7, Strategic next steps and mutual action plan

| Block | Source | Notes |
|---|---|---|
| Strategic next steps | `calls` (Deal Readiness CTA, Close Plan next steps) plus `derived` gaps | Each step names an owner where a call named one, and a target tied to a real event |
| Mutual action plan | Link or attach | **Do not rebuild the MAP here.** The `aircover-mutual-action-plan` skill owns that artifact. Summarize its state, one line per milestone, and link the file |
| Per-opportunity next step | `calls` | An opportunity with no dated next step is a finding, and it is listed |

## 9. Plan section 8, Competitive landscape

| Block | Source | Notes |
|---|---|---|
| Competitor presence | `calls` (MEDDPICC Competition, competitive agent) | A competitor is present only where a call, a document, or a cited source says so. Every row carries a date; an empty evidence column fails the checker |
| Share of wallet | `internal` or `external` | Never estimated from call frequency. Leave it blank rather than guessing; a value with no source fails the checker |
| Incumbent and internal build | `calls` | The in-house alternative is a competitor and is routinely missed. Ask for it if calls are silent |
| Differentiation | `calls` for what the customer responded to, `ask_documents` for the selling org's own positioning | Distinguish "we say this" from "the champion repeated this back" |
| Open competitive objections | `calls` | Absence of extracted objections does not mean objections are handled. Say which is which |

## 10. Appendix, evidence coverage

`derived`, and never omitted. Carries:

- Opportunities in scope, with the meeting count analyzed against the meeting count held
- Date range of evidence, and the date of the most recent customer meeting per opportunity
- Agents run, and agents configured but absent from the org
- Meetings held with no transcript, counted per opportunity
- External sources, each with title, publisher, date, and retrieval date
- Blocks left as INPUT NEEDED, listed so the account team can work the list

## 11. Evidence rules that apply everywhere

**Freshness bands.** Every call-sourced claim carries its meeting date, and a band from
`config.scope.freshness_bands_days`: current, aging, or stale. Stale evidence is included and
labeled, never silently dropped and never used to support a present-tense claim. "Torres owns
security sign-off" needs current evidence. "Torres owned security sign-off as of 2025-11" is
honest with stale evidence.

**Latest wins, per opportunity.** For a dimension measured across many meetings, take the most
recent meeting that produced evidence, and keep that meeting's text. Do this per opportunity
before rolling up to the account, or a live opportunity inherits a dead one's picture.

**Aggregation direction.** Plan sections 1, 2, 3, and 8 are account-wide and aggregate across every
opportunity. Plan sections 4 and 7 are per-opportunity and only roll up for totals. Never average a
qualification score across opportunities; a strong renewal does not qualify a weak expansion.

**Join on the entry title, never the positional key.** A property with `max_score: 0` is
unscored extraction, not a scored dimension.

**Customer voice only.** A rep pitching a value proposition on a call is not evidence the
customer holds that view. See `output_standard.md` §6 for the full rule.
