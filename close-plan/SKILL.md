---
name: close-plan
description: Generate a completed close plan spreadsheet for a deal, pulling qualification, close mechanics, stakeholder coverage, risks, and CRM data from the Aircover Production account and filling the team's standard close plan template. Use this whenever someone says "build a close plan", "run the close plan", "close plan for [company]", "deal review sheet", or wants a deal turned into the standard close plan workbook, even if they do not name the template. Also trigger when someone asks how a specific deal is tracking toward close and wants it written up rather than summarized in chat.
---

# Close Plan

Turn a live Aircover deal into the team's standard close plan workbook: four tabs, each
traced to real call evidence or to the CRM. Sourced values render in black. Anything the data
cannot supply is marked as needing input rather than guessed at. The finished plan is also
saved back into Aircover as a new version of the deal's close plan document (step 9), so the
deal page and the workbook never disagree.

| Tab | Holds | Built from |
|---|---|---|
| 1 Summary | One page: header facts, overall score, a bar per bucket, top 3 risks, next 5 actions, key people, the four deal story questions | CRM, agents, and formulas into tabs 2 to 4 |
| 2 Health Score | 26 items in five buckets, scored live | All three agents |
| 3 Action Plan | One row per item that is not a Yes | Generated from tab 2 |
| 4 Stakeholder Map | Seniority x function heat map and persona detail | Meeting attendance plus Stakeholder Coverage |

> **Blank beats stale.** The engine clears every mapped cell before writing, so an unsupplied
> field never reads as real analysis of this customer's deal. Never reintroduce placeholder
> prose to "fill out" the sheet.

> **Scoring.** Each Health Score item is an equal share of its bucket: Yes 100%, In Progress
> 50%, No and Needs Input 0%. The overall weights the five buckets equally, by live formula.

> **But a blank marker is not blank data.** On the Health Score tab an unanswered item writes
> the words "Needs Input" and counts in the bucket denominator exactly like a No. A truly empty
> cell would shrink the denominator and raise the score, turning missing evidence into apparent
> health. That is the one place where writing something beats writing nothing.

## Bundled resources
- `config.json` - everything customer-specific: environment, agent discovery, the full cell
  map, the five buckets, marker glyphs, colours. Change this, not the code, to retarget.
- `assets/Close_Plan_TEMPLATE.xlsx` - the team template, four tabs, in the Aircover palette.
  Holds all styling, merged blocks, the score formulas, and the dropdowns. Do not rebuild it,
  fill it. The Summary tab's score, bars, next actions and key people are formulas into the
  other tabs, so they follow the AE's edits.
- `scripts/fill_close_plan.py` - template-agnostic engine. Reads `config.json`, clears mapped
  cells, writes only what you supply, preserves everything else. Requires openpyxl.
- `scripts/build_template.py` - regenerates the blank template asset, reading the
  stakeholder axes and every dropdown's options from `config.json` so the two cannot
  drift. Needed when the bucket structure or the grid axes change; a normal run never
  touches it. Pass `--config` when running it from outside the skill directory.
- `references/field_source_map.md` - which agent property feeds which cell, the thresholds, and
  the ceiling rules for items that ask more than their property measures. Read before mapping.
- `references/output_standard.md` - how every written cell must read: the action row, word
  budgets, banned scoring language, owner rules, and the final consistency pass. **Read this
  before writing any cell text.** Skipping it produces a workbook that summarises the deal
  instead of advancing it, which is the single most common failure of this skill.

Copy the resources into your working directory first:
```
cp "$SKILL_DIR/scripts/fill_close_plan.py" .
cp "$SKILL_DIR/config.json" .
cp "$SKILL_DIR/assets/Close_Plan_TEMPLATE.xlsx" .
```

## Requirements
- The **Aircover Production** connector (api.aircover.ai) must be connected. Production and
  Staging share tool names, so an "agent not found" error usually means the wrong environment.
