# Account Plan (Aircover skill)

Build or update a strategic account plan for a whole account: every opportunity, meeting and stakeholder across the account's deals in Aircover, enriched with public company research. The plan covers the snapshot, the customer's business, the stakeholder map, footprint and whitespace, cross-functional GTM tracks, next steps, and the competitive picture. Every claim is labelled with its source: a call, the CRM, a public source, or the account team.

This is an internal seller-facing artifact. It runs as a skill inside an assistant connected to the Aircover MCP server.

## How it works
1. Ask the output format (Word or slide deck, optional PowerPoint template).
2. Find every opportunity at the account, confirm the boundary and the deal values with you.
3. Reconcile held vs transcribed meetings and agree the scope.
4. Run the org's MEDDPICC and Deal Punchcard agents (plus close plan, VoC, persona and competitive agents if present).
5. Research the company (SWOT, priorities, trends), with every external claim checked against a fetched source.
6. Build the document, then sync it back to Aircover as a new version of the deal's account plan.

Say "update my [company] account plan" after a new call and it adds only what is new.

## Requirements
- The **Aircover** connector (Production).
- Code execution / file creation, Node.js with `docx` and `pptxgenjs`.
- Web search and fetch for the research sections (optional).
- To sync back to Aircover, an org admin turns on **Allow MCP Clients to Write** once. Without it the plan is still delivered.

## Configuration
Everything lives in `config.json` and resolves at runtime from your own Aircover data. `sync.mode` is `auto` (save without asking), `confirm` (show it first) or `off`.

## Repo layout
```
SKILL.md                              the skill instructions
config.json                           install-specific settings
references/                           section sources, output standard, GTM playbook, example values (fictional)
scripts/build_account_plan.js         values -> .docx, plus the content checks
scripts/build_account_plan_pptx.js    values -> .pptx
scripts/verify_external_claims.js     blocks unsourced external claims
scripts/check_aircover_fit.js         checks the plan fits Aircover's section size
scripts/package_skill.py              packages the folder into an installable .skill
```

## Install
`python scripts/package_skill.py . ./dist`, then upload the `.skill` under Skills in your assistant.

## Notes
- No customer data is stored in this repo. The example account is fictional.
- The skill never fabricates: missing facts render as labelled INPUT NEEDED questions.

## License
See `LICENSE`.
