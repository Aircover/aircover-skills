---
name: aircover-agent-optimizer
description: Autonomously optimize an Aircover coaching agent by auditing its real output against real call transcripts, revising the config, updating the agent in place, re-running, and repeating until quality converges. Use when someone wants to optimize, tune, harden, or improve an existing coaching or extraction agent end to end, says "optimize this agent", "make this agent better", "run the optimization loop", "tune agent X until it converges", or wants a hands-off loop rather than a manual per-call edit. Drives the whole loop from this manual: baseline eval, per-property scoring, revision, dry-run-checked update, refreshed re-eval, and before/after comparison. Updates the live agent in place with a local snapshot as rollback. Does not design agents from scratch (aircover-agent-builder) and does not clone-before-edit (aircover-agent-eval-loop); this one edits in place.
---

# Aircover Agent Optimizer

An autonomous optimization loop for an existing Aircover coaching or extraction agent. You (the model) run it end to end: pull real output, score it against real transcripts, revise the weakest properties, update the agent, re-run on the same meetings, compare, and repeat until it converges or a stop condition fires.

The engine is `scripts/agent_optimize.py` (all Aircover API calls) plus this manual (all judgment). No MCP, no Anthropic API key. It runs on the customer's Aircover token. You are the LLM in the loop.

**Before anything else, confirm the tool is intact:**
```bash
python3 scripts/test_agent_optimize.py    # expect: All 33 tests passed.
```
If that is not green, stop. The environment is wrong and nothing below is trustworthy.

## The loop

```
BASELINE (cached) -> AUDIT -> REVISE -> UPDATE (dry-run first) -> RE-EVAL (fresh) -> AUDIT -> COMPARE -> loop or stop
```

## Side effects: read before running on a customer account

The agent-results endpoint is NOT a pure read. How you fetch decides whether you spend the customer's tokens and mutate their stored data. `eval --mode` controls it:

| Mode | Sends | Behavior | Cost |
|---|---|---|---|
| `cached` (default) | `cache_only=true` | stored results only; "no cached result" if never run | free, read-only |
| `fresh` | `refresh=true&preview=true` | fresh LLM run, NOT persisted | tokens, no mutation |
| `preview` | same as `fresh` | deprecated alias, identical behavior | tokens, no mutation |
| `persist` | `refresh=true` | fresh run AND overwrites the live cache | tokens, mutates state |

A bare uncontrolled run on a never-run meeting spends tokens and persists. Never issue one. **Baseline = cached. Iteration re-eval = fresh. persist only for a deliberate final run.**

**Why `fresh` sends both flags.** The server's cache short-circuit is gated ONLY on `refresh`. `preview` alone merely suppresses the save at the end, so on any meeting that already has a cached result it returns the STALE pre-change output while looking exactly like a successful fresh run. Only `refresh=true` busts the cache; `preview=true` then skips the write.

**Cost reality.** Token charges are recorded BEFORE the no-persist check, so `fresh` and `persist` cost exactly the same. `fresh` buys non-mutation, not a discount. `persist` additionally writes into the org's qualification and deal rollups, which is customer-visible state moving because of a tuning round.

**Do not infer cache state from visibility.** Visibility is a filter applied on top of routing, never a trigger. Automatic execution requires the agent to be wired into one of three paths: orchestrator-routed (`routeAndExecuteAgents`, runs only agents named in an orchestrator branch whose conditions matched the meeting), in `promptSettings.AggregateTemplateIds` and passing `IsQualificationTemplate()`, or a partner/training override. An agent in none of those never runs on its own, whatever its visibility. The visibility filter then skips personal agents on those automatic paths.

Personal agents CAN still carry cached results, because on-demand writes ignore visibility entirely: any non-preview GET, the PUT save path, the Research Agent, and this script's own `--mode persist`. Note the GET path is creator-exclusive for a personal agent: the same permission check that hides the template from everyone else also means only the creator's token can trigger that write. No teammate can have warmed the cache for you.

So always run `--mode cached` first. It is free and definitive, and it tells you exactly which meetings would return stale output.

## Step 1: Baseline eval

