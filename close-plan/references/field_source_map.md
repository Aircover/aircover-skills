# Field source map

Which source feeds which cell, and the threshold for every Health Score item. Nothing in the
workbook may be written without a source named here.

## Contents
1. Header block
2. Deal Overview, the four questions
3. Health Score, 26 items in five buckets
3b. The coverage note
4. Action Plan
5. Stakeholder Map
6. Marker thresholds
7. Aggregating across meetings

---

## 1. Header block

Deal Overview rows 1 to 4. Unchanged from V2.

| Cell | Field | Source |
|---|---|---|
| B1 | Customer | `get_deal` company name or `prospect_org` |
| D1 | AE | `get_deal.customer_owner`, the deal's recorded owner. Falls back to meeting organizer or most frequent `vendor.email_domain` speaker only when that field is empty. Mark sourced when it came from `customer_owner`, inferred when it came from attendance |
| B2 | Opp Link | `build_opp_link` using `config.crm` (source, fields, instance, url template). With `instance` null there is no hostname to build a URL from, so write the plain reference `"<CRM> - Opportunity <id>"` instead. Never blank when an opp id exists, and never guess a hostname |
| D2 | SE | Prompted. Prefill: second most frequent `vendor.email_domain` speaker, excluding the AE. Always inferred, never sourced |
| B3 | Close Date | `config.crm.<source>.fields.close_date`, written as a real date |
| D3 | Partner | Prompted. No transcript contains this |
| B4 | Net Incremental ARR | `config.crm.<source>.fields.amount` as option A, free text as option B. The engine applies `config.formats.arr`, so it renders as money rather than as a bare quantity |
| D4 | Deal in Forecast | `config.crm.<source>.fields.stage` |

## 2. Deal Overview, the four questions

Four questions and nothing else. The champion, economic buyer, technical win, exec engagement
and vendor sponsor blocks that used to sit below these are gone: they are now Health Score
items and Stakeholder Map rows, and repeating them here produced two answers to one question
that drifted apart.

| Answer cell | Question | Source |
|---|---|---|
| A8 | Primary business units using the product | Close Plan: Usage Footprint, the team and business unit lines |
| A10 | How they are using it **today** | Close Plan: Usage Footprint use case lines |
| A12 | **Primary use case vs secondary use case**, and the problem being solved | Close Plan Usage Footprint, ranked, plus MEDDPICC Identify Pain for the problem |
| A14 | The product's impact on the customer's business, with specific metrics | MEDDPICC Metrics and Identify Pain together. Frequently thin; working sessions rarely quantify ROI |

**A12 must separate primary from secondary.** This is not cosmetic. Which use case leads tells
the AE who to lean on: a governance-first deployment points at the CISO and VP IT, an
engineering-efficiency-first one points at platform and dev leadership. A blended answer that
names four use cases with no ranking gives the AE nothing to act on. Name the primary, name the
secondary, then state the problem being solved.

**A14 absorbed two V2 questions.** The old sheet asked separately what the problem costs the
customer today and what the value proposition and ROI are. Both now land here, which means this
one answer carries the whole commercial case: what the problem costs them, what the product is
worth, and the metrics behind it. Do not reintroduce the split.

## 3. Health Score, 26 items in five buckets

Marker goes in column A, label in column B, bucket score in column C on the bucket's header row.

### Stakeholder Alignment, rows 8 to 13
| Row | Key | Item | Source |
|---|---|---|---|
| 8 | `champion` | Champion identified and confirmed | MEDDPICC Champion |
| 9 | `economic_buyer` | Economic buyer engaged directly | MEDDPICC Economic Buyer |
| 10 | `stakeholders_mapped` | All stakeholders and influencers mapped | Close Plan Stakeholder Coverage. Must agree with the Stakeholder Map tab |
| 11 | `decision_criteria` | Decision criteria documented and agreed | MEDDPICC Decision Criteria |
| 12 | `decision_process` | Decision process and approval chain confirmed | MEDDPICC Decision Process |
| 13 | `compelling_event` | Compelling event explicit | Close Plan Compelling Event |

