---
name: pre-call-prep
description: Generate a pre-call prep Word document for an upcoming meeting, pulling the last 2-4 transcripts from Aircover Production to build deal context, open action items, stakeholder priorities, landmines, and a suggested agenda. Use this whenever someone says "prep me for my call", "pre-call prep", "call prep for [company]", "get me ready for [meeting]", or wants a structured briefing doc before a customer meeting.
---

# Pre-Call Prep

Generate a polished pre-call prep .docx from Aircover Production data. Reads the last 2-4 transcripts for the deal, synthesizes open action items, stakeholder priorities, landmines, and objectives, and outputs a formatted Word document the rep can scan in five minutes before the call.

## Bundled resources
- `scripts/build_prep_doc.js` - generates the .docx from a structured JSON file (requires `docx` npm package).

Copy the script into your working directory before running:
```
cp "$SKILL_DIR/scripts/build_prep_doc.js" .
```
(`$SKILL_DIR` is the folder this SKILL.md is in.)

## Requirements
- The **Aircover Production** connector must be connected. All deal, meeting, and transcript data is read from there.
- **Code execution / file creation** must be on.
- Web search is used for company enrichment (org chart context, public facts).
- `npm install -g docx` must be run before the build step.

## Configuration
- Environment: Production (api.aircover.ai)
- App host: app.aircover.ai (for meeting links)
- Owner scoping: omit `owner` for org-wide, or pass the user's email for "my meetings." If unknown, ask once.

## Run order

### 1. Identify the deal and upcoming meeting
If the user names a company: `get_deals(search="company")`. Take the deal_key, prospect_org, deal_id, and nextMeetingDate. If the user names a date or "my next call": `list_meetings` over the relevant window, optionally scoped by `owner`.

Echo back the matched deal (company + next meeting date + stage) and confirm before proceeding.

### 2. Find the last 2-4 completed meetings for this deal
Use the `get_deal(prospect_org, deal_id)` response. It returns a `completed_meetings` array. Take the most recent 2-4 meetings (sorted newest first). If only 1-2 exist, use what is available.

If `completed_meetings` is missing or empty, fall back to `list_meetings` over a wide window (90 days back from the upcoming meeting) and filter by the deal's prospect_org in the meeting titles/attendees.

### 3. Pull meeting details and transcripts
For each completed meeting (most recent first):
- `get_meeting(meeting_id, include_previous_meeting_notes=true)` for attendees, notes, and prior-meeting notes.
- `get_meeting_transcript(meeting_id)` for the full transcript.

Start with the 2 most recent. Read both transcripts. If the content is thin (short calls, internal only, limited customer discussion), pull a 3rd or 4th. Stop at 4 max.

### 4. Pull deal and CRM context
`get_deal(prospect_org, deal_id)` returns a `crm` block. Extract:
- Opportunity amount, close date, stage (SFDC fields preferred, fall back to HubSpot).
- Any other CRM fields present (owner, account name).

Call `get_deal` once and reuse across all steps.

### 5. Check for qualification agents (optional enrichment)
`list_agents(category="qualification")`. If a qualification agent exists, run `get_qualification_results(deal_key, template_id)` to get deal-level qualification gaps. Use these to inform the "Objectives" and "What Matters Most" sections. If no qualification agent exists, skip silently.

### 6. Web enrichment (conservative)
If the company is a real, identifiable entity (not a test account), use web search for:
- Org chart context (who reports to whom, executive structure).
- Recent company news relevant to the deal.
- Contact titles and roles if not clear from transcripts.

Use only confident, exact-entity matches. If uncertain, use a placeholder or omit.

### 7. Synthesize the prep document
Read all transcripts and meeting notes carefully. Build the following sections by synthesizing across all available data. Write each section into a structured JSON file (`prep_data.json`).

**Header:**
- `company`: Company name
- `meeting_date`: Upcoming meeting date and time (PT, formatted like "Thu Jun 18, 1:30-2:00 PM ET")
- `attendees`: Array of {name, title} for expected attendees. Source from the upcoming meeting invite or infer from prior attendees.
- `call_number`: Integer. Count completed meetings in this deal + 1.

**Deal snapshot:**
- `deal.amount`: From CRM (e.g. "$30,000")
- `deal.close_date`: From CRM
- `deal.stage`: From CRM