**First, prove the sampler can see the corpus. This is free.**
```bash
python3 scripts/agent_optimize.py --stage prod list-meetings --days 90 --count 15
```
`list-meetings` hits only `/meeting_list/` and `/organization/`. No agent runs, no tokens, no mutation. It prints the org, the identity on your token, that identity's role, a per-rep meeting count, and a dropped-reason breakdown. Run it before every baseline. If it returns a handful of meetings on an org you know is busy, read the next section rather than concluding the token lacks access.

### The meeting list is OWNER-SCOPED, not org-scoped

`GET /meeting_list/` with only `start`/`end` does **not** return the org's meetings. Server-side (`server/meeting_http.go` -> `meeting.ReadMeetingsByUser`), a call with no broadening filter resolves to `ReadMeetingsByOwner(filters, ad.Username)`: **only meetings owned by the calling identity.** A helper, integration, or service account that never sits on calls owns nothing, so it gets a near-empty list even though its token can read every one of those meetings individually.

This is scope, not permissions. It is the single most misleading failure this tool has, because a 1-meeting result looks exactly like an access problem and invites you to go hunting for a different token. A token from "someone who attends calls" does not fix it either; it just swaps one person's calendar for another's.

The fix is a broadening filter. `--scope` controls it:

| Scope | Sends | Returns |
|---|---|---|
| `org` (default) | `GET /organization/` then `customer_owner=<rep>` per rep | the org's whole corpus, deduped |
| `self` | nothing | the caller's OWN meetings only (the old behavior) |
| `explicit` | `customer_owner=<email>` for each `--owners` | just those reps |
| `prospect` | `prospect_org=<domain>` | every meeting for one prospect account |

`GET /organization/` is `isVerified`, not admin-gated, so any verified user can read `org_users` to discover the rep list.

**One gate to check: the caller's org role.** Roles are `0 Viewer, 1 Owner, 2 Admin, 3 Editor, 4 Manager, 5 GlobalViewer`. When a **Viewer (role 0)** passes any broadening filter, the server's Viewer enumeration gate refilters the results down to meetings that user personally attended, which puts you right back at near-empty. The sampler reads your role and prints a warning when it is 0. Role 0 is also the zero value, so an identity missing from `org_users` reads as Viewer and fails closed. Fix it in org settings (Editor or above), or pin meetings by ID. `GlobalViewer (5)` is not caught by this gate.

`RestrictMeetingDetailsToParticipants`, if the org has it on, filters on top of all of this for every role.

**Then the baseline:**
```bash
python3 scripts/agent_optimize.py --stage prod eval --agent <ID> --count 10 --mode cached --days 90
```
Samples random 30+ minute recorded meetings (or pass `--meeting-list <file>` / `--include <id...>`), pulls transcript + agent results per meeting, and saves a config snapshot (`agent_config.json`, the only rollback), `agent_summary.md` (read this first), and `manifest.json`. If many meetings come back "no cached result," either sample meetings the agent has run on, or switch to `--mode fresh` (spends tokens); state which in the audit.

**Two sampling filters that quietly shrink the pool.** `--days` defaults to 30 and `--min-duration` to 30. The sampler also requires `actual_start_time` to be set, because a calendar invite the notetaker never joined has no transcript to audit while still passing a duration filter on its scheduled window (`--no-require-recorded` opts out). Duration is computed from a consistent time pair: the actual pair when both ends are present, otherwise the scheduled pair whole. Never mix an actual start with a scheduled end.

**Token lifetime.** Aircover access tokens are short-lived (~15 minutes), which is shorter than a 10-meeting `fresh` eval takes. Prefer `AIRCOVER_USERNAME` + `AIRCOVER_PASSWORD` over `AIRCOVER_TOKEN`: the script re-authenticates on a 401 and retries, so a long run does not lose the meetings it already paid for. With `AIRCOVER_TOKEN` alone there is nothing to refresh from, and the 401 error says so.

**Reading `*_agent_results.json`: config and results are shape-identical.** `/transcript/coaching/` does not return results as their own object. `sendCoachingResults` hydrates the template via `ToPromptCoachingTemplateWithResults` and returns the merged thing, so a results payload has the same `properties`, `description`, `scoring_rubrik`, and `max_score` as a config payload. `result` and `score` are both `omitempty`, so an empty result is indistinguishable from config except by two absent keys. Do not try to tell them apart by looking for a top-level `entries` array; there isn't one, and concluding "this is just the config" is the natural failure of that design.

