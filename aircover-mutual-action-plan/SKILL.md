---
name: aircover-mutual-action-plan
description: Generate a completed Mutual Action Plan (MAP) spreadsheet for a deal, pulling the account, opportunity, sponsors, target go-live date, and deal progress from the Aircover Production account and filling the team's standard MAP template. Use this whenever someone says "build a mutual action plan", "run the MAP", "make a MAP for [company]", "close plan", or "joint action plan", or wants a deal turned into the shared roadmap spreadsheet, even if they do not name the template.
---

# Aircover Mutual Action Plan

Turn a live Aircover deal into a completed Mutual Action Plan: the shared, dated
roadmap from discovery to go-live. The skill keeps the team's standard 17-step
playbook as the backbone and grounds it in real deal data (account, opportunity,
sponsors, close date, current progress, agreed next steps). Sourced values render in
black; anything the data cannot supply stays a grey placeholder so the rep sees

> **This document is customer-facing.** The MAP is shared and reviewed with the
> customer. Every cell must be value-add for both sides. Write the substance of
> what was agreed (objectives, success criteria, decisions, mutual next steps),
> never internal deal commentary. No MEDDPICC/qualification labels, no coaching or
> gap language (for example "captured across 2 calls", "still to be established",
> "process mapped", "X is the economic buyer", "we still need to extract Y"), and
> nothing that reads as the seller's private plan. If you would not say it to the
> customer's face, it does not go in a cell. See "Writing customer-facing content"
> below.
what to finish.

## Bundled resources
- `config.json` - everything org-specific: environment, how to find the agent, the template filename, the cell map, value colours, and status colours. Change this, not the code, to retarget the skill. The engine reads it automatically.
- `assets/Mutual_Action_Plan_TEMPLATE.xlsx` - the team template. Holds all styling, the Status dropdown, and the `=$F$7-Fn` due-date formulas. Do not rebuild it; fill it.
- `scripts/fill_map.py` - template-agnostic engine. Reads `config.json`, writes only the cells you supply, preserves everything else, recolours Status cells when status changes, and writes Go-Live as a real date so all due dates recalculate. Requires openpyxl.
- `references/field_source_map.md` - which Aircover field feeds which cell, and how to infer status.
- `references/example_values.json` - a worked values file.
- `README.md` - install and the three things a new customer changes. Read it if you are forking this for another org.

Copy the script, config, and template into your working directory first:
```
cp "$SKILL_DIR/scripts/fill_map.py" .
cp "$SKILL_DIR/config.json" .
cp "$SKILL_DIR/assets/Mutual_Action_Plan_TEMPLATE.xlsx" .
```

## Requirements
- The **Aircover Production** connector (api.aircover.ai) must be connected. Confirm it before running: Production and Staging share tool names, and an "agent not found" error usually means you are pointed at the wrong environment.
- Code execution / file creation on.
- openpyxl in the environment (`pip install openpyxl --break-system-packages` if missing).

## Configuration
All of this lives in `config.json`. Edit that file to retarget the skill; the engine and run order do not change.
- **Environment:** Production, api.aircover.ai. App host: app.aircover.ai.
- **Agent:** discovered at runtime. `config.agent.pinned_template_id` is null, so the skill calls `list_agents` and matches on `config.agent.category` ("qualification") and `config.agent.title_keywords`. To lock a specific agent, set `pinned_template_id` and discovery is skipped. Always join results on the entry `title`, never the positional key, so a rebuilt agent still works.
- **Template + layout:** `config.template.file`, the sheet name, the overview cell map, the action-item columns and row range, and the status colours all come from config. A customer who wants their own MAP template swaps the file and updates the cell map once; no code change.
- **White-label.** The skill assumes no specific selling company. The "Our" side (sponsor, team owners) is read from whatever Aircover account is connected, so the same skill works unchanged for any company whose team uses Aircover. The only platform constants are the Aircover API and app hosts in config; everything else is per-deal, per-account data pulled at run time.
- Template offsets and the step list are the team standard (config, not deal data). Keep them unless the deal genuinely needs a custom step.

## Run order
1. **Confirm environment.** Make sure the active connector is Aircover Production. Call `tool_search` ("Aircover meetings agents deals") to load the deferred tools, then use the exact parameter names returned.

