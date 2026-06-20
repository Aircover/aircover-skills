---
name: path-to-quota
description: Build a personalized end-of-quarter pipeline strategy from Aircover meeting data, CRM deal stages, MEDDPICC qualification scoring, and Deal Readiness Scorecard (close mechanics). Prompts for quota and EOQ date, finds all customer meetings in the quarter, prioritizes deals by qualification depth, close readiness, and meeting momentum, and delivers a .docx close plan with embedded charts, per-deal strategies, and next steps. Use this when someone says "path to quota", "how do I hit my number", "quarter close plan", "pipeline strategy", "what deals should I focus on", or wants a plan to close their open pipeline.
---

# Path to Quota

Build an actionable end-of-quarter pipeline strategy. Pulls all customer meetings from the trailing quarter, cross-references CRM deal data (stage, amount, close date), scores deals on two axes: MEDDPICC for qualification depth and Deal Readiness Scorecard for close mechanics (tech win, legal, procurement, budget, CTA). Analyzes meeting momentum, and produces a prioritized close plan with per-deal strategies and next steps.

## Requirements
- The **Aircover Production** connector must be connected. All meeting and deal data comes from there.
- **Code execution / file creation** must be on (for charts and the output document).
- **Docx skill** (`/mnt/skills/public/docx/SKILL.md`) must be available. Read it before generating the output. Install with `npm install -g docx`. The output is a .docx file with embedded charts (not markdown), so it opens cleanly in Google Drive, Word, and other editors.
- **Salesforce connector** is optional but recommended. When connected, provides a secondary validation that deals are still open and close dates fall within the quarter. Without it, the skill uses the CRM block from Aircover's get_deal (which mirrors SFDC fields).
- **Web search** is not required.

## Configuration
- Environment: Production (api.aircover.ai)
- App host: app.aircover.ai (for meeting links)
- CRM source: Aircover's get_deal returns a `crm` block with SFDC fields (sfdc_opportunity_name, sfdc_opportunity_id, amount, close date, stage). This is the primary CRM source. The Salesforce connector is a secondary validation layer only.

## Bundled resources
- `references/deal_readiness_scorecard.md` - the full Deal Readiness Scorecard agent spec with scoring rubrics, examples, and exclusion rules. Read this to understand what each DRS dimension means, how scores are assigned, and what the EXCLUDE lists say (critical for interpreting edge cases, especially Tech Win).

## Run order

### 1. Gather inputs from the user

Collect inputs in two rounds. Use tappable options where possible.

**Round 1: Agent selection**

Ask: "Before we start, how do you want to score your deals?"

Offer three options:
- **Use recommended agents** - "I will look for MEDDPICC (or BANT as a fallback) for qualification depth, and the Deal Readiness Scorecard for close mechanics."
- **Choose from your org's agents** - "I will show you the agents available in your Aircover account and you pick which ones to use."
- **Describe your own scoring** - "Tell me what dimensions you want to score deals on and I will build a custom rubric on the fly."

Store the selection as `agent_mode` ("recommended", "choose", "custom").

If `agent_mode` is "custom", ask a follow-up: "Describe the dimensions you want to evaluate each deal on. For example: 'champion strength, technical validation, budget status, urgency' or paste your methodology." Store as `custom_dimensions`. These will be used in step 6 to build a lightweight scoring rubric that Claude applies manually from meeting notes (no Aircover agent needed).

**Round 2: Quota, timeline, and identity**

**a) Quarterly quota.** Ask: "What is your quota for this quarter?"
Offer tappable options: "$250K", "$500K", "$1,000,000", "Type my own"
If "Type my own", accept a dollar amount. Store as `quota_target`.

**b) End of quarter date.** Ask: "When does your quarter end?"
Offer common options: "June 30", "July 31", "September 30", "December 31", or "Other (tell me the date)."
Store as `eoq_date`.

Compute `quarter_start` = `eoq_date` minus 3 calendar months. For example, if EOQ is June 30, quarter_start is April 1.

**c) User email (for owner scoping).** Ask: "What is your email address? (so I pull only your meetings, not the whole org)"
Store as `user_email`. This is required. Omitting `owner` from list_meetings returns the entire org's meetings, which is not what a rep wants here.

Confirm the plan: "Got it. I will look at all your customer meetings from [quarter_start] to [eoq_date], cross-reference your open pipeline, score deals using [agent_mode description], and build a strategy to hit $[quota_target]. Sound right?"

### 2. Load tools

Call `tool_search` with "Aircover meetings agents deals" to load the Aircover Production tools. Confirm the tools are from Production (api.aircover.ai), not Staging.

### 3. Pull all meetings in the quarter window

```
list_meetings(
  start = quarter_start in RFC3339 (e.g. "2026-04-01T00:00:00Z"),
  end = eoq_date + 1 day in RFC3339 (e.g. "2026-07-01T00:00:00Z"),
  owner = user_email
)
```

This returns all meetings the user owns in the quarter. Store the full list. Track:
- `total_meeting_count` = total meetings returned (before filtering)
- Tell the user: "Found [N] total meetings in this quarter."