- Code execution and file creation on.
- openpyxl (`pip install openpyxl --break-system-packages` if missing).

**That is the whole list. No CRM connector is required.** Aircover already syncs the customer's
CRM, so Salesforce and HubSpot fields arrive inside `get_deal`'s `crm` block over the Aircover
MCP. Do not ask the person to connect a Salesforce or HubSpot MCP, and do not query one to fill
this workbook. If the CRM data looks wrong, that is a sync question for the Aircover side, not a
reason to reach for another connector.

## Configuration
All of it lives in `config.json`. Environment is Production, app host app.aircover.ai. Three
agents are discovered at runtime via `list_agents` and matched on title keywords: **close
plan**, **meddpicc**, and **deal readiness**. Pin `pinned_template_id` to lock any of them.

**Nothing is hardcoded to a company, and nothing carries over from whoever built this.**
`vendor.name`, `vendor.email_domain`, and every `crm.stage_taxonomy` list ship empty. Fill them
from the installing org's own data. If `vendor.name` is blank the template labels render
without a company name, which is correct until someone sets it.

**`stakeholder_map.grid.functions`** ships as a generic six-column buying committee. To fit the
vendor's real buyers, change it and regenerate the template
(`python scripts/build_template.py --out assets/Close_Plan_TEMPLATE.xlsx --config config.json`);
keep six columns.

**`crm.source` ships as `auto`** (first CRM with an opp id wins). **Never assume Salesforce**: a
config pinned to `salesforce` in a HubSpot org silently produces an empty header. `instance` is a
hostname for building links only; while null, Opp Link holds plain text.

`sync` controls step 9: `enabled` ships true, `mode` `auto` saves without asking, `confirm` shows
the rendered document first, `off` skips it.

### 0. First run in a new org
Four values are org-specific and ship blank or neutral. Resolve them once, on the first run,
and write the answers into `config.json` so no later run re-asks:

| Value | How to resolve |
|---|---|
| `vendor.name`, `vendor.email_domain` | Ask, or read the selling-side email domain off `get_deal.customer_emails`. Confirm before writing |
| `crm.source` | Detect from the `crm` block, per step 3. Do not ask first, look first |
| `crm.stage_taxonomy` | Band the deal's own stage with the person, per step 3b. One stage per run, not the whole pipeline upfront. Persists only as far as the config file itself does |
| `stakeholder_map.grid.functions` | Ask which functions this vendor sells into, then regenerate the template |

Only the ones that actually bite this run need resolving now. A first close plan can be built
with the neutral grid axes and an unbanded taxonomy: the grid columns will be generic and row 41
will read Needs Input. Both are honest outcomes, and neither is worth spending the question
budget on when the CRM record or the AE and SE are still unconfirmed. Prefer asking about the
grid axes at the end, once the workbook has been delivered and the person can see what the
columns did.

## Run order

### 1. Load tools and confirm environment
Call `tool_search` ("Aircover meetings agents deals") to load the deferred tools, then use
the exact parameter names returned. Confirm the active connector is Production. When
`sync.enabled` is true, also load `list_account_deal_agents`, `get_account_deal_agent_results`
and `save_account_deal_agent_document` (tool_search "deal agent document") for step 9.

### 2. Identify the deal, deal first
`list_meetings` has no account filter, so start from the deal. `get_deals(search="<company>")`.
Use the full `deal_key` (`prospect_org/deal_id`) or `prospect_org`, never the bare integer
`deal_id`, which resets per org and collides. Echo back the matched company, opportunity name,
amount, stage, and close date, and confirm before building.

**Running a deal the caller does not own is normal and supported.** Managers build close plans
for their reps. `get_deals` searches the whole org by default, so no extra parameter is needed
when the company name is known. When the ask is scoped to a person or a team rather than a
company, narrow it: `rep="<their email>"` for one rep's deals, or `team_ids` for a team, after
translating the team name with `get_teams`.

