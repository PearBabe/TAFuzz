import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "file:///C:/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const base = path.dirname(fileURLToPath(import.meta.url));
const outPath = path.join(base, "human_review_packet.xlsx");
const previewDir = path.join(base, "workbook_preview");
const properties = JSON.parse(await fs.readFile(path.join(base, "mitl_property_catalog.json"), "utf8"));
const evidenceDoc = JSON.parse(await fs.readFile(path.join(base, "evidence_manifest.yaml"), "utf8"));

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ""; }
    else if (c === '\n') { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

const scores = parseCsv((await fs.readFile(path.join(base, "protocol_scorecard.csv"), "utf8")).replace(/^\uFEFF/, ""));
const baselines = parseCsv((await fs.readFile(path.join(base, "baseline_artifact_matrix.csv"), "utf8")).replace(/^\uFEFF/, ""));
const hooks = parseCsv((await fs.readFile(path.join(base, "instrumentation_hooks.csv"), "utf8")).replace(/^\uFEFF/, ""));

const wb = Workbook.create();
const navy = "#17365D", teal = "#0F6B78", light = "#EAF2F8", pale = "#E2F0D9", amber = "#FFF2CC", red = "#FCE4D6", grid = "#D9E2F3";
const sheetNames = ["Read Me", "Decision Summary", "Protocol Scores", "Properties", "Source Hooks", "Validation", "Baselines", "Evidence", "Review Signoff"];
for (const sheetName of sheetNames) wb.worksheets.add(sheetName);

function title(sheet, text, endCol) {
  sheet.showGridLines = false;
  const r = sheet.getRange(`A1:${endCol}2`);
  r.merge();
  r.values = [[text]];
  r.format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 18 }, verticalAlignment: "center", horizontalAlignment: "left" };
  r.format.rowHeight = 28;
}

function header(range) {
  range.format = { fill: teal, font: { bold: true, color: "#FFFFFF" }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: grid } };
  range.format.rowHeight = 30;
}

function body(range) {
  range.format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: grid } };
}

function setWidths(sheet, widths) {
  widths.forEach(([col, width]) => { sheet.getRange(`${col}:${col}`).format.columnWidth = width; });
}

// README / decision gate.
{
  const s = wb.worksheets.getItem("Read Me");
  title(s, "SIP MITL 人工审核包 — 研究阶段门禁", "H");
  const rows = [
    ["当前结论", "首选 SIP 事务层；主 SUT=Kamailio；benchmark=ProFuzzBench；20/20 公式机器验证通过。"],
    ["重要限制", "本工作簿不是批准记录。Review Signoff 页所有条目初始为 PENDING；未签字不得实现或写入论文主张。"],
    ["统一语义", "pointwise timed word；绝对整数毫秒；按事务关联后投影；缺失 AP=false；finite + flatten。"],
    ["时间常数", "T1=500ms，T2=4000ms，T4=5000ms，64*T1=32000ms；Timer C 要求严格 >180000ms。"],
    ["审核状态", "APPROVE_AS_CLAIMED / APPROVE_WITH_CAVEAT / REJECT_OR_FIX / DEFER_TO_V2 / KEEP_EXCLUDED"],
    ["建议顺序", "先审 Decision Summary，再逐条审 Properties 与 Source Hooks，最后在 Review Signoff 填状态、姓名、日期与理由。"],
    ["V2 排除", "RFC 4320 的 E→T2/100 Trying 与 RFC 6026 Timer L/M 尚未进入 20 条主目录；原因见 semantic_exclusions.md。"],
  ];
  s.getRange("A4:B10").values = rows;
  s.getRange("A4:A10").format = { fill: light, font: { bold: true, color: navy }, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: grid } };
  body(s.getRange("B4:B10"));
  s.getRange("A12:H12").merge();
  s.getRange("A12").values = [["机器验证摘要"]];
  s.getRange("A12:H12").format = { fill: teal, font: { bold: true, color: "#FFFFFF" } };
  s.getRange("A13:B17").values = [
    ["主性质数", properties.length], ["构造通过", properties.filter(p => p.validation_build_ok).length],
    ["正反 oracle 通过", properties.filter(p => p.validation_expected_oracle_ok).length],
    ["symbolic/concrete 一致", properties.filter(p => p.validation_symbolic_concrete_consistent).length],
    ["人工已批准", 0],
  ];
  body(s.getRange("A13:B17"));
  s.getRange("A13:A17").format.fill = light;
  s.getRange("A13:A17").format.font = { bold: true, color: navy };
  setWidths(s, [["A", 24], ["B", 105], ["C", 14], ["D", 14], ["E", 14], ["F", 14], ["G", 14], ["H", 14]]);
}

