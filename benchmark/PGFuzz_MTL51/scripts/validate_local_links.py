#!/usr/bin/env python3
"""Validate local file and source-line links in all dataset Markdown files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote


DATASET_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = DATASET_ROOT / "validation" / "local_link_validation.json"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")
LINE_SUFFIX = re.compile(r":(\d+)(?:-(\d+))?$")
FILE_EXTENSIONS = (".md", ".json", ".csv", ".py")


def main() -> None:
    failures: list[str] = []
    local_links = 0
    line_links = 0
    checked_markdown_files = 0
    unique_targets: set[str] = set()
    line_count_cache: dict[Path, int] = {}

    for markdown_path in sorted(DATASET_ROOT.rglob("*.md")):
        checked_markdown_files += 1
        text = markdown_path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group(1).strip().split("#", 1)[0]
            if not raw_target or raw_target.startswith(("http://", "https://", "mailto:")):
                continue
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            if not (
                raw_target.startswith("/")
                or raw_target.endswith(FILE_EXTENSIONS)
                or "/" in raw_target
            ):
                # Bracketed logical sub-formulas followed by parentheses can
                # resemble Markdown links; a real local target is path-like.
                continue

            line_match = LINE_SUFFIX.search(raw_target)
            start_line = int(line_match.group(1)) if line_match else None
            end_line = int(line_match.group(2) or line_match.group(1)) if line_match else None
            path_target = LINE_SUFFIX.sub("", raw_target)
            decoded_target = unquote(path_target)
            target_path = (
                Path(decoded_target)
                if decoded_target.startswith("/")
                else (markdown_path.parent / decoded_target).resolve()
            )

            local_links += 1
            unique_targets.add(str(target_path))
            # RESULTS.md links this validator's own output.  On a fresh
            # checkout that report is created at the end of this same run.
            output_will_be_created = target_path == REPORT_PATH
            if not output_will_be_created and not target_path.is_file() and not target_path.is_dir():
                failures.append(f"本地链接目标不存在：{markdown_path}:{raw_target}")
                continue
            if start_line is None:
                continue

            line_links += 1
            if not target_path.is_file():
                failures.append(f"带行号的链接目标不是文件：{markdown_path}:{raw_target}")
                continue
            if target_path not in line_count_cache:
                with target_path.open(encoding="utf-8", errors="replace") as handle:
                    line_count_cache[target_path] = sum(1 for _ in handle)
            if not (1 <= start_line <= end_line <= line_count_cache[target_path]):
                failures.append(
                    "链接行号越界或倒置："
                    f"{markdown_path}:{raw_target}:总行数={line_count_cache[target_path]}"
                )

    report = {
        "schema_version": "1.0",
        "validator": "validate_local_links.py",
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "counts": {
            "markdown_files": checked_markdown_files,
            "local_file_links": local_links,
            "links_with_source_lines": line_links,
            "unique_local_targets": len(unique_targets),
            "unique_line_target_files": len(line_count_cache),
        },
        "status_definitions_zh": {
            "PASS": "自动链接检查通过；只表示本地目标存在且所写行号有效。",
            "FAIL": "至少一个本地目标不存在，或者带行号链接越界或倒置。",
        },
        "scope_note_zh": (
            "本验证不访问外部网页，也不判断链接内容是否能证明语义等价；"
            "即使 PASS，也不能证明论文公式正确、源码绑定等价或固件符合性质。"
        ),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_zh = "通过（PASS）" if not failures else "失败（FAIL）"
    print(
        f"本地链接验证：{result_zh}；Markdown 文件 {checked_markdown_files}，"
        f"本地链接 {local_links}，带行号链接 {line_links}，失败 {len(failures)}。"
    )
    print(f"验证报告：{REPORT_PATH}")
    if failures:
        for failure in failures[:40]:
            print(f"- {failure}")
        if len(failures) > 40:
            print(f"- 其余 {len(failures) - 40} 项失败见验证报告。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