One failure mode to name correctly: a viewer-role caller may only pass their own address to
`rep`, and any other value returns an error. That error means insufficient role, not a missing
deal. Say so plainly and suggest the person ask an admin to raise their role, rather than
reporting the deal as not found or silently retrying without the filter.

### 3. Deal and CRM in one call
`get_deal(prospect_org, deal_id)` returns a `crm` block and a `completed_meetings` array.
Call it once and reuse it. Read the CRM block through `config.crm`, never by reaching for
`sfdc_*` directly. Write the block to a file and pass `--crm crm.json` so the engine resolves
it via `resolve_crm`: amount -> Amount, close date -> Close date, stage -> Stage, opp id ->
CRM, all on the Summary tab's header facts (cells in `config.header_cells`). Anything you set explicitly in `values.json` wins, so a
person's correction in step 4 is never overwritten.

`resolve_crm` also returns `stage_band`, resolved against `crm.stage_taxonomy`. The forecast
item (Health Score row 41) reads the band, not the raw stage string, because stage names differ
per org.

### 3b. Band this deal's stage, not the whole taxonomy

`crm.stage_taxonomy` ships empty. **Never seed it from another org's pipeline, and never invent
stage names.** But you do not need the whole pipeline banded to score row 41. You need one
stage banded: the one on the deal in front of you.

1. Take the stage string from the resolved CRM block, which step 3 already has.
2. If that exact string already sits in one of the five bands in `config.json`, you are done.
   Ask nothing.
3. If it does not, **ask one question**: which band does this stage belong to, with the five
   bands as options. Ask it alongside the other header confirmations in step 4, not as a
   separate round trip.
4. Write that stage into the chosen band in `config.json` immediately, and confirm the write
   landed. Within the session, no later deal in that stage asks again.

A config inside an installed skill folder resets each session, so the band may be asked again
next session. When a band is confirmed, say so, so it can be folded into the distributed
`config.json`.

Band it **with the person, not for them.** Naming conventions are misleading: a stage called
"Confirmed" may sit mid-pipeline, and numbered stages do not always run in order. `excluded`
means excluded from scoring entirely: nurture, prospecting, and similar parking stages.

**Do not skip this question to save an ask**: it is what turns a permanent Needs Input on row 41
into a real marker.

Only sweep the full pipeline when someone is deliberately configuring the skill rather than
building a plan: `get_deals(sort="sfdcCurrentStage", asc=false, limit=100)`, collect distinct
values, page until the set stops growing. Ascending sorts nulls first and returns nothing
useful, so sort descending. If the org runs HubSpot the stage field is the HubSpot one; use
whichever the `crm` blocks actually populate. Note that a HubSpot stage often arrives as an
internal GUID, which is unreadable to the seller: name the deal and ask which stage it is in
rather than showing them the GUID.

Row 41 goes `unknown` only when the seller declines to band the stage. An unbanded stage is
then an honest gap, not an error, but it should be the exception rather than the default.

`crm_matches_deal(resolved, expected_name, expected_amount)` returns `(ok, reason)`. The engine
also prints a warning when the resolved opportunity sits in a `closed` band.

**Verify the CRM record is the opportunity you are planning.** Compare the CRM block's
opportunity name and amount against the deal the person selected. A deal record often carries
a stale or unrelated opportunity: a closed-won original sale, a renewal dated next year, or an
expansion the sync never caught up to. If they do not match, say so and ask the person which
record is authoritative, then use what they give you. Do not go query a CRM connector to resolve
it yourself. Getting this wrong silently mislabels the whole workbook.

**A populated CRM block is not proof of a live sync.** If the values look stale or the person
says there is no integration, treat them as unsourced and take the header values from them in
step 4.

**Detect the CRM before reading it.** With `crm.source` on `auto` the engine picks whichever CRM
populates an opp id, but you still need to know which one it landed on, because everything you
echo back in step 4 depends on it. Read the `crm` block's own keys:

- `sfdc_*` keys populated, `hubspot_*` absent: a Salesforce org.
- `hubspot_*` populated, `sfdc_*` absent: a HubSpot org. Note that the HubSpot stage field
  carries an internal GUID rather than a readable stage name, so the taxonomy in step 3b has to
  be banded against those GUIDs or the stage cell renders unreadable. Ask the person for the
  stage label if the GUID is all you have.
- **Both populated:** two records sit on one deal and they are often different opportunities at
  different amounts and dates. Do not pick one silently. Show both and ask which is
  authoritative, per the verification rule above.
- **Neither populated:** the org syncs no CRM into Aircover, or this deal predates the sync.

An empty `crm` block is a normal state, never a reason to reach for a CRM connector. Say no CRM
record is attached, ask for close date, amount, stage and opportunity name in step 4, leave Opp
Link blank, and row 41 reads Needs Input.

### 4. Show the full header block and get it confirmed

Never build on assumed header values. Resolve everything you can, then show the whole block back
in one table and let the person accept it or correct any line. This is the last point before the
workbook takes shape, and a wrong opportunity or amount here mislabels the entire deliverable.

Present it exactly like this, marking where each value came from:

| Field | Value | Source |
|---|---|---|
| Customer | Acme | deal record |
| CRM record | Acme - Expansion, $40,000, Stage 3 | CRM |
| Opp link | https://... | built from CRM |
| Close date | 2026-09-30 | CRM |
| Net Increm ARR | 40,000 | CRM |
| Deal in Forecast | Stage 3 | CRM |
| AE | Jane Doe | deal record owner |
| SE | Not assigned | not inferable |
| Partner | None identified | no call contains this |

Then ask one question: accept all, or say which lines to change. Offer tappable options where the
choice is bounded (for example the CRM amount versus a different figure the person supplies), and
accept free text for anything else.

**Always confirm AE and SE as their own tappable question**, not only through the table, since
people skim tables. Options: accept both, AE right but SE wrong, both wrong, let me type them.
Any answer other than accept-both gets a free-text follow-up for the corrected names.
Resolve `customer_owner` to a display name via `deal_team_attendees`. Ask who owns the deal, not
"is this you": the caller is often a manager building it for a rep.

The three question ceiling binds here. Fold confirmations into one question where you can (the
vendor and stage band can ride along with the header), and otherwise prioritise: conflicting CRM records, then the stage
band (step 3b), then AE and SE, then meeting scope (step 5).

Rules for this step:
- **Mark inferences as inferences.** The AE comes from `customer_owner` and is sourced fact; say so.
  Where that field is empty, and always for the SE, the value comes from attendance frequency and
  is often wrong. Never present an attendance-derived name as sourced. Sourced does not mean
  settled: `customer_owner` is the record's owner, which on a deal someone else has been running
  is routinely not the person on the calls. Show which of the two the name came from, and let the
  confirmation question decide it.
- **Show the CRM opportunity name, not just the numbers.** That is what lets the person catch a
  record pointing at a renewal or a closed-won original instead of the deal being planned.
- **"None identified" / "Not assigned" is a valid confirmed value** (`output_standard.md` §7). Do not fill Partner to look complete.
- If the person corrects a value, use theirs and mark it sourced. They outrank the CRM.
- **Name which CRM each value came from** in the Source column: "Salesforce, via Aircover" or
  "HubSpot, via Aircover", not a bare "CRM". In an org running both, that column is the only
  thing on screen telling the person which record they are about to accept.
- **When the `crm` block is empty, ask for the header values** rather than shipping blanks: close
  date, amount, stage and opportunity name in one free-text question, blank acceptable for any,
  and anything they give is sourced. Never offer to go fetch the CRM record: it is in the Aircover `crm` block or it comes from the
  person.

### 5. Inventory the meetings, check for gaps, then ask for scope

`completed_meetings` is not capped, but it only contains meetings that produced a transcript.
Held calls that never processed are omitted silently, so a capture outage looks identical to an
absence of evidence. Never skip this step.