The reliable discriminator is the TYPE of `body`, not its contents:
- **`body` is a string** -> config (`/coaching-templates/?id=`). `PromptTemplate.Body` is a stringified JSON you must parse before you can see anything.
- **`body` is an object** -> results (`/transcript/coaching/`). `PromptCoachingTemplate.PromptBodyCoaching` is a real nested struct.

`properties` is a MAP (`Entries map[string]PromptBodyProperty`, tag `json:"properties"`), keyed by entry ID, not an array. The path is `body.properties.<entry_id>.result` and `.score`. Anything indexing by position breaks on it.

To test whether results are actually present, check for any non-empty `result` under `body.properties.*`, which is what the server's own `HasNoResults()` does.

Note the script does not do this for you: `parse_agent_summary` only runs against the config snapshot, and `eval` writes `*_agent_results.json` as a raw dump of the response with no parsing. You are reading the raw payload by hand, with no summary layer to cross-check against.

## Step 2: Audit, score every property per meeting

### 2a. Read every transcript in full. This is not optional and there is no shortcut.

**You must read 100% of every transcript in the sample, start to finish, before you score anything on it.** Not a sample of turns, not a keyword grep, not the first N lines. If a transcript is 650 utterances, read 650 utterances.

This step is where the loop actually earns its value, and it is the step most likely to be skipped, because it is long and boring and the tooling cannot tell whether you did it. The failure is not laziness in the moment; it is that a mechanical proxy produces a complete, valid-looking grid that `summarize` accepts. A grid that passes validation is not evidence the audit happened.

**Bulk verification is evidence of GROUNDING, never of CORRECTNESS.** Checking that a quote string appears in the transcript, that a stakeholder count matches the named lines, or that a format token is present on every row tells you the agent did not hallucinate. It tells you NOTHING about whether the extraction is right, whether the score matches the call, whether the persona is correct, or whether a real signal was missed. Those are the things you are auditing. Run bulk checks if useful, but they are a supplement to reading, never a substitute, and you may not score a cell off them.

**Specifically banned as a basis for scoring:**
- Regex or substring matching quotes back to the transcript
- Reading only the agent's output and judging whether it "looks reasonable"
- Reading only the portions of the transcript that the agent already quoted
- Marking a cell 2 because nothing flagged it (see the default-to-2 ban below)
- Any process that would produce the same grid whether or not you opened the transcript

**Never default to 2.** A cell is 2 only when you have read the call and affirmatively confirmed the output is right. "I found no problem" is not the same as "I checked and it is correct," and the difference is the entire audit. If you have not read the meeting, you do not have a score for it, and you must go read it.

**Cost check.** Reading N transcripts in full is genuinely expensive in context. If the sample will not fit, shrink the sample rather than skim it: an honest 3-meeting audit beats a fabricated 10-meeting one, and the skill's stop conditions read the distribution, not the sample size. Say in the audit how many meetings you read in full. If that number is lower than the number you scored, you have not done this step.

### 2b. Score every property per meeting

Read `agent_summary.md`, then each transcript/results pair. Score **each property, each meeting, 0/1/2**:
- **2 solid** accurate, grounded, and (if scored) the score matches the call.
- **1 weak** partially right, vague, off-by-one, or minor hallucination.
- **0 broken** hallucinated, contradicts the call, "not found" with clear signal, empty, or content bled from another property.

**The score IS the distribution, never a composite average.** Headline: "X of [properties x meetings] solid" plus the list of properties with any broken output, which is the to-do list. Averaging is banned: it lets a gain on one property hide a regression on another.

For scored properties, score on what the **buyer** confirmed, not what the rep pitched. There is no role flag on utterances (`Utterance` carries only `Speaker`/`SpeakerNumber`); infer it from the `speaker` string (no `@` = buyer, `@seller-domain` = rep, other `@domain` = buyer). This matches the server's own logic in `meeting/transcript_utils.go:157-168`. Caveat: the seller set is the org's own `CustomerOrgList`, so a buyer at a domain the org also owns reads as a rep.

