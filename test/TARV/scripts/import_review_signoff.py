#!/usr/bin/env python3
"""Safely import human-owned Review Signoff fields into a review packet.

The generated signoff template is the source of truth for queue linkage,
evidence artifacts, policy fields, and claim boundaries. This importer accepts
a human-filled CSV or workbook sheet, copies only reviewer-owned fields, and
reports any stale generated fields before an optional in-place apply.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REVIEWER_FIELDS = ["reviewer_decision", "reviewer", "review_date", "reviewer_notes"]
KEY_FIELD = "signoff_id"
DEFAULT_SHEET = "Review Signoff"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def column_name_to_index(name: str) -> int:
    value = 0
    for char in name:
        if char.isalpha():
            value = value * 26 + (ord(char.upper()) - ord("A") + 1)
    return value - 1


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[str] = []
    for item in root.findall("main:si", namespace):
        parts = [node.text or "" for node in item.findall(".//main:t", namespace)]
        values.append("".join(parts))
    return values


def workbook_sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = ""
    available: list[str] = []
    for sheet in workbook_root.findall(".//main:sheet", namespace):
        name = sheet.attrib.get("name", "")
        available.append(name)
        if name == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{namespace['rel']}}}id", "")
            break
    if not relationship_id:
        raise ValueError(f"sheet {sheet_name!r} not found; available={available}")

    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in rels_root.findall("pkg:Relationship", namespace):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target", "")
            if target.startswith("/"):
                return target.lstrip("/")
            return str(Path("xl") / target)
    raise ValueError(f"relationship for sheet {sheet_name!r} not found")


def cell_text(cell: ET.Element, strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t", "")
    value_node = cell.find("main:v", namespace)
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", namespace))
    if value_node is None or value_node.text is None:
        return ""
    raw = value_node.text
    if cell_type == "s":
        try:
            return strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[dict[str, str]]:
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(archive)
        sheet_path = workbook_sheet_path(archive, sheet_name)
        root = ET.fromstring(archive.read(sheet_path))
    table_rows: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", namespace):
        values: dict[int, str] = {}
        max_index = -1
        for cell in row.findall("main:c", namespace):
            reference = cell.attrib.get("r", "")
            column_letters = "".join(char for char in reference if char.isalpha())
            index = column_name_to_index(column_letters) if column_letters else max_index + 1
            values[index] = cell_text(cell, strings, namespace)
            max_index = max(max_index, index)
        if max_index >= 0:
            table_rows.append([values.get(index, "") for index in range(max_index + 1)])
    if not table_rows:
        return []
    headers = [header.strip() for header in table_rows[0]]
    return [
        {headers[index]: row[index] if index < len(row) else "" for index in range(len(headers)) if headers[index]}
        for row in table_rows[1:]
        if any(cell.strip() for cell in row)
    ]


def normalize_decision(value: str) -> str:
    return value.strip().upper()


def normalize_import_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {key.strip(): (value or "") for key, value in row.items() if key is not None}
    if "reviewer_note" in normalized and "reviewer_notes" not in normalized:
        normalized["reviewer_notes"] = normalized["reviewer_note"]
    if "reviewer_decision" in normalized:
        normalized["reviewer_decision"] = normalize_decision(normalized["reviewer_decision"])
    return normalized


def index_by_signoff_id(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], list[str]]:
    index: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    for row in rows:
        signoff_id = row.get(KEY_FIELD, "").strip()
        if not signoff_id:
            duplicates.append("<blank>")
            continue
        if signoff_id in index:
            duplicates.append(signoff_id)
        index[signoff_id] = row
    return index, duplicates


def import_signoff(
    output_dir: Path,
    imported_rows: list[dict[str, str]],
    output_path: Path,
    allow_partial: bool,
    apply: bool,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    template_path = output_dir / "review_signoff_template.csv"
    if not template_path.exists():
        raise FileNotFoundError(template_path)
    base_rows = read_csv_rows(template_path)
    if not base_rows:
        raise ValueError("current review_signoff_template.csv has no rows")
    fieldnames = list(base_rows[0].keys())
    missing_reviewer_columns = [field for field in REVIEWER_FIELDS if field not in fieldnames]
    if missing_reviewer_columns:
        raise ValueError(f"current signoff template missing reviewer fields: {missing_reviewer_columns}")

    imported_rows = [normalize_import_row(row) for row in imported_rows]
    imported_index, duplicate_import_ids = index_by_signoff_id(imported_rows)
    base_index, duplicate_base_ids = index_by_signoff_id(base_rows)
    required_import_columns = [KEY_FIELD, *REVIEWER_FIELDS]
    import_columns = set(imported_rows[0].keys()) if imported_rows else set()
    missing_import_columns = [field for field in required_import_columns if field not in import_columns]

    base_ids = set(base_index)
    imported_ids = set(imported_index)
    missing_ids = sorted(base_ids - imported_ids)
    extra_ids = sorted(imported_ids - base_ids)
    immutable_fields = [field for field in fieldnames if field not in REVIEWER_FIELDS]
    immutable_mismatches: list[str] = []
    for signoff_id in sorted(base_ids & imported_ids):
        base_row = base_index[signoff_id]
        import_row = imported_index[signoff_id]
        for field in immutable_fields:
            if field in import_row and import_row.get(field, "") != base_row.get(field, ""):
                immutable_mismatches.append(f"{signoff_id}:{field}")

    merged_rows: list[dict[str, str]] = []
    changed_rows = 0
    imported_nonblank_decisions = 0
    for base_row in base_rows:
        signoff_id = base_row.get(KEY_FIELD, "")
        merged = dict(base_row)
        import_row = imported_index.get(signoff_id)
        if import_row:
            for field in REVIEWER_FIELDS:
                value = import_row.get(field, "")
                if merged.get(field, "") != value:
                    changed_rows += 1
                merged[field] = value
            if merged.get("reviewer_decision", "").strip():
                imported_nonblank_decisions += 1
        merged_rows.append(merged)

    errors: list[str] = []
    if duplicate_base_ids:
        errors.append("duplicate_base_signoff_ids=" + ";".join(duplicate_base_ids))
    if duplicate_import_ids:
        errors.append("duplicate_import_signoff_ids=" + ";".join(duplicate_import_ids))
    if missing_import_columns:
        errors.append("missing_import_columns=" + ";".join(missing_import_columns))
    if missing_ids and not allow_partial:
        errors.append("missing_import_signoff_ids=" + ";".join(missing_ids[:20]))
    if extra_ids:
        errors.append("extra_import_signoff_ids=" + ";".join(extra_ids[:20]))
    if immutable_mismatches:
        errors.append("immutable_field_mismatches=" + ";".join(immutable_mismatches[:20]))

    write_csv_rows(output_path, merged_rows, fieldnames)
    backup_path = ""
    if apply and not errors:
        backup = template_path.with_name(f"review_signoff_template.pre_import_{time.strftime('%Y%m%d-%H%M%S')}.csv")
        shutil.copyfile(template_path, backup)
        shutil.copyfile(output_path, template_path)
        backup_path = str(backup)

    summary = {
        "output_dir": str(output_dir),
        "template_path": str(template_path),
        "output_path": str(output_path),
        "applied": apply and not errors,
        "backup_path": backup_path,
        "allow_partial": allow_partial,
        "base_rows": len(base_rows),
        "import_rows": len(imported_rows),
        "merged_rows": len(merged_rows),
        "changed_reviewer_field_cells": changed_rows,
        "imported_nonblank_decisions": imported_nonblank_decisions,
        "duplicate_import_ids": len(duplicate_import_ids),
        "missing_import_columns": len(missing_import_columns),
        "missing_signoff_ids": len(missing_ids),
        "extra_signoff_ids": len(extra_ids),
        "immutable_field_mismatches": len(immutable_mismatches),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }
    return merged_rows, summary


def write_report(output_dir: Path, summary: dict[str, Any]) -> None:
    rows = [{"key": key, "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)} for key, value in summary.items()]
    write_csv_rows(output_dir / "review_signoff_import_report.csv", rows, ["key", "value"])
    (output_dir / "review_signoff_import_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Review Signoff Import Report",
        "",
        "This report records a safe import of reviewer-owned signoff fields.",
        "Generated queue, evidence, and policy fields remain controlled by the current result packet.",
        "",
        "| key | value |",
        "|---|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['key']}` | `{row['value']}` |")
    lines.append("")
    (output_dir / "review_signoff_import_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="TAMonitor paper-review result directory.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-csv", type=Path, help="Human-filled Review Signoff CSV.")
    source.add_argument("--from-xlsx", type=Path, help="Human-filled paper_review_results.xlsx or compatible workbook.")
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="Workbook sheet name for --from-xlsx.")
    parser.add_argument("--out", type=Path, default=None, help="Merged signoff CSV path. Defaults to <output-dir>/review_signoff_imported.csv.")
    parser.add_argument("--allow-partial", action="store_true", help="Allow missing signoff IDs and leave their reviewer fields unchanged.")
    parser.add_argument("--apply", action="store_true", help="After a clean import, back up and replace review_signoff_template.csv.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_path = (args.out or output_dir / "review_signoff_imported.csv").resolve()
    try:
        if args.from_csv:
            imported_rows = read_csv_rows(args.from_csv.resolve())
            source_path = str(args.from_csv.resolve())
        else:
            imported_rows = read_xlsx_sheet(args.from_xlsx.resolve(), args.sheet)
            source_path = f"{args.from_xlsx.resolve()}#{args.sheet}"
        _, summary = import_signoff(output_dir, imported_rows, output_path, args.allow_partial, args.apply)
        summary["source"] = source_path
    except Exception as error:
        summary = {
            "output_dir": str(output_dir),
            "output_path": str(output_path),
            "applied": False,
            "status": "FAIL",
            "errors": [str(error)],
        }
    write_report(output_dir, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