// Decision summary with formulas linked to signoff.
{
  const s = wb.worksheets.getItem("Decision Summary");
  title(s, "进入实现前的决策总览", "H");
  s.getRange("A4:D4").values = [["门禁", "现状", "证据", "人工决定"]]; header(s.getRange("A4:D4"));
  const gates = [
    ["CCFA 身份/操作性定义", "未定位唯一 CCFA；采用 stateful coverage-guided 操作性定义", "ccfa_identity_audit.md", "PENDING"],
    ["协议硬门", "SIP 唯一通过量表+同 SUT 三 baseline 路径", "protocol_scorecard.csv", "PENDING"],
    ["20 条规范锚点", "20/20 RFC 3261 section + fixed commit hook", "Properties / Source Hooks", "PENDING"],
    ["公式构造", "20/20 PASS", "Validation", "PENDING"],
    ["正反 trace", "20/20 oracle PASS", "Validation", "PENDING"],
    ["实验公平性", "AFLnwe/AFLNet/StateAFL；24h×4 full", "Baselines", "PENDING"],
    ["Timer C 严格边界", "RFC >180000ms；Kamailio 默认 180000ms，存在待审偏差", "SIP-TX-20", "PENDING"],
  ];
  s.getRange("A5:D11").values = gates; body(s.getRange("A5:D11"));
  s.getRange("D5:D11").dataValidation = { rule: { type: "list", values: ["PENDING", "APPROVE_AS_CLAIMED", "APPROVE_WITH_CAVEAT", "REJECT_OR_FIX", "DEFER_TO_V2", "KEEP_EXCLUDED"] } };
  s.getRange("A13:B18").values = [
    ["性质审批完成数", null], ["APPROVE_AS_CLAIMED", null], ["APPROVE_WITH_CAVEAT", null],
    ["REJECT_OR_FIX", null], ["DEFER_TO_V2", null], ["KEEP_EXCLUDED", null],
  ];
  s.getRange("B13").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"<>PENDING\")"]];
  s.getRange("B14").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"APPROVE_AS_CLAIMED\")"]];
  s.getRange("B15").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"APPROVE_WITH_CAVEAT\")"]];
  s.getRange("B16").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"REJECT_OR_FIX\")"]];
  s.getRange("B17").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"DEFER_TO_V2\")"]];
  s.getRange("B18").formulas = [["=COUNTIF('Review Signoff'!E5:E24,\"KEEP_EXCLUDED\")"]];
  body(s.getRange("A13:B18")); s.getRange("A13:A18").format.fill = light; s.getRange("A13:A18").format.font = { bold: true, color: navy };
  s.getRange("F13:H16").values = [["实施门状态", null, null], ["条件", "20 条均完成审核，且无 REJECT_OR_FIX", null], ["当前", "BLOCKED_FOR_HUMAN_REVIEW", null], ["下一步", "用户逐条签字后再实现 harness", null]];
  s.getRange("F13:H13").merge(); s.getRange("F13:H13").format = { fill: amber, font: { bold: true, color: navy } };
  body(s.getRange("F14:H16"));
  setWidths(s, [["A", 30], ["B", 55], ["C", 30], ["D", 24], ["E", 4], ["F", 22], ["G", 36], ["H", 16]]);
  s.freezePanes.freezeRows(4);
}

// Protocol scorecard.
{
  const s = wb.worksheets.getItem("Protocol Scores"); title(s, "协议候选评分（硬门优先于总分）", "J");
  s.getRangeByIndexes(3, 0, scores.length, scores[0].length).values = scores;
  header(s.getRangeByIndexes(3, 0, 1, scores[0].length)); body(s.getRangeByIndexes(4, 0, scores.length - 1, scores[0].length));
  s.getRange(`H5:H${scores.length + 3}`).conditionalFormats.add("colorScale", { colors: ["#F8696B", "#FFEB84", "#63BE7B"] });
  setWidths(s, [["A", 16], ["B", 18], ["C", 18], ["D", 14], ["E", 14], ["F", 14], ["G", 14], ["H", 12], ["I", 22], ["J", 58]]);
  s.freezePanes.freezeRows(4);
}

