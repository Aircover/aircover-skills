# Close Plan (Aircover skill)

Turn a live Aircover deal into the team's standard close plan workbook: a one-page Summary, a scored Health Score across five buckets, an Action Plan with one recommended action per gap, and a Stakeholder Map heat map. Every marker traces to a call or the CRM; anything the data cannot supply reads Needs Input instead of a guess.

This is an internal seller-facing artifact. It runs as a skill inside an assistant connected to the Aircover MCP server.

## How it works
1. Find the deal and confirm the header (CRM record, close date, amount, stage, AE and SE).
2. Reconcile the meetings and agree the scope.
3. Run the org's Close Plan, MEDDPICC and Deal Readiness agents.
4. Score 26 items across Stakeholder Alignment, Technical Validation, Commercial, Timeline & Risk, and Competition.
5. Fill the Excel template, then sync the plan back to Aircover as a new version of the deal's close plan.

## Requirements
- The **Aircover** connector (Production).
- Code execution / file creation, Python with `openpyxl`.
- To sync back to Aircover, an org admin turns on **Allow MCP Clients to Write** once. Without it the workbook is still delivered.

## Configuration
Everything lives in `config.json`: agent discovery, the cell map, buckets, stakeholder grid, CRM source (`auto` by default) and `sync` (`auto`, `confirm` or `off`). If you change the stakeholder grid, regenerate the template with `scripts/build_template.py`.

## Repo layout
```
SKILL.md                            the skill instructions
CHANGELOG.md                        version history
config.json                         install-specific settings
assets/Close_Plan_TEMPLATE.xlsx     the four-tab template
references/                         field source map and output standard
scripts/fill_close_plan.py          fills the template from values + CRM
scripts/build_template.py           regenerates the blank template
```

## Install
Zip the folder as `close-plan.skill` (or download the release), then upload it under Skills in your assistant.

## Notes
- No customer data is stored in this repo.
- The score reads as coverage of what calls can evidence, not deal health.

## License
See `LICENSE`.