**5a. Reconcile.** Compare the newest `completed_meetings` date against `last_meeting_date` from
`get_deals`. If they diverge, call `list_meetings` over the gap window and count the prospect-side
meetings with no transcript. Report the gap to the person before running anything:

> 20 meetings transcribed through 7/9. 11 meetings held 7/10 to 8/14 have no transcript.

**5b. Ask for scope.** Once the count is known, ask whether to run all transcribed meetings or a
date range. Use tappable options: all meetings, last 90 days, a custom range. The count drives the
ask, so give it first: 20 meetings across three agents is 60 runs. Whatever they pick becomes the
worklist. Scope is the person's explicit choice, never a quiet budget cut by the assistant.

**5c. Build the worklist before calling any agent.** Write every meeting x agent pair to disk with
a status column, all `pending`. Mark each row `done`, `no_transcript`, or `out_of_scope` as you go.

**Hard gate: do not write values.json while any row is `pending`.** `no_transcript` and
`out_of_scope` are acceptable terminal states. `pending` is not. Partial agent coverage is a failed
run, not a fast one. All three agents must cover the same meeting set, or items get compared
against evidence that was never measured for them.

**5d. Run.** Discover each agent id via `list_agents`, matching `config.agents.*.title_keywords`.
Apply each role's `category` filter from config first. When several agents still match one role, prefer one visible to the whole org (`visibility` 2), then one that is not a
live, digest or copy variant, then the one with results on the most in-scope meetings, and name
your pick in the final response.
Try deal level `get_qualification_results(deal_key, template_id)` for MEDDPICC and Deal Readiness
first; it is often empty, in which case fall back to per meeting. Loop
`agent_results(meeting_id, template_id)` over the worklist using the full 32 character meeting id.

**Aggregate latest wins.** Each result is timestamped by its meeting. For any dimension, take
the highest score achieved on the most recent meeting that produced evidence, and keep the
evidence text from that meeting. A dimension proven in meeting 3 does not become unproven
because meeting 9 was a technical working session.

**Join on the entry `title`, never the positional key.** A property with `max_score: 0` is
unscored extraction, not a scored dimension. Write results to disk as you go rather than holding
them in context. Report per-agent coverage counts in the final response.

**5e. Collect attendance while you are here.** The Stakeholder Map needs `customer_attendees`
across every meeting in scope, not just who spoke. Agents see speakers; the grid needs the room.
Build the attendee roster in the same pass as the agent runs.

### 5f. Optional email enrichment
If a mail tool is present in the tool list, search it scoped to the prospect domain and the deal
window to corroborate the Commercial bucket. If no mail tool is connected, skip silently and carry
on; most orgs will not have one. Never make the run depend on it.

Tag email-sourced values distinctly from agent-sourced ones. The workbook rule is that every
marker traces to a named source, and "the AE's sent mail" is a different source than "the Close
Plan agent scored this."

### 6. Map to the buckets
Follow `references/field_source_map.md` exactly, **including the section 6a ceiling rules**.
The threshold table alone overstates the deal, because several items ask a harder question
than their source property answers: champion asks for purchase influence, decision process
asks who signs, differentiation asks for the full set, champion backup asks for a plan rather
than a contact list, onboarding owner asks for a person rather than a team. Apply the ceilings
after the threshold. And never award a positive marker from an empty property, per section 6b.

In short: MEDDPICC feeds champion, economic buyer, decision criteria, decision process,
competition, and the business case metric. Deal Readiness feeds technical win, budget,
procurement, legal redlines, mutual plan, and dated next step. Close Plan feeds stakeholder
mapping, compelling event, security review, integration scoping, product gaps, pricing, quote,
differentiation, objections, migration plan, and onboarding owner.

