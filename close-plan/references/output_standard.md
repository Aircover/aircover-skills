# Output standard

How every written cell must read. The scoring rules live in `field_source_map.md`; this
file governs voice, structure, and length. Both are mandatory.

The workbook is a close plan, not an evaluation report. The test for every cell is whether
an AE can act on it. "Here is what happened" fails. "Here is what must happen next, who owns
it, and what done looks like" passes.

## Contents
1. The action row
2. Word budgets
3. Banned language
4. Owners and dates
5. Deal Overview standard
6. Stakeholder Map standard
6b. The coverage note
7. Blank versus "None identified"
8. Final consistency pass

---

## 1. The action row

In V2 the five-part action block lived in six merged risk boxes. In V3 it is spread across
the Action Plan columns, which is easier to write and much easier to scan:

| Part | Column |
|---|---|
| Current status and evidence | F Comments |
| Gap | B Gap, written by the engine |
| Next action | C Recommended Action |
| Owner | D Owner |
| Progress | E Status |

The exit criterion goes at the end of column C: what has to be true for this row to become a
Yes on the Health Score tab.

A row that diagnoses without prescribing is incomplete, even when the diagnosis is correct
and well evidenced. This remains the single most common failure mode. Write the ask.

**Wrong** (diagnosis dressed as an action):
> C: No economic buyer has been identified across the six calls. Budget authority was never
> discussed.

**Right**:
> C: Ask the champion who owns budget and signature for a 150-seat expansion, and secure an
> introduction off the pilot readout. Done when the buyer confirms budget and describes the
> approval path.
> D: <AE name> (AE)
> F: Nobody with budget or signature authority has appeared on any of the six calls. The
> champion authorised the pilot, but their reach over a full rollout is untested.

**Every generated row needs a Recommended Action.** The engine prints a warning naming any
row you left empty. That warning is a build failure, not a note. Fix it before presenting.

Column C is an instruction, so start it with a verb: Ask, Confirm, Issue, Map, Document,
Build, Identify. A column C entry that starts with a noun phrase is usually a restatement of
the gap rather than an action.

## 2. Word budgets

| Cell | Target | Note |
|---|---|---|
| Coverage note | 40 to 80 words | Meetings and window, where coverage stops, what that leaves unobserved |
| A8 business units | 30 to 60 words | |
| A10 how they use it today | 40 to 80 words | The deployment as it stands. The ranking belongs in A12, not here |
| A12 primary vs secondary use case | 50 to 90 words | Name the primary, then the secondary, then the problem being solved. Do not run them together |
| A14 product's impact | 50 to 100 words | The three-part shape in section 5. This question absorbed the old value-proposition and ROI questions, so it carries the whole commercial case |
| Action Plan, column C | 15 to 40 words | One action and its exit criterion. If it needs more, it is two rows |
| Action Plan, column F | up to 40 words | Evidence only |
| Stakeholder Map, notes | 15 to 35 words each | |

Over budget is a real defect, not a style preference: these are cells in a workbook the AE
scans, not a document they read. The V3 tabs carry no overflow space, so unlike V2 there is
nowhere to park detail that will not fit. If an action genuinely needs three sentences, it is
two actions on two rows, which is also more useful.

Never drop a genuine blocker to hit a count.

## 3. Banned language

Model scoring machinery must never appear in a customer-team artifact. It reads as an AI
evaluation report rather than seller guidance.

Never write: "scored 0", "scored 2 of 3", "peaked at 1 of 3", "max_score", "MEDDPICC Economic
Buyer scored", "the agent found", "Not Found" as a literal cell value, property names,
template ids, bucket keys such as `timeline_risk`.

Translate to plain language instead:

| Instead of | Write |
|---|---|
| "Economic Buyer scored 0 on every call" | "Nobody with budget authority has appeared on any call" |
| "CTA peaked at 1 of 3" | "No dated next step has been agreed" |
| "Pricing and Quote Status 0 across six calls" | "Pricing has never been discussed and no quote has been issued" |
| "Security review scored 1" | "A security approval is required but no review has been opened" |
| "This item is Needs Input" | "No call in scope touched this" |

