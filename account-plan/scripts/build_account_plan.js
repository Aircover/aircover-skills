#!/usr/bin/env node
/**
 * build_account_plan.js - Build an account plan .docx from a values file.
 *
 * Config-driven: section order, titles, numbering, colours, fonts, freshness bands, and the
 * placeholder style all come from config.json, so another install can retitle or reorder the
 * plan without touching this code. No company name, agent id, or CRM field is baked in here.
 *
 * Usage:
 *   node build_account_plan.js --values account_plan.json --config config.json \
 *     --out "Account Plan - Acme - 2026-08-22.docx" [--strict]
 *
 * What it does:
 *   - Writes only the blocks you supply. An unsupplied block renders nothing, except where
 *     config marks the section never_blank, which raises a warning instead.
 *   - Renders INPUT NEEDED blocks in the configured placeholder style so the account team can
 *     see at a glance what still needs a human, rather than reading invented prose.
 *   - Opens with a one-page "At a glance" summary (snapshot tiles, open opportunities, key
 *     people, where to spend first, next steps) built from the same values, so nothing on it
 *     can disagree with the sections behind it. config.document.at_a_glance: false turns it off.
 *   - Tags provenance: any block carrying `source` gets a small grey source line beneath it.
 *   - Colour codes stakeholder recency against config.scope.freshness_bands_days.
 *   - Runs the mechanical half of the consistency pass and prints warnings. --strict turns
 *     warnings into a non-zero exit so a bad run cannot be presented by accident.
 *
 * Requires the `docx` npm package (preinstalled in this environment).
 */

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageBreak, ExternalHyperlink, PageNumber,
} = require("docx");

// ---------------------------------------------------------------- CLI

const args = process.argv.slice(2);
let valuesFile, configFile, outFile, strict = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--values" && args[i + 1]) valuesFile = args[++i];
  else if (args[i] === "--config" && args[i + 1]) configFile = args[++i];
  else if (args[i] === "--out" && args[i + 1]) outFile = args[++i];
  else if (args[i] === "--strict") strict = true;
}
if (!valuesFile || !outFile) {
  console.error("Usage: node build_account_plan.js --values account_plan.json --out OUTPUT.docx [--config config.json] [--strict]");
  process.exit(2);
}

const cfg = JSON.parse(fs.readFileSync(configFile || "config.json", "utf-8"));
const data = JSON.parse(fs.readFileSync(valuesFile, "utf-8"));

const DOC = cfg.document || {};
const C = Object.assign({
  heading: "1B2A4A", accent: "2CB5AD", body: "3D4F6F", muted: "7A8CA0", placeholder: "7A8CA0",
  rule: "E2E8F0", table_header_fill: "1B2A4A", table_header_text: "FFFFFF", band_fill: "F7F9FB",
  tile_fill: "F7F9FB", title_fill: "1B2A4A", title_text: "FFFFFF", title_sub: "C8D0DA",
  current: "1E7B55", aging: "8A6100", stale: "B23B3B",
}, DOC.colors || {});
const GLANCE = DOC.at_a_glance !== false;
const FONT = (DOC.fonts && DOC.fonts.body) || "Calibri";
const PLACEHOLDER = Object.assign({ label: "INPUT NEEDED", italic: false }, DOC.placeholder_style || {});
const SHOW_SOURCE = DOC.show_provenance_labels !== false;
const BANDS = (cfg.scope && cfg.scope.freshness_bands_days) || { current: 90, aging: 270 };
const USE_CASES = Object.assign({ enabled: true, vocabulary: null }, cfg.use_cases || {});
const HEADING_FONT = (DOC.fonts && DOC.fonts.heading) || FONT;
const VENDOR = (data.meta && data.meta.vendor && data.meta.vendor.name)
  || (cfg.vendor && cfg.vendor.name) || "";
const VENDOR_DOMAIN = (data.meta && data.meta.vendor && data.meta.vendor.email_domain)
  || (cfg.vendor && cfg.vendor.email_domain) || "";

// Page geometry. DXA, 1440 per inch. A4 for installs outside the US.
const PAGE = String(DOC.page_size || "letter").toLowerCase() === "a4"
  ? { width: 11906, height: 16838 }
  : { width: 12240, height: 15840 };
const MARGIN = { top: 1080, bottom: 1080, left: 1440, right: 1440 };

const meta = data.meta || {};
const S = data.sections || {};
const warnings = [];
const warn = (m) => warnings.push(m);

// ---------------------------------------------------------------- helpers

const CONTENT_WIDTH = PAGE.width - MARGIN.left - MARGIN.right;

/** Substitute {vendor} anywhere it appears. Blank vendor leaves clean text, not a stray brace. */
function sub(str) {
  if (str === null || str === undefined) return str;
  const s = String(str);
  if (s.indexOf("{vendor}") === -1) return s; // never touch ordinary text, spacing included
  return s.replace(/\{vendor\}\s*/g, VENDOR ? VENDOR + " " : "").replace(/[ \t]{2,}/g, " ");
}

const isBlank = (v) => v === undefined || v === null ||
  (typeof v === "string" && v.trim() === "") ||
  (Array.isArray(v) && v.length === 0);

function textOf(block) {
  if (!block) return "";
  if (typeof block === "string") return block;
  return block.text || "";
}

/** Split on newlines so we never emit a literal \n into a run. */
function lines(str) {
  return String(str || "").split(/\r?\n/).filter((l) => l.trim() !== "");
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
    alignment: opts.align,
    indent: opts.indent,
    children: [new TextRun({
      text: sub(text),
      font: FONT,
      size: opts.size || 21,
      bold: !!opts.bold,
      italics: !!opts.italic,
      color: opts.color || C.body,
      allCaps: !!opts.caps,
    })],
  });
}

/** A paragraph built from several differently styled runs. */
function runs(parts, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
    indent: opts.indent,
    children: parts.filter(Boolean).map((p) => new TextRun({
      text: sub(p.text),
      font: FONT,
      size: p.size || opts.size || 21,
      bold: !!p.bold,
      italics: !!p.italic,
      color: p.color || C.body,
    })),
  });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "ap-bullets", level: opts.level || 0 },
    spacing: { after: 60, line: 276 },
    children: [new TextRun({
      text: sub(text), font: FONT, size: opts.size || 21,
      color: opts.color || C.body, bold: !!opts.bold, italics: !!opts.italic,
    })],
  });
}

function sectionHeading(number, title) {
  const parts = [];
  if (number) {
    parts.push(new TextRun({ text: `${number}  `, font: HEADING_FONT, size: 28, bold: true, color: C.accent }));
  }
  parts.push(new TextRun({ text: sub(title), font: HEADING_FONT, size: 28, bold: true, color: C.heading }));
  return new Paragraph({
    spacing: { before: 360, after: 160 },
    keepNext: true,
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.accent, space: 6 } },
    heading: HeadingLevel.HEADING_1,
    children: parts,
  });
}

function subHeading(title) {
  return new Paragraph({
    spacing: { before: 220, after: 80 },
    keepNext: true,
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text: sub(title), font: HEADING_FONT, size: 22, bold: true, color: C.heading })],
  });
}

/** Small teal caps label, used to head the At a glance blocks. */
function kicker(text, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.before === undefined ? 240 : opts.before, after: 80 },
    keepNext: true,
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.rule, space: 4 } },
    children: [new TextRun({ text: sub(text).toUpperCase(), font: FONT, size: 17, bold: true, color: C.accent })],
  });
}