// Core property review table.
{
  const s = wb.worksheets.getItem("Properties"); title(s, "20 条 SIP MITL 主性质", "R");
  const headers = ["ID", "Title", "RFC §", "Strength", "Requirement", "Time ms", "MightyPPL", "APs", "Semantics", "Source", "Symbol", "Lines", "Observability", "Confidence", "Build", "+/- Oracle", "S/C", "Review question"];
  s.getRange("A4:R4").values = [headers]; header(s.getRange("A4:R4"));
  const rows = properties.map(p => [p.id, p.title, p.standard_section, p.normative_strength, p.natural_language, p.time_value_ms,
    p.mightyppl_formula, p.atomic_propositions.join(", "), p.pointwise_semantics, p.source_path, p.source_symbol, p.source_lines,
    p.observability, p.confidence, p.validation_build_ok ? "PASS" : "FAIL", p.validation_expected_oracle_ok ? "PASS" : "FAIL",
    p.validation_symbolic_concrete_consistent ? "PASS" : "FAIL", p.review_question]);
  s.getRange(`A5:R${rows.length + 4}`).values = rows; body(s.getRange(`A5:R${rows.length + 4}`));
  s.getRange(`O5:Q${rows.length + 4}`).conditionalFormats.add("containsText", { text: "PASS", format: { fill: pale, font: { color: "#006100", bold: true } } });
  setWidths(s, [["A", 14], ["B", 34], ["C", 10], ["D", 14], ["E", 58], ["F", 14], ["G", 72], ["H", 44], ["I", 35], ["J", 42], ["K", 30], ["L", 12], ["M", 14], ["N", 12], ["O", 10], ["P", 12], ["Q", 9], ["R", 58]]);
  s.freezePanes.freezeRows(4); s.freezePanes.freezeColumns(2);
}

// Source hook map.
{
  const s = wb.worksheets.getItem("Source Hooks"); title(s, "固定提交源码插桩位置", "I");
  s.getRangeByIndexes(3, 0, hooks.length, hooks[0].length).values = hooks;
  header(s.getRangeByIndexes(3, 0, 1, hooks[0].length)); body(s.getRangeByIndexes(4, 0, hooks.length - 1, hooks[0].length));
  setWidths(s, [["A", 14], ["B", 22], ["C", 44], ["D", 44], ["E", 34], ["F", 14], ["G", 70], ["H", 15], ["I", 85]]);
  s.freezePanes.freezeRows(4);
}

// Validation data.
{
  const s = wb.worksheets.getItem("Validation"); title(s, "MightyPPL / TAMonitor 机器验证", "N");
  const headers = ["ID", "Build", "+ symbolic", "- symbolic", "+ concrete", "- concrete", "Oracle", "S/C", "AP order", "+ loc", "+ edges", "- loc", "- edges", "Status"];
  s.getRange("A4:N4").values = [headers]; header(s.getRange("A4:N4"));
  const rows = properties.map(p => [p.id, p.validation_build_ok ? "PASS" : "FAIL", p.validation_positive_symbolic, p.validation_negative_symbolic,
    p.validation_positive_concrete, p.validation_negative_concrete, p.validation_expected_oracle_ok ? "PASS" : "FAIL",
    p.validation_symbolic_concrete_consistent ? "PASS" : "FAIL", p.validation_ap_order.join(", "), p.validation_positive_locations,
    p.validation_positive_edges, p.validation_negative_locations, p.validation_negative_edges, p.validation_status]);
  s.getRange(`A5:N${rows.length + 4}`).values = rows; body(s.getRange(`A5:N${rows.length + 4}`));
  s.getRange(`B5:N${rows.length + 4}`).conditionalFormats.add("containsText", { text: "PASS", format: { fill: pale, font: { color: "#006100", bold: true } } });
  setWidths(s, [["A", 14], ["B", 10], ["C", 14], ["D", 14], ["E", 14], ["F", 14], ["G", 10], ["H", 10], ["I", 48], ["J", 10], ["K", 10], ["L", 10], ["M", 10], ["N", 10]]);
  s.freezePanes.freezeRows(4);
}

// Baselines.
{
  const s = wb.worksheets.getItem("Baselines"); title(s, "CCFA 类 baseline 与适配成熟度", "H");
  s.getRangeByIndexes(3, 0, baselines.length, baselines[0].length).values = baselines;
  header(s.getRangeByIndexes(3, 0, 1, baselines[0].length)); body(s.getRangeByIndexes(4, 0, baselines.length - 1, baselines[0].length));
  setWidths(s, [["A", 18], ["B", 32], ["C", 44], ["D", 24], ["E", 24], ["F", 40], ["G", 20], ["H", 52]]);
  s.freezePanes.freezeRows(4);
}