**Two items are derived rather than read off a property, and you derive both:**
- `forecast_matches`: the band from step 3b against the deal's own signals. **The engine never
  sets this row; you do.** Banding the stage is necessary but not sufficient, so use the rule the
  template label already states, "don't call it Commit if 3+ boxes above are unchecked". Count
  the Timeline & Risk items above it (the six rows before this one) that are not `yes`:
  - `late`: 3 or more not-yes is a mismatch, so `no`. One or two, `partial`. None, `yes`.
  - `mid`: 5 or 6 not-yes is `no`. Three or four, `partial`. Two or fewer, `yes`.
  - `early`: a thin plan is what an early stage claims, so consistency holds and this is `yes`.
    Where the Commercial bucket shows a quote out or pricing agreed, the deal has outrun its
    stage: `partial`, and say in the comment that the CRM stage needs advancing.
  - `closed` or `excluded`: the stage makes no forward forecast claim, so there is nothing to
    contradict. `yes`, with a comment saying the row asserts nothing and why.
  Name the band in the comment either way, so the AE can see what the marker was measured
  against. Falling back to `unknown` once the seller has banded the stage defeats the point of
  asking.
- `champion_backup`: derived, and capped by the section 6a rule. Stakeholder breadth is not a
  backup plan.

**Route the Close Risks tags rather than dropping them.** The Risk Assessment sheet is gone, but
its content is not. Each tag lands in the Comments column of the Action Plan row for the item it
bears on, per the mapping table in `field_source_map.md` section 3.

### 7. Set markers
Thresholds are in the reference file. On a 0 to 3 dimension: 3 is `yes`, 2 is `partial`,
0 or 1 is `no`, and a dimension with no data at all is `unknown`. "No data" means the property
was absent or the agent never ran. A property that ran and simply did not cover the thing is
`no`: the agent looked. This catches rows 39 and 40, whose source is a fragment of Close Plan
Technical Scope rather than a score of its own. See `field_source_map.md` section 6b.

Markers render as **Yes / In Progress / No / Needs Input**, with a matching dropdown on every
marker cell so the AE picks rather than types. The bucket formulas recompute live when they do.

### 7b. Write the cells to the output standard
Read `references/output_standard.md` and apply it to every written cell. The rules that most
often go missing on a first pass:

- **Every non-Yes item needs a Recommended Action.** The engine prints a warning naming any
  generated row you left empty. That warning is a build failure, not a note.
- **Column C prescribes, it does not diagnose.** Start with a verb and end with the exit
  criterion. Evidence belongs in Comments, not in the action.
- **No scoring machinery in the prose.** "Economic Buyer scored 0" becomes "nobody with budget
  authority has appeared on any call". Sweep all four tabs before presenting.
- **Owners only where a call named one, or where the role is structural.** The AE owns
  commercial actions and the SE owns technical validation; a customer-side owner needs a call
  behind it. Never invent a due date. "Not named" plus naming them as the first action is the
  correct output.
- **Fill the "?" bubbles honestly.** A sparse Stakeholder Map that hides missing personas
  defeats the tab. Place a gap bubble wherever the deal needs a persona no call has produced.
- **The vendor impact answer is never blank.** Observed and expected value, then quantified ROI not found, then the
  metrics to establish, choosing ones actually attributable to the deployment.
- **The use case answer leads with primary, then secondary.** The ranking is the answer. The
  "how are they using it today" answer is the deployment as it stands; keep them distinct.
- **The coverage note is not optional.** Write `values.coverage_note` from the step 5
  worklist: how many meetings, the window they span, where coverage stops against the CRM
  close date, and how many held meetings produced no transcript. `output_standard.md`
  section 6b has the shape. The engine warns if it is missing and that warning is a build
  failure, exactly like a missing Recommended Action.

- **Pick the Summary's risks and next actions.** Write `values.summary.risks`: the three
  things most likely to stop this deal closing on its date, one line each, most serious first,
  each naming the evidence (a date, a person, a missing step). Write
  `values.summary.next_actions`: up to five Health Score item keys, in the order the AE should
  work them, choosing what most moves the close date rather than bucket order. Each must be an
  item that has an Action Plan row (not a Yes). The Summary shows the first sentence of each
  action, so write that sentence to stand alone. Without these the engine falls back to the
  items scored No, in sheet order, and says so; that fallback is a safety net, not the output.

