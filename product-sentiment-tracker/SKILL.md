---
name: product-sentiment-tracker
description: Generate a Customer Product Sentiment report as an Excel workbook from Aircover agent results. Runs the Product VoC agent on every external meeting in a date range, writes each result to disk as it goes, aggregates signals by account, and outputs a professional .xlsx with Sentiment Highlights, Account Summary, Signal Detail, Sentiment Summary, Raw Data, and Agent Properties Guide sheets. Trigger when the user says "product sentiment", "sentiment report", "VoC report", "product feedback report", "customer sentiment tracking", or asks for a summary of product signals across accounts.
---

# Product Sentiment Tracker

Generate a consolidated Customer Product Sentiment report from Aircover meeting data. Runs the Product VoC agent on every processable meeting, writes each result to a JSONL file on disk as it goes, then aggregates product requests, product gaps, feature adoption signals, competitive intelligence, integration requests, and VoC summaries by account. Output is a professionally formatted Excel workbook (.xlsx) where Raw Data is the source of truth and all other sheets aggregate from it.

## Bundled resources

- `scripts/generate_report.py`: Reads the JSONL results file, aggregates, and generates the .xlsx with six sheets (requires `openpyxl`).
- Follows the shared Aircover MCP rules (inlined below).

## Requirements

- The **Production** Aircover connector must be connected.
- Code execution / file creation enabled.

## Configuration

- **Environment:** Production (api.aircover.ai)
- **Agent:** Selected at run time, not hardcoded. The skill lists the available agents and asks the user which to run (see Run order step 2). It works best with a product-sentiment or product-VoC style agent whose properties cover requests, gaps, feature signals, competitive intelligence, integrations, and a summary.
- **App host:** app.aircover.ai (for meeting URLs)
- **Default date range:** Last 30 days from today
- **Default owner:** Omit (pull org-wide). Pass an email if the user asks for "my calls" only.

## Agent properties (expected shape)

A product-VoC agent typically returns these 6 properties. The agent the user selects may use different titles; **join on `title`, never on `key`** (keys are positional and vary), and map the selected agent's properties to the closest report slots below. A property with no equivalent can fold into the VoC Summary or be omitted. If the selected agent looks nothing like a product-sentiment agent, say so and confirm before running.

| # | Title | Scored | Max Score | What it captures |
|---|-------|--------|-----------|-----------------|
| 0 | Product Requests | Yes | 5 | Explicit feature requests from the customer |
| 1 | Product Gaps | Yes | 5 | Existing features that fall short of needs |
| 2 | Feature Adoption Signals | No | 0 | Customer reactions to specific features (Active Use, Interested, Not Adopted, Dropped) |
| 3 | Competitive Intelligence | No | 0 | Competitor mentions, comparisons, sentiment |
| 4 | Integration Requests | Yes | 5 | Integration needs for connecting to other systems |
| 5 | VoC Summary | No | 0 | 2-4 sentence executive summary of all signals |

**Important:** A single property result often contains multiple signals separated by double newlines (`\n\n`). Each block starting with a bold label (e.g., `**Request:**`, `**Gap:**`, `**Feature:**`, `**Competitor:**`, `**Integration:**`) is one individual signal. Parse these into separate rows on the Signal Detail sheet.

## Run order

### 1. Load tools and confirm environment

Call `tool_search("Aircover meetings agents")` to load deferred tools. Use **Aircover Production** tools only.

### 2. Interview (minimal)

First, **select the agent**. Call `list_agents` and present the available agents to the user (name and category), then ask which one to run. Suggest agents whose title or category indicates product sentiment or VoC, but let the user pick any. If exactly one clearly matches, you may propose it and confirm rather than listing everything. Use the chosen agent's `id` as `template_id` for every `agent_results` call below. Do not hardcode an id.

Then confirm the rest, asking only if ambiguous:
- Date range? Default last 30 days. Accept overrides.
- Owner scoped or org-wide? Default org-wide.
- Subset of accounts? Default all.

### 3. Pull meetings

Call `list_meetings(start, end)` with optional `owner`. Save the full response.

### 4. Filter to external prospect meetings

Remove meetings where:
- `prospect_org` is "unknown" (solo/test meetings)
- `prospect_org` is "aircover.ai" AND `customer_org` is "aircover.ai" (internal)
- Fewer than 2 attendees
- Summary starts with "Canceled" or "Declined" (case-insensitive)

### 5. Estimate and warn

Count filtered meetings. Report the count to the user. If over 80, offer to narrow by account or date range. Each meeting is one `agent_results` call. Many meetings will have no transcript and will be skipped automatically.