// Evidence ledger.
{
  const s = wb.worksheets.getItem("Evidence"); title(s, "证据账本", "G");
  const headers = ["ID", "Type", "Title", "Version", "DOI", "Accessed", "URL"];
  s.getRange("A4:G4").values = [headers]; header(s.getRange("A4:G4"));
  const rows = evidenceDoc.sources.map(e => [e.id, e.type, e.title, e.version || "", e.doi || "", e.accessed, e.url]);
  s.getRange(`A5:G${rows.length + 4}`).values = rows; body(s.getRange(`A5:G${rows.length + 4}`));
  setWidths(s, [["A", 10], ["B", 20], ["C", 46], ["D", 48], ["E", 30], ["F", 14], ["G", 90]]);
  s.freezePanes.freezeRows(4);
}

// Human signoff sheet.
{
  const s = wb.worksheets.getItem("Review Signoff"); title(s, "逐条人工签字（唯一批准入口）", "J");
  const headers = ["ID", "Title", "RFC §", "Machine", "Review status", "Reviewer", "Date", "Caveat / rejection reason", "AP & correlation approved?", "Experiment claim allowed?"];
  s.getRange("A4:J4").values = [headers]; header(s.getRange("A4:J4"));
  const rows = properties.map(p => [p.id, p.title, p.standard_section, p.validation_status, "PENDING", "", "", "", "PENDING", "NO"]);
  s.getRange(`A5:J${rows.length + 4}`).values = rows; body(s.getRange(`A5:J${rows.length + 4}`));
  s.getRange(`E5:E${rows.length + 4}`).dataValidation = { rule: { type: "list", values: ["PENDING", "APPROVE_AS_CLAIMED", "APPROVE_WITH_CAVEAT", "REJECT_OR_FIX", "DEFER_TO_V2", "KEEP_EXCLUDED"] } };
  s.getRange(`I5:I${rows.length + 4}`).dataValidation = { rule: { type: "list", values: ["PENDING", "YES", "NO"] } };
  s.getRange(`J5:J${rows.length + 4}`).dataValidation = { rule: { type: "list", values: ["NO", "YES_WITH_CAVEAT", "YES"] } };
  s.getRange(`E5:E${rows.length + 4}`).conditionalFormats.add("containsText", { text: "APPROVE", format: { fill: pale, font: { color: "#006100", bold: true } } });
  s.getRange(`E5:E${rows.length + 4}`).conditionalFormats.add("containsText", { text: "REJECT", format: { fill: red, font: { color: "#9C0006", bold: true } } });
  s.getRange("A27:J29").values = [["全局签字", "首选协议 / 时间常数 / MITL 语义 / AP-correlation / baseline 公平性均已审核", null, null, "PENDING", "", "", "", "", ""], ["实施门", "只有 20 条均非 PENDING 且无 REJECT_OR_FIX，才允许进入 harness 实现", null, null, "BLOCKED", "", "", "", "", ""], ["说明", "DEFER_TO_V2 / KEEP_EXCLUDED 不得进入论文主张或实现需求", null, null, "", "", "", "", "", ""]];
  body(s.getRange("A27:J29")); s.getRange("A27:A29").format.fill = light; s.getRange("A27:A29").format.font = { bold: true, color: navy };
  setWidths(s, [["A", 14], ["B", 40], ["C", 10], ["D", 12], ["E", 26], ["F", 18], ["G", 14], ["H", 60], ["I", 26], ["J", 26]]);
  s.freezePanes.freezeRows(4); s.freezePanes.freezeColumns(2);
}

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of sheetNames) {
  const blob = await wb.render({ sheetName, autoCrop: "all", scale: 0.85, format: "png" });
  await fs.writeFile(path.join(previewDir, sheetName.replaceAll(" ", "_") + ".png"), new Uint8Array(await blob.arrayBuffer()));
}

const overview = await wb.inspect({ kind: "sheet", include: "id,name", maxChars: 5000 });
const decision = await wb.inspect({ kind: "region", sheetId: "Decision Summary", range: "A4:H18", maxChars: 10000 });
const signoff = await wb.inspect({ kind: "region", sheetId: "Review Signoff", range: "A4:J29", maxChars: 14000 });
console.log(overview.ndjson || overview);
console.log(decision.ndjson || decision);
console.log(signoff.ndjson || signoff);

const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outPath);
console.log(`saved ${outPath}`);
