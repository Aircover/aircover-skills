#!/usr/bin/env node
/**
 * build_account_plan_pptx.js
 *
 * Renders the SAME values file the docx engine reads into a slide deck.
 * One source of truth, two output shapes.
 *
 * Deliberately unbranded. An account plan is the seller's internal artifact, so it
 * carries their branding or none. Never Aircover's.
 *
 * Usage:
 *   node build_account_plan_pptx.js --values plan.json [--config config.json] [--out deck.pptx] [--strict]
 */
"use strict";
const fs = require("fs");
const pptxgen = require("pptxgenjs");

// ---------------------------------------------------------------- content budget
// A slide is not a page. These caps are what stop an account plan turning into
// the thing it usually turns into: a document reflowed onto slides.
const BUDGET = { wordsPerSlide: 150, bullets: 6, wordsPerBullet: 34 };

const C = {
  ink: "1A2230", body: "3D4759", muted: "7A8698",
  accent: "1F5C86", rule: "D8DEE7", panel: "F4F6F9", white: "FFFFFF",
  flag: "9A5B1E", flagBg: "FBF2E6",
};
const W = 13.333, H = 7.5, M = 0.62;

const warnings = [];
const warn = (m) => warnings.push(m);

const isBlank = (v) => v === undefined || v === null || String(v).trim() === "";
const textOf = (b) => (b && typeof b === "object" ? (b.text || "") : (b || ""));
const wc = (s) => String(s || "").trim().split(/\s+/).filter(Boolean).length;
const money = (n) => (typeof n === "number" ? "$" + n.toLocaleString("en-US") : (n || ""));

/** Split a list of items into slide-sized groups without exceeding the word budget. */
function paginate(items, textFn, budget = BUDGET.wordsPerSlide, maxItems = BUDGET.bullets) {
  const pages = []; let cur = [], curW = 0;
  items.forEach((it) => {
    const n = wc(textFn(it));
    if (cur.length && (curW + n > budget || cur.length >= maxItems)) { pages.push(cur); cur = []; curW = 0; }
    cur.push(it); curW += n;
  });
  if (cur.length) pages.push(cur);
  return pages;
}

/** Turn a block into slide bullets. Prefers an explicit points array; falls back to sentences. */
function bulletsFor(block, label) {
  const pts = (block && Array.isArray(block.points) ? block.points : [])
    .map((p) => (typeof p === "string" ? p : p.text)).filter((p) => !isBlank(p));
  if (pts.length) return pts;
  const t = textOf(block);
  if (isBlank(t)) return [];
  const sentences = String(t).split(/(?<=[.?!])\s+(?=[A-Z(])/).filter(Boolean);
  if (wc(t) > BUDGET.wordsPerSlide) {
    warn(`"${label}" is ${wc(t)} words of prose on a slide (budget ${BUDGET.wordsPerSlide}). `
       + "Give this block a `points` array composed for slides, rather than reflowing document prose.");
  }
  return sentences;
}

// ---------------------------------------------------------------- slide furniture
function makeDeck() {
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE";           // must precede any addSlide
  p.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };
  return p;
}

function slide(deck, state) {
  const s = deck.addSlide();
  s.background = { color: C.white };
  state.n += 1;
  const num = state.n;
  if (num > 1) {
    s.addText(String(num), { x: W - M - 0.5, y: H - 0.46, w: 0.5, h: 0.26, align: "right",
      fontSize: 9, color: C.muted, margin: 0 });
  }
  return s;
}

function heading(s, title, kicker) {
  let y = M - 0.06;
  if (kicker) {
    s.addText(String(kicker).toUpperCase(), { x: M, y, w: W - 2 * M, h: 0.24,
      fontSize: 10, bold: true, color: C.accent, charSpacing: 1.4, margin: 0 });
    y += 0.3;
  }
  s.addText(title, { x: M, y, w: W - 2 * M, h: 0.52, fontSize: 26, bold: true, color: C.ink, margin: 0 });
  return y + 0.78;
}

