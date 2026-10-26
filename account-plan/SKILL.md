---
name: account-plan
description: Generate or update a strategic account plan for a whole account, rolling up every opportunity, meeting, and stakeholder across that account's deals in the Aircover Production account, enriched with public company research. Use whenever someone says "build an account plan", "account plan for [company]", "strategic account plan", "account review", or "whitespace analysis", or asks where the growth is in an account, who is not covered, or what the whole relationship looks like. Also use it to refresh an existing plan: "update my account plan", "update the [company] plan with my latest meeting", or "add the [date] call to the [company] plan" adds only what is new and rebuilds the same file in the same format rather than starting over. For a single opportunity use the close-plan skill instead.
---

# Account Plan

Turn every open and recent opportunity at one account into the team's standard account plan:
the snapshot, the customer's world, the stakeholder map, the footprint and whitespace, the
GTM tracks, the next steps, and the competitive picture. Each claim is traced to a call, the CRM,
a public source, or the account team's own judgment, and labelled with which. The finished
plan is also synced back into Aircover as a new version of the deal's account plan document
(step 9b), so the deal page and the delivered file never disagree.

> **Account level, not deal level.** An Aircover deal is one opportunity. An account with three
> opportunities is three `deal_key` values, three CRM records, and three meeting sets that must
> be unioned and deduplicated before anything is written. A plan built from one `get_deal` call
> is the failure this skill exists to prevent.

> **Four sources, never blurred.** Calls, CRM, public research, and the account team's own
> knowledge each answer different parts of this document. An unsupplied fact renders as a
> labelled INPUT NEEDED question, never as plausible prose. A finished-looking account plan
> with three invented seat counts is the worst thing this skill can produce.

## Bundled resources
- `config.json` - everything install-specific. Change this, not the code.
- `scripts/build_account_plan.js` (docx) and `scripts/build_account_plan_pptx.js` (pptx) - the
  document engines. Both read `config.json` plus a values file. The docx engine also runs the
  content checks for both formats.
- `scripts/verify_external_claims.js` - refuses any external claim without a ledger row (step 6b).
- `scripts/check_aircover_fit.js` - checks the plan fits Aircover's section size cap (step 9b).
- `references/section_source_map.md` - which source feeds every subsection. **Read before gathering.**
- `references/output_standard.md` - how every block must read. **Read before writing any prose.**
  Skipping it produces a research report about a company instead of a plan for an account.
- `references/gtm_strategy_playbook.md` - the six GTM tracks. **Read before generating section 6.**
- `references/example_account_plan.json` - the full values schema with a fictional account. Copy
  the shape, never the content.

Copy the scripts you need and `config.json` into the working directory. **Write cached
resolutions (vendor, stage bands, use case vocabulary) to both the working copy and
`$SKILL_DIR/config.json`**, because the working directory is wiped between runs. If the skill
directory is read-only, say so once at the end.

## Requirements
- The **Aircover Production** connector. Production and Staging share tool names, so "agent not
  found" usually means the wrong environment.
- Code execution, file creation, and Node with `docx` and `pptxgenjs` (check with
  `node -e "require('pptxgenjs')"` before installing anything).
- Web search and fetch if `config.research.enabled` is true. Without them, set it false and the
  external sections become INPUT NEEDED.
- **No CRM connector.** CRM fields arrive inside each `get_deal`'s `crm` block. Never ask the person
  to connect Salesforce or HubSpot, and never query one to fill this document.

## When to use something else
- One opportunity, closing soon: **close-plan**.
- The shared customer-facing roadmap: **aircover-mutual-action-plan** (a separate skill).
- One upcoming meeting: **pre-call-prep**. A whole pipeline: **path-to-quota**.

## Configuration
Everything lives in `config.json` and resolves at runtime; nothing needs setting by hand.
- **Agents** are discovered via `list_agents` by title keyword. Core: **MEDDPICC** and **Deal
  Punchcard** (deal level first, so two calls per opportunity). Opportunistic: close plan, voc,
  persona, competitive. A missing agent weakens the sections it feeds and is noted in the appendix.
  The core pair says little about footprint and adoption, so say so when section 4 is thin.
