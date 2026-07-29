import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2];
if (!outputDir) {
  console.error("Usage: build_paper_review_workbook.mjs <experiment-output-dir>");
  process.exit(2);
}

const csvFiles = [
  ["Summary", "experiment_summary.csv"],
  ["Review Guide", "review_guide.csv"],
  ["Review Queue", "human_review_queue.csv"],
  ["Review Signoff", "review_signoff_template.csv"],
  ["Signoff Evidence", "review_signoff_evidence_bundle.csv", true],
  ["Signoff Validation", "review_signoff_validation.csv", true],
  ["Signoff Roundtrip", "signoff_import_roundtrip_audit.csv", true],
  ["Goal Audit", "goal_completion_audit.csv"],
  ["Manual Review", "manual_review_checklist.csv"],
  ["Correctness Audit", "mitl_correctness_audit.csv"],
  ["Prefix Oracle", "semantic_prefix_oracle_review.csv"],
  ["Oracle Derivations", "semantic_oracle_derivations.csv"],
  ["Manual Oracle Guide", "manual_oracle_guide.csv"],
  ["MITL Semantic Catalog", "mitl_formula_catalog_semantic_regression.csv", true],
  ["MITL XML Candidates", "mitl_formula_catalog_monitaal_xml_candidates.csv", true],
  ["MITL Runtime Catalog", "mitl_formula_catalog_runtime_runs.csv", true],
  ["Semantic Results", "semantic_regression_results.csv"],
  ["Semantic Cases", "semantic_cases.csv"],
  ["Semantic Exclusions", "semantic_exclusions.csv"],
  ["Syntax Coverage", "mightyppl_syntax_coverage_audit.csv"],
  ["Input Policy", "formula_input_policy_audit.csv"],
  ["CLI Contract", "cli_contract_audit.csv"],
  ["XML Inventory", "monitaal_xml_inventory.csv"],
  ["Translation Review", "monitaal_translation_review.csv"],
  ["Benchmark Manifest", "benchmark_manifest.csv"],
  ["XML Edge Proofs", "xml_edge_guard_proofs.csv"],
  ["XML Proof Appendix", "xml_proof_appendix.csv"],
  ["XML Obligations", "xml_proof_obligations.csv"],
  ["XML Trace Coverage", "xml_trace_coverage_obligations.csv"],
  ["Original Trace Gaps", "xml_original_trace_gaps.csv"],
  ["Gear Original Audit", "gear_original_input_response_audit.csv"],
  ["Non-Gear Input Search", "non_gear_original_input_search_audit.csv"],
  ["Paper Claim Review", "paper_claim_review.csv"],
  ["Claim Audit", "paper_claim_consistency_audit.csv"],
  ["Requirements Audit", "requirements_traceability_audit.csv"],
  ["Repro Manifest", "reproducibility_manifest.csv"],
  ["Transition Details", "monitaal_transition_details.csv"],
  ["Candidate Results", "translation_candidate_results.csv"],
  ["Candidate Step Audit", "candidate_step_audit.csv"],
  ["Baseline Results", "monitaal_baseline_results.csv"],
  ["Timeout Rerun Summary", "timeout_rerun_summary.csv", true],
  ["Timeout Rerun", "timeout_rerun_details.csv", true],
  ["Embedded Benchmarks", "monitaal_embedded_benchmarks.csv"],
  ["Hardcoded Benchmarks", "monitaal_hardcoded_benchmarks.csv", true],
  ["Benchmark Blockers", "benchmark_blocker_diagnostics.csv", true],
];

const previewLimits = {
  maxRows: 250,
  maxCols: 40,
};

const defaultPreviewAllowlist = [
  "Summary",
  "Review Guide",
  "Review Queue",
  "Signoff Evidence",
  "Signoff Validation",
  "Signoff Roundtrip",
  "Goal Audit",
  "Manual Review",
  "Manual Oracle Guide",
  "MITL Semantic Catalog",
  "MITL XML Candidates",
  "MITL Runtime Catalog",
  "Benchmark Manifest",
  "Baseline Results",
  "Hardcoded Benchmarks",
  "Benchmark Blockers",
  "Timeout Rerun Summary",
  "Timeout Rerun",
];

const previewAllowlist = process.env.TAMONITOR_RENDER_WORKBOOK_PREVIEWS === "1"
  ? new Set(defaultPreviewAllowlist)
  : new Set();

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; ++i) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          ++i;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
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
  return rows;
}

function columnName(index) {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - rem - 1) / 26);
  }
  return name;
}

async function readCsvRows(fileName, optional = false) {
  const filePath = path.join(outputDir, fileName);
  let text;
  try {
    text = await fs.readFile(filePath, "utf8");
  } catch (error) {
    if (optional && error?.code === "ENOENT") {
      return null;
    }
    throw error;
  }
  return parseCsv(text);
}