function bulletList(s, items, x, y, w, opts = {}) {
  const rows = items.filter((t) => !isBlank(t)).map((t, i, arr) => {
    // Appendix notes are reference prose for the reader, not slide copy. Exempt.
    if (wc(t) > BUDGET.wordsPerBullet && !opts.reference) {
      warn(`A bullet runs ${wc(t)} words (budget ${BUDGET.wordsPerBullet}): "${String(t).slice(0, 60)}…"`);
    }
    return { text: String(t), options: { bullet: true, breakLine: i !== arr.length - 1 } };
  });
  if (!rows.length) return y;
  s.addText(rows, { x, y, w, h: opts.h || (H - y - 0.85), valign: "top", margin: 0,
    fontSize: opts.fontSize || 13, color: opts.color || C.body, lineSpacingMultiple: 1.12,
    paraSpaceAfter: 7 });
  return y;
}

function sourceNote(s, text) {
  if (isBlank(text)) return;
  s.addText(String(text), { x: M, y: H - 0.72, w: W - 2 * M - 0.6, h: 0.3,
    fontSize: 9, italic: false, color: C.muted, margin: 0, valign: "bottom" });
}

function inputNeeded(s, items, y) {
  const list = (Array.isArray(items) ? items : [items]).filter((i) => !isBlank(i));
  if (!list.length) return y;
  const h = 0.34 + list.length * 0.3;
  s.addShape("roundRect", { x: M, y, w: W - 2 * M, h, fill: { color: C.flagBg },
    line: { color: C.flagBg }, rectRadius: 0.05 });
  s.addText("INPUT NEEDED", { x: M + 0.18, y: y + 0.08, w: 3, h: 0.22,
    fontSize: 9, bold: true, color: C.flag, charSpacing: 1.1, margin: 0 });
  s.addText(list.map((t, i, a) => ({ text: String(t),
    options: { bullet: list.length > 1, breakLine: i !== a.length - 1 } })), {
    x: M + 0.18, y: y + 0.32, w: W - 2 * M - 0.36, h: h - 0.4,
    fontSize: 11, color: C.flag, margin: 0, valign: "top" });
  return y + h + 0.16;
}

function dataTable(s, head, rows, colW, y, opts = {}) {
  const body = [[...head.map((h) => ({ text: h,
    options: { bold: true, color: C.ink, fill: { color: C.panel }, fontSize: opts.headSize || 11 } }))]];
  rows.forEach((r) => body.push(r.map((cell) => ({ text: String(cell ?? ""),
    options: { color: C.body, fontSize: opts.fontSize || 10.5 } }))));
  s.addTable(body, { x: M, y, w: W - 2 * M, colW, border: { type: "solid", color: C.rule, pt: 0.5 },
    align: "left", valign: "top", margin: [5, 7, 5, 7], autoPage: false });
}

// ---------------------------------------------------------------- sections
function titleSlide(deck, state, meta, S) {
  const s = slide(deck, state);
  s.addText("ACCOUNT PLAN", { x: M, y: 2.5, w: W - 2 * M, h: 0.3,
    fontSize: 12, bold: true, color: C.accent, charSpacing: 2, margin: 0 });
  s.addText(meta.account || "Account", { x: M, y: 2.88, w: W - 2 * M, h: 1.1,
    fontSize: 46, bold: true, color: C.ink, margin: 0 });
  const bits = [meta.date, meta.author ? `Prepared by ${meta.author}` : "",
    (meta.domains || []).join(", ")].filter((b) => !isBlank(b));
  s.addText(bits.join("   |   "), { x: M, y: 4.02, w: W - 2 * M, h: 0.34,
    fontSize: 13, color: C.muted, margin: 0 });
  const ev = meta.evidence_window || {};
  if (ev.start && ev.end) {
    s.addText(`Evidence window ${ev.start} to ${ev.end}`, { x: M, y: 4.4, w: W - 2 * M, h: 0.3,
      fontSize: 11, color: C.muted, margin: 0 });
  }
}

function teamSlide(deck, state, St) {
  const team = St.account_team || [];
  if (!team.length) return;
  const s = slide(deck, state);
  let y = heading(s, "Account team", "Who covers this account");
  dataTable(s, ["Name", "Role", "Responsibility", "Mtgs"],
    team.map((m) => [m.name || "", m.role || "unconfirmed", m.responsibility || "", String(m.meetings ?? "")]),
    [2.5, 2.1, 6.5, 0.99], y);
  y += 0.75 + team.length * 0.42;
  if (!isBlank(St.account_team_note)) {
    s.addText(St.account_team_note, { x: M, y, w: W - 2 * M, h: 0.5,
      fontSize: 10.5, color: C.muted, margin: 0 });
    y += 0.6;
  }
  inputNeeded(s, St.account_team_needs_input, y);
}

