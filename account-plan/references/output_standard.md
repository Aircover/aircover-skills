# Output standard

How every written block must read. The sourcing rules live in `section_source_map.md`; this
file governs voice, structure, length, and the checks before you build. Both are mandatory.

An account plan is a plan, not a research report. The test for every block is whether the
account team can act on it or decide from it. "Here is what we know" fails. "Here is what we
know, what it means for the account, and what we do next" passes.

The second test is provenance. A reader must be able to tell, for any sentence, whether it
came from a call, from the CRM, from a public source, or from the account team's own judgment.
An account plan that blurs those four is worse than a short one that keeps them apart.

## Contents
1. The claim shape
2. Provenance tagging
3. Word budgets
4. Banned language and banned patterns
5. Hypotheses, recommendations, and INPUT NEEDED
6. Quotes and evidence
7. Owners and dates
8. Blocks that must never be empty
9. Final consistency pass

---

## 1. The claim shape

Plan section 2 and plan section 8 blocks state a claim, its evidence, and its implication:

**Claim** -> **Evidence with source and date** -> **So what for this account**

A claim with evidence and no implication is a research note. An implication with no evidence
is an opinion. Both are common first-pass failures.

Action-oriented blocks (plan section 3 engagement strategy, plan section 6, plan section 7
next steps) use
the fuller shape:

**Current status** -> **Evidence** -> **Gap** -> **Next action and owner** -> **What done looks like**

## 2. Provenance tagging

Every block in `account_plan.json` carries `source_class`. Every individual claim inside a
block carries its own attribution in the text, in one of these shapes:

| Class | Written as |
|---|---|
| `calls` | (Kwan, VP Platform, 2026-07-14) |
| `crm` | (CRM) |
| `external` | (Q2 2026 earnings call, retrieved 2026-08-22) |
| `internal` | (account team) |
| `derived` | (meeting metadata, 34 meetings) |

Keep tags short and inline. Do not build a footnote apparatus; this is a working document.

The engine renders a small grey source line under a block when `source` is set, so a block
drawn wholly from one place does not need per-sentence tags. Mixed blocks always do.

## 3. Word budgets

| Block | Target |
|---|---|
| Executive summary, whole section | 250 to 400 words, one page maximum |
| Strategic narrative | 60 to 100 |
| Relationship health | 60 to 100 |
| Each business priority | 40 to 70 |
| Each challenge or unconsidered need | 50 to 90, including the evidence and the so-what |
| Each SWOT entry | 15 to 40, one claim each |
| Stakeholder table notes | 25 or fewer per person |
| Each opportunity narrative | 60 to 100 |
| Value and business impact | 80 to 140 |
| Expansion signals | 80 to 140 |
| Each competitor entry | 50 to 90 |
| Differentiation | 80 to 140 |
| Each next step | 30 to 60 |

Over budget is a real defect, and so is trimming by deletion. When the document runs long, cut
words inside blocks and cut unevidenced ones. Never delete an evidenced customer finding to save a
page: a challenge a customer stated, or a SWOT weakness they admitted about their own business, is
the scarcest material in the document and the hardest to reacquire. If length still fails after
every block is inside budget, that is a scope decision to take to the person, not a quiet deletion.

Over budget is a real defect. This document is read by an AE before a QBR and by a manager
before an exec meeting, and length is what stops it being read. Where detail must survive,
push it to the appendix, which carries no budget.

## 3a. Prose or bullets

Two shapes, and the choice is not stylistic. Set `text` for prose, `points` for bullets, or both
where a one or two sentence lead is followed by an enumeration.

**Prose** for blocks that make an argument, where the reasoning is the content and fragmenting it
destroys the point: the strategic narrative, relationship health, the stakeholder coverage read,
each plan section 2 challenge, and the GTM priority ranking.

