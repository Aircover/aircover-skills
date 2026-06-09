# Aircover Mutual Action Plan skill

Generates a completed Mutual Action Plan (MAP) spreadsheet for a deal. It pulls the
account, opportunity, sponsors, target go-live date, and current deal progress from
an Aircover account and fills a standard MAP template: the shared, dated roadmap
from discovery to go-live. Sourced values render in black; anything the data cannot
supply stays a grey placeholder so the rep sees what to finish.

Built on the Aircover MCP. The same skeleton works for any Aircover customer: the
engine is generic and everything org-specific lives in `config.json`.

## Install

**One-click:** download the `.skill` file from the repo's Releases and add it under
Customize > Skills (personal) or Organization settings > Skills (org-wide, on Team
or Enterprise). Either way, each user logs into the Aircover connector once.

**Build from source:** clone the repo and run the bundled packager (standard library,
no dependencies):
```
python package.py dist
```
This writes `dist/aircover-mutual-action-plan.skill`, ready to upload. Then add it
under Customize > Skills as above.

## Requirements
- The Aircover connector connected (Production by default; see config to change).
- Code execution / file creation enabled in the client.
- openpyxl in the runtime (`pip install openpyxl --break-system-packages` if missing).

## The three things a new customer changes

Everything below is in `config.json`. The engine (`scripts/fill_map.py`) and the
run order in `SKILL.md` do not change.

1. **Connect your Aircover connector.** Nothing to edit; this is the only true
   runtime dependency. Set `environment` in config if you are on Staging.

2. **Use the default template or supply your own.** The shipped
   `assets/Mutual_Action_Plan_TEMPLATE.xlsx` is a 17-step B2B close plan. To use
   your own MAP layout, drop your `.xlsx` in `assets/`, point `config.template.file`
   at it, and update `overview_cells`, `item_cols`, and `first_item_row` /
   `last_item_row` to match your sheet. Set `status_styles` to your template's
   status colours (the template hardcodes them per cell; the engine reapplies the
   matching colour whenever it changes a status). The due-date formulas stay in the
   template, so "change the go-live date and everything re-dates" keeps working.

3. **Optionally pin your agent.** By default the skill finds your qualification or
   discovery agent at runtime via `list_agents`, matching on `config.agent.category`
   and `config.agent.title_keywords`, and joins results on the entry title (not the
   positional key) so a rebuilt agent still works. If your agent has an unusual name,
   set `config.agent.pinned_template_id` to its id to skip discovery. If discovery
   finds nothing or several candidates, the skill asks which to use.

## White-label

The skill assumes no specific selling company. The "Our" side (sponsor, team
owners) is read from whatever Aircover account is connected, so the same skill
works unchanged for any company whose team uses Aircover. The only platform
constants are the Aircover API and app hosts in `config.json`. Nothing is hardcoded
to any one customer or deal.

## What stays generic across orgs
- `get_deal` returns both SFDC and HubSpot CRM fields, so no separate CRM connector
  and no per-CRM branching is needed.
- Filtering by `prospect_org` / `deal_key` (never the bare integer `deal_id`) and
  using the full 32-char meeting id are baked into the run order.
- Status is inferred conservatively from CRM stage and call history and defaults to
  Not Started. It is a starting point for the rep, never fabricated progress.

## Repo layout
```
.
  SKILL.md                       run order and rules
  config.json                    all org-specific values (the file you edit to retarget)
  package.py                     build the .skill (standard library)
  README.md  LICENSE  .gitignore
  scripts/fill_map.py            template-agnostic engine
  assets/Mutual_Action_Plan_TEMPLATE.xlsx
  references/field_source_map.md where each cell comes from
  references/example_values.json worked example
```

## License
MIT (see `LICENSE`). Update the copyright holder / license if your team prefers a
different one before publishing.

## Privacy
Reads deal, meeting, and agent data from the connected Aircover account at run time.
Nothing is stored or sent anywhere else. Run against your own org's data only.