**Unresolved speaker labels bias buyer-evidence scoring upward.** Transcripts are segmented on the Deepgram *acoustic* speaker index, then labeled best-effort; `resolveSpeakerByIndex` (`transcriber/.../deepgram.go:471-476`) falls back to the bare index as a string when no name resolves. Index and identity are explicitly not 1:1 in either direction (see the comment at `deepgram.go:497-501`): one person can appear under several indices, and the active-speaker annotation can map two acoustic speakers onto one name.

A numeric label contains no `@`, so the buyer/seller rule above silently reads **every** numerically-labeled utterance as buyer. That is a one-directional bias: on a meeting with unresolved diarization, any buyer-evidence property tends to score higher than the call earns.

**Do not drop meetings over this.** Numeric labels are the common case, not the exception, and a rule that drops them empties the sample. More importantly the bias is a CONSTANT across rounds: every round re-scores the same pinned transcripts, so the same inflation lands on the baseline and on every candidate. It corrupts the absolute level, but it largely cancels in the before/after comparison, and the comparison is what the loop actually consumes. Handle it by recording it, not by discarding data:

- **Record label quality once**, at the top of every `audit_round_N.md`: what share of utterances carry resolved names/emails versus bare indices. Same sentence every round, so a reader can see it was constant.
- **Score buyer-evidence properties from content**, never from the label: who is asking versus answering, who owns the budget or the problem, who describes their own org in the first person.
- **When content leaves a specific item genuinely ambiguous, score it 1, not 2**, and use category `wrong_speaker`. A 1 is the honest representation of "partially right, attribution uncertain" and it keeps the grid complete. Do not invent a 2, and do not invent a 0.
- **Raise the bar for declaring a win** on a buyer-evidence property when labels are unresolved. A one-cell shift is inside the noise. Require the gain to show up in content-grounded evidence you can quote from the transcript, not just in the count.

Drop a meeting from the declared `meetings` list ONLY when content cannot even establish which side is the customer, which is rare and usually means the call is a vendor pitch, an internal call, or misrouted CRM data. If you do drop one, it must be dropped from every round you compare against, including the baseline, because `compare` refuses candidates scored on different meeting samples. Say which and why in the audit.

A confidently wrong 2 still hides regressions, so prefer the honest 1. But a smaller sample has its own cost: fewer meetings makes every distribution noisier, and the loop's stop conditions read that distribution.

### 2c. Evidence requirement: every scored property, every meeting

For any property with `max_score > 0`, you must hand-score the underlying items YOURSELF from the transcript before judging the agent's score, then compare yours to the agent's. Record the comparison. A cell is 2 only if your independent read agrees with the agent.

**Every scored-property cell needs a transcript quote in `audit_round_N.md`, including cells you score 2.** Quote the buyer turn that justifies your score and name the item it belongs to. This is the anti-shortcut mechanism: you cannot quote a turn you never read, so a scorecard with no quotes on scored properties is a scorecard that was not audited. Unscored properties (`max_score` 0) still need quotes on any cell below 2.

Format, one line per item on at least the two weakest scored properties:
```
[meeting] item N | agent=4 | mine=2 | "yeah, that's a problem for us too" (buyer, ~00:14:20) -> assent only, no substance
```

**Do not revise a property off a distribution alone.** A skewed or flat histogram is a HYPOTHESIS, not a finding. It is equally consistent with a miscalibrated agent and with a sample where the answer genuinely is uniform. The only valid trigger for revising a scored property is a set of documented per-item disagreements between your read and the agent's. If you cannot produce those lines, you do not yet know the property is wrong, and revising it is guesswork that burns a round and corrupts the next comparison.

Write `audit_round_N.md` (headline, meetings-read-in-full count, label-quality line, per-property scorecard with quotes, weakest-first fix list with transcript evidence) and `scores_round_N.json` (see below). Then:
```bash
python3 scripts/agent_optimize.py summarize scores_round_N.json
```

### scores_round_N.json (required shape)
```json
{ "agent_id":"...", "round":0, "properties":["e1","e2"], "meetings":["m1","m2"],
  "scores":[ {"property":"e1","meeting":"m1","score":2},
             {"property":"e1","meeting":"m2","score":0,"category":"hallucination","evidence":"named 'Acme', not in transcript"} ] }
```
Every score below 2 needs a `category` from: hallucination, wrong_speaker, missed_signal, miscalibrated, generic, format, bleed. **The scores must be a COMPLETE grid**: exactly one row per (property, meeting) pair in `properties x meetings`. `summarize` enforces set-equality and hard-fails naming any missing, duplicate, or undeclared pair. This is not a formality: an incomplete audit that silently drops the meeting it would score 0 on can win a best-of-K comparison unfairly.