### Technical Validation, rows 16 to 19
| Row | Key | Item | Source |
|---|---|---|---|
| 16 | `technical_win` | Technical win confirmed | Deal Readiness Tech Win |
| 17 | `security_review` | Security review status known | Close Plan Security and Compliance Review |
| 18 | `integration_scoped` | Integration scoped, no blockers open | Close Plan Technical Scope and Product Gaps |
| 19 | `product_gaps` | Product gaps flagged to product team | Close Plan Technical Scope and Product Gaps, the Product gap lines |

Rows 18 and 19 share one property. Row 18 keys on whether open blockers exist; row 19 keys on
whether any Product gap line was captured and routed.

### Commercial, rows 22 to 27
| Row | Key | Item | Source |
|---|---|---|---|
| 22 | `budget_confirmed` | Budget confirmed and allocated | Deal Readiness Budget Confirmed |
| 23 | `pricing_aligned` | Pricing and packaging aligned | Close Plan Pricing and Quote Status |
| 24 | `quote_sent` | Quote or order form sent and reviewed | Close Plan Pricing and Quote Status, quote status line. Corroborate with the CRM |
| 25 | `procurement_started` | Procurement process started | Deal Readiness Access to Procurement |
| 26 | `legal_redlines` | Legal and MSA redlines identified early | Deal Readiness Legal Win and Access to Legal, higher of the two |
| 27 | `value_vs_discounting` | Enough value established with key stakeholders to mitigate discounting | MEDDPICC Metrics **and** Close Plan Pricing and Quote Status together |

**Row 27 is a two-source item and the one most often scored too generously.** It asks whether
value is established well enough that the buyer will not simply demand a discount. Reserve
`yes` for a quantified business case that named stakeholders have acknowledged. An active price
objection on the record caps it at `no` regardless of how much value was presented, because the
objection is the evidence that value did not land. A deal with no pricing conversation at all is
`unknown`, not `yes`.

### Competition, rows 30 to 32
| Row | Key | Item | Source |
|---|---|---|---|
| 30 | `competitive_known` | Competitive landscape known | MEDDPICC Competition |
| 31 | `differentiation` | Differentiation the champion can repeat | Close Plan Competitive Differentiation |
| 32 | `objections_clear` | No unaddressed competitor objections | Close Plan Competitive Differentiation, open objection lines. Inverts: objections present means `no` |

### Timeline & Risk, rows 35 to 41
| Row | Key | Item | Source |
|---|---|---|---|
| 35 | `mutual_plan` | Mutual close plan with agreed dates | Deal Readiness CTA for the Current Quarter |
| 36 | `next_step_dated` | Next step scheduled with a specific date | Deal Readiness CTA for the Current Quarter, dated next step line |
| 37 | `risks_named` | Key risks named explicitly | Close Plan Close Risks. `yes` when any risk is captured **with an owner or a mitigation**, `partial` when risks are named but unowned |
| 38 | `champion_backup` | Backup plan if champion goes dark | Derived: see the ceiling in section 6a |
| 39 | `migration_plan` | Clear migration or onboarding plan | Close Plan Technical Scope, migration and rollout lines, plus Deal Readiness CTA where it names onboarding steps. Agent ran and no such lines exist: `no`, never `unknown` |
| 40 | `onboarding_owner` | Onboarding owner identified | Same sources as row 39, but asks for a **named person** on the customer side. A team or department is `partial`, not `yes`. Nobody named anywhere: `no`, never `unknown` |
| 41 | `forecast_matches` | Forecast category matches actual deal signals | The band against the count of not-yes items in this bucket, per the per-band rule in SKILL.md step 7. **Runner-set: the engine does not compute this row.** When the deal's stage is in no band, ask the seller which of the five it belongs to (step 3b) rather than shipping `unknown`. `unknown` is only for a seller who declined to band it |

Rows 39 and 40 are new in V3 and are usually the last thing anyone discusses, so expect them
to come back unevidenced on otherwise healthy deals. **Unevidenced here means `no`.** Needs Input
on these two rows is a defect: it says nobody looked when the Close Plan agent did. That gap is
real and worth surfacing, not a scoring artifact: a consolidation or migration deal with no
onboarding owner slips after signature rather than before it.