Filter out internal-only meetings (meetings where all attendees share the same email domain as the user). Keep only external/customer meetings. Track:
- `customer_meeting_count` = meetings after filtering
- Tell the user: "[N] are customer meetings across [M] accounts."

### 4. Group meetings by deal

Each meeting from list_meetings includes `prospect_org` and `deal_id`. Group meetings by their deal_key (`prospect_org/deal_id`). This gives you a map of:
- deal_key -> [meeting_1, meeting_2, ...]

For each deal, also compute and store:
- `meeting_count` = number of customer meetings for this deal in the quarter
- `last_meeting_date` = date of the most recent meeting
- `days_since_last_meeting` = days between today and last_meeting_date
- `most_recent_meeting_id` = full 32-char id of the most recent meeting (needed for agent_results and get_meeting calls later)

Also group by prospect_org (company name) for display.

### 5. Pull deal and CRM context

For each unique deal_key, call `get_deal(prospect_org, deal_id)` once. Extract from the `crm` block:
- `sfdc_opportunity_name` (or HubSpot equivalent)
- `sfdc_opportunity_amount` (deal value)
- `sfdc_opp_close_date` (expected close date)
- `sfdc_current_stage` (current deal stage)
- `sfdc_opportunity_id` (for building SFDC links)

**Filter to open pipeline only.** Exclude deals where:
- The stage indicates Closed Won or Closed Lost (check for common stage names: "Closed Won", "Closed Lost", "Closed", "Won", "Lost", or any stage containing "closed"). Be generous with matching since stage names vary per org. If uncertain, keep the deal and flag it.
- The close date is after the EOQ date (these are next-quarter deals, not in scope unless the user wants them).

If the Salesforce connector is available, optionally cross-reference: query Salesforce for the opportunity by sfdc_opportunity_id to confirm the stage is still open and the close date has not shifted. This is a secondary validation, not required.

**Handle missing CRM.** Some deals may have an empty crm block (common before an opportunity is created). Keep these deals in the list but flag them as "No CRM opportunity linked." They still have meeting activity and may represent early-stage pipeline.

Compute `total_open_pipeline` = sum of all open deal amounts.
Compute `gap_to_quota` = quota_target - total_open_pipeline (may be negative if pipeline exceeds quota, which is good).
Compute `pipeline_coverage` = total_open_pipeline / quota_target as a ratio.

### 6. Resolve and run scoring agents

This step depends on the `agent_mode` chosen in step 1.

---

#### Path A: Recommended agents (`agent_mode = "recommended"`)

**Step 6A-1: Find the qualification agent (MEDDPICC, then BANT fallback)**

```
list_agents(category="qualification")
```

Search the results in this priority order:
1. Look for an agent whose title/name contains "MEDDPICC" or "MEDDIC" (case-insensitive). If found, store its `id` as `qual_template_id` and set `qual_methodology = "MEDDPICC"`.
2. If no MEDDPICC/MEDDIC agent exists, look for an agent whose title/name contains "BANT" (case-insensitive). If found, store its `id` as `qual_template_id` and set `qual_methodology = "BANT"`.
3. If neither exists, set `qual_template_id = null`. The skill continues without qualification scoring.

Tell the user which qualification agent was selected (or that none was found).

If a qualification agent exists, pull deal-level qualification for **every** open deal. No exceptions, no skipping.

**CRITICAL: 100% deal coverage is mandatory.**
Do not stop scoring partway through the deal list due to context length, response size, or any other reason. Every open deal must have a qualification score or an explicit "agent returned no data" status. If you find yourself considering skipping deals, that is the signal to use the context management strategy below.

**Context management strategy for qualification pulls:**
The `get_qualification_results` response can be large (especially for deals with many meetings). To prevent context overflow:
1. Call `get_qualification_results(deal_key, qual_template_id)` for one deal at a time.
2. Immediately extract ONLY the numbers you need: for each dimension, read the `title`, `score`, and `max_score`. Optionally read the `result` text for weak dimensions only (score < 50% of max) to inform coaching recommendations later.
3. Write the extracted scores to a running tally (a simple data structure or a file on disk if context is tight).
4. Do NOT hold the full raw response in working memory. Extract, store the numbers, move to the next deal.
5. If a single deal's response is extremely large (20+ meetings of history), extract the deal-level scores from the response and move on. The deal-level scores are what matter, not the per-meeting history.

```
get_qualification_results(deal_key, qual_template_id)
```

This returns per-dimension scores. The dimensions vary by methodology:
- **MEDDPICC:** Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion, Competition, Paper Process
- **BANT:** Budget, Authority, Need, Timeline