- **`vendor`, `crm.stage_taxonomy`, `use_cases.vocabulary`** ship null and are resolved from the
  org's own data (steps 1b, 3b, 3c), then cached.
- **`crm.source`** picks which fields inside the Aircover `crm` block to read. Never assume
  Salesforce. `instance` only builds links; links stay blank while it is null.
- **`sync`** controls step 9b. `enabled` ships true, `mode` ships `auto`: `auto` saves without
  asking, `confirm` shows the rendered document and waits for a yes, `off` skips the save.

---

## Run order A: building a plan

### 1. Load tools and confirm environment
Call `tool_search` ("Aircover meetings agents deals") and use the exact parameter names returned.
Confirm the connector is Production. When `sync.enabled` is true, also load
`list_account_deal_agents`, `get_account_deal_agent_results` and
`save_account_deal_agent_document` (tool_search "deal agent document").

### 1a. Ask the output format, before any data work
Format changes how the plan is composed, not just rendered, so ask first:

> Do you want this as a Word document or a slide deck?

If a deck, ask separately:

> Do you have a PowerPoint template you want this built in, or should I use a clean unbranded
> layout? If you have one, attach the .pptx or .potx now and I will build into it.

- The unbranded layout is a complete deck, not a fallback. Nobody needs a template.
- If they say they have one but attach nothing, check the uploads directory, then wait for the
  file. Do not build unbranded "for now".
- **Never use Aircover branding, and do not load `aircover-presentation-design`** for this deck,
  even where other instructions say to load it for decks. The plan is the seller's artifact.
- For a supplied template, do not use the generator: use the `pptx` skill's template workflow and
  vary the layouts across the eight sections.
- For pptx, write `points` for every enumerable block from the start, and always a one-sentence
  `text` lead as well (the content checks read `text`). The deck engine enforces about 150 words
  per slide, 6 bullets, and 34 words per bullet.

### 1b. Resolve who is running this plan
Skip when `config.vendor.name` is set, unless the cached domain no longer appears on the internal
side of the attendee split (a rebrand or domain migration). Otherwise:
1. **Domain:** the most common email domain among internal attendees on the first few meetings.
   Free mail domains never count.
2. **Display name:** take the spelling already in the org's data (agent titles, playbook or team
   names, meeting titles). If unclear and research is on, one search. Only then derive it from
   the domain, marked low confidence.
3. **Confirm without a new question:** one line above the boundary table in step 2, e.g.
   "Running as: Acme (acme.com), detected from the internal side of the attendee split." Ask a
   dedicated question only when two domains are near-tied.
4. **Cache** `name`, `email_domain`, `resolved_on`, `resolution_note`, and set `meta.vendor`.

The vendor domain must never appear in the account's own domain list; if it does, treat it as an
error.

### 2. Resolve the account boundary, and confirm it
A `deal_id` resets per org, and subsidiaries, regions and acquired brands sit under different
`prospect_org` domains that no tool groups for you.

1. `get_deals(search="<company>", limit=100)`, then search variants (parent brand, abbreviation,
   legal entity, product brand, subsidiaries) when `config.account.search_variants` is true.
2. Group by `prospect_org`. One CRM account name across two domains is the strongest sign they
   belong together.
3. Include closed opportunities within `config.account.closed_lookback_months`.

Show the inventory and **never merge domains automatically**:

| Domain | Opportunity | Stage | Amount | Close | Last meeting |
|---|---|---|---|---|---|
| acme.com | Acme Platform Expansion | 3 - Prove it | $240,000 | 2026-11-30 | 2026-08-10 |
| acme-eu.com | Acme EU Rollout | 2 - Value Creation | $145,000 | 2027-01-31 | 2026-06-04 |

Then ask **two** questions:
1. Is this the account, and is anything out of scope?
2. **Are there open opportunities missing from this list?** Aircover only has deals that had a
   captured call, so an opportunity with no calls cannot be found by any search. Ask for name,
   value and stage, all optional, never a CRM id.