function styleSheet(sheet, rows, options = {}) {
  if (!rows.length || !rows[0].length) return;
  const rowCount = rows.length;
  const colCount = rows[0].length;
  const lastCol = columnName(colCount - 1);
  const used = sheet.getRange(`A1:${lastCol}${rowCount}`);
  used.format.font.name = "Aptos";
  used.format.font.size = 10;
  used.format.wrapText = true;
  used.format.borders = { preset: "outside", style: "thin", color: "#B7C4D6" };

  const header = sheet.getRange(`A1:${lastCol}1`);
  header.format.fill.color = "#1F4E79";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.rowHeight = 24;
  header.format.borders = { preset: "all", style: "thin", color: "#7F9DB9" };

  if (rowCount > 1) {
    const body = sheet.getRange(`A2:${lastCol}${rowCount}`);
    body.format.borders = { preset: "inside", style: "thin", color: "#E5E7EB" };
  }

  sheet.freezePanes.freezeRows(1);
  sheet.showGridLines = false;
  used.format.autofitColumns();
  used.format.autofitRows();

  for (let i = 0; i < colCount; ++i) {
    const colName = columnName(i);
    const col = sheet.getRange(`${colName}1:${colName}${rowCount}`);
    if (options.wideColumns?.has(i)) {
      col.format.columnWidth = 48;
    } else if (options.mediumColumns?.has(i)) {
      col.format.columnWidth = 28;
    } else if (options.narrowColumns?.has(i)) {
      col.format.columnWidth = 14;
    }
  }
}

