# GTM strategy playbook

How to generate plan section 6 when the person chooses `generate`. Read this only after the agent
results, CRM records, stakeholder map, and coverage analysis exist. A GTM strategy written
before the evidence is a template, and a template is exactly what this section must not be.

The strategy is not six paragraphs of best practice. It is six answers to one question:
**given what this account's evidence actually shows, what should each function do next, and
why now.**

## Contents
1. The two engines: value selling and multithreading
2. Inputs you must have before writing
3. The six functions
4. The track output shape
5. Stage gating
6. Prioritization across tracks
7. Failure modes

---

## 1. The two engines

Every track is generated from the same two mechanics. If a track cannot be tied to at least one
of them with named evidence, it does not get written, and the track renders as INPUT NEEDED.

**Value selling.** The chain runs: customer initiative -> the pain blocking it -> the metric they
measure it by -> the capability that moves the metric -> the proof they will accept. Section 2
supplies the initiative and the pain, MEDDPICC Metrics supplies the number where one exists, and
plan section 4 supplies the proof already delivered. A track's objective attaches to a link in that
chain. Where the chain has a missing link, the track's job is often to go get it: an unquantified
metric is a Customer Education and Post Sales problem before it is a pricing problem.

**Multithreading.** Coverage is measured on three axes, all computable from attendance metadata
and the stakeholder map:

- **Breadth of function.** Which functions have attended: engineering, operations, security,
  finance, procurement, legal, executive. Absent functions are the target list.
- **Depth of seniority.** Individual contributor, manager, director, VP, C-level. An account
  with fifteen contacts all below director is not multithreaded, it is crowded.
- **Spread across opportunities.** A person who covers one opportunity does not cover the others.
  Single-threaded opportunities inside a well-covered account are the risk this axis surfaces.

Each track names which specific gap on which axis it closes. "Improve multithreading" is not a
strategy. "Finance has never attended any of the three opportunities and the renewal is 90 days
out, so ADR targets the FP&A lead who owns the software budget" is.

## 2. Inputs you must have before writing

Assemble these first and keep them in front of you. Every track cites at least one.

| Input | Where it comes from |
|---|---|
| Business initiatives and the pain behind them | Section 2, MEDDPICC Identify Pain, external research |
| Quantified metrics, or the absence of them | MEDDPICC Metrics |
| Champion and economic buyer status, per opportunity | MEDDPICC Champion and Economic Buyer |
| Decision process and criteria | MEDDPICC Decision Process and Decision Criteria |
| Technical win, security review, integration blockers | Deal Punchcard technical and security dimensions |
| Budget, procurement, legal status | Deal Punchcard commercial dimensions |
| Dated next steps, or their absence | Deal Punchcard CTA |
| Stage and value per opportunity | CRM, banded through `crm.stage_taxonomy` |
| Renewal and contract dates | Section 5, usually a person input |
| Functions, seniority, and opportunity spread | Stakeholder coverage analysis |
| Units and regions never engaged | Whitespace, from attendance metadata |
| Partners and SIs named on calls | Transcripts, competitive agent if present |
| Competitors and the internal build option | Section 8 |

**If a track's primary inputs from `config.gtm.tracks[].primary_inputs` are all empty, do not
invent a plan.** Write what is missing and what would unblock it. A Partner Strategy for an
account where no partner has ever been mentioned is fiction, and the correct output is: no
partner presence is evidenced across N meetings, confirm whether an SI is involved.

## 3. The six functions

Definitions ship in `config.gtm.tracks` so the generator and the person share one meaning. What
follows is the logic each one is generated from.

### ADR Strategy
Owns net new entry into parts of the account with no relationship.

Generate from whitespace and the unengaged table. Rank targets by: does the uncovered unit run
the same workflow as an evidenced use case, is there a named person or only a function, and is
there an internal referral path from an existing contact. The strongest ADR play in an account
plan is almost always a warm introduction from a champion into a sibling unit, not cold outbound,
so check the stakeholder map for the bridge before proposing a sequence.

### Customer Education
Owns depth of adoption where entitlement already exists.

Generate from the gap between units with entitlement and units with evidenced usage, plus any
confusion, misuse, or repeated basic questions surfacing on calls. This track is the one that
manufactures the metric the value chain is missing: a unit that is trained and instrumented
produces the before-and-after number that Post Sales and the executive track later spend.

### CSE / PS Strategy
Owns technical risk.