Then run the section 8 consistency pass: tabs agree, map against row 10, overview against the
buckets, banned language sweep, word budgets.

### 8. Build and present
Write `values.json`, then:
```
python fill_close_plan.py --template Close_Plan_TEMPLATE.xlsx --values values.json \
  --crm crm.json --out "Close Plan - {Company} - {YYYY-MM-DD}.xlsx" --config config.json
```
The engine prints the five bucket percentages, the overall, the action row count, and any
missing-action, missing-coverage-note or Summary fallback notes. Read that output before presenting: it is
the fastest check that the mapping did what you intended.

Before writing anything the engine preflights the config against the template and exits on a
mismatch: a bucket range that does not line up with its header, an item row with no label in
the template, or a persona with no prepared row. If you see "Layout does not match the
template", `config.json` and the template asset have drifted apart. Fix them together with
`build_template.py`; do not work around it by editing config alone.

Copy the result to the outputs directory and call `present_files`. A file that is written but
never presented is unreachable on mobile.

Then tell the person, in two or three lines, the overall score, the weakest bucket, and the
single most important action. Do not restate the sheet.

### 9. Sync the plan back to Aircover
When `sync.enabled` is true (the shipped default), the finished plan is also saved into
Aircover as a new version of this deal's Close Plan document, so the deal page and the
workbook say the same thing and the next agent run builds on what was delivered instead of
regenerating over it. With `sync.mode` `auto` this happens without asking; `confirm` shows the
rendered document and waits for a yes; `off` skips the step.