**A deal record with no CRM name, amount or stage and no meetings in the window** is dormant: list
it in the inventory and the coverage table, but do not count it as an open opportunity.

**A manually added opportunity** gets `manual: true`. It counts in every total and appears in the
coverage table with zero meetings, but never gets call-sourced claims. Re-check the strategic
narrative after adding one, since it often changes the account's size.

Running an account the caller does not own is normal. To scope to a person or team, use
`rep="<email>"` or `team_ids` from `get_teams`. A viewer-role caller can only pass their own
email; an error there means insufficient role, not a missing account.

### 2a. Confirm the value field
The amount field may not be the figure the team plans against (TCV vs annual, incremental vs
blended). Ask once, with the numbers on screen:

> The amounts above come from the `{amount field}` field on each opportunity. Is that the figure
> you plan against, or do you use a different one?

Offer: use these, use a different CRM field (re-read it from the same `crm` block), or enter by
hand (authoritative). Record one sentence in `meta.value_basis`, e.g. "Values from the CRM amount
field, confirmed by the account team on 2026-09-12." It renders under the opportunity table. Never mix bases across rows silently. Re-ask
on updates only if the person raises it or a CRM amount changed.

### 3. Pull every opportunity
`get_deal(prospect_org, deal_id)` per confirmed opportunity, writing each result to disk as it
returns (agent results in step 5 too), so nothing lives only in context. Union the meetings, deduplicate by
the full 32 character id, and keep a meeting-to-opportunity map: sections 4 and 7 are
per-opportunity, sections 1, 2, 3 and 8 are account-wide.

Read the CRM block through `config.crm`. If a CRM record's name or amount disagrees with what the
person confirmed, ask which is right. A populated CRM block is not proof of a live sync; an empty
one is a placeholder, not an error.

### 3b. Discover the stage taxonomy
Skip if cached. Copy a confirmed banding from the close-plan skill if installed. Otherwise
`get_deals(sort="sfdcCurrentStage", asc=false, limit=100)`, page until the distinct stages stop
growing, and **band them with the person** (stage names mislead). Never invent or borrow stage
names. Cache the result.

### 3c. Resolve the use case vocabulary
Skip if cached. Section 4 computes product whitespace by subtracting selected use cases from this
list. Source it from the account_plan template's own use case catalogue if it has been set (not
`[SET PER CUSTOMER]`), then extraction agent taxonomies, then playbook/card/VSE titles, then ask: five
to ten items at the level a customer would recognize. Cache it.

### 4. Inventory the meetings, report the gaps, then ask for scope
`completed_meetings` only lists transcribed meetings, so a capture outage looks like silence.

**4a. Reconcile per opportunity against `meeting_ids`**, not against `last_meeting_date`:
1. Take every `meeting_ids` entry (`<start_time>/<room-or-id>/info.json`), drop future ones and
   any in `cancelled_meeting_ids` (unless it has a transcript, which proves it was held). Add any
   `completed_meetings` entry missing from `meeting_ids`.
2. **Deduplicate on `start_time`.** When the customer also runs Aircover, one real meeting
   appears under two or three ids; counting ids overstates meetings by 20% or more.
3. Subtract `completed_meetings`. Split what remains at the newest transcript into trailing gaps
   (capture problem or quiet account) and interior gaps (the analyzed calls are a sample, say so
   on the document).

Write held-meeting dates to `coverage.meetings_held_dates` and fill `coverage.attendance`. **Never
describe a cadence gap from analyzed calls**: the gap between two transcripts is an evidence gap,
not a relationship gap.

**4b. Do the run math, then ask scope.** Opportunities x meetings x agents can be large. Under
`config.scope.max_runs_without_confirmation`, use the default window without asking and say so.
Above it, give the number and offer: every meeting, the
default window, the most recent N per opportunity, or a custom range. Sample per opportunity,
never off a merged list. The agent set is a separate decision; never drop an agent silently.

**4c. Build the worklist** (meeting x agent, status `pending`) before calling any agent. Do not
compose while any row is `pending`.