function sourceLine(source) {
  if (!SHOW_SOURCE || isBlank(source)) return null;
  return para(`Source: ${source}`, { size: 16, color: C.muted, after: 160 });
}

/** An unsupplied fact a human holds. Rendered so it cannot be mistaken for content. */
function inputNeeded(question) {
  return runs([
    { text: `${PLACEHOLDER.label}: `, bold: true, color: C.placeholder, size: 19 },
    { text: String(question), color: C.placeholder, size: 19, italic: !!PLACEHOLDER.italic },
  ], { after: 100 });
}

function inputBlock(items) {
  const list = (items || []).filter((x) => !isBlank(x));
  return list.map((q) => inputNeeded(typeof q === "string" ? q : q.question || ""));
}

/** Free text block plus optional source line. Returns [] when empty. */
/**
 * Renders a block as prose, as bullets, or as a lead paragraph followed by bullets.
 *
 * `text`   narrative prose. Use for blocks that make an argument, where fragmenting
 *          the reasoning destroys it: the strategic narrative, relationship health,
 *          the coverage read.
 * `points` an array of enumerated findings, rendered as bullets. Use for blocks that
 *          are already lists wearing prose clothing: expansion signals, org footprint,
 *          value delivered, differentiation, objections.
 *
 * Both may be set, in which case `text` becomes a one or two sentence lead and the
 * points carry the enumeration. See output_standard.md section 3a.
 */
function textBlock(block, opts = {}) {
  const t = textOf(block);
  const pts = (block && Array.isArray(block.points)) ? block.points.filter((p) => !isBlank(p)) : [];
  if (isBlank(t) && !pts.length) return [];
  const out = [];
  if (!isBlank(t)) out.push(...lines(t).map((l) => para(l, opts)));
  pts.forEach((p) => out.push(bullet(typeof p === "string" ? p : (p.text || ""), opts)));
  if (pts.length) out.push(para("", { after: 40 }));
  const src = sourceLine(block && block.source);
  if (src) out.push(src);
  return out;
}

function freshnessBand(dateStr) {
  if (isBlank(dateStr)) return { label: "unknown", color: C.muted };
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return { label: "unknown", color: C.muted };
  const ref = meta.date ? new Date(meta.date) : new Date();
  const days = Math.round((ref - d) / 86400000);
  if (days <= BANDS.current) return { label: "current", color: C.current };
  if (days <= BANDS.aging) return { label: "aging", color: C.aging };
  return { label: "stale", color: C.stale };
}

function cell(children, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill, color: "auto" } : undefined,
    margins: opts.margins || { top: 80, bottom: 80, left: 120, right: 120 },
    borders: opts.borders,
    verticalAlign: opts.valign,
    children,
  });
}

const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const NO_BORDERS = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER,
                     insideHorizontal: NO_BORDER, insideVertical: NO_BORDER };
const hairline = () => ({ style: BorderStyle.SINGLE, size: 4, color: C.rule });

/**
 * rows: array of arrays. Each entry is a string, or {text, color, bold}.
 * widths must sum to CONTENT_WIDTH.
 */
function table(headers, rows, widths) {
  const sum = widths.reduce((a, b) => a + b, 0);
  if (Math.abs(sum - CONTENT_WIDTH) > 2) {
    widths = widths.map((w) => Math.round((w / sum) * CONTENT_WIDTH));
  }
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => cell(
      [para(h, { bold: true, size: 18, after: 0, color: C.table_header_text })],
      widths[i], { fill: C.table_header_fill, borders: { left: NO_BORDER, right: NO_BORDER } },
    )),
  });
  const bodyRows = rows.map((r, ri) => new TableRow({
    children: r.map((v, i) => {
      const val = typeof v === "object" && v !== null ? v : { text: v };
      const content = lines(val.text).length
        ? lines(val.text).map((l, idx, arr) => para(l, {
            size: 18, after: idx === arr.length - 1 ? 0 : 40,
            color: val.color || C.body, bold: !!val.bold,
          }))
        : [para("", { size: 18, after: 0 })];
      return cell(content, widths[i], { fill: ri % 2 === 1 ? C.band_fill : undefined,
                                        borders: { left: NO_BORDER, right: NO_BORDER } });
    }),
  }));
  return new Table({
    columnWidths: widths,
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    borders: { top: NO_BORDER, left: NO_BORDER, right: NO_BORDER, insideVertical: NO_BORDER,
               bottom: hairline(), insideHorizontal: hairline() },
    rows: [headerRow, ...bodyRows],
  });
}

/** A one-cell box with a teal bar down its left edge, for the line a reader must not miss. */
function callout(paragraphs) {
  return new Table({
    columnWidths: [CONTENT_WIDTH],
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    borders: NO_BORDERS,
    rows: [new TableRow({ children: [cell(paragraphs, CONTENT_WIDTH, {
      fill: C.band_fill,
      margins: { top: 140, bottom: 100, left: 220, right: 200 },
      borders: { left: { style: BorderStyle.SINGLE, size: 36, color: C.accent },
                 top: NO_BORDER, bottom: NO_BORDER, right: NO_BORDER },
    })] })],
  });
}

/** Metric tiles: big value over a small caps label, teal rule on top. */
function tiles(metrics) {
  const m = (metrics || []).filter((x) => x && !isBlank(x.value));
  if (!m.length) return [];
  const gap = 120;
  const w = Math.floor((CONTENT_WIDTH - gap * (m.length - 1)) / m.length);
  const widths = [];
  m.forEach((_, i) => { widths.push(w); if (i < m.length - 1) widths.push(gap); });
  const cells = [];
  // Tiles are for a number or a date. A value that runs to a phrase still renders, but
  // smaller, so one wordy tile cannot push the whole page onto a second sheet.
  const longest = Math.max(...m.map((x) => String(x.value).length));
  const vsize = longest <= 12 ? 34 : longest <= 20 ? 26 : 22;
  m.forEach((x, i) => {
    cells.push(cell([
      para(String(x.value), { size: vsize, bold: true, color: C.heading, after: 20 }),
      para(x.label, { size: 15, caps: true, color: C.muted, after: 0 }),
    ], w, {
      fill: C.tile_fill,
      margins: { top: 140, bottom: 140, left: 160, right: 120 },
      borders: { top: { style: BorderStyle.SINGLE, size: 24, color: C.accent },
                 bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER },
    }));
    if (i < m.length - 1) cells.push(cell([para("", { after: 0 })], gap, { borders: NO_BORDERS }));
  });
  return [new Table({
    columnWidths: widths,
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    borders: NO_BORDERS,
    rows: [new TableRow({ children: cells })],
  })];
}

function money(v) {
  if (isBlank(v)) return "";
  if (typeof v === "number") return "$" + v.toLocaleString("en-US");
  return String(v);
}

// ---------------------------------------------------------------- sections

