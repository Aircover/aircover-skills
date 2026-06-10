# Pre-Call Prep (Aircover skill)

Generate a polished pre-call prep document for an upcoming customer meeting, built from Aircover meeting data. The skill reads the last 2-4 completed transcripts for a deal, synthesizes open action items, stakeholder priorities, account hierarchy, landmines, objectives, and success criteria, and outputs a formatted Word document a rep can scan in five minutes before the call.

This is an internal rep-facing artifact. It is designed to run as a skill inside an assistant connected to the Aircover MCP server.

## How it works
1. Identify the deal and the upcoming meeting (deal-first when a company is named).
2. Pull the last 2-4 completed meetings for the deal and read their transcripts and notes.
3. Pull deal and CRM context, and deal-level qualification gaps if a qualification agent exists.
4. Optionally enrich org-chart and company context from the web (conservative, exact matches only).
5. Synthesize the sections into `prep_data.json`.
6. Render the `.docx` with `scripts/build_prep_doc.js`.

The model does the synthesis. The bundled script is the deterministic renderer: it turns a structured JSON file into the formatted document, so layout and styling are consistent every run.

## Requirements
- An assistant connected to the **Aircover** MCP server (production), with code execution / file creation enabled.
- **Node.js** with the `docx` package: `npm install docx`.
- Web search available (for optional company enrichment).

## Repo layout
```
SKILL.md                     the skill instructions (the brain)
scripts/build_prep_doc.js    renderer: prep_data.json -> .docx (needs the docx npm package)
scripts/package_skill.py     packages this repo into an installable .skill (standard library only)
examples/prep_data.example.json          a fictional, PII-free example input
examples/Pre-Call_Prep_AcmeRobotics_SAMPLE.docx   the document that example produces
```

## Try the renderer
```
npm install docx
node scripts/build_prep_doc.js --input examples/prep_data.example.json --out sample.docx
```

## Install as a skill
Package the repo into an installable `.skill`, then upload it in your assistant under Skills (personal: Customize > Skills; org-wide: Organization settings > Skills):
```
python scripts/package_skill.py . ./dist
```
Each user authenticates to Aircover once.

## Usage
With the skill installed, ask in plain language:
- "prep me for my Acme call"
- "pre-call prep for [company]"
- "get me ready for my next call"

## Configuration
- Environment: Aircover production (api.aircover.ai).
- Meeting links: `https://app.aircover.ai/meetings/{full id}`. Change the host if your Aircover app host differs.
- Owner scoping: pass the user's email to `list_meetings` for "my meetings," omit for org-wide.

## Notes
- No customer data is stored in this repo. The example is fictional.
- The skill never fabricates: sections with no supporting data are omitted rather than guessed.
- No em dashes, lists for enumerations, times in Pacific.

## License
See `LICENSE`. Confirm the copyright holder before publishing.