2. **Identify the deal (deal-first).** `list_meetings` has no account filter, so start from the deal. `get_deals(search="<company>")` to find it. Use the full `deal_key` (`prospect_org/deal_id`) or `prospect_org`, never the bare integer `deal_id` (it resets per org and collides). Echo back the matched deal (company + opportunity + close date) and confirm before building.

3. **Deal + CRM in one call.** `get_deal(prospect_org, deal_id)` returns a `crm` block (both SFDC and HubSpot fields) and a `completed_meetings` array. Pull:
   - `crm.sfdc_opportunity_name` (or HubSpot equivalent) -> **Project** (B6).
   - the CRM close date -> **Target Go-Live** (F7). If absent, fall back to the agent Timeline in step 4.
   - the CRM stage and `completed_meetings` -> evidence for inferring statuses (step 6).
   - `prospect_org` / company name -> **Account** (B5).
   Call `get_deal` once and reuse it. An empty `crm` block is a placeholder, not an error: Project and Go-Live then stay grey.

4. **Qualification agent on the key meeting.** Pick the most recent substantive meeting from `completed_meetings`. If `config.agent.pinned_template_id` is set, use it. Otherwise discover the agent: call `list_agents` and match on `config.agent.category` and `config.agent.title_keywords`. Then `agent_results(meeting_id, template_id=<that id>)`. Join on title:
   - **Discovery fallback:** if `list_agents` returns no match, or more than one plausible candidate, ask the user which agent to use rather than guessing or erroring. If they confirm there is no qualification agent, skip this step and leave Objective and Their Sponsor as grey placeholders for the rep.
   - Pain / Metrics / Why Now -> synthesize one **Objective** line (B7), the customer's words where possible.
   - The objectives and success criteria discussed -> the **Notes** on the "Confirm business objectives and success criteria" row. List the actual business objectives. For success criteria: if the two sides set specific metrics, state them as agreed. If they did not, write that they are still to be defined and add recommendations from the agent output, in this shape: "Success criteria to be defined. Recommended based on the customer's needs: X, Y, Z." This is honest (nothing is presented as agreed when it is not) and still value-add. Never write a bare gap note like "metrics still to be established".
   - Authority -> the buying committee. The economic buyer and champion -> **Their Sponsor** (F6) and the Owner (Them) on the approval rows. Use the person's name and real title; do not write internal labels like "Champion" or "Economic Buyer" in cells the customer reads.
   - Timeline -> sanity-check or supply Go-Live if CRM had none.
   - The agreed buying/decision process and mutual next steps -> Notes on the relevant rows, phrased as shared understanding ("Agreed process: ...", "Next step: ..."), not as a private map of their org.
   - A genuine shared blocker (a security review, a legal document in flight, a procurement window) -> Notes on the affected row plus At Risk/Blocked status, stated neutrally as a joint item to clear, not as the seller's worry.
   A property with `max_score: 0` is unscored rollup text, not a dimension. If a dimension is "Not found", that is accurate for an early call: leave it as a placeholder.

5. **Meeting metadata and the seller side.** `get_meeting(meeting_id)` returns `deal_team`, `prospect_attendees`, and an AI `notes` summary. The "Our" side is always derived from the connected Aircover account, never assumed: take **Our Sponsor** (F5) and the Owner (Us) people from `deal_team` (the senior owner as sponsor; map AE/SC/CSM to real names where you can). If `deal_team` is thin, use `get_teams` or the connected user's own email to anchor the seller org. Do not hardcode or assume any specific selling company: whoever is connected is "us". Use the `notes` summary to find agreed decisions and mutual next steps for the Notes column, not internal observations about the deal.

6. **Infer status conservatively (judgment, not keywords).** Read the CRM stage and meeting history and reason about which phases are genuinely done. Discovery captured -> rows 1-4 Complete/In Progress; POC underway -> rows 5-9 In Progress then Not Started; security pending -> that row In Progress with the blocker noted; a real blocker -> At Risk/Blocked with the reason. Only mark Complete/In Progress what the data supports. Default everything else to the template's Not Started. Never fabricate progress. See `references/field_source_map.md` for the full mapping.