### 4d. Propose the account team, then confirm it
Propose everyone on the internal side who joined a call, plus `customer_emails` on the deal, and
ask who to add or remove (exec sponsors and partner managers rarely join calls). Record a role only
if the person or a call states it. Section 6 needs owners, so this list matters. **Never put a
customer employee on the account team.**

### 5. Run the agents
Discover ids via `list_agents`, applying each role's `category` filter from config. When several
agents still match one role, prefer one visible to the whole org (`visibility` 2), then one that is not a live, digest or copy variant, then the one with results on the
most in-scope meetings, and record the pick in the appendix. For `deal_level_first` roles, try
`get_qualification_results(deal_key, template_id)` once per opportunity, else
`agent_results(meeting_id, template_id)` over the worklist.

- **Latest wins, per opportunity, then roll up.** Never let a dead renewal's picture leak into a
  live expansion.
- **Never average across opportunities.** State the spread instead: "the champion is evidenced on
  the expansion only."
- Join on the entry `title`, never the positional key. `max_score: 0` is extraction, not a score.

### 6. External research, including the SWOT
Gated by `config.research.enabled`. Fills business priorities, industry trends, and the SWOT.

Work each SWOT quadrant as its own research job using `config.research.swot.query_patterns`:
- **Strengths / Weaknesses** are internal to the customer's business (filings, earnings calls,
  and customer-stated weaknesses from calls, which are the strongest entries).
- **Opportunities / Threats** are external (research only).
- Every entry carries a source. Two to five per quadrant; if research found nothing, say so.
- **Never a seller-centric weakness** ("they have not standardized on our platform").
- Where a researched weakness matches a pain a customer described on a call, cite both.

Research rules: fetch what you cite; prefer filings and IR over trade press; financial figures
from filings or IR only; reject excluded sources and vendor content marketing; every trend names
its mechanism into this account; stay within `recency_months` and `max_searches`.

### 6b. The evidence ledger, written as you research
The risk is drift: a real number from the right source attached to the wrong period, division or
region. So every external claim gets an `external_ledger` row **when you take the fact**:

```json
{ "id": "q2-ebit", "claim": "Group EBIT rose 30% in Q2 2026",
  "quote": "Operating profit (EBIT) increased 30 percent to EUR 1.9 billion (Q2 2025: EUR 1.4 billion)",
  "period": "Q2 2026", "entity": "DHL Group", "url": "https://...", "publisher": "DHL Group",
  "source_date": "2026-08-05", "retrieved": "2026-09-12", "obtained_by": "fetch" }
```

1. **A snippet is a lead, not a source.** `obtained_by` must be `fetch`.
2. **The quote is verbatim** from the fetched page.
3. **Bind `period` and `entity`** before writing the claim.
4. **Your arithmetic is not the source's.** Set `derived` and `derived_from`.

When sources conflict, record both with `conflicts_with` and `conflict_note`. Cutting a claim you
cannot back is normal; the appendix lists what was cut. The ledger never renders.

**Call quotes follow the same rule.** Copy fragments from the transcript, never compose them from
an agent summary. Verify against `get_meeting_transcript` (agent output is a summary, so a quote's
absence there proves nothing), and set `evidence_agent` to `transcript <meeting_id> @00:26:42`.
If no usable fragment exists, keep the finding and drop the quote.

### 7. Optional internal corpus
`ask_documents` searches the selling org's own content. Useful for section 8 positioning. Tag it
as vendor material, never customer evidence. Skip silently if empty.

### 7b. Ask how to handle the GTM strategy and the mutual action plan
Ask both in one question set, after the evidence exists:

**GTM strategy** (`config.gtm.modes`): have Aircover draft it, I'll write it myself, or something
else. On **draft**, follow `references/gtm_strategy_playbook.md`: six tracks (ADR, Customer
Education, CSE / PS, Partner, Post Sales, Executive), each with objective, why now with evidence,
two to four plays, owner, and exit criterion, opened by a ranking of the two tracks to spend on
first. A track with no inputs renders INPUT NEEDED. Everything generated is labelled a
recommendation. On **write it myself**, render each track's definition plus the questions it needs
answered.