**Open action items:** Extracted from the most recent 1-2 transcripts. Listen for commitments, promises, and agreed next steps. Classify each as:
- `action_items.ours`: Things our team committed to do
- `action_items.theirs`: Things the prospect committed to do
- `action_items.joint`: Shared commitments or parallel workstreams

For each item, include who committed and when (if stated). Flag items that appear to have slipped (committed in an earlier call but not referenced as done in a later one).

**Account hierarchy:**
- `account_hierarchy`: A text block showing the org structure as mentioned across transcripts. Use indentation to show reporting lines. Include names, titles, and roles. Only include people actually mentioned in transcripts or meeting attendees. Do not fabricate org structure. If the hierarchy is unclear, note what is known and what is inferred.

**What matters most today:**
- `what_matters`: 2-4 sentences. The single most important strategic insight for this call. What is the champion trying to accomplish? What is the biggest risk? What momentum should be protected? This is the "if you read nothing else" paragraph.

**Contact priorities (one per key stakeholder):**
- `contact_priorities`: Array of {name, priorities: [string]}. For each key contact expected on the call, list 3-5 priorities or concerns they have expressed across transcripts. Use their language. Source from what they actually said, not assumed.

**Landmines:**
- `landmines`: Array of {label, detail}. Risks, sensitivities, or topics to handle carefully. Source from transcript signals: objections raised, concerns expressed, bad past experiences mentioned, political dynamics, competitor mentions, compliance/legal constraints. Each landmine gets a short label and a 1-2 sentence detail with the recommended handling approach.

**Objectives for this call:**
- `objectives`: Array of strings. 3-5 specific, actionable objectives for the upcoming meeting. Derived from: open action items that need follow-up, qualification gaps to close, logical next steps for this deal stage, anything the champion signaled they want to accomplish.

**Success criteria:**
- `success_criteria`: Array of strings. 3-5 concrete, checkable outcomes that define a successful call. These are the "end of call" checklist items.

### 8. Build the document
1. Write the synthesized content to `prep_data.json`.
2. Run: `node build_prep_doc.js --input prep_data.json --out "Pre-Call_Prep_{Company}_{Date}.docx"`
3. Validate: `python /mnt/skills/public/docx/scripts/office/validate.py "Pre-Call_Prep_{Company}_{Date}.docx"`
4. If validation fails, fix and rebuild.
5. Present the finished .docx.

### 9. Briefing notes
After presenting the document, give a 2-3 sentence verbal summary of the most important thing to get right on this call. Mention any action items that appear to have slipped.

## Output format
The .docx follows the structure in the reference template:
- Title line with company, date/time, attendees, call number
- Deal snapshot table (Amount, Close Date, Stage)
- Horizontal rule
- Open Action Items (Ours / Theirs / Joint with checkboxes)
- Account Hierarchy (indented org chart)
- What Matters Most Today (narrative paragraph)
- Per-contact priority sections (bulleted)
- Landmines (bold label + detail)
- Objectives for This Call (numbered)
- Success = End of Call (checkbox list)

## Rules
- **Join agent_results on title, not key.** Discover field names at runtime. Never fabricate; placeholder instead.
- **Full 32-char meeting ids** everywhere, especially in URLs. Build meeting links as `https://app.aircover.ai/meetings/{full_id}`.
- **Filter by prospect_org or deal_key**, never bare deal_id.
- **No em dashes** anywhere. Use commas, periods, colons, or parentheses.
- **Lists** for enumerations (stakeholders, action items). Short prose for narrative sections.
- **Times in PT**, no UTC.
- **Omit empty sections.** If there are no landmines or no qualification gaps, skip that section rather than writing "None."
- **Never fabricate.** If a transcript does not contain clear action items, priorities, or org structure, say what is known and leave the rest out. Do not invent stakeholder titles, reporting lines, or commitments.
- **Echo the prospect's language** in priorities and landmines. Use their words, not generic sales jargon.
- **Action item slippage.** When a commitment from an earlier call is not mentioned as completed in a later call, flag it with a note like "(committed [date], not yet confirmed)."
- **Distinguish "no data" from "retry."** A get_deals cache-miss error means retry once, not that the deal is empty.
- **Handle "no transcript" gracefully.** If a meeting has no transcript, note it and move on. Never error out mid-run.
- **Scale is small.** This skill processes 2-4 transcripts per run. No batching or CSV-append pattern needed.
- **Web enrichment is conservative.** Only use confident, exact-entity matches for org chart and contact enrichment. If uncertain, omit.