**Bullets** for blocks that are already lists wearing prose clothing. If a block is a sequence of
independent findings joined by "and" or by semicolons, it is a list and should be one: expansion
signals, organizational footprint, value and business impact delivered, differentiation, open
objections, technical blockers.

The test: if reordering two sentences changes nothing, they are list items. If it breaks the
argument, they are prose.

**Bullets do not relax provenance, and this is where the format usually fails.** A bullet invites
a fragment, and a fragment is where the date and the implication get dropped. Every bullet still
carries the claim shape from section 1: the claim, its evidence with a source and a date, and the
so-what. One bullet is one claim with one date. A bullet that reads "41 discovery fields" has lost
both the speaker and the point; "Reps complete 41 discovery fields by hand, which Emily
Schlittenhart said makes discovery feel like an interrogation (2026-06-18), so field completion is
the most measurable before-and-after available" is a finding.

## 4. Banned language and banned patterns

**Scoring machinery never appears.** Never write "scored 0", "scored 2 of 3", "max_score",
"the agent found", "Not Found" as a literal value, property names, or template ids. Translate:

| Instead of | Write |
|---|---|
| "Economic Buyer scored 0 across the account" | "No budget holder has appeared on any call in any of the three opportunities" |
| "Metrics scored 1" | "The customer has not attached a number to the outcome" |
| "Competition scored 3 on the renewal" | "The champion named the incumbent and the internal build option unprompted" |

**Banned patterns, each of which quietly turns the plan into fiction:**

- **Template text carried forward.** The uploaded outline's examples (the payment products
  board mandate, PSD2, the CIO integration KPI, Kong, MuleSoft, Accenture, the named people)
  are illustrative. If any of them reaches the finished document without this account's own
  evidence behind it, the run has failed.
- **Seller-centric SWOT.** "They have not standardized on our platform" is not a customer
  weakness. A weakness is a weakness of their business against their competitors. Sweep the
  weakness quadrant for the word "we", "us", and the vendor name.
- **Sector filler.** "AI adoption is accelerating across financial services" says nothing
  about this account. Every trend entry names the mechanism by which it hits this company.
- **Hypothesis laundering.** A hypothesis in plan section 2 that reappears as a finding in plan
  section 1 or plan section 8. Check by name before building.
- **Roster counted as attendance.** The deal record's contact list and the set of people who
  actually appeared on calls are different numbers, and the first is always the larger. Writing
  "20 named contacts" next to "19 calls" implies 20 people attended when 17 did. Count distinct
  attendees from meeting metadata, state the roster separately, and treat contacts on the record
  who never attended as a coverage finding rather than as coverage. Record all six counts in
  `coverage.attendance` so they can be reconciled: the subtotals must sum to the total, and a plan
  claiming the two sets match cannot also record someone who attended without being on the roster.
- **Unresolved display names counted as people.** Attendee lists contain entries like a raw email
  or a device name that resolve to nobody. They inflate the distinct count and belong in the
  appendix as unidentified, not in the stakeholder table.
- **Attendance as advocacy.** Frequency of attendance is not championship, and headcount on
  calls is not multithreading.
- **Rep statements as customer voice.** See §6 below.
- **Present tense on stale evidence.** See the freshness rule in the source map.

## 5. Hypotheses, recommendations, and INPUT NEEDED

Three distinct things, three distinct renderings. Do not blur them.

**Hypothesis.** Something plausible that no evidence supports yet. Lives only in the
"Hypotheses to validate" list, always with the question that would resolve it:

> Fragmented tooling across the four engineering groups. Not evidenced. Ask Kwan which teams
> outside Platform own their own API tooling budget.

**Recommendation.** A judgment the plan proposes, drawn from evidence, for the account team to
accept or reject. Labeled as a recommendation, with the evidence attached.

**INPUT NEEDED.** A fact that exists but that only a human in the selling org holds. Render
the specific question, not a blank:

> INPUT NEEDED: seat count and tier by business unit at the last true-up, and the renewal
> date for the original subscription.