**Row 41 is derived, and you derive it: the engine never writes this marker.** Take the band
from step 3b and count the not-yes items in this bucket, then apply the per-band rule in
SKILL.md step 7. A `late` band with the Commercial bucket largely unevidenced is a mismatch, and
so is an `early` band on a deal with a quote out. An unbanded stage yields `unknown`, but that
is now a last resort rather than the default: when the deal's stage sits in no band, ask the
seller which of the five it belongs to and write it into `config.json`. `unknown` is honest only
for a seller who declined to answer.

### Removed in V3
The red flag block (single threaded, no business case, verbal yes without dates, legal or
security review not started) and the standalone Risk Assessment sheet are both gone. They
restated the same gaps a second time in a different vocabulary and routinely contradicted the
rows above them. Their content now lands as follows:

| Old element | Now lives in |
|---|---|
| Single threaded | Stakeholder Map: a thin committee is visible in the grid |
| No business case tied to a metric | Row 27 and Deal Overview A14 |
| Verbal yes but no dates on paper | Rows 35 and 36 |
| Legal or security review not started near close | Row 17, and the Action Plan row it generates |
| Risk boxes: PRICING, COMPETITIVE, TECHNICAL, EXEC ALIGNMENT, LEGAL SECURITY, SIGNATURE | Action Plan `action` and `comments` on the matching bucket's items |
| Overall Deal Risk Level | Overall Close Plan Score, Health Score B3 |

Close Risks entries are not discarded. Route each tag to the bucket that owns it, and put the
evidence in the Comments column of the generated Action Plan row: PRICING and SIGNATURE to
Commercial, COMPETITIVE to Competition, TECHNICAL to Technical Validation, EXEC ALIGNMENT to
Stakeholder Alignment, LEGAL SECURITY to rows 17 and 26, TIMELINE to row 37.

## 3b. The coverage note

`config.health.coverage_note_cell`, below the last bucket on the Health Score tab.
Supplied as `values.coverage_note`. **This cell is required.** The engine prints a
warning when it is missing and that warning is a build failure, for the same reason a
missing Recommended Action is.

| Element | Source |
|---|---|
| Meetings in scope and the window they span | The worklist from run order step 5 |
| Where transcript coverage stops, against the CRM close date | Newest `completed_meetings` date vs `config.crm.<source>.fields.close_date` |
| Meetings held with no transcript | The step 5a reconciliation |

The overall percentage divides by every item, and several items can only be evidenced
by conversations that happen over email, Slack and direct exec contact. So the number
is coverage of what the calls in scope can evidence, and a reader who does not know
that will read a low score as a dying deal. Say which items are unevidenced because
the evidence lives outside the calls, and give the date coverage ends. Do not soften
the score to compensate: fix the label, not the number.

## 4. Action Plan

Not mapped, **generated**. The engine emits one row for every Health Score item whose marker is
not `Yes`, in bucket order, and nothing for the items that are. You never choose which rows
appear; you supply the text that fills them, keyed by the item key from section 3.

| Column | Content | Source |
|---|---|---|
| A Bucket | Written by the engine | `config.actions.bucket_titles` |
| B Gap | Written by the engine from the Health Score label | Do not restate it differently |
| C Recommended Action | You supply | The action that closes this specific gap |
| D Owner | You supply | Only where a call named that person, per the output standard |
| E Status | You supply, defaults to Not started | Set In progress only where work is evidenced underway |
| F Comments | You supply | The evidence: what was said, by whom, that makes this a gap |

An item marked `partial` (In Progress) still generates a row. In Progress is not Yes, and the
whole point of the tab is that a half-finished item still needs an action.

The engine warns on any generated row with no Recommended Action. Treat that warning as a
build failure, not a note: a gap with no action is the defect this tab exists to prevent.

## 5. Stakeholder Map

Two blocks on one tab.