## Writing customer-facing content
The MAP is shared with the customer, so the Notes column and the Owner cells must
read as a joint working document. Two tests for every note: (1) would you be glad
the customer read it, and (2) does it add value for both sides. Convert internal
agent/coaching output into shared substance.

| Row | Internal (do not write) | Customer-facing (write this) |
|---|---|---|
| Confirm business objectives and success criteria | "Pain, decision criteria, and process captured across 2 calls. Quantified metrics still to be established." | "Objectives: improve prospecting efficiency, raise hit rates, ensure privacy compliance through the role restructure. Success criteria to be defined. Recommended based on the customer's needs: target hit-rate lift, ramp-time reduction, compliance benchmark." |
| Map decision process and stakeholders | "Process mapped: committee demo, narrow to 2, vote, exec approval." | "Agreed evaluation path: committee demo, shortlist to two, trials, committee vote, final approval." |
| Present business case to Economic Buyer | "Sam Patel is the economic buyer. Jordan to be briefed and aligned before exec presentation." | "Executive review with Sam Patel (final approver). Pre-brief Jordan Lee beforehand." |

Rules for Notes:
- State objectives, success criteria, decisions, and mutual next steps. Recommend
  success criteria when none were set, framed as a joint proposal.
- No qualification labels (Champion, Economic Buyer, MEDDPICC terms), no "captured /
  established / mapped / extracted" coaching verbs, no "across N calls", no private
  seller plans, no internal risk editorializing.
- Name people by their real role/title, not their deal label. Keep notes short,
  concrete, and neutral. If a row has nothing value-add to say, leave it blank.
1. Write `values.json` (see `references/example_values.json`). Schema:
```json
{
  "overview": {
    "account":       {"value": "...", "sourced": true},
    "project":       {"value": "...", "sourced": true},
    "objective":     {"value": "...", "sourced": true},
    "our_sponsor":   {"value": "...", "sourced": true},
    "their_sponsor": {"value": "...", "sourced": false},
    "go_live":       {"value": "2026-10-01", "sourced": true}
  },
  "action_items": [
    {"row": 12, "status": "Complete", "owner_them": "Name (Champion)", "notes": "..."}
  ]
}
```
   - `sourced: true` renders black; `sourced: false` renders grey italic (placeholder still needs the rep). Action-item rows are 12-28; include only the fields you are changing.
   - `go_live` is an ISO date (YYYY-MM-DD). It is written into F7 as a real date; the Due Date column is `=$F$7-Fn`, so every date recalculates from it.

2. Run:
```
python fill_map.py --template Mutual_Action_Plan_TEMPLATE.xlsx --values values.json --out "Mutual Action Plan - {Company} - {YYYY-MM-DD}.xlsx"
```

3. **Recalculate** so the in-chat preview shows correct due dates:
```
python /mnt/skills/public/xlsx/scripts/recalc.py "Mutual Action Plan - {Company} - {YYYY-MM-DD}.xlsx"
```
   Expect `status: success` and 0 errors. (Excel and Google Sheets also recalc on open, but recalc here makes the preview right.)

4. **Present** the `.xlsx`. Note which overview fields are still grey placeholders (the rep's input), confirm the primary champion/EB if there were several attendees, and remind them that changing the Go-Live date in F7 re-dates the whole plan.

## Rules (house style)
- **No em dashes** anywhere. Use commas, periods, colons, or parentheses.
- Discover field names at runtime; schemas vary per org and per agent. **Never fabricate**: if a tool returns nothing, leave the grey placeholder, do not invent a value, sponsor, date, or progress.
- Join `agent_results` on `title`, not the positional key. Use the full 32-char meeting id. Filter by `prospect_org` / `deal_key`, never the bare `deal_id`.
- Objective and Notes are short and concrete. Times and dates are local (PT), no UTC.
- Keep the template's structure, banding, formulas, and the Status dropdown intact: the script does this as long as you only pass values.

## Caveats to surface
- Early deals with no CRM opportunity: Project and Go-Live come back grey; the rep sets them.
- The 17 steps are the team's standard close plan. If a specific deal needs a different step or cadence, edit `action`/`days_before` for that row in `values.json`; the due date recalcs.
- Status is an inference from CRM stage and call history, not ground truth. Frame it as a starting point for the rep to confirm.