function addTable(sheet, rows, tableName) {
  if (!rows.length || !rows[0].length) return;
  const lastCol = columnName(rows[0].length - 1);
  const range = `A1:${lastCol}${rows.length}`;
  const table = sheet.tables.add(range, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
}

function csvEscape(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

async function writeRowsCsv(filePath, rows, headers) {
  const csv = [
    headers.map(csvEscape).join(","),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(",")),
  ].join("\n") + "\n";
  await fs.writeFile(filePath, csv, "utf8");
}

function previewDecision(sheet) {
  if (!previewAllowlist.has(sheet.sheetName)) {
    return {
      render: false,
      reason: "skipped_not_in_preview_allowlist",
    };
  }
  if (sheet.rowCount > previewLimits.maxRows || sheet.colCount > previewLimits.maxCols) {
    return {
      render: false,
      reason: `skipped_large_sheet_rows_${sheet.rowCount}_cols_${sheet.colCount}`,
    };
  }
  return { render: true, reason: "rendered" };
}

async function main() {
  const workbook = Workbook.create();

  console.error(`[workbook] loading summary from ${outputDir}`);
  const summaryJson = JSON.parse(await fs.readFile(path.join(outputDir, "experiment_summary.json"), "utf8"));
  const summaryRows = [
    ["metric", "value"],
    ...Object.entries(summaryJson).map(([k, v]) => [k, String(v)]),
  ];
  const summaryCsv = summaryRows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n") + "\n";
  await fs.writeFile(path.join(outputDir, "experiment_summary.csv"), summaryCsv, "utf8");

  const renderedSheets = [];
  for (const [sheetName, fileName, optional = false] of csvFiles) {
    console.error(`[workbook] reading ${fileName} for sheet ${sheetName}`);
    const rows = await readCsvRows(fileName, optional);
    if (rows === null) {
      console.error(`[workbook] optional ${fileName} missing; skipped ${sheetName}`);
      continue;
    }
    renderedSheets.push({ sheetName, fileName, rowCount: rows.length, colCount: rows[0]?.length ?? 0 });
    console.error(`[workbook] rendering sheet ${sheetName}: rows=${rows.length}, cols=${rows[0]?.length ?? 0}`);
    const sheet = workbook.worksheets.add(sheetName);
    if (rows.length) {
      const lastCol = columnName(rows[0].length - 1);
      sheet.getRange(`A1:${lastCol}${rows.length}`).values = rows;
      const tableSafeName = sheetName.replaceAll(" ", "") + "Table";
      addTable(sheet, rows, tableSafeName);
      const wideHeaders = new Set([
        "formula",
        "trace",
        "rationale",
        "stderr_excerpt",
        "stdout_excerpt",
        "translation_reason",
        "correctness_evidence",
        "step_evidence",
        "evidence",
        "labels",
        "guards",
        "assignments",
        "other_labels",
        "source_invariants",
        "target_invariants",
        "ap_mapping",
        "candidate_mitl",
        "matched_input_paths",
        "timeout_input_paths",
        "original_timeout_stderr",
        "blocker_or_next_step",
        "blocker_class",
        "diagnostic_evidence",
        "pattern",
        "positive_edge_evidence",
        "negative_edge_evidence",
        "reset_edge_evidence",
        "acceptance_evidence",
        "trace_evidence",
        "manual_review_notes",
        "manual_review_action",
        "paper_claim_scope",
        "paper_body_recommendation",
        "appendix_recommendation",
        "proof_sketch",
        "edge_guard_evidence",
        "baseline_evidence_boundary",
        "must_not_claim",
        "next_manual_action",
        "source_artifacts",
        "exclusion_reason",
        "checked_rules",
        "issues",
        "warnings",
        "recommended_action",
        "requirement",
        "evidence_summary",
        "evidence_artifacts",
        "gap_or_risk",
        "value",
        "xml_path",
        "run_dir",
        "input_path",
        "input_rationale",
        "trace_path",
        "input_origin_match_counts",
        "expected_prefix",
        "expected_prefix_verdict",
        "actual_prefix_verdict",
        "prefix_oracle_status",
        "source_context",
        "reviewer_note",
        "correctness_claim_scope",
        "candidate_step_evidence",
        "raw_step_artifact",
        "construct",
        "evidence_summary",
        "evidence_case_ids",
        "finite_case_ids",
        "infinite_case_ids",
        "evidence_categories",
        "source_reference",
        "notes",
        "review_action",
        "coverage_status",
        "review_focus",
        "blocking_claim",
        "decision_allowed",
        "reviewer_notes",
        "instruction",
        "decision_rule",
        "completion_requirements",
        "expected_policy",
        "probe_input_disclosure",
        "expected_exit_class",
        "actual_exit_class",
        "probe_policy",
        "diagnostic_contains",
        "workbook_sheet",
        "review_question",
        "must_not_claim",
        "suggested_action",
        "requested_goal",
        "review_gate",
        "semantic_rule",
        "final_oracle_derivation",
        "prefix_oracle_derivation",
        "sat_oracle_derivation",
        "protocol_step",
        "pass_condition",
        "reject_or_fix_condition",
        "scenario",
        "input_surface",
        "expected_behavior",
        "report_files",
        "command",
      ]);
      const mediumHeaders = new Set([
        "queue_id",
        "priority",
        "source_id",
        "signoff_id",
        "signoff_required",
        "reviewer_decision",
        "recommended_decision",
        "forbidden_decisions",
        "reviewer",
        "review_date",
        "guide_id",
        "section",
        "review_id",
        "review_area",
        "review_status",
        "automatic_status",
        "human_decision_required",
        "oracle_scope",
        "oracle_status",
        "sample_case_ids",
        "actual_exit_class",
        "expected_exit_class",
        "bdd_interface_status",
        "status",
        "completion_state",
        "decision_counts",
      ]);
      const narrowHeaders = new Set([
        "word",
        "state",
        "events",
        "returncode",
        "timeout",
        "transition_index",
        "nails",
        "pair_role",
        "parse_status",
        "review_status",
        "monitor_advanced",
        "starred",
        "user_level",
        "run_policy",
        "all_trace_steps_recorded",
        "assert_like_failure",
        "signoff_required",
        "retry_timeout_seconds",
        "available_timeout_rows",
        "selected_timeout_rows",
        "rerun_completed",
        "rerun_timeouts",
        "elapsed_ms",
      ]);
      const wideColumns = new Set();
      const mediumColumns = new Set();
      const narrowColumns = new Set();
      rows[0].forEach((header, index) => {
        if (wideHeaders.has(header)) wideColumns.add(index);
        if (mediumHeaders.has(header)) mediumColumns.add(index);
        if (narrowHeaders.has(header)) narrowColumns.add(index);
      });
      styleSheet(sheet, rows, { wideColumns, mediumColumns, narrowColumns });
    }
  }

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  await fs.writeFile(path.join(outputDir, "workbook_formula_error_scan.ndjson"), errors.ndjson ?? String(errors), "utf8");

  const previewRows = [];
  for (const renderedSheet of renderedSheets) {
    const { sheetName } = renderedSheet;
    const decision = previewDecision(renderedSheet);
    const previewPath = `${sheetName.replaceAll(" ", "_").toLowerCase()}_preview.png`;
    if (!decision.render) {
      console.error(`[workbook] skipping preview ${sheetName}: ${decision.reason}`);
      previewRows.push({ ...renderedSheet, preview_path: "", preview_status: "skipped", preview_reason: decision.reason });
      continue;
    }
    console.error(`[workbook] rendering preview ${sheetName}`);
    const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(path.join(outputDir, previewPath), bytes);
    previewRows.push({ ...renderedSheet, preview_path: previewPath, preview_status: "rendered", preview_reason: decision.reason });
  }
  await writeRowsCsv(
    path.join(outputDir, "workbook_preview_manifest.csv"),
    previewRows,
    ["sheetName", "fileName", "rowCount", "colCount", "preview_path", "preview_status", "preview_reason"],
  );
  await fs.writeFile(path.join(outputDir, "workbook_preview_manifest.json"), JSON.stringify(previewRows, null, 2), "utf8");

  console.error("[workbook] exporting xlsx");
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(outputDir, "paper_review_results.xlsx"));

  console.error("[workbook] inspecting final workbook");
  const inspect = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 6000,
    tableMaxRows: 5,
    tableMaxCols: 8,
  });
  await fs.writeFile(path.join(outputDir, "workbook_inspect.ndjson"), inspect.ndjson ?? String(inspect), "utf8");
}

main().catch((error) => {
  console.error(error?.stack ?? error);
  process.exit(1);
});