**The heat map**, seniority x function. `config.stakeholder_map.grid.functions` is org-specific
and must be set to the functions this vendor actually sells into before the first run.

| Element | Source |
|---|---|
| Grid placements | `customer_attendees` across all meetings for who actually attended, plus Close Plan Stakeholder Coverage AND the transcript's own attendee header for role, title, and function. Attendance is the stronger signal: agents see who spoke, not who was in the room |
| Function and seniority | **In this order: what a call states, then the attendee header title.** Someone describing their own remit on a call outranks a directory title, which can be stale. Where no call states a level, read the header title: SVP or VP to VP, Head of or Senior Director to Director, Lead or team leader to Manager. Some orgs enrich the header with titles and LinkedIn URLs and some return only an email-derived name, so check it before concluding a level is unstated. Never infer a level from tone, airtime, or who defers to whom |
| Seniority not stated | The last grid row. Function evidenced, level not. A person who plainly owns procurement or security belongs on the map at their function even when no source gives their level |
| `engagement: engaged` | Attended multiple meetings and spoke to the deal, not just to logistics |
| `engagement: emerging` | Named on calls, or attended once, or reached only through the champion |
| `engagement: gap` | A persona this deal should have and does not. Renders as a red "?" bubble |
| C-Suite band | Only a person a call or an attendee title states is C-level. **Authority over the deal is not the test.** Someone who owns the budget and must approve pricing, with no title stated anywhere, is the Economic Buyer persona and nothing else. Never promote the economic buyer into this band, for the same reason you never promote them into Executive Sponsor: it asserts a seniority no source gave and duplicates them against their own persona row. Blank is the normal state |

**The "?" bubbles are the point of the tab, not decoration.** A grid with two green cells and
nothing else looks sparse; a grid with two green cells and four red "?" bubbles reads as a
thinly covered buying committee, which is what it is. Place a `gap` bubble wherever the deal
plainly needs a persona that no call has produced: security on a deal with a security review
pending, procurement on a deal heading to a quote, IT on a migration.

`unplaced_cell`, the row directly under the grid, carries the attendees the grid cannot
hold. Since the grid now has a **Seniority not stated** row, this line is only for people whose
**function** is unevidenced too: someone who joined a call and whose team, remit, and title
appear in no call, no Stakeholder Coverage line, and no attendee header. An unstated level is no
longer a reason to drop anyone. Name whoever remains, with their meeting dates and the reason.
This is not optional tidiness. Attendance is the strongest signal the map has, and a grid that
quietly drops four people who sat on calls reports a narrower committee than the deal has.

**A grid with no named placements is a build failure, not a thin committee.** If every attendee
ended up on the unplaced line, the run skipped a source: re-read the attendee headers and the
Stakeholder Coverage role lines before shipping. The engine warns on this.

**Whether titles are available at all is per-org, so check before concluding either way.**
`get_meeting` and `get_meeting_transcript` return an attendee block per meeting. In an org with
contact enrichment switched on, entries carry a job title and often a LinkedIn URL, for example
a security lead arriving as "VP, Enterprise Technology & Security". In an org without it, the
same call returns only an email address and a name derived from the local part, and no title
exists anywhere in the payload. Look at one meeting's attendee block early. If titles are there,
use them per the precedence above. If they are not, say so plainly in the unplaced line, for
example "no attendee titles are available in this workspace, so seniority reflects only what
people stated on calls." That one sentence is the difference between a reader thinking the map
is unfinished and a reader understanding it is complete to the limit of the data.

**The persona detail table**, the six rows under the heat map. With the shipped five-row
seniority axis that is rows 18 to 23, but `personas.first_row` is the source of truth. Economic
Buyer, Champion, Executive Sponsor, and three influencer slots.

| Column | Content |
|---|---|
| A Role | Fixed by the template |
| B Name | The person, or "?" when unmapped. The engine writes "?" for any role you leave out |
| C Engagement | Engaged, Emerging, or Not mapped, colour-coded green, amber, red |
| D Notes / Gap | What they control, what is unresolved, and what would move them a colour |