Never fill an INPUT NEEDED block to make the document look complete. A finished-looking
account plan with three invented seat counts is the worst possible output of this skill.

## 5a. Freshness words are computed, not chosen

`current`, `aging` and `stale` are defined by `config.scope.freshness_bands_days`, which ships at
90 and 270 days. They are not synonyms for old. Compute the day count from the plan date before
writing any of the three words, because reaching for "stale" to mean "a while ago" contradicts the
appendix and the colour coding the engine applies to the same date. A contact last seen 248 days
ago is aging, and calling them stale overstates the decay by a whole band.

Every call-sourced claim carries its meeting date. Where the band is the point being made, name
the band and the date together: "one meeting each on 2026-05-06, now aging".

## 6. Quotes and evidence

- Verbatim, with speaker name, title where known, and meeting date. No paraphrase inside
  quotation marks.
- Customer-side speakers only. A quote from the AE, the SE, or anyone on the vendor domain is
  not customer evidence, and using one is the single most common contamination in call-sourced
  analysis.
- Trim to the load-bearing clause. Long quotes hide the point.
- Never merge two speakers or two meetings into one quote.
- Where the strongest evidence is stale, quote it and date it rather than reaching for a
  weaker current one, but do not write the claim in the present tense.

## 7. Owners and dates

Assign an owner only where a call named that person for that work, or the person supplies one.
Never generate a calendar date nobody committed to. Where the owner is genuinely unknown:

> Owner: not named. Naming the owner is the first action.

Relative targets tied to a real event are fine, because they are recommendations rather than
recorded commitments: "before the Q4 business review", "within two weeks of the renewal date".

## 8. Blocks that must never be empty

A block stays empty only when the underlying fact genuinely is not evidenced and no human
input is pending. These are never empty:

- **Executive summary.** Written from the body. If the body is thin, the summary says so.
- **Relationship health.** At minimum: opportunity count, total open value, most recent
  customer meeting date, and meeting cadence trend. All of that is derivable.
- **Stakeholder coverage analysis.** Even with two known contacts, the coverage read is the
  finding: which functions are absent, which opportunities are single threaded.
- **Whitespace and expansion signals.** Units and teams that have never appeared on a call are
  computable from attendance and are the core of an account plan.
- **Per-opportunity next step.** An opportunity with none is listed as having none.
- **Appendix coverage table.** Always.

Writing these from data already gathered is synthesis, not fabrication. Leaving them blank
while the appendix shows 40 analyzed meetings implies the calls said nothing, which is
affirmatively misleading.

## 9. Final consistency pass

Run before building the document. Seven checks, all cheap:

1. **Summary against body.** Every assertion in plan section 1 traces to a block below it. No
   claim, number, or name appears in the summary for the first time.
2. **Numbers reconcile.** Opportunity totals equal the sum of the rows. The meeting count in
   the appendix equals the count used in the coverage claims. ARR in plan section 1 equals plan section 5.
3. **Hypothesis check.** Every item on the validate list appears nowhere else in the document.
4. **Template text sweep.** Grep for the outline's example strings and for the vendor name
   inside the customer's SWOT weaknesses.
5. **Banned language sweep.** Section 4 strings, across every block.
6. **Provenance completeness.** Every external claim has a source and a retrieval date. Every
   call claim has a meeting date. Every INPUT NEEDED block carries a specific question. Every
   `source` is a plain sentence, never a nested object: the engine interpolates it directly, so
   an object reaches the page as `[object Object]` with no warning raised.
7. **Word budgets.** Executive summary and the plan section 2 challenge blocks run long by default.
8. **External claims.** Run `verify_external_claims.js`. Every external claim needs a ledger row
   carrying the verbatim sentence, from a fetched page, bound to a period and an entity. A correct
   citation on a figure lifted from a snippet is the hardest defect in this document to see, because
   it looks exactly like a verified one.

Report the pass in the final response in one line. Do not narrate each check.