## Before Step 2: is this loop even the right shape for your change?

This loop measures a **change in quality on output the agent already produces**. Baseline (`cached`) -> audit -> revise -> re-eval -> compare works because there is a before to compare against.

It does **not** measure whether a *newly added* thing fires. If your change is an addition (a new taxonomy value, a new property, a new category) then every cached result on the agent was produced by a config that has no such value in it. The baseline is measuring absence. It is structurally incapable of telling you anything about your addition, and no amount of scoring rounds changes that.

**Recognize this before you spend a round.** Ask: after my edit, is there a cell in the grid whose baseline value could have been anything other than "absent"? If no, you are measuring a fire rate, not a quality delta.

For an addition, do this instead:

1. **Pin a sample deliberately, do not sample randomly.** A new value's fire rate on 10 random calls is usually 0, which tells you nothing. Pick meetings where the signal should be present and meetings where it should not, and write both into a `--meeting-list` file. `list-meetings --out-file` gives you the pinned file for free.
2. **Baseline with `--mode fresh`, not `cached`.** On an addition the cached read is worthless; you need the pre-change config's fresh behavior on the pinned meetings as your true baseline. This costs tokens. Say so before spending them.
3. **Score fire rate and precision, not the 0/1/2 quality grid.** Did it fire where it should? Did it fire where it should not? A false positive on a new value is the expensive failure, because it pollutes every downstream rollup.
4. **Then, and only then, run the quality loop** on the value's *content* once you know it fires.

### Clone before edit when the live agent is load-bearing

This skill edits in place, and there is **no server-side rollback**. Before pushing to any agent, check the snapshot for these, all of which raise the cost of being wrong:

- `visibility: 2` (org-wide) rather than 0 (personal draft)
- teams attached, so reps see it live
- `field_mapping` set, or the agent feeding qualification/deal rollups or a CRM dashboard
- an aggregate/qualification template (`promptSettings.AggregateTemplateIds`)

**If any of those hold, and the change is an addition rather than a fix, clone to a `visibility: 0` draft and run the loop on the clone.** Same token cost, and the live agent never moves. The upstream note that clone-before-edit "belongs to a different skill" is about which skill owns the *workflow*, not a prohibition: you can POST a copy of the snapshot to `/coaching-templates/` with `visibility: 0`, a distinct name, and `teams` omitted, then point this skill's `eval` / `update-agent` / `compare` machinery at the clone's ID. Nothing in the loop cares that the ID is a draft.

Promote by copying the converged property set back onto the live agent as one reviewed edit, with a `--dry-run` first.

**Ask the user which they want** when the live agent is load-bearing. Do not decide in-place-vs-clone on your own for a `visibility: 2` agent that feeds someone's dashboards. Note that a `visibility: 0` draft is readable **only** by `meta.created_by`, so create the clone with the same token you will run the loop with.

## Step 3: Revise

**Gate before you touch anything.** Answer these in `audit_round_N.md`. If any answer is no, go back to Step 2; do not revise.
- Did I read every transcript in the sample start to finish this round?
- Does the audit contain a transcript quote for every scored-property cell?
- For each property I am about to change, can I point at specific items where my hand-score disagrees with the agent's, with the quote attached?
- Am I changing this because of documented disagreements, or because a summary statistic looked wrong to me?

Change 2 to 4 weakest properties per round, each citing specific transcript evidence. Do not touch already-solid properties. Use semantic judgment, never keyword triggers. Do not change entry IDs, titles, `max_score`, `sort_order`, or `field_mapping` without confirmation. Write the revised config to `revised_agent_round_N.json`. The `prompt_template.body` stays a stringified JSON. `scoring_rubrik` is misspelled on purpose, do not fix it.

**Where instructions actually bind.** A property with `MaxScore > 0` emits TWO OpenAI properties (`openai/templates.go:33-54`):
- `key` -> description = the property Description ONLY
- `key_score` -> description = Description + `"Create a score based on this rubrik: {ScoringRubrik}. The max score is {N}"`

