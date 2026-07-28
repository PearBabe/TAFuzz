import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "file:///C:/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const base = "analysis/protocol_fuzzing_study/independent_reanalysis/sip_kamailio";
const outPath = path.join(base, "human_review_packet.xlsx");
const previewPath = path.join(base, "human_review_packet_summary_preview.png");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      quoted = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (c !== "\r") {
      field += c;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [header, ...body] = rows.filter((r) => r.some((v) => v !== ""));
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""])));
}

function sheetWrite(sheet, matrix) {
  if (!matrix.length) return;
  sheet.getRangeByIndexes(0, 0, matrix.length, matrix[0].length).values = matrix;
  const header = sheet.getRangeByIndexes(0, 0, 1, matrix[0].length);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.wrapText = true;
  const used = sheet.getUsedRange();
  used.format.wrapText = true;
  used.format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
  used.format.autofitColumns();
  sheet.freezePanes.freezeRows(1);
}

function objectsToMatrix(rows, fields) {
  return [fields, ...rows.map((r) => fields.map((f) => {
    const v = r[f];
    if (Array.isArray(v)) return v.join("|");
    if (v && typeof v === "object") return JSON.stringify(v);
    return v ?? "";
  }))];
}

const props = JSON.parse(await fs.readFile(path.join(base, "mitl_property_catalog.json"), "utf8"));
const hooks = parseCsv(await fs.readFile(path.join(base, "instrumentation_hooks.csv"), "utf8"));
const validation = parseCsv(await fs.readFile(path.join(base, "formula_validation_summary.csv"), "utf8"));
const sourceLines = parseCsv(await fs.readFile(path.join(base, "source_line_verification.csv"), "utf8"));
const evidenceYaml = await fs.readFile(path.join(base, "evidence_manifest.yaml"), "utf8");

const passCount = validation.filter((r) =>
  r.build_status === "PASS" &&
  r.positive_symbolic === "PASS" &&
  r.negative_symbolic === "PASS" &&
  r.positive_concrete === "PASS" &&
  r.negative_concrete === "PASS" &&
  r.symbolic_concrete_consistent === "YES"
).length;

const apToProps = new Map();
for (const p of props) {
  for (const ap of p.aps) {
    if (!apToProps.has(ap)) apToProps.set(ap, []);
    apToProps.get(ap).push(p.pid);
  }
}

const evidenceRows = [];
let cur = null;
for (const line of evidenceYaml.split(/\r?\n/)) {
  const id = line.match(/^\s+- id: (.*)$/);
  if (id) {
    if (cur) evidenceRows.push(cur);
    cur = { id: JSON.parse(id[1]), source_type: "", url: "", local_path: "", sha256: "", access_date: "" };
    continue;
  }
  if (!cur) continue;
  const m = line.match(/^\s+([a-z_]+): (.*)$/);
  if (m) {
    let value = m[2];
    try { value = JSON.parse(value); } catch {}
    cur[m[1]] = value;
  }
}
if (cur) evidenceRows.push(cur);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
sheetWrite(summary, [
  ["Item", "Value", "Notes"],
  ["Protocol/SUT", "SIP / Kamailio", "Single-track Kamailio/ProfuzzBench reanalysis"],
  ["Kamailio commit", "2648eb330b133a20f1398d59a28c53532106cad3", "Fixed source mapping commit"],
  ["ProfuzzBench commit", "8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074", "SIP/Kamailio subject"],
  ["Main properties", props.length, "All remain PENDING human review"],
  ["Formula validation", `${passCount}/${validation.length} PASS`, "flatten + finite; positive/negative; symbolic/concrete consistency"],
  ["Timer caveat", "PFB-COMPAT disables timer processes", "Timer-expiry claims require MITL-VALID reference profile"],
  ["Preferred third baseline", "NSFuzz (CONDITIONAL)", "Download/hash/audit artifact before main claim"],
  ["Excluded baseline", "SGFuzz", "No fair Kamailio/SIP UDP/fork-compatible public path"],
]);

const propFields = [
  "pid", "category", "role", "requirement", "strength", "rfc", "section",
  "time_bound_ms", "time_source", "formula", "aps", "hooks", "aux_hooks",
  "correlation_key", "observability", "oracle_value", "confidence", "caveat",
  "review_question"
];
sheetWrite(workbook.worksheets.add("Properties"), objectsToMatrix(props, propFields));

const apRows = [...apToProps.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([ap, pids]) => ({
  ap,
  property_ids: pids.join("|"),
  dynamic_id_policy: "metadata only; not in AP name",
}));
sheetWrite(workbook.worksheets.add("AP_Map"), objectsToMatrix(apRows, ["ap", "property_ids", "dynamic_id_policy"]));

sheetWrite(workbook.worksheets.add("Hooks"), objectsToMatrix(hooks, [
  "hook_id", "file", "function", "line", "phase", "event_type", "emits", "payload", "overhead", "notes", "source_url"
]));

sheetWrite(workbook.worksheets.add("Validation"), objectsToMatrix(validation, [
  "property_id", "build_status", "positive_symbolic", "negative_symbolic",
  "positive_concrete", "negative_concrete", "symbolic_concrete_consistent",
  "positive_locations", "positive_edges", "negative_locations", "negative_edges",
  "proposition_order"
]));

sheetWrite(workbook.worksheets.add("Source_Lines"), objectsToMatrix(sourceLines, [
  "hook_id", "file", "line", "status", "line_text", "function_or_symbol", "source_url"
]));

const decisions = props.map((p) => ({
  property_id: p.pid,
  decision: "PENDING",
  allowed_statuses: "APPROVE_AS_CLAIMED|APPROVE_WITH_CAVEAT|REJECT_OR_FIX|DEFER_TO_V2|KEEP_EXCLUDED",
  reviewer_notes: "",
  question: p.review_question,
}));
sheetWrite(workbook.worksheets.add("Review_Decisions"), objectsToMatrix(decisions, [
  "property_id", "decision", "allowed_statuses", "reviewer_notes", "question"
]));

sheetWrite(workbook.worksheets.add("Evidence"), objectsToMatrix(evidenceRows, [
  "id", "source_type", "url", "local_path", "sha256", "access_date"
]));

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outPath);
const preview = await workbook.render({ sheetName: "Summary", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const inspect = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 8000, tableMaxRows: 4, tableMaxCols: 5 });
await fs.writeFile(path.join(base, "human_review_packet.inspect.txt"), String(inspect), "utf8");
console.log(`Wrote ${outPath}`);
console.log(`Wrote ${previewPath}`);