function snapshotSlide(deck, state, es) {
  const s = slide(deck, state);
  let y = heading(s, "Executive summary", "Section 1");
  const mets = (es.snapshot_metrics || []).slice(0, 6);
  if (mets.length) {
    const gap = 0.16, cw = (W - 2 * M - gap * (mets.length - 1)) / mets.length;
    mets.forEach((m, i) => {
      const x = M + i * (cw + gap);
      s.addShape("roundRect", { x, y, w: cw, h: 1.16, fill: { color: C.panel },
        line: { color: C.panel }, rectRadius: 0.06 });
      s.addText(String(m.label || "").toUpperCase(), { x: x + 0.14, y: y + 0.13, w: cw - 0.28, h: 0.44,
        fontSize: 8.5, bold: true, color: C.muted, charSpacing: 0.7, margin: 0, valign: "top" });
      s.addText(String(m.value || ""), { x: x + 0.14, y: y + 0.6, w: cw - 0.28, h: 0.44,
        fontSize: 17, bold: true, color: C.accent, margin: 0, valign: "top" });
    });
    y += 1.42;
  }
  const nar = es.strategic_narrative || {};
  s.addText("Why this account matters", { x: M, y, w: W - 2 * M, h: 0.3,
    fontSize: 14, bold: true, color: C.ink, margin: 0 });
  y += 0.38;
  const dims = (nar.dimensions || []).filter((d) => !isBlank(d));
  if (dims.length) {
    const rows = dims.map((d, i, a) => {
      const label = typeof d === "string" ? "" : (d.label || "");
      const text = typeof d === "string" ? d : (d.text || "");
      return [
        ...(label ? [{ text: `${label}. `, options: { bold: true, color: C.ink, bullet: true } }] : []),
        { text, options: { color: C.body, bullet: !label, breakLine: i !== a.length - 1 } },
      ];
    }).flat();
    s.addText(rows, { x: M, y, w: W - 2 * M, h: H - y - 0.85, fontSize: 12, color: C.body,
      margin: 0, valign: "top", lineSpacingMultiple: 1.1, paraSpaceAfter: 6 });
  } else {
    bulletList(s, bulletsFor(nar, "strategic narrative"), M, y, W - 2 * M, { fontSize: 12.5 });
  }
  sourceNote(s, nar.source);
}

function healthSlide(deck, state, es, cov) {
  const rh = es.relationship_health || {};
  const rhLive = !isBlank(textOf(rh)) || (rh.points || []).length;
  if (!rhLive) return;
  const s = slide(deck, state);
  let y = heading(s, "Relationship health", "Section 1");
  bulletList(s, bulletsFor(rh, "relationship health"), M, y, W - 2 * M, { fontSize: 13, h: 2.6 });
  const rows = (cov.opportunities || []).filter((r) => !isBlank(r.gap_note));
  if (rows.length) {
    let gy = y + 2.75;
    s.addText("Evidence coverage", { x: M, y: gy, w: W - 2 * M, h: 0.28,
      fontSize: 13, bold: true, color: C.ink, margin: 0 });
    gy += 0.34;
    bulletList(s, rows.map((r) => `${r.name}: ${r.meetings_analyzed} of ${r.meetings_held} meetings analyzed.`),
      M, gy, W - 2 * M, { fontSize: 12, h: 0.9 });
  }
  sourceNote(s, rh.source);
}

/** Rough rendered height of body copy in a column of width `w` inches at `pt`. */
function estHeight(text, w, pt) {
  const charsPerLine = Math.max(12, (w * 96) / (pt * 0.5));
  const lines = String(text || "").split(/\n/).reduce(
    (n, seg) => n + Math.max(1, Math.ceil(seg.length / charsPerLine)), 0);
  return lines * (pt / 72) * 1.28;
}