Generate from the Punchcard technical dimensions. Every open blocker, unscoped integration, and
unopened security review becomes a line with an owner and an exit criterion. Distinguish sharply
between a blocker to the current use case and a blocker to full rollout; conflating them either
stalls a deal that could close or ships a rollout that breaks.

### Partner Strategy
Owns borrowed trust and delivery reach.

Generate only from evidence: partners named on calls, an SI already embedded in the customer's
architecture, a competitor delivering through a partner, or a region with no direct coverage. If
a competitor is being delivered by an SI the customer trusts, that is a partner problem before
it is a product problem, and it belongs here rather than in plan section 8.

### Post Sales Strategy
Owns the installed base and the renewal.

Generate from renewal timing, delivered value evidence, and coverage decay. The trigger to watch
for: an opportunity with no customer-side attendee inside the freshness `current` band. Quiet
plus a renewal date is the highest-signal pattern in an account plan and this track must name it.

### Executive Strategy
Owns the peer relationship.

Generate from economic buyer status and deal size. Where no budget holder has appeared on any
call and the combined open value is material, that is the finding, and the track is the plan to
fix it. Name which customer executive, which selling-org executive, and what the meeting is
*for*, because an executive meeting with no agenda beyond relationship building burns the one
introduction a champion can give you. Pairing is an internal decision, so propose it as a
recommendation and leave the name as an INPUT NEEDED where the person has not supplied one.

## 4. The track output shape

Every generated track carries five fields. Missing any one makes it commentary rather than
strategy.

| Field | Content |
|---|---|
| `objective` | One sentence, the outcome this function owns for this account this quarter |
| `why_now` | The evidence, with source and date. This is what makes it this account's strategy |
| `plays` | Two to four specific actions. Each names the person, unit, or artifact involved |
| `owner` | A role or a person. Never invented. "Not named" plus naming them as the first play |
| `exit_criterion` | What done looks like, stated so it can be checked at the next review |

Word budget: 90 to 150 per track including all five fields. Tracks run long by default and a
six-track section that nobody reads has failed.

Everything in a generated track is a **recommendation**. The engine labels it as such. The
account team accepts, edits, or rejects; the plan does not assert that these decisions have been
made.

## 5. Stage gating

Do not propose a play the deal is not ready for. Band each opportunity through
`crm.stage_taxonomy` and gate accordingly:

| Band | Appropriate | Inappropriate |
|---|---|---|
| Early | Discovery breadth, ADR into adjacent units, initial technical scoping, champion development | Implementation planning, services statements of work, executive business reviews |
| Mid | Technical validation, business case construction, economic buyer access, security review | Renewal mechanics, expansion sequencing before the first win |
| Late | Procurement and legal paths, executive alignment, mutual plan execution, deployment readiness | Net new discovery presented as the primary play |
| Closed won | Post sales, education, expansion whitespace, reference development | Anything framed as closing this opportunity |

An account with opportunities in different bands gets different plays per opportunity inside one
track. Say which opportunity each play serves.

## 6. Prioritization across tracks

Six equally weighted tracks is a list, not a strategy. Rank them and say why. Rank on:

1. **Blocking now.** A track that removes a blocker on the largest near-term opportunity.
2. **Coverage risk.** A track that fixes a single point of failure: one champion, one function,
   one opportunity carrying most of the value.
3. **Compounding.** A track whose output other tracks depend on. Education producing the metric
   that Executive Strategy needs is compounding; run it earlier than its urgency suggests.
4. **Whitespace value.** Size of the uncovered surface against the effort to enter it.

State the top two tracks and the reason at the head of the section. That ordering is the
strategy; the six tracks are the execution.

## 7. Failure modes

- **Generic playbook.** If a track would read the same for any account in the vertical, it is not
  written from evidence. Delete it and write what is missing instead.
- **Plays with no named object.** "Engage procurement early" fails. "Ask Devlin who owns the
  software budget line the renewal sits on, on the 9/3 operations review" passes.
- **Inventing partners, CSMs, or executives.** All three are internal facts. Recommend a role,
  never a name the person has not supplied.
- **Ignoring stage.** A services plan on a stage-one opportunity signals the plan was not read
  against the CRM.
- **Restating the risk as the strategy.** "Single threaded on Okonkwo" is a finding from plan section
  3. The strategy is the specific second thread and how it gets opened.
- **Six tracks, no ranking.** See §6 above.