Note from experience: expect roughly 40-60% of meetings to have processable transcripts. Teams meetings, very short calls, and same-day meetings often lack transcripts. The skill handles these gracefully.

### 6. Loop: run agent_results per meeting, write to disk as you go

Create a JSONL file at `/home/claude/sentiment_results.jsonl`. For each meeting:

```
agent_results(meeting_id=<full 32-char id>, template_id=<the agent id selected in step 2>)
```

**On success:** Extract the entries by joining on `title`. Write one JSON line to the JSONL file:
```json
{"mid":"<id>","date":"<YYYY-MM-DD from start_time>","acct":"<prospect_org>","title":"<meeting summary>","pr":"<Product Requests result>","pr_c":<score>,"pg":"<Product Gaps result>","pg_c":<score>,"fs":"<Feature Adoption Signals result>","ci":"<Competitive Intelligence result>","ir":"<Integration Requests result>","ir_c":<score>,"voc":"<VoC Summary result>","url":"https://app.aircover.ai/meetings/<full id>"}
```

**On error:** Check the error message.
- If it contains "no transcript available": skip silently, increment a `no_transcript` counter.
- If it is a generic error: skip, increment a `errors` counter.
- In both cases, do NOT write a row to the JSONL. Do NOT stop the loop.

**After every 10-15 meetings**, briefly report progress to the user (e.g., "Processed 15/49, 8 with data, 7 no transcript").

### 7. Report processing summary

After the loop, tell the user:
- Total meetings attempted
- Meetings with data (rows in JSONL)
- Meetings skipped: no transcript
- Meetings skipped: error
- This is the actual meeting count the report will reflect.

### 8. Generate the .xlsx

Run the bundled script:

```bash
pip install openpyxl --break-system-packages 2>/dev/null
python3 scripts/generate_report.py /home/claude/sentiment_results.jsonl /mnt/user-data/outputs/Customer_Sentiment_Report.xlsx "<name of the agent selected in step 2>"
```

The script:
1. Reads the JSONL file (one JSON object per line)
2. Aggregates by account (using `acct` field as the grouping key)
3. Parses multi-signal entries into individual signal rows (splitting on `\n\n` blocks)
4. Computes signal counts, distributions, and top signals per account
5. Writes all six sheets with Raw Data as the source of truth

### 9. Present the file

Call `present_files` with the output path.

## Output format

The .xlsx workbook contains six sheets:

1. **Sentiment Highlights**: Title, subtitle with accurate meeting/account counts, and a summary table with one row per account sorted by signal count descending. Columns: Account, Meetings, Total Signals, Product Requests, Product Gaps, Feature Signals, Top Product Request, Top Product Gap. Frozen header, auto-filter.

2. **Account Summary**: One row per account with detail. Columns: Account, Meetings, Signals, PR, PG, FS, Top Signal, First Date, Latest Date, Blockers?, Latest VoC Summary. Frozen header, auto-filter.

3. **Signal Detail**: One row per individual signal (multi-signal entries parsed into separate rows). Columns: Account, Date, Signal Type, Signal, Confidence, Meeting URL. Frozen header, auto-filter.

4. **Sentiment Summary**: Two tables. Signal Type Distribution (type, accounts, count, %). Top Signal Sources by Account (account, PR count, PG count, FS count).

5. **Raw Data**: One row per meeting with the full agent output per property. This is the source of truth. All other sheets aggregate from this data. Columns: Meeting ID, Date, Account, Meeting Title, Product Requests, PR Conf, Product Gaps, PG Conf, Feature Sentiment, VoC Summary, Meeting URL. Frozen header, auto-filter.

6. **Agent Properties Guide**: Reference sheet documenting the 6 agent properties, their types, scoring, and what they capture.

## Rules

- **Raw Data is the source of truth.** Every other sheet aggregates from it. The meeting count on Sentiment Highlights must equal the row count on Raw Data, not the total from list_meetings.
- Join agent_results on title, not key. Discover field names at runtime. Never fabricate; use "Not found" or omit.
- "Not found" matching is case-insensitive ("Not found", "Not Found", "not found" all mean empty).
- Full 32-char meeting ids everywhere, especially in URLs.
- Filter by prospect_org, never bare deal_id.
- No em dashes anywhere. Use commas, periods, colons, or parentheses.
- Lists for enumerations, short prose for narrative.
- Times in PT, no UTC.
- Write results to JSONL on disk after each call. Do not hold all results in conversation context.
- If agent_results errors on a meeting, skip and continue. Track skipped counts separately for "no transcript" vs generic errors.
- Multi-signal entries: split on double newlines and bold-label patterns to produce individual signal rows.
- Expect 40-60% of meetings to lack transcripts (Teams without recording, same-day meetings, short calls). This is normal, not a failure.