function renderExecSummary(s) {
  const out = [];
  const d = s.account_details || {};
  const rows = [];
  const push = (k, v) => { if (!isBlank(v)) rows.push([k, String(v)]); };
  push("Account", meta.account);
  push("Industry", d.industry);
  push("Revenue", d.revenue);
  push("Employees", d.employees);
  push("Headquarters", d.hq);
  push("Domains in scope", (meta.domains || []).join(", "));
  push("Account owner", meta.account_owner);
  push("Evidence window", meta.evidence_window
    ? `${meta.evidence_window.start} to ${meta.evidence_window.end}` : "");
  if (rows.length) {
    out.push(table(["Field", "Value"], rows, [2400, 6960]));
    out.push(para("", { after: 60 }));
  }
  if (d.source) { const sl = sourceLine(d.source); if (sl) out.push(sl); }

  const m = s.snapshot_metrics || [];
  // With the At a glance page on, the tiles live there and are not repeated here.
  if (m.length && !GLANCE) {
    out.push(subHeading("Snapshot"));
    const w = Math.floor(CONTENT_WIDTH / Math.max(m.length, 1));
    out.push(new Table({
      columnWidths: m.map(() => w),
      width: { size: w * m.length, type: WidthType.DXA },
      rows: [
        new TableRow({ children: m.map((x) => cell(
          [para(x.label, { size: 16, caps: true, color: C.muted, after: 40 })], w, { fill: C.table_header_fill })) }),
        new TableRow({ children: m.map((x) => cell(
          [para(x.value, { size: 24, bold: true, color: C.heading, after: 0 })], w)) }),
      ],
    }));
    out.push(para("", { after: 60 }));
  }

  if (!isBlank(textOf(s.strategic_narrative)) || (s.strategic_narrative || {}).dimensions) {
    out.push(subHeading("Why this account matters"));
    const nar = s.strategic_narrative || {};
    if (!isBlank(textOf(nar))) out.push(...lines(textOf(nar)).map((l) => para(l)));
    (nar.dimensions || []).filter((d) => !isBlank(d)).forEach((d) => {
      const label = typeof d === "string" ? "" : (d.label || "");
      const text = typeof d === "string" ? d : (d.text || "");
      out.push(label
        ? runs([{ text: `${label}. `, bold: true }, { text }], { indent: { left: 360, hanging: 0 } })
        : bullet(text));
    });
    if ((nar.dimensions || []).length) out.push(para("", { after: 40 }));
    const sl = sourceLine(nar.source); if (sl) out.push(sl);
  }
  if (!isBlank(textOf(s.relationship_health))) {
    out.push(subHeading("Current relationship health"));
    out.push(...textBlock(s.relationship_health));
  }
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderLandscape(s) {
  const out = [];
  const listBlock = (title, items) => {
    if (!items || !items.length) return;
    out.push(subHeading(title));
    items.forEach((it) => {
      if (it.title) out.push(para(it.title, { bold: true, after: 40 }));
      lines(it.text).forEach((l) => out.push(para(l, { after: 60 })));
      if (it.evidence) out.push(para(`"${it.evidence}"`, { size: 19, color: C.muted, indent: { left: 360 }, after: 40 }));
      const sl = sourceLine(it.source);
      if (sl) out.push(sl);
    });
  };

  listBlock("Business priorities", s.business_priorities);
  listBlock("Challenges and unconsidered needs", s.challenges);
  listBlock("KPIs and performance measures", s.kpis);
  listBlock("Industry trends affecting this account", s.industry_trends);

  const sw = s.swot;
  if (sw && (sw.strengths || sw.weaknesses || sw.opportunities || sw.threats)) {
    out.push(subHeading("Customer SWOT"));
    const fmt = (arr) => (arr && arr.length)
      ? arr.map((e) => `${e.text}${e.source ? ` (${e.source})` : ""}`).join("\n")
      : "";
    out.push(table(
      ["Strengths", "Weaknesses"],
      [[fmt(sw.strengths), fmt(sw.weaknesses)]],
      [4680, 4680],
    ));
    out.push(para("", { after: 60 }));
    out.push(table(
      ["Opportunities", "Threats"],
      [[fmt(sw.opportunities), fmt(sw.threats)]],
      [4680, 4680],
    ));
    out.push(para("", { after: 120 }));
  }

  if (s.hypotheses && s.hypotheses.length) {
    out.push(subHeading("Hypotheses to validate"));
    out.push(para("Not evidenced. Each item carries the question that would confirm or kill it. Nothing here appears elsewhere in this plan.", { size: 18, color: C.muted }));
    s.hypotheses.forEach((h) => {
      out.push(bullet(h.text, { bold: false }));
      if (h.question) out.push(para(`Ask: ${h.question}`, { size: 18, color: C.muted, indent: { left: 720 }, after: 60 }));
    });
  }
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderStakeholders(s) {
  const out = [];
  const known = s.known || [];
  if (known.length) {
    out.push(subHeading("Known stakeholders"));
    const rows = known.map((p) => {
      const band = freshnessBand(p.last_touched);
      return [
        `${p.name || ""}${p.title ? `\n${p.title}` : ""}`,
        p.role || "Attendee, role unconfirmed",
        (p.opportunities || []).join(", ") || String(p.opportunities || ""),
        { text: `${p.last_touched || "unknown"}${band.label !== "unknown" ? `\n${band.label}` : ""}`, color: band.color },
        p.notes || "",
      ];
    });
    out.push(table(
      ["Person", "Role", "Opportunities", "Last touched", "Notes"],
      rows, [2100, 1500, 1700, 1360, 2700],
    ));
    out.push(para("", { after: 120 }));
  }

  // Roles the deal requires and nobody has a name for. Distinct from `unengaged`, which is
  // people who were named on a call and never met. This half is derived from the decision
  // process, security, procurement, and legal dimensions, so it exists even when no name does.
  const gaps = s.role_gaps || [];
  if (gaps.length) {
    out.push(subHeading("Who we do not know yet"));
    out.push(para("Roles this account requires with no named contact. Each one is a coverage gap with an owner, not an observation.", { size: 18, color: C.muted }));
    out.push(table(
      ["Role needed", "Why it is needed", "Opportunities at risk", "Route in", "Owner"],
      gaps.map((g) => [
        g.role || "",
        g.why_needed || "",
        (g.opportunities || []).join(", ") || String(g.opportunities || ""),
        g.route_in || "Not identified",
        g.owner || "unassigned",
      ]),
      [2000, 2800, 1500, 1900, 1160],
    ));
    out.push(para("", { after: 120 }));
  }

  const un = s.unengaged || [];
  if (un.length) {
    out.push(subHeading("Named or implied, never engaged"));
    out.push(para("People and functions referenced on calls who have not attended a meeting. Each is an open coverage gap.", { size: 18, color: C.muted }));
    out.push(table(
      ["Person or function", "Mentioned in", "Mentioned for", "Why it matters"],
      un.map((u) => [u.name_or_function || "", u.mentioned_in || "", u.mentioned_for || "", u.why_it_matters || ""]),
      [2340, 1800, 2340, 2880],
    ));
    out.push(para("", { after: 120 }));
  }

  const team = s.account_team || [];
  if (team.length) {
    out.push(subHeading("Account team"));
    out.push(table(
      ["Name", "Role", "Responsibility", "Meetings"],
      team.map((m) => [m.name || "", m.role || "unconfirmed", m.responsibility || "", String(m.meetings ?? "")]),
      [2400, 1900, 4260, 800],
    ));
    out.push(para("", { after: 80 }));
    if (!isBlank(s.account_team_note)) out.push(para(s.account_team_note, { size: 19, color: C.muted }));
    out.push(...inputBlock(s.account_team_needs_input));
  }

  if (!isBlank(textOf(s.coverage))) {
    out.push(subHeading("Coverage analysis"));
    out.push(...textBlock(s.coverage));
  }
  if (!isBlank(textOf(s.engagement_strategy))) {
    out.push(subHeading("Engagement strategy"));
    out.push(...textBlock(s.engagement_strategy));
  }
  out.push(...inputBlock(s.needs_input));
  return out;
}

// Use cases are chosen from a fixed catalogue rather than written as prose. The not-selected
// half is computed by subtraction, so product whitespace can never be quietly omitted.
function useCaseSplit(u) {
  const vocab = USE_CASES.vocabulary;
  const selected = (u && u.selected) || [];
  if (!Array.isArray(vocab) || !vocab.length) return { selected, notSelected: null, vocab: null };
  const norm = (x) => String(x).trim().toLowerCase();
  const chosen = new Set(selected.map(norm));
  return { selected, notSelected: vocab.filter((v) => !chosen.has(norm(v))), vocab };
}

function renderUseCases(u) {
  const out = [];
  if (USE_CASES.enabled === false) return out;
  const { selected, notSelected } = useCaseSplit(u);
  if (!selected.length && !(notSelected && notSelected.length) && isBlank(u && u.needs_input)) return out;

  out.push(subHeading("Use cases"));
  out.push(para(
    selected.length ? `In play: ${selected.join(", ")}.` : "In play: none evidenced.",
    { size: 19 },
  ));
  if (notSelected) {
    out.push(para(
      notSelected.length
        ? `Available, not in play: ${notSelected.join(", ")}. Each is expansion whitespace until a call says otherwise.`
        : "Every use case in the catalogue is in play at this account.",
      { size: 19, color: C.muted },
    ));
  } else {
    out.push(para(
      "No use case catalogue is configured, so the not-in-play half cannot be computed. "
      + "Set use_cases.vocabulary in config.json.",
      { size: 18, color: C.placeholder },
    ));
  }
  if (u && u.source) {
    const sl = sourceLine(u.source);
    if (sl) out.push(sl);
  }
  out.push(...inputBlock(u && u.needs_input));
  out.push(para("", { after: 120 }));
  return out;
}

function renderOpportunities(s) {
  const out = [];
  const opps = s.opportunities || [];
  if (opps.length) {
    out.push(subHeading("Opportunities in scope"));
    out.push(table(
      ["Opportunity", "Type", "Stage", "Amount", "Close", "Owner"],
      opps.map((o) => [
        `${o.name || ""}${o.manual ? "\nAdded by the account team. No Aircover meetings, so no call evidence."
          : (o.initiative ? `\n${o.initiative}` : "")}`,
        o.type || "", o.stage || "unknown", money(o.amount), o.close_date || "", o.owner || "",
      ]),
      [2700, 1200, 1600, 1300, 1200, 1360],
    ));
    const vb = sourceLine((data.meta || {}).value_basis);
    if (vb) out.push(vb);
    out.push(para("", { after: 80 }));
    const manual = opps.filter((o) => o.manual);
    if (manual.length) {
      out.push(para(
        `${manual.length} opportunit${manual.length === 1 ? "y was" : "ies were"} supplied by the account team `
        + `and had no Aircover meetings. ${manual.length === 1 ? "It is" : "They are"} counted in the totals `
        + `below, but nothing in this plan that draws on call evidence covers ${manual.length === 1 ? "it" : "them"}.`,
        { size: 19, color: C.muted },
      ));
    }
    const t = s.totals || {};
    const bits = [];
    if (!isBlank(t.open_count)) bits.push(`${t.open_count} open`);
    if (!isBlank(t.open_value)) bits.push(`${money(t.open_value)} open value`);
    if (!isBlank(t.closed_won_value)) bits.push(`${money(t.closed_won_value)} closed won in the lookback`);
    if (bits.length) out.push(para(bits.join(". ") + ".", { size: 19, color: C.muted }));
  }

  out.push(...renderUseCases(s.use_cases));

  const blocks = [
    ["Current footprint", s.footprint],
    ["Adoption and usage", s.adoption],
    ["Organizational footprint", s.org_footprint],
    ["Value and business impact delivered", s.value_impact],
    ["Expansion signals and whitespace", s.expansion],
  ];
  blocks.forEach(([title, b]) => {
    if (isBlank(textOf(b)) && isBlank(b && b.needs_input)) return;
    out.push(subHeading(title));
    out.push(...textBlock(b));
    out.push(...inputBlock(b && b.needs_input));
  });
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderLicenses(s) {
  const out = [];
  const blocks = [
    ["Active licenses", s.licenses],
    ["Contract terms and key dates", s.contract_terms],
    ["Historical spend", s.historical_spend],
    ["Budget and buying cycle", s.budget_cycle],
  ];
  const BASIS = { evidenced: "Evidenced", public: "Public record", inferred: "Inferred",
                  mixed: "Mixed", input_needed: "Input needed" };
  blocks.forEach(([title, b]) => {
    if (isBlank(textOf(b)) && isBlank(b && b.needs_input) && !((b && b.points) || []).length) return;
    out.push(subHeading(title));
    if (b && BASIS[b.basis]) out.push(para(`Basis: ${BASIS[b.basis]}.`, { size: 19, color: C.muted }));
    out.push(...textBlock(b));
    out.push(...inputBlock(b && b.needs_input));
  });
  out.push(...inputBlock(s.needs_input));
  return out;
}

const GTM_MODE_NOTES = {
  generate: "Drafted from the evidence in this plan. Every track is a recommendation for the account team to accept, edit, or reject, not a decision that has been made.",
  person: "The account team is writing this section. The prompts below are the questions each track needs answered.",
  custom: null,
};

function renderGtm(s) {
  const out = [];
  const mode = s.mode || (s.tracks && s.tracks.some((t) => t.objective) ? "generate" : null);
  const note = s.mode_note || GTM_MODE_NOTES[mode];
  if (!isBlank(note)) out.push(para(note, { size: 18, color: C.muted, after: 140 }));

  if (!isBlank(textOf(s.priority))) {
    out.push(subHeading("Where to spend first"));
    out.push(...textBlock(s.priority));
  }

  (s.tracks || []).forEach((t) => {
    out.push(subHeading(t.title || ""));
    if (!isBlank(t.definition)) out.push(para(t.definition, { size: 18, color: C.muted, after: 100 }));

    if (!isBlank(t.objective)) {
      out.push(runs([{ text: "Objective: ", bold: true, size: 19 }, { text: t.objective, size: 19 }], { after: 80 }));
    }
    if (!isBlank(t.why_now)) {
      out.push(runs([{ text: "Why now: ", bold: true, size: 19 }, { text: t.why_now, size: 19 }], { after: 80 }));
    }
    if ((t.plays || []).length) {
      out.push(para("Plays", { bold: true, size: 19, after: 40 }));
      t.plays.forEach((p) => out.push(bullet(typeof p === "string" ? p : p.text, { size: 19 })));
    }
    const endStop = (v) => String(v).trim().replace(/[.\s]+$/, "") + ".";
    const tail = [];
    if (!isBlank(t.owner)) tail.push(`Owner: ${endStop(t.owner)}`);
    if (!isBlank(t.exit_criterion)) tail.push(`Done when: ${endStop(t.exit_criterion)}`);
    if (tail.length) out.push(para(tail.join(" "), { size: 19, after: 80 }));

    out.push(...textBlock(t));
    if (!isBlank(t.recommendation)) {
      out.push(runs([
        { text: "Recommendation, for the account team to confirm: ", bold: true, size: 19 },
        { text: t.recommendation, size: 19 },
      ]));
      const sl = sourceLine(t.recommendation_source);
      if (sl) out.push(sl);
    } else {
      const sl = sourceLine(t.source);
      if (sl) out.push(sl);
    }
    out.push(...inputBlock(t.needs_input));
  });
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderNextSteps(s) {
  const out = [];
  const steps = s.steps || [];
  if (steps.length) {
    out.push(subHeading("Strategic next steps"));
    out.push(table(
      ["Step", "Opportunity", "Owner", "Target"],
      steps.map((st) => [st.text || "", st.opportunity || "Account wide", st.owner || "Not named", st.target || ""]),
      [4200, 1900, 1700, 1560],
    ));
    out.push(para("", { after: 120 }));
  }
  const MAP_NOTES = {
    aircover_skill: "Built with the mutual action plan skill. That file is the working artifact; the summary below is a snapshot as of this plan's date.",
    uploaded: "Supplied by the account team. That file is the working artifact; the summary below is a snapshot as of this plan's date.",
    deferred: "No mutual action plan is in place for this account. Creating one is itself a next step, and until it exists the milestones below are internal intent rather than a shared commitment with the customer.",
    custom: null,
  };
  const mapMode = s.map_mode;
  const mapNote = s.map_note || MAP_NOTES[mapMode];
  if (mapMode || !isBlank(s.map_link) || (s.map_status || []).length) {
    out.push(subHeading("Mutual action plan"));
    if (!isBlank(mapNote)) out.push(para(mapNote, { size: 18, color: C.muted, after: 120 }));
    if (!isBlank(s.map_link)) {
      out.push(new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({ text: "Plan document: ", font: FONT, size: 21, color: C.body }),
          new ExternalHyperlink({
            link: s.map_link,
            children: [new TextRun({ text: s.map_link, font: FONT, size: 21, color: C.heading, underline: {} })],
          }),
        ],
      }));
    }
    if ((s.map_status || []).length) {
      out.push(table(
        ["Milestone", "Owners", "Status"],
        s.map_status.map((m) => [m.milestone || "", m.owners || "", m.status || ""]),
        [4680, 2700, 1980],
      ));
      out.push(para("", { after: 120 }));
    }
  }
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderCompetitive(s) {
  const out = [];
  const comps = s.competitors || [];
  if (comps.length) {
    out.push(subHeading("Competitor presence"));
    out.push(table(
      ["Competitor", "Presence in the account", "Share of wallet", "Evidence"],
      comps.map((c) => [c.name || "", c.presence || "", c.share || "", c.evidence || ""]),
      [1800, 3000, 1560, 3000],
    ));
    out.push(para("", { after: 120 }));
  }
  if (!isBlank(textOf(s.differentiation))) {
    out.push(subHeading("Differentiation"));
    out.push(...textBlock(s.differentiation));
  }
  if ((s.objections || []).length) {
    out.push(subHeading("Open competitive objections"));
    s.objections.forEach((o) => {
      out.push(bullet(typeof o === "string" ? o : o.text));
      if (o && o.source) {
        const sl = sourceLine(o.source);
        if (sl) out.push(sl);
      }
    });
  }
  out.push(...inputBlock(s.needs_input));
  return out;
}

function renderCoverage(s) {
  const out = [];
  out.push(para("What this plan is built on, and where the evidence runs out.", { color: C.muted, size: 19 }));
  const opps = s.opportunities || [];
  if (opps.length) {
    out.push(subHeading("Meeting coverage by opportunity"));
    out.push(table(
      ["Opportunity", "Analyzed", "Held", "Most recent", "Gap"],
      opps.map((o) => [
        `${o.name || ""}${o.deal_key ? `\n${o.deal_key}` : ""}`,
        String(o.meetings_analyzed === undefined ? "" : o.meetings_analyzed),
        String(o.meetings_held === undefined ? "" : o.meetings_held),
        o.latest_meeting || "",
        o.gap_note || "",
      ]),
      [2700, 1100, 1000, 1560, 3000],
    ));
    out.push(para("", { after: 120 }));
  }
  if ((s.agents || []).length) {
    out.push(subHeading("Agents"));
    out.push(table(
      ["Agent", "Status", "Runs"],
      s.agents.map((a) => [a.name || "", a.status || "", String(a.runs === undefined ? "" : a.runs)]),
      [4680, 3000, 1680],
    ));
    out.push(para("", { after: 120 }));
  }
  if ((s.external_sources || []).length) {
    out.push(subHeading("External sources"));
    out.push(table(
      ["Source", "Publisher", "Published", "Retrieved"],
      s.external_sources.map((x) => [x.title || "", x.publisher || "", x.date || "", x.retrieved || ""]),
      [3800, 2400, 1580, 1580],
    ));
    out.push(para("", { after: 120 }));
  }
  if ((s.open_inputs || []).length) {
    out.push(subHeading("Open inputs"));
    out.push(para("Facts this plan needs that only the account team holds.", { size: 18, color: C.muted }));
    s.open_inputs.forEach((q) => out.push(bullet(q, { color: C.placeholder })));
  }
  return out;
}

const RENDERERS = {
  exec_summary: renderExecSummary,
  landscape: renderLandscape,
  stakeholders: renderStakeholders,
  opportunities_footprint: renderOpportunities,
  licenses: renderLicenses,
  gtm: renderGtm,
  next_steps_map: renderNextSteps,
  competitive: renderCompetitive,
  coverage: renderCoverage,
};

// ---------------------------------------------------------------- validation

const VAL = cfg.validation || {};
const BANNED = VAL.banned_scoring_strings || [];
// Placeholder strings from an account plan template. If one survives into a real plan, the run
// pasted example text instead of writing evidence. Configurable, because one install's trap is
// another install's legitimate subject matter.
const TEMPLATE_TRAPS = VAL.template_trap_strings || [];

/** Currency figures. Must end on a digit so trailing punctuation is not captured. */
const MONEY_RE = /\$[\d,]*\d(?:\.\d+)?[KMB]?/g;

function walkStrings(node, fn, path = "") {
  if (node === null || node === undefined) return;
  if (typeof node === "string") { fn(node, path); return; }
  if (Array.isArray(node)) { node.forEach((v, i) => walkStrings(v, fn, `${path}[${i}]`)); return; }
  if (typeof node === "object") {
    Object.keys(node).forEach((k) => walkStrings(node[k], fn, path ? `${path}.${k}` : k));
  }
}

function validate() {
  // never_blank sections
  (DOC.sections || []).forEach((sec) => {
    if (!sec.never_blank) return;
    const body = S[sec.id];
    if (!body || Object.keys(body).length === 0) {
      warn(`Section ${sec.number} (${sec.title}) is marked never_blank in config but has no content.`);
    }
  });

  // banned language and template traps
  walkStrings(S, (str, path) => {
    BANNED.forEach((b) => {
      if (str.toLowerCase().includes(b.toLowerCase())) warn(`Banned scoring language "${b}" at ${path}.`);
    });
    TEMPLATE_TRAPS.forEach((t) => {
      if (str.includes(t)) warn(`Outline example text "${t}" at ${path}. Replace with this account's own evidence or remove.`);
    });
  });

  // seller-centric SWOT weaknesses
  const vendorName = VENDOR;
  if (!vendorName) {
    warn("No selling org resolved. It should be detected at runtime from the internal side of the meeting "
       + "attendee split (SKILL.md step 1b) and written to meta.vendor. Without it the Executive Strategy "
       + "track renders untitled and the seller-centric SWOT check cannot run.");
  }
  if (VENDOR_DOMAIN && meta.domains && meta.domains.some((d) => String(d).toLowerCase() === VENDOR_DOMAIN.toLowerCase())) {
    warn(`The selling org's own domain (${VENDOR_DOMAIN}) is listed as an account domain. The vendor was `
       + "probably misdetected, or an internal meeting was treated as a customer one.");
  }
  const weaknesses = ((S.landscape || {}).swot || {}).weaknesses || [];
  weaknesses.forEach((w, i) => {
    const t = (w.text || "").toLowerCase();
    if (vendorName && t.includes(vendorName.toLowerCase())) {
      warn(`SWOT weakness ${i + 1} names the selling org. A weakness is a weakness of the customer's business.`);
    }
    if (/\b(we|us|our)\b/.test(t)) {
      warn(`SWOT weakness ${i + 1} is written from the seller's point of view.`);
    }
  });

  // hypotheses must not appear elsewhere
  const hyps = (S.landscape || {}).hypotheses || [];
  hyps.forEach((h) => {
    const key = (h.text || "").trim().toLowerCase().slice(0, 40);
    if (key.length < 12) return;
    walkStrings(S, (str, path) => {
      if (path.startsWith("landscape.hypotheses")) return;
      if (str.toLowerCase().includes(key)) {
        warn(`Hypothesis "${h.text.slice(0, 40)}..." also appears at ${path}. A hypothesis may not be stated as a finding.`);
      }
    });
  });

  // opportunity totals reconcile
  const oppSec = S.opportunities_footprint || {};
  const opps = oppSec.opportunities || [];
  const totals = oppSec.totals || {};
  if (opps.length && typeof totals.open_value === "number") {
    const sum = opps
      .filter((o) => !/closed/i.test(o.stage || ""))
      .reduce((a, o) => a + (typeof o.amount === "number" ? o.amount : 0), 0);
    if (sum && Math.abs(sum - totals.open_value) > 1) {
      warn(`Open value total (${totals.open_value}) does not equal the sum of open opportunity rows (${sum}).`);
    }
  }

  // prose must agree with the opportunity table. This is the numbers-reconcile check from
  // output_standard.md section 9, which cannot be done by eye on a document this long.
  const WORDNUM = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
  const openRows = opps.filter((o) => !/closed/i.test(o.stage || ""));
  if (openRows.length) {
    walkStrings(S, (str, path) => {
      if (path.startsWith("coverage.")) return;
      const re = /\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:open\s+)?opportunit(?:y|ies)\b/gi;
      // Strip currency figures first: "$56,000 open opportunity" must not read as "000 opportunities".
      const scan = str.replace(MONEY_RE, " ");
      let m;
      while ((m = re.exec(scan)) !== null) {
        const tok = m[1].toLowerCase();
        const n = WORDNUM[tok] !== undefined ? WORDNUM[tok] : parseInt(tok, 10);
        if (!isNaN(n) && n !== openRows.length) {
          warn(`Prose at ${path} says "${m[0]}" but the table carries ${openRows.length} open opportunit${openRows.length === 1 ? "y" : "ies"}.`);
        }
      }
    });
  }

  // money in the executive summary must trace to the opportunity table or the totals
  const known = new Set();
  const addMoney = (v) => { if (typeof v === "number") known.add("$" + v.toLocaleString("en-US")); };
  opps.forEach((o) => addMoney(o.amount));
  ["open_value", "closed_won_value"].forEach((k) => addMoney(totals[k]));
  walkStrings(S.exec_summary || {}, (str, path) => {
    (str.match(MONEY_RE) || []).forEach((fig) => {
      if (/[KMB]$/.test(fig)) return; // rounded externals like $4.1B are research figures, not CRM totals
      if (!known.has(fig)) warn(`Executive summary cites ${fig} at exec_summary.${path}, which matches no opportunity amount or total. Verify it reconciles.`);
    });
  });

  // manually added opportunities must be declared, counted, and never given call evidence
  const manualOpps = opps.filter((o) => o.manual);
  const covRows = ((S.coverage || {}).opportunities || []);
  manualOpps.forEach((o) => {
    const nm = (o.name || "").trim();
    if (!nm) { warn("A manual opportunity has no name. Name, value and stage are all optional, but a row with none of them carries nothing."); return; }
    const row = covRows.find((r) => (r.name || "").trim().toLowerCase() === nm.toLowerCase());
    if (!row) {
      warn(`Manual opportunity "${nm}" is missing from the appendix coverage table. It belongs there with `
         + "0 meetings analyzed, because zero evidence coverage on an open opportunity is a finding.");
    } else if (Number(row.meetings_analyzed) > 0) {
      warn(`Manual opportunity "${nm}" claims ${row.meetings_analyzed} meetings analyzed. It was added by hand `
         + "and has no Aircover deal record, so it can have none.");
    }
    if (!isBlank(o.deal_key)) {
      warn(`Manual opportunity "${nm}" carries a deal_key. A hand-added opportunity has no Aircover deal record.`);
    }
    ((S.next_steps_map || {}).steps || []).forEach((st) => {
      if ((st.opportunity || "").trim().toLowerCase() === nm.toLowerCase() && /\b20\d\d-\d\d-\d\d\b/.test(st.text || "")) {
        warn(`A next step for manual opportunity "${nm}" cites a call date. There is no call evidence for it.`);
      }
    });
  });
  if (manualOpps.length && openRows.length) {
    const anyOpenManual = manualOpps.some((o) => !/closed/i.test(o.stage || ""));
    if (anyOpenManual && isBlank(totals.open_value)) {
      warn("An open manual opportunity was added but totals.open_value is blank. Manual opportunities count in the totals.");
    }
  }

  // the strategic narrative must have been worked against the five value dimensions
  const nar = (S.exec_summary || {}).strategic_narrative || {};
  const dims = Array.isArray(nar.dimensions) ? nar.dimensions.filter((d) => !isBlank(d)) : [];
  if (!isBlank(textOf(nar)) && !dims.length) {
    warn("The strategic narrative has no `dimensions`. Work the five in SKILL.md step 8 (expansion headroom, "
       + "referenceability, logo and segment credibility, design partnership, strategic displacement) and record "
       + "each as evidenced, a recommendation, or INPUT NEEDED. Agent output covers only the first, so without "
       + "this the narrative defaults to deal mechanics and understates why the account matters.");
  }

  // freshness words must match the configured bands, not be used as loose adjectives
  const planDate = meta.date ? new Date(meta.date) : new Date();
  const dayGap = (d) => Math.round((planDate - new Date(d)) / 86400000);
  const bandFor = (n) => (n <= BANDS.current ? "current" : n <= BANDS.aging ? "aging" : "stale");
  ((S.stakeholders || {}).known || []).forEach((p) => {
    if (isBlank(p.last_touched)) return;
    const n = dayGap(p.last_touched);
    if (isNaN(n)) return;
    const actual = bandFor(n);
    const said = `${p.notes || ""} ${p.role_evidence || ""}`.toLowerCase();
    ["current", "aging", "stale"].forEach((word) => {
      if (new RegExp(`\\b${word}\\b`).test(said) && word !== actual) {
        warn(`${p.name || "A stakeholder"} was last touched ${p.last_touched}, which is ${n} days and bands as `
           + `"${actual}", but the text says "${word}". Freshness words are computed from `
           + "config.scope.freshness_bands_days, not chosen for emphasis.");
      }
    });
  });

  // coverage must not silently claim a census when it is a sample
  ((S.coverage || {}).opportunities || []).forEach((r) => {
    const a = Number(r.meetings_analyzed), h = Number(r.meetings_held);
    if (isNaN(a) || isNaN(h) || !h) return;
    if (a > h) warn(`Coverage row "${r.name || "?"}" analyzes ${a} meetings but records only ${h} held.`);
    if (a < h && isBlank(r.gap_note)) {
      warn(`Coverage row "${r.name || "?"}" shows ${h - a} meetings with no transcript and no gap_note. `
         + "Say how many gaps fall after the last transcript and how many sit inside the evidence window, "
         + "because interior gaps make the analyzed calls a sample of the period rather than a census.");
    }
  });

  // account team and customer stakeholders come from opposite sides of one attendee split
  const teamRows = ((S.stakeholders || {}).account_team || []);
  const stakeNames = new Set(((S.stakeholders || {}).known || [])
    .map((p) => (p.name || "").trim().toLowerCase()).filter(Boolean));
  teamRows.forEach((m) => {
    const nm = (m.name || "").trim();
    if (!nm) { warn("An account team row has no name."); return; }
    if (stakeNames.has(nm.toLowerCase())) {
      warn(`"${nm}" appears on the account team and in the customer stakeholder table. Those lists come from `
         + "opposite sides of the attendee split; one of the two is wrong.");
    }
  });
  if (teamRows.length) {
    const unowned = ((S.gtm || {}).tracks || []).filter((t) => /not named/i.test(t.owner || "")).length;
    if (unowned >= 3) {
      warn(`${unowned} GTM tracks say the owner is not named, but the account team lists ${teamRows.length} `
         + "people. Assign owners from that list, or say why none of them fit.");
    }
  }

  // use cases: selections must stay inside the configured catalogue
  const UC = (S.opportunities_footprint || {}).use_cases || {};
  const ucSel = UC.selected || [];
  const ucVocab = USE_CASES.vocabulary;
  if (USE_CASES.enabled !== false) {
    if (Array.isArray(ucVocab) && ucVocab.length) {
      const known = new Set(ucVocab.map((v) => String(v).trim().toLowerCase()));
      ucSel.forEach((v) => {
        if (!known.has(String(v).trim().toLowerCase())) {
          warn(`Use case "${v}" is not in use_cases.vocabulary. A list that accepts free text stops being `
             + "computable, so either add it to the vocabulary in config.json or drop it.");
        }
      });
    } else if (ucSel.length) {
      warn("Use cases are selected but use_cases.vocabulary is null, so the not-in-play half cannot be "
         + "computed and the section reports adoption without reporting whitespace.");
    }
    if (Array.isArray(ucVocab) && ucVocab.length && !ucSel.length) {
      warn(`A use case catalogue of ${ucVocab.length} entries is configured but nothing is selected, so `
         + "section 4 reports the whole catalogue as whitespace. That is right for a greenfield account "
         + "and wrong everywhere else, so confirm it rather than shipping it.");
    }
  }

  // role gaps: the account needs the second half of the stakeholder map, not just the first
  const rg = (S.stakeholders || {}).role_gaps || [];
  if (!rg.length && ((S.stakeholders || {}).known || []).length) {
    warn("stakeholders.role_gaps is empty. Every account has roles it needs and cannot name; an empty list "
       + "usually means the block was skipped rather than that coverage is complete.");
  }
  rg.forEach((g) => {
    if (isBlank(g.why_needed)) {
      warn(`Role gap "${g.role || "unnamed"}" has no why_needed. A role with no stated consequence is an `
         + "observation, not a coverage gap.");
    }
  });

  // budget basis must be declared, and inferred content must read as inferred
  const bc = (S.licenses || {}).budget_cycle || {};
  const bcText = `${textOf(bc)} ${((bc.points) || []).join(" ")}`.trim();
  if (bcText) {
    if (isBlank(bc.basis)) {
      warn("budget_cycle has content but no `basis`. Set evidenced, public, inferred, mixed, or input_needed, so "
         + "that a fiscal year end and a buying window derived from it are not printed in the same voice.");
    }
    if (["inferred", "mixed"].includes(bc.basis)
        && !/\b(inferred|convention|conventional|typically|usually|generally|assum)/i.test(bcText)) {
      warn("budget_cycle is marked inferred but nothing in the text reads as inferred. A buying window derived "
         + "from a fiscal year is a convention and must say so in the sentence, not only in a source line.");
    }
  }

  // external sources need a retrieval date
  ((S.coverage || {}).external_sources || []).forEach((x, i) => {
    if (isBlank(x.retrieved)) warn(`External source ${i + 1} ("${x.title || "untitled"}") has no retrieval date.`);
  });

  // stakeholder roles must be evidenced
  ((S.stakeholders || {}).known || []).forEach((p) => {
    if (/champion|blocker|detractor/i.test(p.role || "") && isBlank(p.role_evidence) && isBlank(p.notes)) {
      warn(`${p.name || "A stakeholder"} is marked ${p.role} with no evidence recorded.`);
    }
  });

  // SWOT entries need a source, and each quadrant needs some content
  const swotCfg = (cfg.research && cfg.research.swot) || {};
  const swot = (S.landscape || {}).swot || {};
  ["strengths", "weaknesses", "opportunities", "threats"].forEach((q) => {
    const entries = swot[q] || [];
    const min = swotCfg.min_entries_per_quadrant;
    if (swotCfg.enabled !== false && entries.length === 0) {
      warn(`SWOT ${q} is empty. Research it or state plainly that the research found nothing usable.`);
    } else if (min && entries.length > 0 && entries.length < min) {
      warn(`SWOT ${q} has ${entries.length} entr${entries.length === 1 ? "y" : "ies"}, under the configured minimum of ${min}.`);
    }
    if (swotCfg.require_source_per_entry === false) return;
    entries.forEach((e, i) => {
      if (isBlank(e.source)) warn(`SWOT ${q} entry ${i + 1} has no source. Every quadrant entry is researched or evidenced, never assumed.`);
    });
    const max = swotCfg.max_entries_per_quadrant;
    if (max && entries.length > max) warn(`SWOT ${q} has ${entries.length} entries, over the configured maximum of ${max}.`);
  });

  // GTM tracks: generated tracks must carry the full shape
  const gtm = S.gtm || {};
  if (gtm.mode === "generate") {
    (gtm.tracks || []).forEach((t) => {
      const label = t.title || "a track";
      const hasAny = !isBlank(t.objective) || !isBlank(t.why_now) || (t.plays || []).length;
      if (!hasAny) return; // an unevidenced track rendered as INPUT NEEDED is a valid outcome
      ["objective", "why_now", "exit_criterion"].forEach((f) => {
        if (isBlank(t[f])) warn(`GTM track "${label}" is generated but has no ${f.replace("_", " ")}.`);
      });
      if (!(t.plays || []).length) warn(`GTM track "${label}" is generated but has no plays.`);
      if (isBlank(t.owner)) warn(`GTM track "${label}" has no owner. Use "Not named" and make naming them the first play.`);
    });
    if (isBlank(textOf(gtm.priority))) {
      warn("GTM strategy was generated with no ranking across tracks. Six equally weighted tracks is a list, not a strategy.");
    }
  } else if (gtm.tracks && gtm.tracks.length && isBlank(gtm.mode)) {
    warn("GTM section has tracks but no mode. Ask the person whether to generate the strategy, write it themselves, or something else.");
  }

  // MAP routing
  const ns = S.next_steps_map || {};
  if (Object.keys(ns).length && isBlank(ns.map_mode)) {
    warn("No mutual action plan route recorded. Ask the person: build it with the MAP skill, upload their own, skip for now, or something else.");
  }
  if (ns.map_mode === "uploaded" && isBlank(ns.map_link) && !(ns.map_status || []).length) {
    warn("MAP route is 'uploaded' but no link or milestone summary was supplied.");
  }

  // exec summary present
  if (isBlank(textOf((S.exec_summary || {}).relationship_health))) {
    warn("Relationship health is empty. It is derivable from opportunity count, value, and meeting recency, and must never be blank.");
  }
}

// ---------------------------------------------------------------- at a glance

/** The first n sentences of a block of prose, for the one-page summary. */
function firstSentences(text, n) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  if (!t) return "";
  const parts = t.match(/[^.!?]+[.!?]+(\s|$)/g) || [t];
  return parts.slice(0, n).join("").trim();
}