function listSection(deck, state, items, cfg) {
  if (!items.length) return;
  // Up to three items always share one slide; splitting 3 into 1+2 looks like an error.
  const maxItems = cfg.maxItems || 3;
  const pages = items.length <= maxItems
    ? [items]
    : paginate(items, (i) => `${i.title || ""} ${i.text || i.presence || ""}`,
        cfg.budget || BUDGET.wordsPerSlide, maxItems);
  pages.forEach((page, pi) => {
    const s = slide(deck, state);
    const y0 = heading(s, pages.length > 1 ? `${cfg.title} (${pi + 1}/${pages.length})` : cfg.title, cfg.kicker);
    const gap = 0.22, cw = (W - 2 * M - gap * (page.length - 1)) / page.length;
    const avail = H - y0 - 0.55;
    // One height for every card on the slide, sized to the longest, capped at the slide floor.
    const cardH = Math.min(avail, page.reduce((mx, it) => {
      const titleH = estHeight(it.title || it.name || "", cw - 0.4, 13);
      const bodyH = estHeight(it.text || it.presence || "", cw - 0.4, 11);
      const evH = isBlank(it.evidence) ? 0 : estHeight(it.evidence, cw - 0.4, 10) + 0.12;
      const srcH = isBlank(it.source) ? 0 : estHeight(it.source, cw - 0.4, 8.5) + 0.1;
      return Math.max(mx, 0.42 + titleH + 0.16 + bodyH + evH + srcH + 0.28);
    }, 1.6));
    page.forEach((it, i) => {
      const x = M + i * (cw + gap);
      s.addShape("roundRect", { x, y: y0, w: cw, h: cardH, fill: { color: C.panel },
        line: { color: C.panel }, rectRadius: 0.06 });
      const titleH = estHeight(it.title || it.name || "", cw - 0.4, 13);
      s.addText(it.title || it.name || "", { x: x + 0.2, y: y0 + 0.18, w: cw - 0.4, h: titleH + 0.1,
        fontSize: 13, bold: true, color: C.ink, margin: 0, valign: "top" });
      const srcH = isBlank(it.source) ? 0 : estHeight(it.source, cw - 0.4, 8.5) + 0.1;
      const evH = isBlank(it.evidence) ? 0 : estHeight(it.evidence, cw - 0.4, 10) + 0.12;
      const bodyTop = y0 + 0.18 + titleH + 0.18;
      s.addText(String(it.text || it.presence || ""), {
        x: x + 0.2, y: bodyTop, w: cw - 0.4, h: Math.max(0.3, y0 + cardH - 0.2 - evH - srcH - bodyTop),
        fontSize: 11, color: C.body, margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
      if (evH) {
        s.addText(`"${it.evidence}"`, { x: x + 0.2, y: y0 + cardH - 0.16 - srcH - evH, w: cw - 0.4,
          h: evH, fontSize: 10, color: C.accent, margin: 0, valign: "bottom" });
      }
      if (srcH) {
        s.addText(String(it.source), { x: x + 0.2, y: y0 + cardH - 0.14 - srcH, w: cw - 0.4,
          h: srcH, fontSize: 8.5, color: C.muted, margin: 0, valign: "bottom" });
      }
    });
  });
}

function swotSlide(deck, state, swot) {
  const quads = [["Strengths", swot.strengths], ["Weaknesses", swot.weaknesses],
    ["Opportunities", swot.opportunities], ["Threats", swot.threats]]
    .filter(([, v]) => (v || []).length);
  if (!quads.length) return;
  const s = slide(deck, state);
  const y0 = heading(s, "Account SWOT", "Section 2");
  const gap = 0.2, cw = (W - 2 * M - gap) / 2, ch = (H - y0 - 0.85 - gap) / 2;
  quads.forEach(([label, items], i) => {
    const x = M + (i % 2) * (cw + gap), y = y0 + Math.floor(i / 2) * (ch + gap);
    s.addShape("roundRect", { x, y, w: cw, h: ch, fill: { color: C.panel },
      line: { color: C.panel }, rectRadius: 0.06 });
    s.addText(label.toUpperCase(), { x: x + 0.18, y: y + 0.12, w: cw - 0.36, h: 0.26,
      fontSize: 10, bold: true, color: C.accent, charSpacing: 1.1, margin: 0 });
    const rows = [];
    items.slice(0, 3).forEach((it, j, a) => {
      const last = j === a.length - 1;
      rows.push({ text: String(it.text || it), options: { bullet: true, breakLine: true } });
      if (it && it.source) {
        rows.push({ text: String(it.source), options: { fontSize: 8.5, color: C.muted, breakLine: !last } });
      }
    });
    s.addText(rows, {
      x: x + 0.18, y: y + 0.42, w: cw - 0.36, h: ch - 0.56,
      fontSize: 10.5, color: C.body, margin: 0, valign: "top", paraSpaceAfter: 5 });
  });
}

// Use cases. The not-in-play half is computed from the configured catalogue so that
// product whitespace is enumerated rather than remembered. Populated from --config in main().
let UC_CFG = { enabled: true, vocabulary: null };

function useCaseSlide(deck, state, O) {
  if (UC_CFG.enabled === false) return;
  const u = O.use_cases || {};
  const selected = u.selected || [];
  const vocab = Array.isArray(UC_CFG.vocabulary) ? UC_CFG.vocabulary : null;
  if (!selected.length && !vocab) return;
  const norm = (x) => String(x).trim().toLowerCase();
  const chosen = new Set(selected.map(norm));
  const notSelected = vocab ? vocab.filter((x) => !chosen.has(norm(x))) : null;

  const s = slide(deck, state);
  const y = heading(s, "Use cases in play, and the rest", "Section 4");
  const rows = [["In play", selected.length ? selected.join(", ") : "None evidenced"]];
  if (notSelected) {
    rows.push(["Available, not in play",
      notSelected.length ? notSelected.join(", ") : "None. Every use case is in play."]);
  } else {
    rows.push(["Available, not in play", "No catalogue configured. Set use_cases.vocabulary."]);
  }
  dataTable(s, ["", "Use cases"], rows, [3.2, 8.89], y, { fontSize: 11 });
  sourceNote(s, u.source);
}

function roleGapSlides(deck, state, St) {
  const gaps = St.role_gaps || [];
  if (!gaps.length) return;
  const pages = paginate(gaps, (g) => `${g.role} ${g.why_needed}`, 9999, 6);
  pages.forEach((page, pi) => {
    const s = slide(deck, state);
    const y = heading(s, pages.length > 1 ? `Who we do not know yet (${pi + 1}/${pages.length})`
      : "Who we do not know yet", "Section 3");
    dataTable(s, ["Role needed", "Why it is needed", "Route in", "Owner"],
      page.map((g) => {
        const opps = (g.opportunities || []).join(", ") || String(g.opportunities || "");
        return [g.role || "",
          `${g.why_needed || ""}${opps ? `\nAt risk: ${opps}` : ""}`,
          g.route_in || "Not identified", g.owner || "unassigned"];
      }),
      [2.9, 4.9, 2.5, 1.79], y, { fontSize: 10 });
  });
}

function stakeholderSlides(deck, state, St) {
  const known = St.known || [];
  if (known.length) {
    const pages = paginate(known, (p) => `${p.name} ${p.title} ${p.role}`, 9999, 9);
    pages.forEach((page, pi) => {
      const s = slide(deck, state);
      const y = heading(s, pages.length > 1 ? `Key contacts (${pi + 1}/${pages.length})` : "Key contacts",
        "Section 3");
      dataTable(s, ["Name", "Role", "Function", "Meetings", "Last touched"],
        page.map((p) => [`${p.name}${p.title && p.title !== "Not stated on any call" ? `\n${p.title}` : ""}`,
          p.role || "", p.function || "", String(p.meetings ?? ""), p.last_touched || ""]),
        [3.5, 2.5, 2.6, 1.1, 2.39], y, { fontSize: 10 });
    });
  }
  const un = St.unengaged || [];
  if (un.length) {
    const pages = paginate(un, (u) => `${u.name_or_function} ${u.why_it_matters}`, 9999, 6);
    pages.forEach((page, pi) => {
      const s = slide(deck, state);
      const y = heading(s, pages.length > 1 ? `Named but never engaged (${pi + 1}/${pages.length})`
        : "Named but never engaged", "Section 3");
      dataTable(s, ["Who", "Raised on", "Why it matters"],
        page.map((u) => [u.name_or_function || "", u.mentioned_in || "", u.why_it_matters || ""]),
        [3.4, 1.9, 6.79], y, { fontSize: 10 });
    });
  }
  if (!isBlank(textOf(St.coverage))) {
    const s = slide(deck, state);
    const y = heading(s, "Coverage analysis", "Section 3");
    bulletList(s, bulletsFor(St.coverage, "stakeholder coverage"), M, y, W - 2 * M, { fontSize: 12.5 });
    sourceNote(s, (St.coverage || {}).source);
  }
}

function opportunitySlides(deck, state, O) {
  const opps = O.opportunities || [];
  if (opps.length) {
    const s = slide(deck, state);
    let y = heading(s, "Opportunities", "Section 4");
    dataTable(s, ["Opportunity", "Stage", "Amount", "Close", "Owner"],
      opps.map((o) => [`${o.name || ""}${o.manual ? "\nAdded by the account team. No call evidence." : ""}`,
        o.stage || "unknown", money(o.amount), o.close_date || "", o.owner || ""]),
      [4.6, 2.2, 1.7, 1.7, 1.89], y);
    y += 0.75 + opps.length * 0.5;
    const t = O.totals || {};
    s.addText(`Open ${money(t.open_value || 0)} across ${t.open_count ?? 0}   |   `
      + `Closed won ${money(t.closed_won_value || 0)}`, { x: M, y, w: W - 2 * M, h: 0.3,
      fontSize: 12, bold: true, color: C.accent, margin: 0 });
  }
  [["Footprint and adoption", [O.footprint, O.adoption, O.org_footprint]],
   ["Value delivered and expansion", [O.value_impact, O.expansion]]].forEach(([title, blocks]) => {
    const live = blocks.filter((b) => b && (!isBlank(textOf(b)) || (b.points || []).length || (b.needs_input || []).length));
    if (!live.length) return;
    const s = slide(deck, state);
    let y = heading(s, title, "Section 4");
    live.forEach((b) => {
      const bl = bulletsFor(b, title);
      if (bl.length) { bulletList(s, bl, M, y, W - 2 * M, { fontSize: 11.5, h: 1.5 }); y += 0.34 + bl.length * 0.34; }
      y = inputNeeded(s, b.needs_input, y);
    });
  });
}

function licenseSlide(deck, state, L) {
  const blocks = [["Contract terms", L.contract_terms], ["Historical spend", L.historical_spend],
    ["Budget and buying cycle", L.budget_cycle], ["Licenses", L.licenses]]
    .filter(([, b]) => b && (!isBlank(textOf(b)) || (b.points || []).length || (b.needs_input || []).length));
  if (!blocks.length) return;
  const BASIS = { evidenced: "Evidenced", public: "Public record", inferred: "Inferred",
    mixed: "Mixed", input_needed: "Input needed" };
  let s = null, y = 0;
  blocks.forEach(([title, b]) => {
    const bl = bulletsFor(b, title);
    const need = 0.42 + bl.length * 0.44 + ((b.needs_input || []).length ? 0.8 : 0);
    if (!s || y + need > H - 1.0) { s = slide(deck, state); y = heading(s, "Contract and budget", "Section 5"); }
    s.addText(title, { x: M, y, w: W - 2 * M, h: 0.28, fontSize: 13, bold: true, color: C.ink, margin: 0 });
    y += 0.3;
    if (b.basis && BASIS[b.basis]) {
      s.addText(`Basis: ${BASIS[b.basis]}`, { x: M, y, w: W - 2 * M, h: 0.24,
        fontSize: 9.5, color: C.muted, margin: 0 });
      y += 0.26;
    }
    if (bl.length) { bulletList(s, bl, M, y, W - 2 * M, { fontSize: 11, h: bl.length * 0.44 }); y += bl.length * 0.44 + 0.14; }
    y = inputNeeded(s, b.needs_input, y);
    y += 0.16;
  });
}

function gtmSlides(deck, state, G) {
  const prioLive = G.priority && (!isBlank(textOf(G.priority)) || (G.priority.points || []).length);
  if (prioLive) {
    const s = slide(deck, state);
    const y = heading(s, "Where to focus", "Section 6");
    bulletList(s, bulletsFor(G.priority, "GTM priority"), M, y, W - 2 * M, { fontSize: 13 });
    sourceNote(s, (G.priority || {}).source);
  }
  (G.tracks || []).forEach((t) => {
    const live = !isBlank(t.objective) || (t.plays || []).length || (t.needs_input || []).length;
    if (!live) return;
    const s = slide(deck, state);
    let y = heading(s, t.title || "Track", "Section 6");
    if (!isBlank(t.objective)) {
      s.addText(t.objective, { x: M, y, w: W - 2 * M, h: 0.5, fontSize: 14, bold: true,
        color: C.accent, margin: 0, valign: "top" });
      y += 0.6;
    }
    if (!isBlank(t.why_now)) {
      s.addText("WHY NOW", { x: M, y, w: 3, h: 0.22, fontSize: 9, bold: true, color: C.muted,
        charSpacing: 1.1, margin: 0 });
      y += 0.26;
      s.addText(t.why_now, { x: M, y, w: W - 2 * M, h: 1.05, fontSize: 11.5, color: C.body,
        margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
      y += 1.15;
    }
    if ((t.plays || []).length) {
      s.addText("PLAYS", { x: M, y, w: 3, h: 0.22, fontSize: 9, bold: true, color: C.muted,
        charSpacing: 1.1, margin: 0 });
      y += 0.26;
      bulletList(s, t.plays, M, y, W - 2 * M, { fontSize: 11.5, h: 1.5 });
      y += 0.2 + t.plays.length * 0.42;
    }
    const foot = [t.owner ? `Owner: ${t.owner}` : "", t.exit_criterion ? `Exit: ${t.exit_criterion}` : ""]
      .filter((f) => !isBlank(f)).join("    |    ");
    if (!isBlank(foot)) {
      s.addText(foot, { x: M, y: Math.min(y, H - 1.35), w: W - 2 * M, h: 0.5,
        fontSize: 10, color: C.muted, margin: 0, valign: "top" });
    }
    if ((t.needs_input || []).length) inputNeeded(s, t.needs_input, Math.min(y, H - 1.9));
  });
}

function nextStepsSlide(deck, state, N) {
  const steps = N.steps || [];
  if (!steps.length && !(N.needs_input || []).length) return;
  const pages = paginate(steps, (s) => s.text, 9999, 5);
  pages.forEach((page, pi) => {
    const s = slide(deck, state);
    let y = heading(s, pages.length > 1 ? `Next steps (${pi + 1}/${pages.length})` : "Next steps", "Section 7");
    dataTable(s, ["Action", "Opportunity", "Owner", "Target"],
      page.map((st) => [st.text || "", st.opportunity || "", st.owner || "", st.target || ""]),
      [6.4, 2.3, 1.9, 1.49], y, { fontSize: 10 });
    if (pi === pages.length - 1) {
      y += 0.75 + page.length * 0.58;
      inputNeeded(s, N.needs_input, Math.min(y, H - 1.7));
    }
  });
}

function competitiveSlides(deck, state, K) {
  const comps = K.competitors || [];
  if (comps.length) {
    listSection(deck, state, comps.map((c) => ({ title: c.name, text: c.presence, source: c.evidence })),
      { title: "Competitive landscape", kicker: "Section 8", maxItems: 3, budget: 240 });
  }
  const blocks = [["Differentiation", K.differentiation]]
    .filter(([, b]) => b && (!isBlank(textOf(b)) || (b.points || []).length));
  const objs = K.objections || [];
  if (blocks.length || objs.length) {
    const s = slide(deck, state);
    let y = heading(s, "Differentiation and open objections", "Section 8");
    blocks.forEach(([, b]) => {
      const bl = bulletsFor(b, "differentiation");
      bulletList(s, bl, M, y, W - 2 * M, { fontSize: 11.5, h: 1.7 });
      y += 0.2 + bl.length * 0.44;
    });
    if (objs.length) {
      s.addText("OPEN OBJECTIONS", { x: M, y: Math.min(y, H - 2.4), w: 4, h: 0.22,
        fontSize: 9, bold: true, color: C.muted, charSpacing: 1.1, margin: 0 });
      bulletList(s, objs.map((o) => o.text), M, Math.min(y, H - 2.4) + 0.26, W - 2 * M,
        { fontSize: 11, h: 1.6 });
    }
    inputNeeded(s, K.needs_input, H - 1.35);
  }
}

function appendixSlides(deck, state, cov) {
  const s = slide(deck, state);
  let y = heading(s, "Evidence coverage", "Appendix");
  const rows = cov.opportunities || [];
  if (rows.length) {
    dataTable(s, ["Opportunity", "Analyzed", "Held", "Latest", "Gap"],
      rows.map((r) => [r.name || "", String(r.meetings_analyzed ?? ""), String(r.meetings_held ?? ""),
        r.latest_meeting || "", r.gap_note || ""]),
      [2.6, 1.0, 0.9, 1.2, 6.39], y, { fontSize: 9.5 });
    y += 0.7 + rows.length * 0.8;
  }
  const ag = cov.agents || [];
  if (ag.length && y < H - 2.2) {
    dataTable(s, ["Agent", "How it was run", "Runs"],
      ag.map((a) => [a.name || "", a.status || "", String(a.runs ?? "")]),
      [3.6, 7.0, 1.49], y, { fontSize: 9.5 });
  }
  const notes = cov.notes || [], inputs = cov.open_inputs || [];
  if (notes.length || inputs.length) {
    const s2 = slide(deck, state);
    let y2 = heading(s2, "Reading notes and open inputs", "Appendix");
    if (notes.length) {
      s2.addText("HOW TO READ THIS PLAN", { x: M, y: y2, w: 5, h: 0.22, fontSize: 9, bold: true,
        color: C.muted, charSpacing: 1.1, margin: 0 });
      y2 += 0.26;
      bulletList(s2, notes, M, y2, W - 2 * M, { fontSize: 10, h: notes.length * 0.62, reference: true });
      y2 += notes.length * 0.62 + 0.2;
    }
    if (inputs.length) inputNeeded(s2, inputs, Math.min(y2, H - 0.9 - inputs.length * 0.3));
  }
  const ext = cov.external_sources || [];
  if (ext.length) {
    const s4 = slide(deck, state);
    const y4 = heading(s4, "External sources", "Appendix");
    dataTable(s4, ["Title", "Publisher", "Date", "Retrieved"],
      ext.map((e) => [e.title || "", e.publisher || "", e.date || "", e.retrieved || ""]),
      [6.4, 2.6, 1.6, 1.49], y4, { fontSize: 9.5 });
  }
}

// ---------------------------------------------------------------- main
function main() {
  const args = process.argv.slice(2);
  const get = (f) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : null; };
  const valuesPath = get("--values");
  if (!valuesPath) { console.error("--values is required"); process.exit(2); }
  const v = JSON.parse(fs.readFileSync(valuesPath, "utf8"));
  const cfgPath = get("--config");
  if (cfgPath && fs.existsSync(cfgPath)) {
    const c = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
    UC_CFG = Object.assign(UC_CFG, c.use_cases || {});
  }
  const S = v.sections || {}, meta = v.meta || {};
  const out = get("--out") || `Account Plan - ${meta.account || "Account"}.pptx`;

  const deck = makeDeck();
  const state = { n: 0 };

  titleSlide(deck, state, meta, S);
  teamSlide(deck, state, S.stakeholders || {});
  snapshotSlide(deck, state, S.exec_summary || {});
  healthSlide(deck, state, S.exec_summary || {}, S.coverage || {});

  const L = S.landscape || {};
  listSection(deck, state, L.business_priorities || [], { title: "Business priorities", kicker: "Section 2" });
  listSection(deck, state, L.challenges || [], { title: "Challenges", kicker: "Section 2" });
  listSection(deck, state, L.industry_trends || [], { title: "Industry trends", kicker: "Section 2" });
  listSection(deck, state, L.kpis || [], { title: "How they measure themselves", kicker: "Section 2" });
  swotSlide(deck, state, L.swot || {});
  if ((L.hypotheses || []).length) {
    const s = slide(deck, state);
    const y = heading(s, "Hypotheses to test", "Section 2");
    bulletList(s, (L.hypotheses || []).map((h) => `${h.text} → ${h.question}`), M, y, W - 2 * M,
      { fontSize: 11.5 });
  }

  stakeholderSlides(deck, state, S.stakeholders || {});
  roleGapSlides(deck, state, S.stakeholders || {});
  useCaseSlide(deck, state, S.opportunities_footprint || {});
  opportunitySlides(deck, state, S.opportunities_footprint || {});
  licenseSlide(deck, state, S.licenses || {});
  gtmSlides(deck, state, S.gtm || {});
  nextStepsSlide(deck, state, S.next_steps_map || {});
  competitiveSlides(deck, state, S.competitive || {});
  appendixSlides(deck, state, S.coverage || {});

  return deck.writeFile({ fileName: out }).then(() => {
    console.log(`Wrote ${out}  (${state.n} slides)`);
    if (warnings.length) {
      console.log(`\n${warnings.length} slide-budget warning(s):`);
      [...new Set(warnings)].forEach((w) => console.log("  - " + w));
      if (args.includes("--strict")) process.exit(1);
    } else {
      console.log("Slide budget checks passed.");
    }
  });
}

main();