Sources: MEDDPICC Champion for the champion, MEDDPICC Economic Buyer for the economic buyer.
For the three influencer slots, Close Plan Stakeholder Coverage **and the attendee roster with
its titles**, on the same precedence as the grid: what a call states, then the header title.
Executive Sponsor is the customer's exec sponsor and is usually an internal fact nobody said
aloud: leave it "?" rather than promoting the economic buyer into the slot.

**Fill an influencer slot from an attendee whose function matches it.** This is the same defect
the grid had: someone attends, their title names their function, and the slot is left "?"
because no agent property happened to name them. A VP of Enterprise Technology and Security who
joined a call and asked about the security add-on is the Security / Legal influencer; do not
leave that row blank and then place them on the grid two inches above it. Engagement still
follows the evidence, so an attendee who came once is Emerging, not Engaged.

**A `?` influencer means nobody fills that function in any source, not that no property named
them.** Before leaving one blank, check the attendee roster across every meeting against that
slot's function. Reserve "?" for a function genuinely absent from the deal: no security contact
attended, none was named, and no title matches. That is a real gap and it should show. Do not
ask the seller to name them; this tab reports what the calls and the roster support.

**Row 10 of the Health Score and this tab must agree.** If the map shows three "?" personas,
`stakeholders_mapped` is not `yes`.

Row 24 carries a standing open question that the template already asks. **`gap_line` supplies
the answer only, not the question**: the engine appends it to the prompt already in the cell.
Passing the full question back duplicates it. Leave `gap_line` out entirely when no call
settled it, and the workbook still asks the question.

## 6. Marker thresholds

Standard items, on a 0 to 3 dimension:

| Score | Status | Renders as | Worth |
|---|---|---|---|
| 3 | `yes` | Yes, green | a full share of its bucket |
| 2 | `partial` | In Progress, amber | half a share |
| 0 or 1 | `no` | No, red | nothing |
| Property absent, or agent never ran | `unknown` | Needs Input, grey | nothing |

A bucket of six items gives each item a sixth; a bucket of three gives each a third. So
`partial` is not a free hedge: it pays out half an item. Choosing it over `no` to avoid
looking harsh moves the overall score, which is why the section 6a ceilings are mandatory
rather than advisory.

**`unknown` is a real answer with a real cost.** In V2 it wrote a blank cell. In V3 it writes
the words "Needs Input" and counts in the bucket denominator exactly like a `no`, because the
bucket score divides by the item count, not the answered count. This is deliberate: a blank
that quietly shrinks the denominator turns missing evidence into a higher score, which is the
opposite of what the number should do. Do not avoid `unknown` to protect the score, and do not
use `partial` as a synonym for "we do not know" -- `partial` asserts work in progress, which is
itself a claim.

Every marker cell carries a Yes / No / In Progress / Needs Input dropdown so the AE can
override by selecting rather than typing. The bucket formulas recompute live when they do.

### 6a. Ceiling rules, applied after the threshold

The threshold table converts a score into a marker. It does **not** check that the property
measured the same thing the item asks for. Several items ask a harder question than their
source property answers, and taking the raw score straight through systematically overstates
the deal. Apply these ceilings after the threshold, never before.

The general rule: **where an item asks for more than its property measures, cap at `partial`
unless the extra element is separately evidenced.** Then look for the extra element and
promote only if you find it.

**The table below is illustrative, not exhaustive.** It names the items where this bites
hardest; it is not the set of items where the rule applies. Before setting any marker, read the
label and the property text side by side and ask whether the property measured the thing the
label asks about. An item's absence from this table is not an exemption. The failure is always
the same shape: a property scores well for discussing, reacting to, or having access to
something, and the item asks whether that thing is aligned, started, agreed, or documented.

