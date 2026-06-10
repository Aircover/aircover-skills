# Product Sentiment Tracker (Aircover skill)

Generate a consolidated Customer Product Sentiment report as an Excel workbook from Aircover meeting data. The skill runs the Product VoC agent on every external meeting in a date range, writes each result to disk as it goes, aggregates product signals by account, and outputs a formatted `.xlsx` with six sheets.

This runs as a skill inside an assistant connected to the Aircover MCP server.

## How it works
1. Pull meetings for a date range and filter to external prospect meetings.
2. Run the Product VoC agent on each meeting, writing one JSON line per meeting to a JSONL file on disk as it goes.
3. Aggregate product requests, product gaps, feature adoption signals, competitive intelligence, integration requests, and VoC summaries by account.
4. Render the workbook with `scripts/generate_report.py`.

The model does the per-meeting pull and signal extraction. The bundled script is the deterministic aggregator and renderer: it reads the JSONL and produces the workbook, so the output is consistent every run. Raw Data is the source of truth; every other sheet aggregates from it.

## Output: six sheets
Sentiment Highlights, Account Summary, Signal Detail (one row per individual signal), Sentiment Summary (distributions), Raw Data (source of truth, one row per meeting), and an Agent Properties Guide.

## Requirements
- An assistant connected to the **Aircover** MCP server (production), with code execution / file creation enabled.
- Python with `openpyxl`: `pip install openpyxl`.

## Repo layout
```
SKILL.md                       the skill instructions (the brain)
scripts/generate_report.py     aggregator + renderer: JSONL -> .xlsx (needs openpyxl)
scripts/package_skill.py       packages this repo into an installable .skill (standard library only)
examples/sentiment_results.example.jsonl       a fictional, PII-free example dataset
examples/Customer_Sentiment_Report_SAMPLE.xlsx the workbook that example produces
```

## Try the renderer
```
pip install openpyxl
python3 scripts/generate_report.py examples/sentiment_results.example.jsonl sample.xlsx
```

## Install as a skill
Package the repo into an installable `.skill`, then upload it under Skills (personal: Customize > Skills; org-wide: Organization settings > Skills):
```
python scripts/package_skill.py . ./dist
```
Each user authenticates to Aircover once.

## Usage
With the skill installed, ask in plain language:
- "product sentiment report for the last 30 days"
- "VoC report across our accounts"
- "summarize product signals this quarter"

## Configuration
- Environment: Aircover production (api.aircover.ai).
- Agent: selected at run time. The skill lists your available agents and asks which to run, so nothing is hardcoded. It works best with a product-sentiment or product-VoC style agent.
- Meeting links: `https://app.aircover.ai/meetings/{full id}`. Change the host if your Aircover app host differs.
- Scope: org-wide by default. Pass the user's email to `list_meetings` for "my calls" only.

## Notes
- No customer data is in this repo. The example dataset and sample workbook are fictional.
- The skill never fabricates: empty or "Not found" signals are treated as empty, not invented.
- Expect 40-60% of meetings to lack transcripts (handled gracefully, skipped and counted).
- No em dashes, lists for enumerations, times in Pacific.

## License
See `LICENSE`.
