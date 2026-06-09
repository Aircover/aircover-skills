# Field source map: Mutual Action Plan

Where each cell in the template comes from. Discover the actual key names at
runtime (schemas vary per org and per agent); the tool names below are stable.

## Overview block

| Cell | Field | Source | Notes |
|---|---|---|---|
| B5 | Account | `get_deal` -> `prospect_org`, or the deal's company name | The account you are selling into. |
| B6 | Project | `get_deal` -> `crm.sfdc_opportunity_name` (or HubSpot equivalent) | If CRM block is empty, leave grey placeholder. |
| B7 | Objective | Qualification agent: the Pain / Metrics / Why Now dimensions, synthesized into one shared business outcome | One line, the customer's words where possible. Never invent. |
| F5 | Our Sponsor | `get_meeting` -> `deal_team` (the AE or exec on the Aircover side) | Pick the senior owner, not every rep. |
| F6 | Their Sponsor | Qualification agent: Authority dimension (the champion and economic buyer) | Name + real title. Do not write internal labels like "Champion" or "Economic Buyer". Grey placeholder if the call did not establish it. |
| F7 | Target Go-Live | `get_deal` -> `crm` close date; fall back to the agent's Timeline | Written as a real date. Drives every Due Date via `=$F$7-Fn`. |

## Action items (rows 12-28)

The 17-row playbook is the backbone of the plan: keep it. Ground it in the deal,
do not rebuild it. The MAP is customer-facing: every cell must be value-add for
both sides (see "Writing customer-facing content" in SKILL.md). Per row you may set:

| Column | Field | Source / rule |
|---|---|---|
| C | Action Item | Keep the template wording unless the deal needs a custom step. |
| D | Owner (Us) | Map roles to real people from `deal_team` where you can (AE, SC, CSM). Otherwise keep the role label. |
| E | Owner (Them) | The responsible person on their side, by name and real title. Avoid internal qualification labels in the customer-facing cell. |
| F | Days Before Go-Live | Keep template offsets unless the deal's cadence differs. The Due Date recalcs from this and F7. |
| H | Status | Infer conservatively from CRM stage and meeting history (see below). Default to Not Started. |
| I | Notes / Blockers | Shared substance only: objectives, success criteria, agreed decisions, mutual next steps. On the objectives row, list the business objectives; state success criteria as agreed if they were set, otherwise write "Success criteria to be defined. Recommended based on the customer's needs: X, Y, Z" using the agent output. No coaching/gap language, no qualification labels, no private seller plans. Blank if nothing value-add to say. |

## Inferring status (use judgment, not keyword matching)

Read the CRM stage and the completed-meeting history and reason about which phases
are genuinely done. Examples of sound inferences:

- Discovery happened and objectives are captured -> Discovery & Alignment rows (1-4) likely Complete or In Progress.
- A POC / trial is underway -> Evaluation rows (5-9) In Progress; later ones Not Started.
- Security review is pending -> mark that row In Progress with the blocker in Notes.
- A known blocker (legal hold, budget freeze, stalled champion) -> At Risk or Blocked on the affected row, with the reason in Notes.

Only mark Complete or In Progress what the data actually supports. When in doubt,
leave the template's Not Started. Never fabricate progress to make the plan look further along.

## What this skill does NOT source

- Days-before offsets and the step list are a sales-team standard; they are config, not deal data.
- If CRM is empty (early deal, no opportunity yet), Project and Go-Live stay grey placeholders and the rep fills them.