function coverBlock() {
  const subBits = [];
  if (meta.date) subBits.push(meta.date);
  // The cover carries a name, not the reasoning behind it; that stays in section 1.
  if (meta.account_owner) subBits.push(`Owner ${String(meta.account_owner).split(/\s*[(;.]/)[0]}`);
  if (meta.author) subBits.push(`Prepared by ${meta.author}`);
  if ((meta.domains || []).length) subBits.push(meta.domains.join(", "));
  const kids = [
    para("ACCOUNT PLAN", { size: 17, bold: true, color: C.accent, after: 60 }),
    para(meta.account || "Account", { size: 52, bold: true, color: C.title_text, after: 80 }),
  ];
  if (subBits.length) kids.push(para(subBits.join("   |   "), { size: 18, color: C.title_sub, after: 0 }));
  return new Table({
    columnWidths: [CONTENT_WIDTH],
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    borders: NO_BORDERS,
    rows: [new TableRow({ children: [cell(kids, CONTENT_WIDTH, {
      fill: C.title_fill, margins: { top: 300, bottom: 300, left: 360, right: 360 },
      borders: { top: { style: BorderStyle.SINGLE, size: 36, color: C.accent },
                 bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER },
    })] })],
  });
}

/**
 * One page a reader can act on without opening the rest: the snapshot, where to
 * spend first, the open opportunities, the people who matter and the next steps.
 * Everything is read from the same sections the body renders, never restated.
 */