**Mutual action plan.** Built only by the separate `aircover-mutual-action-plan` skill; this plan
holds one line per milestone plus a link. Check it is installed before offering to build one:
- Installed: build it with the MAP skill (after this plan, as a separate run), link my own, skip.
- Not installed: link my own, skip. Say the MAP skill is not installed and name it.

On **skip**, state on the document that no shared plan exists. Set `sections.gtm.mode` and
`sections.next_steps_map.map_mode` from the answers.

### 8. Compose the sections
Read `references/section_source_map.md` and `references/output_standard.md`, then write. The
rules most often missed:

- **Challenge prompts are a checklist, not content.** Each is evidenced, externally supported, or
  a hypothesis, and a hypothesis only appears in the validate list.
- **Unknown stakeholders are findings.** `unengaged`: named on a call, never met. `role_gaps`:
  roles the account needs with no name at all, derived from MEDDPICC decision process and the
  Punchcard security, procurement and legal dimensions. Each gap states its consequence, the
  opportunities at risk, a route in, and an owner.
- **Attendance is not advocacy.** Champion, blocker and detractor need evidence. Name a detractor
  in the executive summary alongside the champion.
- **Adoption and usage data is not in Aircover.** Ask for an export; never infer usage from call
  frequency.
- **Whitespace is computed:** business units, regions and functions never seen on a call.
- **Use cases:** write only `use_cases.selected` from the vocabulary. The builder prints the
  not-in-play half. A use case is in play when a customer describes doing it, not when a rep
  pitched it.
- **Every opportunity gets a next step**, including "none agreed".
- **Budget and buying cycle: assemble, never investigate.** Label each statement `evidenced`
  (agent or call), `public` (filings, public companies only) or `inferred` (a convention applied
  to a known fiscal year), and say "inferred" in the sentence. A `Budget Confirmed` property that
  never fired across N meetings is a finding: budget has never been discussed.
- **Strategic narrative:** work five dimensions, not just the agent output: expansion headroom,
  referenceability, logo and segment credibility, design partnership, strategic displacement.
  Only the first is derivable from tools; the rest are labelled recommendations. Record each in
  `strategic_narrative.dimensions`.
- **Write the executive summary last**, asserting nothing that is not in the body.

Then run the consistency pass (`output_standard.md` §9) and both checks:

```
node build_account_plan.js --values account_plan.json --config config.json --out /tmp/gate.docx
node verify_external_claims.js --values account_plan.json
```

Run the docx engine as the gate **even for a deck**; it holds the content checks. Discard
`/tmp/gate.docx`. Never pass `--warn-only` to get past a failed claim: fetch and quote the source,
or cut the claim.

### 9. Build and present
Write `account_plan.json` to the schema in `references/example_account_plan.json`, then:

```
node build_account_plan.js --values account_plan.json --config config.json \
  --out "Account Plan - {Account} - {YYYY-MM-DD}.docx"
```

(or `build_account_plan_pptx.js` for a deck). **Fix every warning and rebuild.** Add `--strict`
when running unattended.

### 9a. Present the document, and only the document
Copy the .docx or .pptx to the outputs directory and call `present_files` with that one file.
**Never present or mention the values file**; it is working state.

### 9b. Sync the plan back to Aircover
Aircover is where the plan lives between runs: chat files are wiped, and run order B reads the plan
back from here. `account_plan` documents are versioned, restorable from the version dropdown,
visible to the rep, and syncable to the CRM. Governed by `sync`: `auto` saves without asking,
`confirm` shows the rendered document first, `off` skips (then say an update will need a full
rebuild).

1. `list_account_deal_agents` for the `account_plan` category's `default_template_id`. Use the
   org's default; never shop for another template, and never create or modify one.
2. `get_account_deal_agent_results` on the anchor deal for `declared_sections` and
   `current_version`.
3. `save_account_deal_agent_document` with `base_version` set to that `current_version`.

