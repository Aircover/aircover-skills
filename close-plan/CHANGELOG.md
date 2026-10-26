# Close Plan changelog

## V5
New look, same scoring. The workbook is restyled in the Aircover palette (navy headers, teal
accents, soft status colours, no gridlines) and the Deal Overview tab is replaced by a
**Summary** tab that reads the deal on one page: header facts, the overall score, a bar per
bucket with the weakest flagged, the top three risks, the next five actions with owner and
status, the key people with engagement, and the four deal story questions. The score, bars,
next actions and people are formulas into the other tabs, so an AE's edits flow through.
- values.json gains an optional `summary` block: `risks` (three lines) and `next_actions`
  (up to five Health Score item keys, in priority order). Without it the engine falls back
  to the items scored No and prints a note.
- The Action Plan has filter buttons and a frozen header row.
- `build_template.summary_layout` is the one definition of the Summary rows; the builder
  refuses to run if `header_cells`, `synopsis_cells` or `label_overrides` disagree with it.
- Health Score, Action Plan and Stakeholder Map keep their names and row positions.

## V4.2
Instructions trimmed by about a quarter with no change to the engine, template or scoring: the
version notes moved out of SKILL.md into this file, and the configuration, stage banding and
header confirmation steps were tightened. Two rules were made explicit: a corrected AE or SE
answer gets a free-text follow-up for the right names, and header values typed in for an empty
CRM block are asked in one question and count as sourced.

Fixes from a live test run:
- The Close Plan agent no longer ships pinned to one org's agent id; it is discovered like the others.
- The sync saves to the deal-level Close Plan template (`list_account_deal_agents`), not the
  meeting-level Close Plan agent used for scoring.
- When several agents match one role, a stated rule picks between them.
- An unknown SE or Partner reads "Not assigned" / "None identified", matching the output standard.
- Call wording says transcribed, not recorded.

## V4.1
One addition, no engine or template change: **the finished plan now syncs back to Aircover**
(step 9, `sync` in config.json, on by default in `auto` mode). After the workbook is built,
the same content is rendered to the Close Plan agent's own section contract and saved as a
new version of the deal's document through `save_account_deal_agent_document`, so the deal
page in Aircover matches the delivered workbook and the next agent run builds on it instead
of regenerating over it. Needs the org setting **Allow MCP Clients to Write**; without it the
save is refused and the run completes workbook-only, exactly as before.

## V4
Defects found in two rounds of real customer feedback, all in the rules rather than the engine.
The template asset changed, so the config and the template must travel together from here on:

- **An agent that ran and found nothing is `no`, not Needs Input.** Rows 39 and 40 read a
  fragment of Close Plan Technical Scope rather than a score of its own, and the looked-vs-
  nothing-looked test was written at the property level only, so an empty fragment read as
  absent data. The test now applies to the property: if the agent returned content, a missing
  fragment is `no`. Row 41 is the only item where `unknown` can be right at all, and even
  there only when a seller declines to band their stage.
- **The C-Suite band takes only a stated C-level title.** It was defined as whoever holds the
  decision, which is a test of authority, and it put an untitled budget owner in a band
  labelled C-Suite while also duplicating them against their own Economic Buyer row. Authority
  is explicitly not the test now, and the no-promote rule that already protected Executive
  Sponsor covers this band too.
- **Function and seniority come from the call first, then the attendee title.** Orgs that
  enrich the transcript header with titles and LinkedIn URLs were having those titles ignored,
  because the only sanctioned sources were what a call said and Stakeholder Coverage. Whole
  committees were dropping to the unplaced line as "no seniority stated" while their titles sat
  in the header. Level mappings: SVP or VP to VP, Head of or Senior Director to Director, Lead
  or team leader to Manager.
- **New grid row: Seniority not stated.** Function evidenced, level not, is now a placement
  rather than a drop. The unplaced line is only for people with neither axis. This is why the
  template asset changed: every row below the grid derives from the seniority axis length, so
  the legend, unplaced line, persona table and gap line all moved down one.
- **Two new guards.** The engine warns when the grid ends up with no named placements, which
  is nearly always a skipped source rather than an unmappable committee. And a layout check
  fails loudly when the seniority axis is extended in config without regenerating the template,
  instead of writing grid cells over the legend.
- **Row 41 has a decision rule, not two examples.** Banding the stage was necessary but not
  sufficient: the engine never sets that row, and the guidance gave two illustrations and
  nothing at all for closed or excluded bands, so a runner could still fall back to Needs Input
  after asking. Step 7 now carries a per-band rule built on the template's own "3+ boxes
  unchecked" label text.
- **Stage banding is now one stage per run, asked at the point of need.** Step 3b used to ask
  the seller to band a whole pipeline, an ask large enough that the step told the runner to skip
  it unless nothing else was contested. Sellers were left looking at Needs Input on the forecast
  row with no way to clear it. Now the run bands only the stage on the deal in front of it, as a
  single tap alongside the other header confirmations, and writes it to `config.json`. That
  write lasts as long as the config file does, which for an installed skill is the session;
  fold confirmed bands into the distributed config to make them permanent.
- **The persona table fills from the attendee roster as well.** The title fix above was applied
  to the grid only, leaving the same bug in the persona rows: an identifiable attendee could be
  placed on the heat map while the influencer slot for their own function still read `?`. The
  three influencer slots now draw on the roster and its titles on the same precedence.
