#!/usr/bin/env python3
import csv
import html
import json
import sys
import zipfile
from pathlib import Path


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def cell_ref(row, col):
    letters = ""
    n = col
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return f"{letters}{row}"


def sheet_xml(rows):
    body = []
    for r_idx, row in enumerate(rows, 1):
        cells = []
        for c_idx, value in enumerate(row, 1):
            ref = cell_ref(r_idx, c_idx)
            escaped = html.escape(str(value), quote=False)
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        body.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetData>'
        + "".join(body)
        + '</sheetData></worksheet>'
    )


def workbook_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        '<sheet name="Steps" sheetId="1" r:id="rId1"/>'
        '<sheet name="Summary" sheetId="2" r:id="rId2"/>'
        '<sheet name="Metadata" sheetId="3" r:id="rId3"/>'
        '</sheets></workbook>'
    )


def build(output_dir):
    output_dir = Path(output_dir)
    steps = read_csv(output_dir / "steps.csv")
    summary = read_csv(output_dir / "summary.csv")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata_rows = [["field", "value"]]
    for key, value in metadata.items():
        metadata_rows.append([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])

    xlsx_path = output_dir / "results.xlsx"
    with zipfile.ZipFile(xlsx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ))
        zf.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ))
        zf.writestr("xl/workbook.xml", workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
            '</Relationships>'
        ))
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml(steps))
        zf.writestr("xl/worksheets/sheet2.xml", sheet_xml(summary))
        zf.writestr("xl/worksheets/sheet3.xml", sheet_xml(metadata_rows))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_tamonitor_xlsx.py <output_dir>")
    build(sys.argv[1])