**9a. Read the contract.** The save targets the deal-level Close Plan template, not the
meeting-level Close Plan agent from step 5. Find it with `list_account_deal_agents`: the
`deal_agent` category's default template when it is a close plan, otherwise the template named
Close Plan in that category. Name the template you used in the final response. Then call `get_account_deal_agent_results(deal_key, <that template id>)`. Keep two things from the result: `current_version`, and
`declared_sections` (each with `entry_id`, `title`, and the author's `description`).

**9b. Render.** Write Markdown for each declared section, following that section's
`description` exactly: its headings, its labeled lines, its table header, its fixed item
list. The section contract is usually smaller than the workbook (the common Close Plan
section asks for 13 checklist rows where the workbook scores 26): condense onto the
section's own items, keeping the marker the workbook's evidence supports; the full detail
stays in the workbook, never padded into the section. Header values the person confirmed or corrected in
step 4 are the values here, so the deal page matches the workbook. Unknowns keep the section's own fill-in or Needs Input convention;
never promote a Needs Input to an answer to make the document read finished.

**9c. Save.** Call `save_account_deal_agent_document` with the `deal_key`, the same
`template_id`, `sections` as a map of entry id to the rendered Markdown, and `base_version`
set to the `current_version` from 9a. Omit a section you cannot fill rather than sending an
empty string: omitted means unchanged, empty means cleared. Then tell the person it synced,
with the version number and the `url` the result returns, in the same closing lines as the
score summary.

**9d. When the save is refused**, the workbook is still the deliverable; the sync is
additive, so never let this step fail the run.
- *Writes not enabled for the org*: say that an Aircover org admin needs to turn on **Allow
  MCP Clients to Write** in the org settings, once, and that the plan will sync on the next
  run. Do not retry.
- *Version conflict* (someone saved between 9a and 9c): re-read. If the newer version is
  this same run's content, stop, it is already there. Otherwise someone edited the document
  mid-run: show the person what changed and ask before overwriting. Never silently stomp a
  hand edit.
- *Agent run in progress*: wait a minute, re-read, retry once. Still locked, report it and
  move on.
- *Caller lacks edit rights on this deal's plan*: name the role problem plainly, as in
  step 2; it is not a missing deal or a missing document.

## Reading the score honestly
Transcribed calls skew toward technical working sessions. Commercial conversation often happens
over email, Slack, and direct exec contact, and none of it is in the transcript corpus. Expect
the Commercial and Competition buckets to come back low even on healthy late stage deals, and
expect low bucket scores to be normal rather than alarming.

**Recurring office hours and training sessions contaminate the score.** In those calls the
customer's reps review their own pipeline, so the agents extract signals about *their* deals and
attribute them to yours. A pricing or signature gap that names people who are not in the deal is
the tell. Exclude office hours from scoring, or verify every extracted name against the deal's
known stakeholders before trusting the item.

**When transcript coverage ends before the CRM close date, the score is not a deal read.** State
that on the face of the workbook rather than scoring around it: that is what the coverage note
cell is for, and it is required. If coverage ends weeks before close, the pricing, procurement,
and legal window is entirely unobserved, which is exactly where the Commercial bucket comes
from.

Present the overall as **coverage of what calls can evidence**, not as deal health. If the AE
reads 22% as "this deal is dying" when it is a Negotiation stage renewal, the number has done
harm. Say plainly which items are Needs Input because the evidence lives outside the calls.

## Rules
- Never fabricate. If a tool returns nothing, mark the item Needs Input and say so. Do not infer
  a value from an adjacent field, and do not reuse template example text. Needs Input means the
  data is missing, not that the answer is no: if an agent ran and found nothing, that is `no`.
- Every marker must trace to a specific agent property and score. If you cannot name the
  source, the marker is `unknown`.
- Join `agent_results` on title. Discover field names at runtime; schemas vary per org.
- Full 32 character meeting ids. Filter by `prospect_org` or full `deal_key`.
- No em dashes. Lists for enumerations. Times in PT, no UTC.
- The workbook is internal to the selling team, not customer facing, so plain deal commentary is
  fine here. Keep it factual and evidence led rather than editorial.
- Write for an AE, not for a reviewer. Every cell answers "what do I do next", not "what did the
  model find". Scoring vocabulary never reaches the sheet.
- A cell that only describes the gap is unfinished. Prescribe the next action, name an owner
  where a call named one, and define what done looks like.
- No company name belongs in the code, the template asset, or this file. All of it comes from
  `config.vendor` and `config.crm`.
- Later evidence that contradicts an earlier higher score supersedes it. Silence does not.
  See `field_source_map.md` section 7, and watch for an earlier positive that was scoped to a
  smaller deal: a price agreed for a pilot is not pricing alignment for a rollout.
- Every meeting attendee is either placed on the Stakeholder Map grid or named in
  `stakeholders.unplaced` with the reason. Take function and seniority from what a call states
  first, then from the attendee title in the transcript header, which some orgs enrich and some
  leave as a bare email. Where the function is evidenced and the level is not, place them on the
  **Seniority not stated** row rather than dropping them; unplaced is only for people with
  neither axis. Guessing an axis is fabrication, but dropping people is the more common error,
  because the grid then under-reports who has been in the room. A grid with no named placements
  at all means a source was skipped. A red "?" in a cell where someone has actually attended is
  worse still.
- **Influencer slots fill from the attendee roster too, not just agent properties.** An
  attendee whose title names their function fills the matching influencer row. Reserve `?` for a
  function absent from every source. Never leave a slot blank while placing that same person on
  the grid above it.
- **Every persona row carries a note, including the `?` rows.** A gap row with an empty note is
  why a delivered plan reads as half-finished. Say what the calls do establish about that
  function, and what would close it.
- The C-Suite band takes only someone stated to be C-level. Owning the budget is not a title:
  that person is the Economic Buyer persona and does not also go in the band.
- Never paint a marker colour by hand on a finished workbook. If a colour is wrong, the rule
  is wrong; fix `add_live_colors` and rebuild.