| Item | Property measures | Item also asks | Ceiling |
|---|---|---|---|
| 8 Champion | Advocacy: is someone selling internally | Purchase influence: can they carry a commercial decision | Cap `partial` unless the champion is evidenced engaging budget, pricing, or the economic buyer. A champion who runs the pilot brilliantly and has never discussed money is `partial` |
| 11 Decision criteria | Criteria discussed | Criteria documented **and agreed by the buyer** | Cap `partial` unless the buyer confirmed them back |
| 12 Decision process | Any process discussion, including onboarding and rollout sequencing | The approval chain: who signs | Cap `partial`. Promote only with evidence of signature authority or an approval sequence. An implementation plan is not a decision process, and agents routinely score one as the other |
| 16 Technical win | Progress toward validation | Success criteria **met** | Cap `partial` while any blocking item is open |
| 17 Security review | That a review is needed or mentioned | Status **known**: in progress, passed, or not required | A named requirement with no owner, no artifacts and no timeline is `no`, not `partial`. Distinguish "risk identified" from "formal review opened" |
| 27 Value vs discounting | Value discussed | Value established **with key stakeholders**, enough to hold price | Cap `no` while any live price objection is on the record |
| 31 Differentiation | Differentiation stated on a call | The champion can repeat **the** differentiation | One differentiator repeated is `partial`. Reserve `yes` for the champion articulating the substantive set unprompted |
| 38 Champion backup | Stakeholder breadth | A backup **plan** | Multiple named contacts across functions is **not** a backup plan. Cap `no` unless a second person is evidenced advocating commercially, not merely attending. Technical contacts do not backstop a commercial champion |
| 40 Onboarding owner | Onboarding discussed | A **named person** owns it | A team, a department, or "their IT group" is `partial`. Reserve `yes` for a person |

### 6b. Absence is not evidence

Never award a positive marker because a property came back empty. A `0` means the agent looked
and found nothing; it does not mean the underlying condition is satisfied.

This bites hardest on **item 32, no unaddressed competitor objections**. No objection lines
extracted does not mean objections are handled. Resolve it this way:

- No competitor identified anywhere in the deal: `unknown`.
- Competitor known and the competitive picture is partial, for example an incumbent whose
  contract, renewal, or counter-position is unexamined: `partial`.
- Reserve `yes` for objections explicitly raised **and** addressed on a call.

An incumbent sitting in the account is an open competitive question by default, regardless of
how warmly the champion speaks about us.

A 0 means the agent looked and found nothing. `unknown` means nothing looked. Keep them
distinct: the first is a gap the AE should close, the second is a gap in the data. Both
generate an Action Plan row, but the action differs -- close the gap versus go find out.

**A few items read a fragment of a property rather than its score**, for example rows 39 and 40,
which want the migration and rollout lines inside Close Plan Technical Scope. Apply the test to
the **property**, not the fragment. If the agent ran and returned content for that property, it
looked, and a missing fragment is `no`. Reserve `unknown` for the property being absent
altogether or the agent never having run. Row 41 is the one item whose input is a config value
rather than an agent, so it is the only place `unknown` can be right at all, and even there only
when the seller declined to band the stage. If the Action Plan comment you are about to write
says "no call addressed this", the marker is `no`.

## 7. Aggregating across meetings

The rule is latest wins: for any dimension take the highest score achieved on the most
recent meeting that produced evidence, and keep that meeting's evidence text. A
dimension proven in meeting 3 does not become unproven because meeting 9 was a
technical working session that never raised it.

**Silence is not contradiction, and contradiction is not silence.** The rule above
protects a proven dimension from a later meeting that simply did not cover it. It must
not be used to protect a dimension a later meeting actively disproved. Two different
shapes:

- Later meeting returns nothing on the dimension: the earlier score stands.
- Later meeting speaks to the dimension and contradicts the earlier read: **the later
  evidence supersedes, even when it scores lower.** A buyer saying on a June call that
  leadership has not confirmed budget overrides an April call where a contra budget was
  named, because the same dimension was examined again and came back worse.

Watch for the related trap: **an earlier positive that was scoped to a smaller deal.**
A price agreed for a 10-seat pilot is not pricing alignment for a full rollout, and a
budget that covered the pilot fee is not budget for the platform. When the deal's scope
has grown since the evidence was captured, the evidence has expired. Score the deal in
front of you, and put the superseded fact in the Action Plan comments so the AE can see
what changed.
