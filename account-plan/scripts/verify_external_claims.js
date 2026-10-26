#!/usr/bin/env node
/**
 * verify_external_claims.js
 *
 * Refuses to let an externally-sourced claim into an account plan unless a ledger
 * row proves where it came from. This is the check that catches the failure the
 * rest of the pass cannot see: a claim that carries a correct-looking citation and
 * a real source, but whose NUMBER came from a snippet, a headline, or a neighbouring
 * period rather than from the sentence cited.
 *
 * It cannot verify that a quote is true. It CAN verify that you held the quote in
 * your hand when you wrote the claim, which is what stops reconstruction from memory.
 *
 * Usage:
 *   node verify_external_claims.js --values plan.json [--warn-only]
 *
 * Exits non-zero on any failure unless --warn-only.
 */
"use strict";
const fs = require("fs");

const args = process.argv.slice(2);
const get = (f) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : null; };
const valuesPath = get("--values");
if (!valuesPath) { console.error("--values is required"); process.exit(2); }
const v = JSON.parse(fs.readFileSync(valuesPath, "utf8"));
const S = v.sections || {};

const fail = [];
const warn = [];

// ---------------------------------------------------------------- the ledger
const ledger = v.external_ledger || [];
const byId = new Map();
ledger.forEach((row, i) => {
  const id = row.id || `(row ${i})`;
  if (byId.has(id)) fail.push(`Ledger: duplicate id "${id}".`);
  byId.set(id, row);

  // A row is only evidence if it carries the sentence it came from.
  if (!row.quote || String(row.quote).trim().length < 12) {
    fail.push(`Ledger "${id}": no verbatim quote. If you cannot paste the sentence, you do not have the fact.`);
  }
  if (!row.url || !/^https?:\/\//.test(row.url || "")) {
    fail.push(`Ledger "${id}": no absolute source URL.`);
  }
  if (!row.retrieved) fail.push(`Ledger "${id}": no retrieval date.`);

  // Snippets and headlines are leads, not sources. This is the rule that would have
  // caught "EBIT surges 30%" being attributed to the wrong period.
  const how = String(row.obtained_by || "").toLowerCase();
  if (how !== "fetch") {
    fail.push(`Ledger "${id}": obtained_by is "${row.obtained_by || "unset"}". `
      + "A search snippet or headline is a lead. Fetch the page and quote the sentence.");
  }

  // Every figure belongs to a period and an entity. Mis-binding these is the most
  // common way a real number becomes a false claim.
  if (/\d/.test(String(row.claim || "")) ) {
    if (!row.period) fail.push(`Ledger "${id}": numeric claim with no period (FY2025, Q2 2026, H1 2026...).`);
    if (!row.entity) fail.push(`Ledger "${id}": numeric claim with no entity (group, division, region).`);
  }

  // Arithmetic you performed is not something the source said.
  if (row.derived && !row.derived_from) {
    fail.push(`Ledger "${id}": marked derived but does not name the inputs it was computed from.`);
  }

  // Conflicts get recorded, never silently resolved.
  if (row.conflicts_with && !row.conflict_note) {
    fail.push(`Ledger "${id}": names a conflicting source but no note saying how it was resolved.`);
  }
});

// ---------------------------------------------------------------- claims needing backing
// Any block whose source line carries a retrieval date is asserting external fact.
const EXTERNAL_HINT = /retrieved\s+\d{4}-\d{2}-\d{2}|annual report|earnings call|press release|filing|investor/i;

function checkItems(items, label) {
  (items || []).forEach((it, i) => {
    const text = typeof it === "string" ? it : (it.text || "");
    const src = (typeof it === "object" && (it.source || "")) || text;
    if (!EXTERNAL_HINT.test(src)) return;
    const ids = (typeof it === "object" && it.ledger) || [];
    if (!ids.length) {
      fail.push(`${label}[${i}]: external claim with no ledger reference. "${String(text).slice(0, 70)}..."`);
      return;
    }
    ids.forEach((id) => {
      if (!byId.has(id)) fail.push(`${label}[${i}]: ledger id "${id}" does not exist.`);
    });
  });
}

const L = S.landscape || {};
["strengths", "weaknesses", "opportunities", "threats"].forEach((q) =>
  checkItems((L.swot || {})[q], `swot.${q}`));
checkItems(L.industry_trends, "industry_trends");
checkItems(L.business_priorities, "business_priorities");
checkItems(L.kpis, "kpis");
checkItems(L.challenges, "challenges");

// ---------------------------------------------------------------- call quotes
// Same discipline, different corpus. A quoted fragment must be copied from an agent
// result, not composed from what the agent reported. Naming the agent is the forcing
// function: you cannot name the output you copied from if you did not copy from one.
function checkQuotes(items, label) {
  (items || []).forEach((it, i) => {
    if (!it || typeof it !== "object" || isBlankStr(it.evidence)) return;
    if (isBlankStr(it.evidence_agent)) {
      fail.push(`${label}[${i}]: quoted evidence with no evidence_agent naming the agent output it was `
        + `copied from. "${String(it.evidence).slice(0, 50)}..."`);
    }
    if (!/\d{4}-\d{2}-\d{2}/.test(String(it.source || ""))) {
      fail.push(`${label}[${i}]: quoted evidence whose source carries no meeting date.`);
    }
  });
}
function isBlankStr(x) { return x === undefined || x === null || String(x).trim() === ""; }
checkQuotes(L.challenges, "challenges");
checkQuotes(L.business_priorities, "business_priorities");
checkQuotes(L.kpis, "kpis");
checkQuotes((S.competitive || {}).competitors, "competitors");