function atAGlance() {
  const out = [];
  const ex = S.exec_summary || {};
  out.push(para("", { after: 160 }));
  out.push(...tiles(ex.snapshot_metrics));

  const g = S.gtm || {};
  const lead = firstSentences(textOf(g.priority), 2)
    || firstSentences(textOf(ex.strategic_narrative), 2);
  if (lead) {
    out.push(kicker(textOf(g.priority) ? "Where to spend first" : "Why this account matters"));
    out.push(callout([para(lead, { size: 21, color: C.heading, after: 0 })]));
  }

  // Deal records with no amount and no close date are listed in section 4 but are not
  // open opportunities a reader should act on, so the summary leaves them out and says so.
  const allOpps = ((S.opportunities_footprint || {}).opportunities || []);
  const live = allOpps.filter((o) => !isBlank(o.amount) || !isBlank(o.close_date));
  const opps = live.length ? live : allOpps;
  if (opps.length) {
    out.push(kicker("Open opportunities"));
    out.push(table(["Opportunity", "Stage", "Amount", "Close"],
      opps.map((o) => [{ text: o.name || "", bold: true, color: C.heading }, o.stage || "unknown",
                       money(o.amount), o.close_date || ""]),
      [4360, 2200, 1500, 1300]));
    const hidden = allOpps.length - opps.length;
    if (hidden > 0) {
      out.push(para(`Plus ${hidden} deal record${hidden > 1 ? "s" : ""} with no amount or close date, listed in the opportunities section.`,
        { size: 16, color: C.muted, after: 0 }));
    }
  }

  const known = ((S.stakeholders || {}).known || []).slice(0, 4);
  if (known.length) {
    out.push(kicker("Key people"));
    out.push(table(["Name", "Role", "Last touched"],
      known.map((p) => {
        const band = freshnessBand(p.last_touched);
        return [{ text: `${p.name || ""}${p.title ? `\n${p.title}` : ""}`, color: C.heading },
                p.role || "", { text: `${p.last_touched || "unknown"}  ${band.label}`, color: band.color }];
      }),
      [4360, 2600, 2400]));
  }

  const steps = ((S.next_steps_map || {}).steps || []).slice(0, 3);
  if (steps.length) {
    out.push(kicker("Next steps"));
    out.push(table(["#", "Step", "Owner", "Target"],
      steps.map((st, i) => [{ text: String(i + 1), bold: true, color: C.accent }, st.text || "",
                            st.owner || "Not named", st.target || ""]),
      [500, 5160, 1700, 2000]));
  }
  return out;
}