- **A `?` persona row must carry a note.** Gap rows were shipping with empty Notes cells, which
  is the main reason a finished plan reads as half-finished: the reader cannot tell whether
  nobody was found or nobody looked. The engine now warns on any empty note.
- **Title availability is per-org and now documented.** Some workspaces enrich the attendee
  block with job titles and LinkedIn URLs; some return only an email and a derived name. Check
  one meeting early, and when titles are absent, say so in the unplaced line rather than leaving
  the map looking incomplete.

## V3.2
Prepared for distribution to any org, not just the one it was built in. Nothing about the
scoring or the layout moved; what changed is what ships and what gets asked:

- **Every org-specific value ships blank or neutral again.** `vendor.name`,
  `vendor.email_domain` and all five `crm.stage_taxonomy` bands are empty, and
  `stakeholder_map.grid.functions` is a generic six-column buying committee rather than one
  vendor's buyer set. A shipped config carrying the last install's pipeline stages is how one
  org's deal data ends up labelling another org's workbook.
- **`crm.source` ships as `auto`.** Pinned to `salesforce`, the engine reads empty `sfdc_*`
  fields in a HubSpot org and silently produces a header block with no opportunity, no amount
  and no stage. Step 3 now detects which CRM the block actually populates, handles both being
  present, and handles neither.
- **No CRM sync is a supported state, not a broken install.** Step 4 asks for the four header
  values instead of shipping blanks, and nothing in the run reaches for a Salesforce or HubSpot
  connector.
- **`build_opp_link` falls back to plain text.** It used to return nothing when `instance` was
  null, which is the shipped default, so the Opp Link cell came out blank in every fresh
  install while both reference files said it must never be blank when an opp id exists. It now
  writes `"<CRM> - Opportunity <id>"`, with the label configurable per CRM via `display_name`.
- **First-run configuration is step 0**, with guidance on which values are worth spending a
  question on during the first build and which can wait until after delivery.

## V3.1
Four defects found by an AE reading a finished workbook, all fixed in the engine and
the template rather than by hand on one deliverable:

- **Markers are coloured by conditional formatting rule, not by a fill.** V3 painted
  the fill at build time, so changing a marker from No to Yes recomputed the bucket
  formula and left the cell red. Red beside the word "Yes" does not read as a stale
  fill, it reads as a broken score. The rules key on the marker text and cover the
  Health Score markers, the persona Engagement column and the Action Plan Status
  column, which previously had no colour at all.
- **The coverage note is a required cell** on the Health Score tab, below the buckets.
  The rule that the score is coverage rather than deal health was already in this file
  and was still only ever reaching the chat response. Now it is on the artifact, and
  the engine warns when it is missing.
- **`build_template.py` reads the stakeholder axes from `config.json`.** They used to
  be hardcoded in both places, so retargeting the grid to a vendor's real buyer set
  meant editing config and then finding the template header still asking about someone
  else's departments. One source now.
- **The ARR cell gets a number format** from `config.formats`, instead of rendering a
  CRM amount as a bare quantity.

Two follow-ons worth knowing:

- On the heat map grid, engagement level is carried by colour, so green and amber
  cannot be derived from a name and stay painted at build time. Only the "?" gap
  bubble and an emptied cell are rule-driven. A level changed by hand needs its fill
  changed by hand, copied from the Key row.
- `config.crm.<source>.instance` ships null, so the Opp Link cell holds a plain text
  reference rather than a link. Set the hostname once per install and every future
  workbook gets a clickable opportunity.

## V3
The workbook used to be one crowded Deal Overview sheet plus a Risk Assessment sheet. If you
have seen the old layout, the differences that matter:

- The synopsis is **four questions**, not eight. The champion, economic buyer, technical win,
  exec engagement and vendor sponsor blocks below them are gone, because they duplicated the
  checklist and the two answers drifted apart.
- Usage is **split into two questions**: how they are using it today, then the **primary use
  case versus the secondary use case**. That ranking is what tells the AE which persona to lean
  on, and it gets buried when it shares a cell with the deployment description.
- The problem-impact, value-proposition and ROI questions are **collapsed into one**: the
  product's impact on the customer's business, with specific metrics. That single answer now
  carries the whole commercial case.
- Scoring moved to its own tab with **five bucket scores and an equally weighted overall**,
  computed by live formulas so the AE's overrides recompute.
- **Each item is worth an equal share of its bucket: Yes 100%, In Progress 50%, No and
  Needs Input 0%.** Needs Input scores zero on purpose, so missing evidence can never raise
  a score. Because In Progress now carries real weight, the section 6a ceiling rules move the
  number, not just the label: an item argued up from `no` to `partial` adds half an item's
  worth to its bucket. Apply them as written rather than by feel.
- **Red Flags to Watch For and the Risk Assessment sheet are both deleted.** They restated the
  same gaps in a second vocabulary and produced contradictory signals. Their content routes
  into the buckets, the Action Plan comments, and the Stakeholder Map. See
  `field_source_map.md` section 3 for the mapping.
- Two new Timeline & Risk items: a migration or onboarding plan, and a named onboarding owner.
- One new Commercial item: enough value established to mitigate discounting.
- The Action Plan and Stakeholder Map tabs are new.