So the rubrik does reach the model, but only on the numeric `_score` field. It has ZERO influence on the extracted text. **Any output-format instruction placed in `scoring_rubrik` will not land on the text output.** Put every format rule and every critical distinction in the Description; use `scoring_rubrik` only for the numeric scale anchors.

Setting `max_score` from 0 to N is what CREATES the `_score` field: at 0, no score property is emitted at all. `ApplyCoachingResults` maps the `_score` suffix back on read, so expect TWO new fields per property you score, not one.

**Free pre-flight before spending a gate run:** grep the revised config to confirm your new format tokens are in `description` and not in `scoring_rubrik`. Thirty seconds beats three LLM calls.

## Step 4: Update in place (dry-run first, always)

```bash
python3 scripts/agent_optimize.py --stage <stage> update-agent --agent <ID> --from revised_agent_round_N.json --dry-run
python3 scripts/agent_optimize.py --stage <stage> update-agent --agent <ID> --from revised_agent_round_N.json
```
The dry-run shows exactly what changes (ignoring server-forced fields) and warns if the update would wipe a set field. PUT is a full replace with no merge: omitting `teams` unshares the agent. The push refuses by default if it would wipe a set field; `--force` overrides (you should not need it if the config was built from the snapshot). **There is no server-side rollback. `agent_config.json` from the baseline is the only undo, never overwrite it.**

## Step 5: Re-eval (fresh)

```bash
python3 scripts/agent_optimize.py --stage <stage> eval --agent <ID> --meeting-list <round0_dir>/meeting_ids.txt --mode fresh
```
Same meetings, to isolate the change. Use `fresh`: a config edit does NOT invalidate cached results (cache is keyed by `{meeting_id}/coaching/{template_id}`, with no config hash or version), so a `cached` read returns the OLD output and shows no change.

**Gate the spend on a format check first.** If the revision changed an output format, run 3 of the pinned meetings (one per outcome, including at least one where the signal is likely thin) into a separate `round0_gate/` dir, confirm the new fields actually land, then run the remaining 7. Total spend is unchanged, but a broken format costs 3 runs instead of 10. `compare` hard-refuses candidates scored on different meeting samples, so the round must still land on all pinned meetings: merge both dirs into ONE `scores.json` at scoring time and keep the gate dir intact.

## Step 6: Audit round N and compare

Re-score every property per meeting (do not carry old scores). Put a comparison at the top of `audit_round_N.md`: per-property solid/weak/broken before -> after, and an explicit **regressions** callout for anything that went from solid to broken. The distribution makes a regression impossible to hide behind an aggregate gain.

## Step 7: Stop conditions (two rules, do not blur them)

- **Eliminate broken / verify jumps:** do not stop while any property still has broken outputs and a fix is available. Do not stop after a single improving round, even a large one, run one more to verify. Early rounds are the noisiest (illegal/invalid proposals start high and fall as feedback accumulates), so do not over-trust round 1.
- **Do not over-polish weak:** do not chase every weak-to-solid on subjective properties. Once the only issues are weak-but-usable outputs on judgment calls, stop, that is overfitting to these 10 meetings.

Stop when: zero broken and nothing majority-weak; OR no property leaves "broken" for two consecutive rounds; OR 5 rounds. Then write `final_summary.md` (score progression, changes that landed, changes that did not, remaining issues, recommendations).

## Critical invariants (do not break these)