**Write under the template's own `## ` headings, in its order, never renamed, and follow each
heading's own guidance in the template exactly:** its word and row caps, table headers, opening
sentence, and fill-in lines. The template's description is the contract; read it before
composing. The Aircover version is therefore a condensed plan. Keep the findings the evidence
supports most strongly; the full detail stays in the delivered file. The stock global template
declares nine headings:

| Aircover heading | Fed by |
|---|---|
| Executive Summary and Account Snapshot | Section 1, written to the template's opening sentence |
| Account Objectives | **Our** commercial objective for the account: expansion units and use cases (section 4), contract structure, stated volumes, the date it must land. Not the customer's goals |
| Customer Landscape and Market Insights | The customer's own targets and KPIs, challenges, trends and the SWOT (section 2), plus coverage caveats |
| Relationship and Stakeholder Mapping | Section 3, in the template's table format and row cap |
| Opportunities, Footprint and Whitespace | Section 4 |
| Qualification Gaps | Role gaps, open INPUT NEEDED questions, unevidenced qualification dimensions |
| Cross-Functional GTM Strategy | Section 6 |
| Strategic Next Steps and Mutual Action Plan | Section 7, in the template's table format |
| Competitive Landscape | Section 8, applying the template's own competitor tests |

If an org's template declares different headings, map the same content onto them by meaning.

**Where the template and this skill disagree, the template wins inside the declared headings.**
Its caps apply to those headings only. If a heading's guidance excludes something this skill
produces (public research, our own meeting counts), leave it out of that heading and carry it in
the extras block below instead; the delivered file keeps it either way.

**Researched claims go inside these headings where the template allows, not only in the leftover block.** Aircover
regenerates the plan automatically after each new meeting and keeps the declared headings, but
progressively drops anything outside them. The same goes for evidence coverage caveats (interior
gaps, "the calls are a sample"): put them under a declared heading, not only in the extras. After the last heading, add `### Account Plan Extras`
(consolidated SWOT, coverage table) and pass it as `leftover_heading`, plus a
six-line `### Plan settings` block for run order B: format, template, deal keys, value basis,
evidence watermark, revisions.

Write the markdown directly into the save call, not via a script to a file. First run
`node check_aircover_fit.js --values account_plan.json`: the section cap is 31,900 characters and
an oversized save is refused. Size follows evidence density, not opportunity count. Trim in the
order the script prints; never trim evidence, quotes or INPUT NEEDED questions. If it only fits by
cutting evidence, save the declared headings without the extras and say so.

**The sync is additive: a refused save never fails the run.** The plan file is still the
deliverable. Handle each refusal plainly:
- *Writes not enabled* (save tool missing, or refused for permissions): an Aircover org admin
  needs to turn on **Allow MCP Clients to Write** on the Aircover MCP settings page, once; the plan
  syncs on the next run. Do not retry.
- *Version conflict*: re-read. If the newer version is this run's content, stop. Otherwise someone
  edited mid-run: show what changed and ask before overwriting. Never stomp a rep's edit.
- *Agent run in progress*: wait a minute, re-read, retry once, then report and move on.
- *No edit rights on this deal's plan*: name the role problem plainly.
- *Too large*: trim as above and save again.

### 9c. Tell them what they have
Three or four lines: opportunities and value in scope, meetings analyzed vs held, the largest
whitespace or coverage gap, and how many INPUT NEEDED blocks wait on them. Then one line on the
sync: version N with the `url` the save returned, or which refusal stopped it and what unblocks it.
Close with:

> When you have another call with them, just say "update my DHL account plan" and I'll add it.

---

## Run order B: updating an existing plan
Triggered by "update my account plan", "add Tuesday's call to the {account} plan", or similar.
**An update is not a rerun:** it pulls only what is new and touches only what that changes, so it
never reshuffles wording the team has already edited or presented.

**B1. Read the plan from Aircover.** `get_account_deal_agent_results` for the `account_plan`
template on the anchor deal: the declared headings plus `### Plan settings` (boundary, format,
template, value basis, watermark). The Aircover document wins on content, because a rep may have
edited it there. You are merging into that markdown rather than a values file, which changes the
mechanics, not the B4 rules; rebuild the values file from it for the B6 render. If there is no
saved plan, say so and offer a full run. Never reconstruct a plan from a rendered file or an
earlier chat.