Sweep every written cell on all four tabs before presenting. This is a build step, not a
style check.

## 4. Owners and dates

Assign an owner **only** where a call named that person for that work, or where the role is
structurally unambiguous: the AE owns commercial actions, the SE owns technical validation.
A named admin on tenant config, or a named security contact on CRM access questions, is
legitimate. A plausible-sounding customer-side owner is not.

Never generate a calendar date that nobody committed to. A fabricated due date on a close plan
looks exactly like a real commitment and is worse than an honest gap.

Where the owner is genuinely unknown, write in column D:

> Not named

and make naming them the first clause of column C. Relative targets tied to a real event are
acceptable in column C because they are recommendations, not recorded commitments: "before the
pilot review", "ahead of the 10/30 close date".

## 5. Deal Overview standard

Four questions. Resist the pull to answer a fifth.

**A12 leads with the ranking.** Write "Primary use case: X. Secondary use case: Y." as the
first two sentences, then the problem being solved. An answer that lists four use cases in a
paragraph has not answered the question, because the question exists to tell the AE which
persona to lean on: governance-first points at the CISO and VP IT, engineering-efficiency-first
points at platform leadership. A10 describes the deployment; A12 ranks it.

**A14 is never blank.** A missing ROI figure does not make the question unanswerable. Write it
in three parts:

> Observed and expected value: [what the customer gets, in their words where available]
> Quantified ROI: not found in calls reviewed. [what specifically was never stated]
> Metrics to establish: [3 to 4 measures attributable to this deployment]

Use "Observed and expected value", not "Value stated by the customer", unless every item is a
direct quote. Some of it is always inference from usage patterns.

Metrics must be attributable to the product. Time saved on a named manual process, coverage of
a named governance gap, and consolidation of named duplicate contracts are clean. Revenue
growth and win rate are confounded by everything else happening in the business and should not
be proposed.

## 6. Stakeholder Map standard

**Fill the "?" bubbles honestly.** The temptation is to leave the grid sparse and the persona
table half empty, which looks tidy and communicates nothing. A persona the deal needs and does
not have is a red "?", and four of them on one tab is the most useful thing in the workbook.

**Do not promote people into roles they do not hold.** The economic buyer is not the executive
sponsor. A technical champion is not a commercial champion. An influencer who attended one
call is Emerging, not Engaged. Every promotion of this kind makes the committee look better
covered than it is, which is the failure this tab exists to prevent.

**Notes state the gap and the move.** "Holds the decision for the full expansion; not yet
engaged directly by the account team" is right. "Senior stakeholder" is not.

**A `?` persona still needs a note, and needs one more than a filled row does.** A row reading
`?` with an empty Notes cell is the single most common reason a delivered workbook gets called
half-finished: the reader cannot tell whether nobody was found or nobody looked. Write what the
calls do say about that function even when no name attaches to it, and what would close it. For
an unnamed security contact: "InfoSec review named as a requirement on four calls, never with an
owner; ask the champion who runs it." Never leave the cell blank. The engine warns on this.

**Name the attendees the grid cannot hold.** Placing someone needs a function; the level can
be unstated, in which case they go on the **Seniority not stated** row rather than off the
grid. Take both from what a call states first, then from the attendee title in the transcript
header. Only a person with no evidenced function belongs in the unplaced row, with the reason,
never a guessed cell and never silence. Keep it to one line: who, which meetings, and what is
missing. A grid with no names on it at all means a source was skipped, not that the committee
is unmappable.

Engagement colours are evidence-based, not impressions:

| Colour | Means |
|---|---|
| Green, Engaged | Attended more than once and spoke to the deal itself |
| Amber, Emerging | Named on calls, attended once, or reached only through the champion |
| Red, Not mapped | The deal needs this persona and no call has produced one |