0. **Read every transcript in full, every round.** No sampling, no grepping, no scoring from the agent's output alone, no defaulting a cell to 2 because nothing flagged it. Bulk verification proves grounding, never correctness. If the sample is too large to read, shrink the sample; do not skim it. A grid that passes `summarize` is not evidence the audit happened, and every downstream revision inherits the audit's honesty.
1. **Never short-circuit the feedback loop.** The re-eval-and-compare step is load-bearing, not decoration: measured feedback is what makes the loop work. A revision you did not re-eval and compare is not validated.
2. **Audit before you revise, and revise only off documented per-item disagreements.** A distribution is a hypothesis, not a finding. Never tune a scored property because its histogram looked wrong; tune it because you read the call, scored the items yourself, and can quote where the agent disagreed with you. Tuning against your own unverified output compounds the error into the next round's comparison.
3. **Never produce agent output directly.** Every change routes through the real Aircover API and its legality/validation. Do not have the model hand-write or hand-edit agent *results*; direct generation without formal validation has a measurable hidden-error rate.
4. **Mode discipline.** cached baseline, `fresh` iteration, persist only deliberately. A config edit does not invalidate the cache, so never re-eval in cached mode after a change, and never re-eval with `preview` alone on a pre-patch copy of this script.
5. **Compute totals yourself.** There is no total-score field on the wire; sum per-property scores. Never trust a total the LLM wrote into a summary field.
6. **The local snapshot is the only rollback.** No server versioning.
7. **Verify sampler scope before you trust an empty corpus.** An unfiltered `/meeting_list/` call is owner-scoped, so a near-empty result from a service identity is the expected behavior of the wrong scope, not evidence the org has no calls and not an access problem. Run `list-meetings` (free) and read the printed role and per-rep counts before concluding anything about the token.
8. **A baseline can only measure something that already exists.** For an addition (new value, new property), `cached` baselines are measuring absence. Pin a deliberate sample, baseline `fresh`, and score fire rate and precision instead of the quality grid.
9. **Pre-flight on prod, never on staging.** Staging has different agents and different meetings, so a green staging round-trip proves nothing about the prod agent you are about to mutate. Every pre-flight step is read-only or `--dry-run`.

## Best-of-K (HELD, opt-in only)

`compare` (offline) ranks multiple `scores.json` candidates by the distribution philosophy (fewest broken, then fewest weak, then most solid) and flags per-property tradeoffs so an overall winner that regressed a critical property is surfaced. Best-of-K means running the whole loop K times from the ORIGINAL config on the SAME pinned meeting sample, then `compare`-ing the candidates and keeping the best. It hedges the local-optima risk but costs K whole loops of tokens, so it is opt-in only, and only after this skill has run on two or three real agents and the score distributions look sane. Default ceiling K=3, max 5. Do not run best-of-K unless the user explicitly asks.

## Auth and stages

`export AIRCOVER_TOKEN="..."` (or `AIRCOVER_USERNAME` + `AIRCOVER_PASSWORD`). `--stage prod|staging|develop` picks the host and is a TOP-LEVEL flag: it goes before the subcommand (`agent_optimize.py --stage prod eval ...`), not after. **It defaults to `prod`.** For a tool whose job is mutating live agents in place, omitting the flag puts you on production. App API, not AWS.

**Permissions.** Every user-facing read filters the org template list by caller identity. A `visibility: 0` template ("Draft" in the UI, `VisibilityPersonal`) is readable ONLY by `meta.created_by`, with no admin escape hatch: org Owner, Admin, and Editor all fail. A non-creator token gets HTTP 500 "Template not found in template list", and no list filter or query param will surface it, because the list handler reads only `id` and `include_field_mapping`. Either run as the creator, or set visibility to 1/2. If you already hold a snapshot of the agent, `prompt_template_list_item.meta.created_by` names the owner.

## First run on any account: pre-flight (runs entirely on prod, no staging needed)

Every step here is read-only or explicitly non-mutating, so it runs against the account you actually care about. **Do not route the pre-flight through staging.** Staging holds different agents and different meetings, so a green staging round-trip tells you nothing about the prod agent you are about to edit, and typical network allowlists only reach `api.aircover.ai` anyway. `--stage` defaults to `prod`; leave it there.

1. `python3 scripts/test_agent_optimize.py` -> expect all tests passing.
2. `--stage prod list-meetings --days 90 --count 15`. Free. Confirms the sampler sees the corpus, and prints the caller identity, its org role, and the per-rep counts. If this comes back near-empty, fix scope or role before spending anything (see Step 1).
3. `--stage prod get-agent --agent <ID>` -> saves the snapshot, which is your only rollback. Check `meta.created_by` and `visibility` here.
4. `--stage prod update-agent --agent <ID> --from <that same snapshot> --dry-run` -> expect "No meaningful changes." This is the round-trip safety check, on the real agent, and `--dry-run` sends no PUT.
5. `--stage prod eval --agent <ID> --count 1 --mode cached` -> open `*_transcript.json`, confirm speakers are emails vs bare names (sets the buyer-vs-rep scoring ceiling), confirm `*_agent_results.json` parses.
6. Then let the loop run.
