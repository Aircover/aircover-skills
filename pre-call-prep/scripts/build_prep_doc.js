#!/usr/bin/env node
/**
 * build_prep_doc.js - Generate a pre-call prep .docx from a structured JSON file.
 *
 * Usage:
 *   node build_prep_doc.js --input prep_data.json --out "Pre-Call_Prep_Acme_Jun18.docx"
 *
 * Input JSON format: see the SKILL.md for the full schema.
 * Requires: npm install -g docx
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink,
  HeadingLevel, BorderStyle, WidthType, ShadingType, PageBreak,
  TabStopType, TabStopPosition
} = require("docx");

// --- CLI ---
const args = process.argv.slice(2);
let inputFile, outFile;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--input" && args[i + 1]) inputFile = args[++i];
  if (args[i] === "--out" && args[i + 1]) outFile = args[++i];
}
if (!inputFile || !outFile) {
  console.error("Usage: node build_prep_doc.js --input prep_data.json --out output.docx");
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(inputFile, "utf-8"));

// --- Colors ---
const TEAL = "1F6F8B";
const DARK_GREY = "333333";
const MED_GREY = "666666";
const LIGHT_GREY = "F2F2F2";
const BORDER_GREY = "CCCCCC";
const WHITE = "FFFFFF";

// --- Helpers ---
const border = { style: BorderStyle.SINGLE, size: 1, color: BORDER_GREY };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0 };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function textRun(text, opts = {}) {
  return new TextRun({
    text,
    font: "Calibri",
    size: opts.size || 20, // 10pt default
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || DARK_GREY,
    ...(opts.underline ? { underline: { type: "single" } } : {}),
  });
}

function heading(text, level) {
  const sizes = { 1: 28, 2: 24, 3: 22 };
  return new Paragraph({
    spacing: { before: level === 1 ? 300 : 200, after: 120 },
    children: [
      textRun(text, { size: sizes[level] || 22, bold: true, color: TEAL }),
    ],
  });
}

function bodyPara(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.afterSpacing || 80 },
    children: [textRun(text, opts)],
  });
}

function hrule() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: {
      bottom: { style: BorderStyle.SINGLE, size: 6, color: BORDER_GREY, space: 1 },
    },
    children: [],
  });
}

function checkboxItem(text, checked = false) {
  const prefix = checked ? "\u2611 " : "\u2610 ";
  return new Paragraph({
    spacing: { after: 40 },
    indent: { left: 360 },
    children: [textRun(prefix + text, { size: 20 })],
  });
}

// --- Build sections ---
const children = [];

// ============================================================
// TITLE BLOCK
// ============================================================
const attendeeStr = (data.attendees || [])
  .map((a) => {
    let s = `**${a.name}**`;
    if (a.title) s += ` (${a.title})`;
    return s;
  })
  .join(" + ");

// Company + date line (title, then date)
children.push(
  new Paragraph({
    spacing: { after: 60 },
    children: [
      textRun(`${data.company} Pre-Call Prep`, { size: 32, bold: true, color: TEAL }),
    ],
  })
);
children.push(
  new Paragraph({
    spacing: { after: 60 },
    children: [
      textRun(data.meeting_date || "", { size: 22, color: MED_GREY }),
    ],
  })
);

// Attendees + call number
const attendeeRuns = [];
(data.attendees || []).forEach((a, i) => {
  if (i > 0) attendeeRuns.push(textRun(" + ", { color: MED_GREY }));
  attendeeRuns.push(textRun(a.name, { bold: true }));
  if (a.title) attendeeRuns.push(textRun(` (${a.title})`, { color: MED_GREY }));
});
if (data.call_number) {
  attendeeRuns.push(textRun(` | Call #${data.call_number}`, { color: MED_GREY }));
}
children.push(new Paragraph({ spacing: { after: 120 }, children: attendeeRuns }));

// ============================================================
// DEAL SNAPSHOT TABLE
// ============================================================
if (data.deal) {
  const dealRows = [];
  // Header row
  dealRows.push(
    new TableRow({
      children: ["Opp Amount", "Close Date", "Stage"].map(
        (label) =>
          new TableCell({
            borders,
            width: { size: 3120, type: WidthType.DXA },
            shading: { fill: LIGHT_GREY, type: ShadingType.CLEAR },
            margins: cellMargins,
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [textRun(label, { bold: true, size: 18 })],
              }),
            ],
          })
      ),
    })
  );
  // Data row
  dealRows.push(
    new TableRow({
      children: [
        data.deal.amount || "",
        data.deal.close_date || "",
        data.deal.stage || "",
      ].map(
        (val) =>
          new TableCell({
            borders,
            width: { size: 3120, type: WidthType.DXA },
            margins: cellMargins,
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [textRun(val, { size: 20 })],
              }),
            ],
          })
      ),
    })
  );
  children.push(
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [3120, 3120, 3120],
      rows: dealRows,
    })
  );
}

children.push(hrule());

// ============================================================
// OPEN ACTION ITEMS
// ============================================================
if (data.action_items) {
  children.push(heading("Open Action Items", 2));

  const groups = [
    { key: "ours", label: "Ours:" },
    { key: "theirs", label: "Theirs:" },
    { key: "joint", label: "Joint:" },
  ];
  for (const g of groups) {
    const items = data.action_items[g.key];
    if (items && items.length > 0) {
      children.push(
        new Paragraph({
          spacing: { before: 100, after: 40 },
          children: [textRun(g.label, { bold: true })],
        })
      );
      for (const item of items) {
        const checked = typeof item === "object" ? item.done : false;
        const text = typeof item === "object" ? item.text : item;
        children.push(checkboxItem(text, checked));
      }
    }
  }
  children.push(hrule());
}

// ============================================================
// ACCOUNT HIERARCHY
// ============================================================
if (data.account_hierarchy) {
  children.push(heading("Account Hierarchy", 2));
  // Render as monospaced lines to preserve indentation
  const lines = data.account_hierarchy.split("\n");
  for (const line of lines) {
    if (line.trim() === "") continue;
    children.push(
      new Paragraph({
        spacing: { after: 20 },
        children: [
          new TextRun({
            text: line,
            font: "Consolas",
            size: 18,
            color: DARK_GREY,
          }),
        ],
      })
    );
  }
  children.push(hrule());
}

// ============================================================
// WHAT MATTERS MOST TODAY
// ============================================================
if (data.what_matters) {
  children.push(heading("What Matters Most Today", 2));
  children.push(bodyPara(data.what_matters, { afterSpacing: 120 }));
  children.push(hrule());
}

// ============================================================
// CONTACT PRIORITIES
// ============================================================
if (data.contact_priorities && data.contact_priorities.length > 0) {
  for (const contact of data.contact_priorities) {
    children.push(heading(`${contact.name}'s Priorities`, 2));
    if (contact.priorities && contact.priorities.length > 0) {
      for (const p of contact.priorities) {
        children.push(
          new Paragraph({
            spacing: { after: 40 },
            indent: { left: 360 },
            children: [
              textRun("\u2022 ", { color: TEAL }),
              textRun(p),
            ],
          })
        );
      }
    }
  }
  children.push(hrule());
}

// ============================================================
// LANDMINES
// ============================================================
if (data.landmines && data.landmines.length > 0) {
  children.push(heading("Landmines", 2));
  for (const lm of data.landmines) {
    children.push(
      new Paragraph({
        spacing: { after: 60 },
        indent: { left: 360 },
        children: [
          textRun(`${lm.label}: `, { bold: true }),
          textRun(lm.detail),
        ],
      })
    );
  }
  children.push(hrule());
}

// ============================================================
// OBJECTIVES FOR THIS CALL
// ============================================================
if (data.objectives && data.objectives.length > 0) {
  children.push(heading("Objectives for This Call", 2));
  data.objectives.forEach((obj, i) => {
    children.push(
      new Paragraph({
        spacing: { after: 50 },
        indent: { left: 360 },
        children: [
          textRun(`${i + 1}. `, { bold: true, color: TEAL }),
          textRun(obj),
        ],
      })
    );
  });
  children.push(hrule());
}

// ============================================================
// SUCCESS = END OF CALL
// ============================================================
if (data.success_criteria && data.success_criteria.length > 0) {
  children.push(heading("Success = End of Call", 2));
  for (const sc of data.success_criteria) {
    children.push(checkboxItem(sc, false));
  }
}

// ============================================================
// MEETING LINKS (footer-style, if meeting_ids provided)
// ============================================================
if (data.meeting_links && data.meeting_links.length > 0) {
  children.push(hrule());
  children.push(
    new Paragraph({
      spacing: { before: 80, after: 40 },
      children: [textRun("Meeting Links", { size: 18, bold: true, color: MED_GREY })],
    })
  );
  for (const ml of data.meeting_links) {
    children.push(
      new Paragraph({
        spacing: { after: 30 },
        children: [
          new ExternalHyperlink({
            children: [
              new TextRun({
                text: ml.label,
                font: "Calibri",
                size: 18,
                color: TEAL,
                underline: { type: "single" },
              }),
            ],
            link: ml.url,
          }),
        ],
      })
    );
  }
}

// ============================================================
// BUILD DOCUMENT
// ============================================================
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: "Calibri", size: 20 },
      },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, right: 1260, bottom: 1080, left: 1260 },
        },
      },
      children,
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outFile, buffer);
  console.log("Wrote", outFile);
});