// ---------------------------------------------------------------- build

function build() {
  validate();

  const children = [];

  children.push(coverBlock());
  if (GLANCE) {
    children.push(...atAGlance());
    children.push(new Paragraph({ children: [new PageBreak()] }));
  } else {
    children.push(para("", { after: 200 }));
  }

  (DOC.sections || []).forEach((sec) => {
    const body = S[sec.id];
    const renderer = RENDERERS[sec.id];
    if (!renderer) return;
    if (!body || Object.keys(body).length === 0) {
      if (!sec.never_blank) return;
    }
    if (sec.id === "coverage") children.push(new Paragraph({ children: [new PageBreak()] }));
    children.push(sectionHeading(sec.number, sec.title));
    const rendered = renderer(body || {});
    if (!rendered.length) {
      children.push(inputNeeded("No content supplied for this section."));
    } else {
      children.push(...rendered);
    }
  });

  const doc = new Document({
    creator: meta.author || (cfg.vendor && cfg.vendor.name) || "Account Plan",
    title: `Account Plan - ${meta.account || ""}`,
    numbering: {
      config: [{
        reference: "ap-bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 360, hanging: 180 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 180 } } } },
        ],
      }],
    },
    sections: [{
      properties: {
        page: { size: PAGE, margin: MARGIN },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({
              text: `${meta.account || ""} Account Plan${meta.date ? `  |  ${meta.date}` : ""}`,
              font: FONT, size: 16, color: C.muted,
            })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: C.muted })],
          })],
        }),
      },
      children,
    }],
  });

  Packer.toBuffer(doc).then((buf) => {
    fs.writeFileSync(outFile, buf);
    console.log(`Wrote ${outFile}`);
    if (warnings.length) {
      console.error(`\n${warnings.length} consistency warning(s):`);
      warnings.forEach((w) => console.error(`  - ${w}`));
      if (strict) process.exit(1);
    } else {
      console.log("Consistency checks passed.");
    }
  }).catch((e) => {
    console.error("Failed to build document:", e);
    process.exit(2);
  });
}

build();