// ---------------------------------------------------------------- competitor evidence
// A competitor is present only where a call, a document or a cited source says so.
// A competitor row with an empty evidence column asserts presence with nothing behind it.
((S.competitive || {}).competitors || []).forEach((c, i) => {
  const backing = [c.source, c.evidence, c.presence].map((x) => String(x || "")).join(" ");
  if (!/\d{4}-\d{2}-\d{2}/.test(backing)) {
    fail.push(`competitors[${i}] "${c.name || ""}": no dated evidence anywhere on the row. `
      + "Presence is claimed with nothing behind it.");
  }
  if (!isBlankStr(c.share_of_wallet) && !/\d{4}-\d{2}-\d{2}|internal|account team/i.test(String(c.share_of_wallet))) {
    fail.push(`competitors[${i}]: share of wallet stated with no source. It is never estimated from call frequency.`);
  }
});

// ---------------------------------------------------------------- attendance arithmetic
// The roster on the deal record and the set of people who actually attended are different
// numbers, and conflating them is the error the source map calls out by name. When the plan
// states these counts, they have to reconcile to each other.
const att = (S.coverage || {}).attendance;
if (att) {
  const need = ["distinct_attendees", "roster_count", "attended_not_on_roster",
                "appeared_once", "appeared_more_than_once"];
  need.forEach((k) => {
    if (typeof att[k] !== "number") fail.push(`coverage.attendance.${k} missing or not a number.`);
  });
  if (need.every((k) => typeof att[k] === "number")) {
    if (att.appeared_once + att.appeared_more_than_once !== att.distinct_attendees) {
      fail.push(`Attendance does not reconcile: ${att.appeared_once} once + `
        + `${att.appeared_more_than_once} more than once != ${att.distinct_attendees} distinct.`);
    }
    if (att.attended_not_on_roster > 0 && /roster and attendance (set )?match/i.test(JSON.stringify(S))) {
      fail.push(`The plan claims roster and attendance match while `
        + `attended_not_on_roster is ${att.attended_not_on_roster}.`);
    }
    if (typeof att.appeared_once_at_largest_meeting === "number"
        && att.appeared_once_at_largest_meeting > att.appeared_once) {
      fail.push("More single-appearance people attributed to one meeting than appeared once in total.");
    }
  }
} else {
  warn.push("coverage.attendance is absent, so the attendee counts in the prose cannot be reconciled.");
}

// ---------------------------------------------------------------- cadence gaps
// A gap in the ANALYZED evidence is not a gap in the relationship. Any gap claim is checked
// against the meetings actually held, not the ones that produced a transcript.
const held = ((S.coverage || {}).meetings_held_dates || []).slice().sort();
const GAP = /(\d+|one|two|three|four|five|six|seven|eight|nine|ten)[\s-]week gap between (\d{4}-\d{2}-\d{2}) and (\d{4}-\d{2}-\d{2})/gi;
const WORDS = { one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10 };
const blob = JSON.stringify(v);
let m;
while ((m = GAP.exec(blob)) !== null) {
  const [, nRaw, a, b] = m;
  const n = WORDS[String(nRaw).toLowerCase()] || parseInt(nRaw, 10);
  const between = held.filter((d) => d > a && d < b);
  if (between.length) {
    fail.push(`Claimed a ${nRaw}-week gap between ${a} and ${b}, but ${between.length} meeting(s) `
      + `were held in between (${between.join(", ")}). That is a gap in the evidence, not in the relationship.`);
  }
  const weeks = Math.round((Date.parse(b) - Date.parse(a)) / (7 * 864e5));
  if (held.length && weeks !== n) {
    fail.push(`Claimed a ${nRaw}-week gap between ${a} and ${b}; the actual span is ${weeks} weeks.`);
  }
}

// ---------------------------------------------------------------- appendix agreement
const ext = (S.coverage || {}).external_sources || [];
const ledgerUrls = new Set(ledger.map((r) => (r.url || "").replace(/\/$/, "")));
if (ledger.length && !ext.length) {
  fail.push("Ledger has rows but the appendix lists no external sources. The reader cannot see what the plan rests on.");
}
ext.forEach((e) => {
  if (!e.retrieved) warn.push(`Appendix source "${(e.title || "").slice(0, 50)}" has no retrieval date.`);
});
// Every ledger domain should appear in the appendix, even though the ledger itself stays internal.
const appendixPublishers = ext.map((e) => (e.publisher || "").toLowerCase()).join(" | ");
[...new Set(ledger.map((r) => r.publisher).filter(Boolean))].forEach((pub) => {
  if (!appendixPublishers.includes(String(pub).toLowerCase())) {
    warn.push(`Ledger cites "${pub}" but the appendix external sources table does not list it.`);
  }
});

// ---------------------------------------------------------------- report
const claimsBacked = ledger.length;
console.log(`External claim check: ${claimsBacked} ledger row(s).`);
if (warn.length) {
  console.log(`\n${warn.length} warning(s):`);
  warn.forEach((w) => console.log("  - " + w));
}
if (fail.length) {
  console.log(`\n${fail.length} FAILURE(s):`);
  fail.forEach((f) => console.log("  - " + f));
  console.log("\nAn unbacked external claim does not go in the plan. Fetch and quote it, or cut it.");
  if (!args.includes("--warn-only")) process.exit(1);
} else {
  console.log("Every external claim traces to a fetched, quoted source.");
}
