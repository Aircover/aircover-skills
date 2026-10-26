#!/usr/bin/env node
/**
 * check_aircover_fit.js
 *
 * Answers one question before you compose an Aircover save: will this plan fit?
 *
 * Aircover caps one declared section at 31,900 characters and REFUSES an oversized
 * save by name rather than truncating it. The stock account_plan template declares a
 * single section holding nine `## ` headings, so the whole plan plus the leftover extras
 * land in that one budget.
 *
 * This is an UPPER BOUND. It measures the values file, while the Aircover document is
 * condensed to the template's own per-heading caps; in 2026-10 tests the real document came
 * to 45-60% of this estimate. "Over cap" here means check before saving, not that the
 * save will fail.
 *
 * Run this BEFORE writing the save call, so trimming is a decision rather than a retry.
 *
 * Usage:
 *   node check_aircover_fit.js --values plan.json [--cap 31900]
 */
"use strict";
const fs = require("fs");

const args = process.argv.slice(2);
const get = (f) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : null; };
const valuesPath = get("--values");
if (!valuesPath) { console.error("--values is required"); process.exit(2); }
const CAP = parseInt(get("--cap") || "31900", 10);

const v = JSON.parse(fs.readFileSync(valuesPath, "utf8"));
const S = v.sections || {};

// CALIBRATION. OVERHEAD comes from the original single-section save (values file 32,994
// characters, rendered 30,123). Under the nine-heading template with its own caps, the real
// document is far smaller, so treat the total as a ceiling.
const OVERHEAD = 0.913;

const len = (x) => {
  if (x === undefined || x === null) return 0;
  if (typeof x === "string") return x.length;
  if (Array.isArray(x)) return x.reduce((n, i) => n + len(i), 0);
  if (typeof x === "object") {
    // ledger and provenance fields never render into the Aircover document
    const skip = new Set(["ledger", "evidence_agent", "source_class"]);
    return Object.entries(x).reduce((n, [k, val]) => n + (skip.has(k) ? 0 : len(val)), 0);
  }
  return String(x).length;
};

const L = S.landscape || {};
const OF = S.opportunities_footprint || {};
const CP = S.competitive || {};
// The stock global account_plan template's nine declared headings, in template order.
const SW = L.swot || {};
const COV = S.coverage || {};
// The stock global account_plan template's nine declared headings, in template order,
// grouped the way SKILL.md step 9b maps the plan onto them.
const groups = [
  ["Executive Summary and Account Snapshot", [S.exec_summary], true],
  ["Account Objectives", [OF.expansion, (S.exec_summary || {}).strategic_narrative], true],
  ["Customer Landscape and Market Insights", [L.business_priorities, L.kpis, L.challenges, L.trends, L.industry_trends, SW, COV.notes], true],
  ["Relationship and Stakeholder Mapping", [S.stakeholders], true],
  ["Opportunities, Footprint and Whitespace", [OF.opportunities, OF.org_footprint, OF.use_cases], true],
  ["Qualification Gaps", [(S.stakeholders || {}).role_gaps, S.qualification_gaps], true],
  ["Cross-Functional GTM Strategy", [S.gtm], true],
  ["Strategic Next Steps and Mutual Action Plan", [S.next_steps_map], true],
  ["Competitive Landscape", [CP], true],
  ["EXTRA: evidence coverage table", [COV.opportunities], false],
  ["EXTRA: plan settings", [v.meta], false],
];

let total = 0;
const rows = groups.map(([name, parts, declared]) => {
  const n = Math.round(parts.reduce((a, p) => a + len(p), 0) * OVERHEAD);
  total += n;
  return { name, n, declared };
});

const opps = ((S.opportunities_footprint || {}).opportunities || []).length || 1;

console.log(`Aircover section fit: ${total} / ${CAP} characters (${Math.round((total / CAP) * 100)}%)`);
console.log(`Opportunities in scope: ${opps}\n`);
rows.forEach((r) => {
  const bar = "#".repeat(Math.max(1, Math.round((r.n / total) * 50)));
  console.log(`  ${String(r.n).padStart(6)}  ${bar.padEnd(50)} ${r.name}`);
});

const headroom = CAP - total;
console.log(`\nHeadroom: ${headroom} characters.`);

if (headroom < 0) {
  console.log("\nOVER CAP. The save will be REFUSED, not truncated. Trim in this order and re-check:");
  console.log("  1. Appendix reading notes  -> keep the coverage table and plan settings only.");
  console.log("  2. GTM tracks              -> keep objective, why_now and exit_criterion; cut plays to two.");
  console.log("  3. Stakeholder table       -> collapse single-appearance attendees into one counted row.");
  console.log("  4. Per-opportunity prose   -> one paragraph each, totals stay in the table.");
  console.log("Never trim an evidenced customer finding, a quote, or an INPUT NEEDED question to fit.");
  process.exit(1);
} else if (headroom < CAP * 0.15) {
  console.log("TIGHT. Under 15% headroom. The save will land, but the next update that adds a\n  meeting and a few findings probably will not. Trim now rather than at save time.");
  console.log("Trim the appendix reading notes now rather than at save time.");
} else {
  console.log("Fits with room for updates.");
}