## 6b. The coverage note

Required, and the one cell whose job is to stop the score being misread. Three parts,
in this order:

> Coverage note: this score reflects what [n] transcribed calls between [first] and
> [last] can evidence, not deal health. Transcript coverage ends [gap] before this
> build and [gap] before the [date] close date, so any pricing, procurement or legal
> activity after [last] is unobserved. [n] meetings held [window] produced no
> transcript.

Rules for it:

- **State dates, not adjectives.** "Coverage is somewhat limited" tells the reader
  nothing. "Coverage ends 7/16, seven weeks before this build" tells them exactly
  which window to distrust.
- **Name what the gap makes invisible**, and be specific: the Commercial bucket is
  built from pricing, procurement and legal conversations, which are the ones most
  likely to have happened off-call.
- **Do not use it to apologise for the score.** It explains what the number measures.
  It never says the deal is healthier than the items show, and it never excuses an
  item that is genuinely a gap rather than a blind spot.
- **Untranscribed meetings belong here**, not only in the chat response. A capture
  outage and an absence of evidence look identical on the Health Score tab, and only
  this cell can tell them apart.

## 7. Blank versus "None identified"

| Cell type | When there is nothing to write |
|---|---|
| Health Score markers | "Needs Input". Never leave blank: a blank shrinks the bucket denominator and inflates the score |
| Header free text (Partner, SE) | "None identified" or "Not assigned" |
| Header CRM cell B2 | Full opportunity URL when an instance is configured, else "Salesforce - Opportunity {id}" or the HubSpot equivalent. Never blank when an opp id exists |
| Deal Overview A8 to A14 | Never blank. Write what the calls do support and name what they do not |
| Action Plan, column C | Never blank. See section 1 |
| Action Plan, columns D and F | "Not named" for owner; blank is acceptable for comments |
| Stakeholder Map, names | "?" written by the engine. Leave it |
| Stakeholder Map, gap line (`gap_line_row`, row 25 as shipped) | Blank rather than an invented question |
| Stakeholder Map, unplaced row | Blank only when every attendee is on the grid |
| Coverage note | Never blank. The engine warns, and that warning is a build failure |

## 8. Final consistency pass

Run before writing the workbook. Five checks, all cheap:

1. **Tabs agree.** The Health Score and the Action Plan cannot disagree, because the engine
   generates one from the other, but the *prose* still can. A comment saying pricing was never
   discussed contradicts anything above `no` on row 23. Where marker and prose disagree, the
   prose is usually right, because it was written from the evidence and the marker from a
   threshold. Fix the marker, then re-run, since a corrected marker changes the bucket score
   and adds or removes an Action Plan row.
2. **Stakeholder Map against row 10.** Three "?" personas and `stakeholders_mapped` at `yes`
   is a contradiction. So is a fully populated map with row 10 at `no`.
3. **Overview against the buckets.** A14 claiming a quantified business case while row 27 is
   `no` is a contradiction. A12 ranking governance as the primary use case while the Stakeholder
   Map has no security persona is a gap worth a "?" bubble.
4. **Banned language sweep.** Grep every written cell on all four tabs for the section 3
   strings.
5. **Word budgets.** Column C runs long by default; check it first.
6. **Coverage note present and dated.** Read it against the meeting worklist: the
   count, the window and the untranscribed total all have to match what step 5
   actually found.

Colour is no longer part of this pass. The markers are painted by conditional
formatting rule keyed on the marker text, so a marker and its colour cannot disagree,
and an AE's own override recolours itself. The one exception is the heat map grid,
where engagement level is carried by colour rather than by text: green and amber are
painted at build time and cannot be inferred from a name, so a level changed by hand
needs the fill changed by hand too. Copy the cells in the Key row rather than picking
an approximate colour.

Report the pass in the final response, briefly. Do not narrate each check.