**B1a. Read the version history first.**

| `source` | Written by | Meaning |
|---|---|---|
| `edit`, `origin: "mcp:AnthropicClaudeAI"` | This skill | Yours; run order B applies |
| `meeting` with a `meeting_id` | Aircover, after each meeting processed | Rewritten automatically |
| anything else | The portal or another client | Not yours; use run order A |

Aircover rewrites the whole plan once per new meeting, and each rewrite drops more of the extras.
Find the newest `edit` version from this skill. If meeting versions follow it, say so:

> Aircover has rewritten this plan <n> times since your version <v>, once per meeting. The SWOT
> and evidence coverage notes are no longer in the current version. Version <v> is restorable from
> the dropdown. I can merge your research back in.

Recover missing research from version <v>, never by re-researching, and never treat missing extras
as proof they never existed. If version <v> is not readable through the tools, ask the person to
restore it from the version dropdown in Aircover, then run the update again.

**B2. Find what is new.** `get_deal` for each deal key in Plan settings; take meetings after the
evidence watermark, and re-run the 4a reconciliation (older meetings may have finished
transcribing). **If nothing is new, stop** and do not rebuild.

**B3. Run agents on the new meetings only**, with the same agent set.

**B4. Merge, do not rewrite.**
- **Recompute what is mechanical:** meeting counts, coverage, freshness, last-touched dates,
  snapshot metrics, relationship health, CRM stage, amount and close date.
- **Add what is genuinely new**, with its meeting date.
- **Supersede, never duplicate.** Replace a block's text and date rather than adding a near-copy.
- **Leave the rest alone.** Research, SWOT, trends, narrative and GTM tracks change only if new
  evidence contradicts them, an exit criterion was met, or material aged past `recency_months`.
  Carry research forward with its original retrieval dates; re-fetch and write a new ledger row
  rather than refreshing a date.
- **Resolution is an update, not a deletion.** A filled role gap or answered INPUT NEEDED becomes a
  dated resolution.

**B5. Record the revision** in `meta.revisions` and Plan settings, move the watermark, and add one dated appendix line
naming the meetings added.

**B6. Rebuild in the same format and template**, rerun the consistency pass, and sync as in 9b,
including its conflict rule: if someone edited the plan in Aircover since you read it, re-read,
show the person what changed, and merge your additions into their edits rather than overwriting
their words. Present only the rebuilt document.

**B7. Say what changed**, not what the plan says:

> Added the 2026-09-29 call with Levent. Procurement is now named (Dana Wu), so that role gap is
> closed. The pilot vote moved to 2026-10-20. Nothing else changed.

## Reading the plan honestly
- Calls skew technical. Contract, pricing and exec relationship blocks often come back unevidenced
  even on healthy accounts, because that conversation happens over email and in person.
- Coverage is uneven: report per opportunity so the loud one does not speak for the account.
- **Recurring office hours and training sessions contaminate everything.** Customers discuss their
  own pipeline there. Exclude them, or verify every extracted name against known attendees.
- A champion evidenced fourteen months ago is history. Band every call claim by freshness and never
  write stale evidence in the present tense.
- Present coverage as what calls can show, not as account health. A thin account gets a thin plan
  that says so.

## Rules
- Never fabricate. No tool result means an empty block or an INPUT NEEDED question.
- Never reuse template example text (`config.validation.template_trap_strings`).
- Every claim traces to a dated call, a CRM field, a fetched source with retrieval date, or the
  account team. Customer-side speakers only for customer evidence (`output_standard.md` §6).
- Full 32 character meeting ids and full `deal_key` (`prospect_org/deal_id`).
- No em dashes. One timezone, stated once. Scoring vocabulary never reaches the document.
- Every competitor row carries dated evidence.
- No quotation marks around anything not copied from a transcript.
- The values file is working state, never a deliverable.
- No company name belongs in the code, config defaults, or this file.