For each deal, compute:
- `qual_total_score` = sum of scored dimensions (where max_score > 0)
- `qual_max_possible` = sum of max_score values
- `qual_pct` = total_score / max_possible as a percentage
- `weak_dimensions` = dimensions where score is 0 or significantly below max_score (less than 50% of max). For weak dimensions, save the `result` text (the agent's finding) to use in coaching recommendations.
- `strong_dimensions` = dimensions where score is at or near max

Join on the entry `title`, not the key. Discover the actual dimension titles from the first response rather than hardcoding.

**If you have more than 15 open deals:** Write scores to a CSV on disk as you go (`/home/claude/qual_scores.csv`) rather than holding everything in the conversation. Columns: deal_key, company, dimension, score, max_score, result_summary. Read from the file when building the output.

**Step 6A-2: Find the Deal Readiness Scorecard agent**

**First:** Read `references/deal_readiness_scorecard.md` for the full scoring rubrics, example signals, and exclusion lists. The exclusion rules are critical for interpreting scores correctly, especially Tech Win where discovery conversations and conceptual alignment are explicitly excluded from scoring.

While still in the `list_agents` results (or re-call `list_agents()` without a category filter if needed), look for an agent whose title/name contains "Deal Readiness" or "Punchcard" (case-insensitive). If found, store its `id` as `deal_readiness_template_id`.

The Deal Readiness Scorecard measures late-stage close mechanics across six scored dimensions (each 0-3) plus a Recommendation extraction:

| Dimension | What it measures |
|---|---|
| Tech Win | Has the solution been technically validated through hands-on testing (POC, pilot, internal endorsement)? Excludes conceptual alignment, discovery, demos without buyer-confirmed results. |
| Access to Legal | Does the rep have access to legal/contracts stakeholders? |
| Legal Win | Is legal review complete or actively progressing toward signature? |
| Access to Procurement | Is the rep engaged with procurement/purchasing for PO or vendor onboarding? |
| CTA for Current Quarter | Is there a mutual close plan with specific quarter-linked milestones? |
| Budget Confirmed | Is funding verified, allocated, or approved? |
| Recommendation | (Unscored, max_score=0) Synthesized coaching recommendation across all dimensions |

**How to pull scores:** For **every** open deal that has at least one meeting with a transcript, run the scorecard against the most recent meeting:
```
agent_results(meeting_id=most_recent_meeting_id, template_id=deal_readiness_template_id)
```

**Same 100% coverage rule applies.** Score every deal. Use the same extract-and-discard strategy: pull the response, extract title/score/max_score/result for each dimension, save the Recommendation text, discard the raw response, move to the next deal. Write to disk if context is tight.

Note: Unlike MEDDPICC/BANT (which have deal-level qualification via get_qualification_results), the Deal Readiness Scorecard runs per-meeting via agent_results. Use the most recent external meeting per deal for the most current read.

For each deal, compute:
- `drs_total_score` = sum of scored dimensions (where max_score > 0, i.e. the 6 scored categories)
- `drs_max_possible` = sum of max_score values (6 x 3 = 18 max)
- `drs_pct` = total_score / max_possible as a percentage
- `drs_weak_categories` = dimensions scoring 0 or 1 (major gaps in close mechanics)
- `drs_strong_categories` = dimensions scoring 2 or 3 (close mechanics on track)
- `drs_recommendation` = the Recommendation property text (max_score=0, unscored extraction)

Join on the entry `title`, not the key.

If no Deal Readiness Scorecard agent exists, skip silently.

---

#### Path B: User chooses from org's agents (`agent_mode = "choose"`)

Pull the full agent list:
```
list_agents()
```

Present the available agents to the user in a clean list: agent name, category, and a one-line description if available. Ask:

"Here are the agents available in your Aircover account. Pick up to 3 that you want to use for scoring deals. I will use them to evaluate your pipeline."

For each selected agent, determine how to run it:
- If the agent's category is "qualification", use `get_qualification_results(deal_key, template_id)` for deal-level scoring.
- For all other categories, use `agent_results(meeting_id, template_id)` on the most recent meeting per deal.

Store the selected agents as `selected_agents = [{id, name, run_method}]`.

For each deal, run the selected agents and extract scores the same way as Path A: discover dimensions from the first response, compute total/max/pct, identify weak and strong dimensions. Store results keyed by agent name.

---

#### Path C: User describes custom scoring (`agent_mode = "custom"`)

The user provided `custom_dimensions` in step 1 (e.g. "champion strength, technical validation, budget status, urgency").

No Aircover agent is used for scoring. Instead, Claude builds a lightweight rubric from the user's dimensions and applies it manually using the meeting notes and deal context already pulled in steps 3-5 and 8.

**Build the rubric:** For each dimension the user described, define a 0-3 scale:
- 0: No signal found in any meeting
- 1: Mentioned or early stage
- 2: In progress, partially confirmed
- 3: Confirmed, validated, or complete

**Apply the rubric:** For each deal, read the `get_meeting` notes and `customer_summary` from step 8 (the most recent meeting per deal). Score each custom dimension based on the evidence in those notes. Be conservative: only credit what is explicitly stated, not inferred.

For each deal, compute:
- `custom_total_score` = sum of dimension scores
- `custom_max_possible` = number of dimensions x 3
- `custom_pct` = total / max as a percentage
- `weak_dimensions` = dimensions scoring 0 or 1
- `strong_dimensions` = dimensions scoring 2 or 3

**Important:** Tell the user these scores are Claude's interpretation from meeting notes, not from a trained Aircover agent. They are directional, not authoritative.

---

#### Interpreting the scores (all paths)

Regardless of which path was used, the skill now has two potential score layers per deal:
- **Qualification score** (MEDDPICC, BANT, user-chosen qualification agent, or custom rubric) measuring how well the deal is qualified
- **Close readiness score** (Deal Readiness Scorecard, user-chosen close agent, or custom rubric) measuring how close the deal is to actually closing

When both layers exist:
- High qualification + High close readiness = deal is well-qualified AND close mechanics are in place. Priority: execute the close plan.
- High qualification + Low close readiness = deal is well-qualified but process gaps will block the close. Priority: unblock legal, procurement, budget, or tech validation.
- Low qualification + High close readiness = close mechanics are moving but qualification is thin. Risk: deal may close at bad terms or churn. Priority: shore up qualification before finalizing.
- Low qualification + Low close readiness = early stage or stalled. Priority: re-qualify or deprioritize.

When only one layer exists, use it alongside momentum and deal size for prioritization.

**Scale note:** agent_results is one call per meeting per agent. For per-meeting agents (DRS and non-qualification agents), run only on the most recent meeting per deal, so the call count equals the number of open deals per agent.

**NON-NEGOTIABLE: Score 100% of deals.**
The skill MUST score every open deal with every available agent before producing output. "Running out of context" or "this is taking a while" is not a valid reason to skip deals. Use these strategies to manage context:
1. Extract scores immediately, discard raw responses. You need title + score + max_score per dimension, plus the result text for weak dimensions only. That is ~50 tokens per deal per agent, not thousands.
2. Write extracted scores to a file on disk (`/home/claude/scores.csv`) if you have more than 10 deals.
3. Process deals sequentially: pull, extract, discard, next.
4. If a single agent_results call returns an error or no data (no transcript), record "No transcript" for that deal and continue. Do not stop the loop.
5. Tell the user the progress: "Scoring deal 5 of 15..." so they know work is happening.

If there are 30+ open deals, warn the user that scoring will take several minutes and proceed. Do not ask permission to skip deals. Do not offer to "come back and score the rest later." Do the work.

### 7. Analyze meeting momentum

For each deal, analyze the meeting pattern from the grouped meetings in step 4:

**Frequency signals (strong momentum indicators):**
- Multiple meetings in the same calendar week = high engagement signal
- Meetings occurring at a regular cadence (weekly, biweekly) = sustained engagement
- Recent meeting activity (meeting within the last 2 weeks) = active deal
- Increasing meeting frequency over the quarter = accelerating deal

**Staleness signals (risk indicators):**
- No meeting in the last 3+ weeks = deal may be stalling
- Single meeting with no follow-up scheduled = early stage or disengaged
- Decreasing meeting frequency = losing momentum

For each deal, assign a `momentum_score`:
- HIGH: 2+ meetings in any single week, OR meetings at least weekly for 3+ consecutive weeks, OR a meeting in the last 7 days AND 3+ total meetings
- MEDIUM: Meetings at least biweekly, OR a meeting in the last 14 days with 2+ total meetings
- LOW: Last meeting more than 21 days ago, OR only 1 meeting total with no upcoming scheduled

### 8. Pull next steps from the most recent meeting per deal

For each deal, take the most recent completed meeting. Call:
```
get_meeting(meeting_id, include_previous_meeting_notes=true)
```

Read the `notes` and `customer_summary` for agreed next steps, commitments, and action items. Extract:
- `next_steps`: what was agreed
- `owners`: who committed to what (ours vs theirs)
- `last_meeting_date`: when it happened
- `days_since_last_meeting`: computed from today

If the notes mention a next meeting date or follow-up, capture that too.

### 9. Prioritize and rank deals

Score each deal on a composite basis using three signal layers: qualification depth (from the qualification agent or custom rubric), close readiness (from the Deal Readiness Scorecard or custom rubric), and behavioral momentum (meeting patterns).

The thresholds below use percentages so they work regardless of which methodology or agent is in play.

**Priority Tier 1 (Must Win):**
- High momentum + high qualification (top 25% of scored deals) + high close readiness (67%+ of max) + close date within 30 days of EOQ
- OR: high close readiness (67%+) regardless of qualification, indicating close mechanics are actively in motion
- OR: deal amount alone would close >25% of the remaining gap to quota

**Priority Tier 2 (Should Win):**
- Medium or high momentum + decent qualification (above 50%) + moderate close readiness (40-66% of max) + close date before EOQ
- OR: high momentum + high close readiness but lower qualification (close mechanics outpacing qualification, common in fast-moving deals)
- OR: high momentum regardless of scoring (meeting activity is a leading indicator)

**Priority Tier 3 (Could Win):**
- Low momentum but still open, or early-stage deals with some activity
- Low close readiness (below 40%) but decent qualification = well-qualified deal that has not entered close process yet
- These need a close mechanics activation strategy

**Priority Tier 4 (Long Shot):**
- Low momentum + low or no qualification score + low close readiness + no recent activity
- Flag these as at-risk for push or loss

Sort within each tier by: close readiness score (descending), then qualification score (descending), then deal amount (descending), then recency of last meeting (most recent first).

### 10. Build per-deal close strategies

For each deal (starting with Tier 1), write a strategy section:

**Deal header:** Company name, deal name, amount, stage, close date, qualification score and methodology name (if available), close readiness score (if available), momentum rating, last meeting date.

**Meeting link:** `https://app.aircover.ai/meetings/{most_recent_meeting_id}` for the most recent meeting.

**Close readiness gap analysis (if Deal Readiness Scorecard or close-readiness agent exists):**
This is the close mechanics layer. For each weak category (score 0 or 1), provide the specific unblock action:

- **Tech Win (0-1):** "Technical validation is incomplete. Important: a score of 0-1 means no hands-on testing has confirmed the solution works in the buyer's environment. Conceptual alignment, use case mapping, and demo reactions do not count. Prioritize getting a POC or pilot scheduled with measurable success criteria. Ask: 'What does your technical evaluation process look like, and who leads it? What specific criteria do you need validated before moving forward?' If score is 1 (early interest or conceptual fit only), push for concrete testing: 'Can we set up a proof of concept against your actual environment so your team can validate the results firsthand?'"
- **Access to Legal (0-1):** "You do not have access to legal stakeholders. This will block contract execution. Ask: 'What does your typical contract review process look like? Who specifically handles that, and can we start that conversation now?'"
- **Legal Win (0-1):** "Legal review has not progressed. If Access to Legal is scored 2-3 but Legal Win is low, the bottleneck is review speed. Ask: 'What remaining redline items exist? What is the expected resolution timeline? Can we help accelerate?'"
- **Access to Procurement (0-1):** "Procurement is not engaged. This is often the last-mile blocker for quarter-end deals. Ask: 'What does your purchasing process look like? Who manages vendor onboarding, and what do they need from us to get started?'"
- **CTA for Current Quarter (0-1):** "There is no mutual close plan tied to this quarter. Without this, the deal drifts. Ask: 'Is there a business reason this needs to be in place by [EOQ date]? What milestones do we need to hit between now and then?'"
- **Budget Confirmed (0-1):** "Budget is not confirmed. This must be resolved before procurement can issue a PO. Ask: 'Has funding been identified for this? What does the budget approval process look like, and who owns it?'"

For categories scoring 2, note them as "in progress" and identify the specific next step to reach a 3.

**Coaching recommendation echo:** If the close readiness agent returned a Recommendation property (max_score=0, unscored), include it as "Agent's coaching note: [text]".

**Qualification gap analysis (if qualification agent or custom rubric exists):**
This is the qualification depth layer. For each weak dimension, provide a specific, actionable recommendation.

If the methodology is known (MEDDPICC, BANT, or another standard), use methodology-specific coaching:

**MEDDPICC coaching bank:**
- **Metrics:** "You have not established quantified business impact. In your next meeting, ask: 'What would solving this problem be worth to you in [revenue/cost savings/time] per [month/quarter/year]?'"
- **Economic Buyer:** "The economic buyer has not been identified or engaged. Ask your champion: 'Who ultimately signs off on this budget? Can we get 15 minutes with them to understand their priorities?'"
- **Decision Criteria:** "The formal evaluation criteria are unclear. Ask: 'What will you be evaluating solutions against? Is there a scorecard or RFP?'"
- **Decision Process:** "You do not have a clear picture of the buying process. Ask: 'Walk me through what happens between now and a signed contract. Who needs to approve, in what order, and what could slow things down?'"
- **Identify Pain:** "The core pain has not been deeply validated. Ask: 'What happens if you do nothing? What is the cost of the status quo for the next 6-12 months?'"
- **Champion:** "You need a stronger internal champion. Ask: 'Who internally is most invested in making this happen? Can they help us navigate the internal process?'"
- **Competition:** "Competitive landscape is unclear. Ask: 'Are you evaluating other solutions? What do you like about what you have seen so far?'"
- **Paper Process:** "Legal, procurement, and contract process is undefined. Ask: 'What does your procurement process look like? Are there standard terms, security reviews, or legal reviews we should start now?'"

**BANT coaching bank:**
- **Budget:** "Budget status is unclear. Ask: 'Has funding been identified for this initiative? What does budget approval look like, and where are you in that process?'"
- **Authority:** "The decision maker has not been confirmed. Ask: 'Who ultimately makes the final call on this? Have they been involved in our conversations?'"
- **Need:** "The business need has not been deeply validated. Ask: 'What is the cost of not solving this? What happens to your team or business if you do nothing for the next 6 months?'"
- **Timeline:** "There is no clear timeline driving this purchase. Ask: 'Is there a specific event, deadline, or initiative that determines when you need this in place?'"

**For user-chosen agents or custom rubrics:** Generate coaching recommendations dynamically based on the dimension name and the deal context. Frame each weak dimension as: what is missing, why it matters, and a specific question to ask in the next meeting.

Note: If both MEDDPICC/BANT "Paper Process"/"Budget" and DRS close-mechanic categories exist, lead with the DRS categories (they are more granular on close mechanics) and reference the qualification dimension only if it surfaces something the DRS missed.

Tailor each recommendation to the specific deal context (industry, stage, what was discussed in the last meeting).

**Combined close readiness assessment:**
Based on the qualification + close readiness + momentum signals together, categorize the deal into one of these action modes:
- **EXECUTE:** High qualification + High close readiness + High momentum. The deal is qualified and the close process is running. Focus: hit every milestone on time, remove friction, do not introduce new variables.
- **UNBLOCK:** High qualification + Low close readiness. Well-qualified but process-stuck. Focus: activate the specific close mechanic that is missing (legal, procurement, budget, tech validation).
- **ACCELERATE:** High close readiness + Medium/Low qualification. Close process is moving but qualification is thin. Focus: shore up qualification (especially champion, economic buyer, metrics) before the deal closes at bad terms or with churn risk.
- **RE-ENGAGE:** Low momentum regardless of scores. Focus: get a meeting on the calendar this week with a value-based hook. If no response in 7 days, flag for push/loss decision.
- **DEPRIORITIZE:** Low everything. Focus: make a go/no-go decision. Either invest a focused re-engagement sprint or move the close date out and reallocate time to Tier 1 deals.

**Momentum-based strategy:**
- HIGH momentum: "This deal is active. Focus on advancing the process, not re-engaging. Key moves: [specific actions based on the next steps and scoring gaps]."
- MEDIUM momentum: "Engagement is decent but not urgent for the buyer. Create urgency: [specific actions]. Suggest a mutual action plan with dates tied to their EOQ initiatives."
- LOW momentum: "This deal is stalling. Re-engage with a value-based touchpoint: share a relevant case study, new ROI data, or connect them with a reference customer. If no response in 7 days, this deal is at risk for push."

**Next steps recap:** Echo the next steps from step 8 with owner assignments and flag anything that appears to have slipped.

### 11. Produce the output

The output should be scannable, visual, and action-oriented. Use bullets and tables over paragraphs. Generate charts where the data supports them.

**Formatting rules for the entire document:**
- **Bullets, not paragraphs.** Every per-deal strategy, tier breakdown, and recommendation should be bulleted, not written as flowing prose. Reps scan this before calls, they do not read essays.
- **Bold the action.** In each bullet, bold the verb or the thing that needs to happen: "**Send** security one-pager to Ken", "**Ask:** 'Who manages vendor onboarding?'"
- **One line per insight.** If a point takes more than 2 lines, break it into sub-bullets.

**Output format: Word document (.docx)**

Read the docx skill (`/mnt/skills/public/docx/SKILL.md`) before generating the output. Use `npm install -g docx` and build the document in JavaScript with the `docx` library. This produces a .docx that opens cleanly in Google Drive, Word, and other editors (unlike markdown with embedded PNG references, which fails on Google Drive export).

**Document design:**
- Font: Arial throughout. Default body size 11pt.
- Heading 1: 18pt bold, color #1B2A4A (navy). Heading 2: 14pt bold, color #1B2A4A. Heading 3: 12pt bold, color #2CB5AD (teal).
- Tables: header row with navy background (#1B2A4A) and white text, light cell shading by tier (green-tint for T1, blue-tint for T2, amber-tint for T3, red-tint for T4). Always use DXA widths, never percentages. Set both `columnWidths` on the table and `width` on each cell.
- Bullets: use `LevelFormat.BULLET` with numbering config. Never use unicode bullet characters.
- Bold action verbs in every bullet using TextRun with `bold: true`.
- Page breaks between major sections (after charts, before per-deal strategies, before closing playbook).
- Charts: generate as PNGs with matplotlib at 300 DPI, then embed as `ImageRun` with `type: "png"`. Size to ~650px wide for full-width charts.
- After building, validate with `python scripts/office/validate.py`.

Build the .docx with the following sections:

---

**Executive Summary (table format):**

| Metric | Value |
|---|---|
| Quota | $[quota_target] |
| Open Pipeline | $[total_open_pipeline] |
| Pipeline Coverage | [ratio]x |
| Gap to Quota | $[gap_to_quota] or "Pipeline exceeds quota by $X" |
| Deals in Play | [count] |
| Total Meetings (Last 90 Days) | [total count from list_meetings before filtering] |
| Customer Meetings | [count after filtering out internal-only] |
| Quarter Window | [quarter_start] to [eoq_date] |
| Days Remaining | [computed from today to eoq_date] |

Below the table, add a 2-3 bullet reality check: what the coverage ratio actually means given close dates, momentum, and deal health. Example:
- "Coverage looks healthy at 2.5x, but only $X of pipeline has close dates before EOQ"
- "Real in-quarter pipeline: $X across N deals"
- "You need to close [all of Tier 1 / pull in N Tier 2 deals] to hit quota"

---

**Charts (generate with code execution, embed in docx):**

Generate the following charts using matplotlib, save as PNGs, then embed them in the .docx via `ImageRun`. Do NOT save charts as separate output files; the whole point of .docx is that the charts live inside the document.

**Chart generation process:**
1. Generate each chart with matplotlib and save as PNG at 300 DPI to `/home/claude/` (working directory, not outputs).
2. In the docx build script, `fs.readFileSync` each PNG and embed as `new ImageRun({ data: buffer, transformation: { width: 650, height: N }, type: "png" })`.
3. Charts go in their own section after the Executive Summary, before the Pipeline Overview Table.

**Color palette (use consistently across all charts):**
- Tier 1 / Must Win / High / Score 3: `#2E7D32` (strong green)
- Tier 2 / Should Win / Medium / Score 2: `#1565C0` (strong blue)
- Tier 3 / Could Win / Low / Score 1: `#F9A825` (amber/warning)
- Tier 4 / Long Shot / Score 0: `#C62828` (red)
- Quota line: `#212121` (black, dashed)
- Background: white, no gridlines

**Chart styling rules:**
- Title in bold, 14pt. Axis labels 11pt.
- Label data directly on bars/cells (not in a separate legend) when possible.
- Use commas in dollar amounts ($51,000 not $51000).
- Save each chart as a separate PNG at 300 DPI to `/home/claude/` (working directory). They will be embedded in the docx, not presented separately.

1. **Pipeline by Tier (horizontal stacked bar):** Single horizontal bar showing Tier 1 (green) / Tier 2 (blue) / Tier 3 (amber) / Tier 4 (red) amounts stacked left to right, with a vertical dashed black line at the quota target. Label each segment with the dollar amount and tier name. Shows at a glance how much pipeline sits in each tier relative to the number. Add a second thin bar below showing "In-Quarter Only" (deals with close dates before EOQ) to highlight the real coverage gap.

2. **Scenario Waterfall:** Horizontal waterfall chart showing the cumulative path to quota. Start with Tier 1 total (green), then add the best pull-in deals one at a time (blue), with a horizontal dashed black line at quota. Label each bar with the deal name and amount. The bar that crosses the quota line should be visually highlighted. Makes the "what combination do I need" question instantly clear.

3. **Deal Momentum Timeline (optional, if 5+ deals):** Scatter plot with x-axis = date (quarter window), y-axis = deal name. Each dot is a meeting, color-coded by tier (green/blue/amber/red). Dot size slightly larger for external meetings. Instantly shows cadence, gaps, and recency. Add a vertical "today" line in black.

4. **Close Readiness Heatmap (if DRS or close-readiness agent exists):** Grid chart with deals as rows and DRS categories as columns. Color-coded cells: green (3), yellow-green (2), amber (1), red (0). White cells for "Not scored." Add the numeric score inside each cell. Sort rows by total DRS score descending. This replaces the text-based heatmap table and is the single most important chart in the output.

---

**Pipeline Overview Table:**
| Priority | Company | Deal | Amount | Stage | Close Date | Qual % | Close Readiness | Mtgs | Last Mtg | Momentum | Action Mode |
Add a `Mtgs` column (count of meetings for this deal in the quarter) and `Last Mtg` column (date of most recent meeting, with "X days ago" in parentheses). Sorted by priority tier, then amount descending. Omit score columns that do not exist.

---

**Priority Tier Breakdown:**
For each tier:
- Tier header with deal count and total dollar amount
- One bullet per deal: Company ($amount): one-line summary of status and why it is in this tier
- No paragraphs. No multi-sentence explanations. The per-deal strategies section has the detail.

Example format:
```
### Tier 1: Must Win (3 deals, $86,856)
- **Corpay ($51K):** Active pilot, weekly meetings, close hinges on product fixes and procurement extension
- **FacilityOS ($28K):** Pilot running, Salesforce integration in progress, no budget/legal/procurement yet
- **Unravel ($7.4K):** Pending renewal, steady cadence, should be straightforward
```

---

**Per-Deal Strategies (bulleted, not paragraphs):**

Each deal section should follow this exact format:

```
### [Company] ($[amount]) | Tier [N] | [ACTION MODE]

**Scores:** Qual [X%] | Close Readiness [X/18] | Momentum [HIGH/MED/LOW] | [N] meetings, last [date] ([X] days ago)
**Meeting link:** https://app.aircover.ai/meetings/{id}

**Close Readiness Gaps:** (if close-readiness agent exists)
- [Category] ([score]/3): [one-line finding or "Not started"]
- [Category] ([score]/3): [one-line finding]

**Qualification Gaps:** (if qualification agent exists)
- [Dimension] ([score]/3): [one-line finding]
- [Dimension] ([score]/3): [one-line finding]

**Strategy:**
1. **[This week]:** [specific action with bold verb]
2. **[Next week]:** [specific action]
3. **[By date]:** [specific action]

**Key Questions to Ask:**
- "[Exact question tied to the biggest gap]"
- "[Second question]"

**Next Steps (from last meeting):**
- [Action item] (owner: [name], committed [date])
- [Action item] (owner: [name])
```

No flowing prose anywhere in the per-deal section. Every insight is a bullet. Every action has a bold verb and a date.

---

**Close Readiness Heatmap:**
If the heatmap chart was generated, embed it here via ImageRun. If not (no code execution), fall back to a formatted Table:
| Deal | Tech Win | Legal Access | Legal Win | Procurement | CTA Quarter | Budget |
Use: checkmark (3), arrow (2), warning (1), X (0).

After the heatmap, add a **Portfolio-Level Gaps** section (bulleted):
- "N out of N deals have [category] at 0. This is your #1 systemic blocker."
- "Strongest area: [category] averaging [X]/3 across scored deals."

---

**Closing Playbook:**

**Week-by-week action plan** (bulleted, one section per week from today to EOQ):
```
**Week of [date range]:**
- **Corpay:** [specific action]
- **DHL:** [specific action]
- **Huntress:** [go/no-go decision point]
```

**Scenario Analysis** (bulleted, with chart reference if generated):
- Tier 1 only: $X (Y% of quota)
- Tier 1 + [best pull-in]: $X (Y%)
- Tier 1 + Tier 2 best case: $X (Y%)
- Path to 100%: [specific combination required]

**Risk Flags** (bulleted, bold the risk):
- **[Risk]:** [one-line explanation and recommendation]

---

Save as a Word document: `Path_to_Quota_{eoq_date}.docx` in `/mnt/user-data/outputs/`.
Validate with `python /mnt/skills/public/docx/scripts/office/validate.py <file>` before presenting.
Present the single .docx file to the user. Charts are embedded inside the document, not saved separately.

## Rules (from the Aircover MCP playbook)

- **100% DEAL COVERAGE IS MANDATORY.** Every open deal must be scored by every available agent. Do not skip deals due to context length, large responses, or time. Extract scores (title + score + max_score), discard raw responses, write to disk if needed, and continue. "Not scored" in the output is acceptable ONLY when the deal has no transcript or the agent returned an error, never because you ran out of room or made a judgment call to stop early. This is the #1 quality bar for this skill.
- **Join agent_results on title, not key.** Discover field names at runtime. Never fabricate; use placeholders instead. This applies to all agents: qualification (MEDDPICC, BANT, or other) via get_qualification_results, and per-meeting agents (Deal Readiness Scorecard or other) via agent_results.
- **Full 32-char meeting ids** everywhere, especially in URLs. Build meeting links as `https://app.aircover.ai/meetings/{full_id}`.
- **Filter by prospect_org or deal_key**, never bare deal_id. Use `prospect_org/deal_id` as the composite key.
- **Call get_deal once per unique (prospect_org, deal_id)** and reuse across all steps.
- **No em dashes** anywhere. Use commas, periods, colons, or parentheses.
- **Bullets over prose.** Every per-deal strategy, tier breakdown, and recommendation should be bulleted. Bold the verb in each action bullet. Reps scan this document, they do not read it. One insight per line.
- **Times in PT**, no UTC.
- **Omit empty sections.** If no qualification agent was found or selected, skip qualification gap analysis entirely (do not write "N/A"). Same for close readiness. If a deal has no CRM data, flag it but do not fabricate values.
- **Never fabricate.** If a deal has no amount, no stage, or no close date, say so. Do not invent values. Mark them as "Not set" or "No CRM opportunity linked." If agent_results returns "Not Found" for a scored category, treat it as score 0 for that category.
- **Custom rubric caveat.** When using Path C (custom scoring), always note in the output that scores are Claude's interpretation from meeting notes, not from a trained Aircover agent.
- **Distinguish "no data" from "retry."** A get_deals cache-miss error means retry once, not that the deal is empty.
- **Handle "no transcript" gracefully.** If a meeting has no transcript, still include it in the meeting count and momentum analysis, but skip both the next-steps extraction and any per-meeting agent runs for that meeting (agent_results needs a transcript).
- **Scale awareness.** This skill typically processes 10-50 deals. If list_meetings returns 200+ meetings, warn the user it will take a few minutes and proceed (do not ask to narrow). For get_qualification_results, run one call per deal. For agent_results (per-meeting agents), run one call per deal on the most recent meeting only. Total agent_results calls = number of open deals x number of per-meeting agents selected. For 15 deals x 2 agents = 30 calls, which is fine. For 50+ deals, warn about time and proceed.
- **Owner scoping is mandatory.** Always pass the user's email to list_meetings. Pulling the whole org's meetings and trying to filter client-side is wasteful and may exceed context.
- **Discover field names at runtime.** Inspect the first get_deal, get_qualification_results, and agent_results responses to confirm the actual CRM field names and agent dimension titles before building the output. Do not hardcode field names.
- **All scoring agents are optional.** The skill works with any combination: both agents, one agent, custom rubric, or none. When no scoring exists, prioritization uses CRM data (deal amount, stage, close date) and meeting momentum only.
