#!/usr/bin/env python3
"""Generate a static paper-to-code analysis report for TAFuzz.

The report is intentionally self-contained: PDF extraction, code symbol line
lookup, mapping tables, and inline diagrams all happen here so future agents can
regenerate the artifact without rediscovering the project.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


ROOT = Path("/home/lqq/download/TAFuzz")
OUT_DIR = ROOT / "analysis"
DATA_DIR = OUT_DIR / "data"
REPORT = OUT_DIR / "mightyppl_monitaal_paper_code_report.html"

MIGHTY = ROOT / "tool" / "MightyPPL"
MONI = ROOT / "tool" / "MoniTAal"

MIGHTY_PDF = Path(
    "/mnt/c/Users/lqq27/Zotero/storage/E3UQKD7D/Ho 等 - 2025 - MightyPPL Verification of MITL with past and pnueli modalities.pdf"
)
MONI_PDF = Path(
    "/mnt/c/Users/lqq27/Zotero/storage/IKF2LXSD/Cimatti 等 - 2025 - Exploiting assumptions for\u00a0effective monitoring of\u00a0real-time properties under partial observability.pdf"
)


@dataclass(frozen=True)
class CodeRef:
    path: str
    pattern: str
    note: str = ""


def sh(cmd: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True, stderr=subprocess.STDOUT)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: str | Path) -> str:
    return str(Path(path).relative_to(ROOT))


def abs_path(path: str | Path) -> str:
    return str((ROOT / path).resolve() if not str(path).startswith("/") else Path(path).resolve())


def find_line(path: str | Path, pattern: str) -> int:
    p = ROOT / path if not str(path).startswith("/") else Path(path)
    text = read_text(p).splitlines()
    try:
        rx = re.compile(pattern)
    except re.error:
        rx = re.compile(re.escape(pattern))
    for i, line in enumerate(text, 1):
        if rx.search(line):
            return i
    return 1


def code_link(ref: CodeRef | str, pattern: str | None = None, label: str | None = None) -> str:
    if isinstance(ref, CodeRef):
        path = ref.path
        pat = ref.pattern
    else:
        path = ref
        pat = pattern or "."
    line = find_line(path, pat)
    ap = abs_path(path)
    display = label or f"{ap}:{line}"
    return f'<a class="code" href="file://{html.escape(ap)}#L{line}">{html.escape(display)}</a>'


def extract_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    pages = []
    for idx, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append({"page": idx, "text": text})
    return {"path": str(path), "name": path.name, "page_count": len(pages), "pages": pages}


def compact_pdf(pdf: dict) -> dict:
    pages = []
    for page in pdf["pages"]:
        preview = re.sub(r"\s+", " ", page["text"]).strip()[:500]
        pages.append({"page": page["page"], "char_count": len(page["text"]), "preview": preview})
    return {
        "path": pdf["path"],
        "name": pdf["name"],
        "page_count": pdf["page_count"],
        "pages": pages,
    }


def page_for(pdf: dict, needle: str) -> int:
    n = needle.lower()
    for p in pdf["pages"]:
        if n in p["text"].lower():
            return p["page"]
    return 0


def excerpt(pdf: dict, needle: str, width: int = 220) -> str:
    n = needle.lower()
    for p in pdf["pages"]:
        text = re.sub(r"\s+", " ", p["text"])
        i = text.lower().find(n)
        if i != -1:
            start = max(0, i - width // 3)
            end = min(len(text), i + width)
            return text[start:end].strip()
    return ""


def list_files(base: Path) -> list[str]:
    out = sh(["rg", "--files", str(base.relative_to(ROOT))])
    return sorted(out.splitlines())


def file_inventory() -> dict:
    mighty_files = list_files(MIGHTY)
    moni_files = list_files(MONI)

    def group(files: list[str]) -> dict[str, int]:
        g: dict[str, int] = {}
        for f in files:
            parts = Path(f).parts
            if "testcases" in parts:
                k = "testcases"
            elif "test" in parts:
                k = "test"
            elif "benchmark" in parts:
                k = "benchmark"
            elif "cmake" in parts:
                k = "cmake"
            elif "src" in parts:
                k = "/".join(parts[:4]) if len(parts) > 3 else "/".join(parts[:2])
            elif f.endswith(".patch"):
                k = "patch/case snapshots"
            elif Path(f).suffix in {".cpp", ".h", ".g4"}:
                k = "root source"
            else:
                k = "docs/license/config"
            g[k] = g.get(k, 0) + 1
        return dict(sorted(g.items()))

    return {
        "mighty_files": mighty_files,
        "monitaal_files": moni_files,
        "mighty_groups": group(mighty_files),
        "monitaal_groups": group(moni_files),
    }


def status_snapshot() -> dict:
    def safe(cmd: list[str], cwd: Path) -> str:
        try:
            return sh(cmd, cwd=cwd).strip()
        except subprocess.CalledProcessError as e:
            return e.output.strip()

    return {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "mighty_status": safe(["git", "status", "--short"], MIGHTY),
        "monitaal_status": safe(["git", "status", "--short"], MONI),
        "mitppl_help": safe([str(MIGHTY / "build" / "mitppl"), "--help"], MIGHTY / "build")
        if (MIGHTY / "build" / "mitppl").exists()
        else "build/mitppl not found",
    }


def rows(items: Iterable[Iterable[str]]) -> str:
    out = []
    for item in items:
        out.append("<tr>" + "".join(f"<td>{x}</td>" for x in item) + "</tr>")
    return "\n".join(out)


def cards(items: Iterable[tuple[str, str]]) -> str:
    return "\n".join(
        f'<div class="card"><h4>{html.escape(title)}</h4><p>{body}</p></div>' for title, body in items
    )


def badge(status: str) -> str:
    key = {
        "已实现": "ok",
        "部分实现": "partial",
        "工程化替代": "partial",
        "未发现实现": "missing",
        "论文未覆盖但代码存在": "extra",
        "未重新验证": "partial",
    }.get(status, "partial")
    return f'<span class="badge {key}">{html.escape(status)}</span>'


def section_table(title: str, body: list[dict]) -> str:
    trs = []
    for x in body:
        links = "<br>".join(x.get("links", [])) or "—"
        trs.append(
            [
                html.escape(x["paper"]),
                badge(x["status"]),
                html.escape(x["analysis"]),
                links,
            ]
        )
    return f"""
    <h3>{html.escape(title)}</h3>
    <table>
      <thead><tr><th>论文内容</th><th>状态</th><th>分析</th><th>代码证据</th></tr></thead>
      <tbody>{rows(trs)}</tbody>
    </table>
    """


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    mighty_pdf = extract_pdf(MIGHTY_PDF)
    moni_pdf = extract_pdf(MONI_PDF)
    inv = file_inventory()
    stat = status_snapshot()

    (DATA_DIR / "mighty_paper_pages.json").write_text(
        json.dumps(compact_pdf(mighty_pdf), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "monitaal_paper_pages.json").write_text(
        json.dumps(compact_pdf(moni_pdf), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "code_inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "status_snapshot.json").write_text(json.dumps(stat, ensure_ascii=False, indent=2), encoding="utf-8")

    mighty_pages = {
        "abstract": 1,
        "intro": page_for(mighty_pdf, "1 Introduction"),
        "prelim": page_for(mighty_pdf, "2 Preliminaries"),
        "logic": page_for(mighty_pdf, "2.1 Metric Temporal Logic"),
        "ta": page_for(mighty_pdf, "2.2 Timed Automata"),
        "translation": page_for(mighty_pdf, "2.3 Compositional Translation"),
        "past_pnueli": page_for(mighty_pdf, "3 Past"),
        "past_mitl": page_for(mighty_pdf, "3.1 Tester Automata"),
        "pnueli": page_for(mighty_pdf, "3.2 Tester Automata for Pnueli"),
        "sequential": page_for(mighty_pdf, "4 General Time Intervals"),
        "implementation": page_for(mighty_pdf, "5 Implementation and Experiments"),
        "experiments": page_for(mighty_pdf, "5.2 Experiments"),
        "conclusion": page_for(mighty_pdf, "6 Conclusion"),
    }
    moni_pages = {
        "abstract": 1,
        "intro": page_for(moni_pdf, "1 Introduction"),
        "prelim": page_for(moni_pdf, "2 Preliminaries"),
        "assumptions": page_for(moni_pdf, "3 Monitoring Under Assumptions"),
        "algorithm": page_for(moni_pdf, "4 A Zone-Based Monitoring Algorithm"),
        "evaluation": page_for(moni_pdf, "5 Evaluation"),
        "related": page_for(moni_pdf, "6 Related Work"),
        "conclusion": page_for(moni_pdf, "7 Conclusion"),
    }
    (DATA_DIR / "paper_sections.json").write_text(
        json.dumps({"mighty": mighty_pages, "monitaal": moni_pages}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mighty_map = [
        {
            "paper": f"摘要/第1节：工具目标是把 MITPPL 公式翻译到 TA，并服务 satisfiability/model checking。页 {mighty_pages['abstract']}, {mighty_pages['intro']}",
            "status": "已实现",
            "analysis": "命令行从公式文件读入，ANTLR 解析后构建 TA；无输出文件时直接调用 MoniTAal/PARDIBAAL 风格的 backward fixpoint。",
            "links": [
                code_link("tool/MightyPPL/main.cpp", r"ANTLRInputStream"),
                code_link("tool/MightyPPL/main.cpp", r"build_ta_from_main"),
                code_link("tool/MightyPPL/main.cpp", r"Calculating fixpoint"),
            ],
        },
        {
            "paper": f"第2.1节：MITL with past and Pnueli modalities 的语法与语义。页 {mighty_pages['logic']}",
            "status": "已实现",
            "analysis": "语法层覆盖 F/G/U/R、O/H/S/T、Fn/On/Gn/Hn 与计数风格变体；visitor 链负责类型检查、NNF 转换、编号和 BDD 标签提取。",
            "links": [
                code_link("tool/MightyPPL/Mitl.g4", r"parser grammar|grammar Mitl|main"),
                code_link("tool/MightyPPL/MitlTypingVisitor.h", r"class\s+MitlTypingVisitor"),
                code_link("tool/MightyPPL/MitlToNNFVisitor.cpp", r"visitAtom"),
                code_link("tool/MightyPPL/MitlAtomNumberingVisitor.cpp", r"visitAtom"),
            ],
        },
        {
            "paper": f"第2.2节：Timed Automata 基础。页 {mighty_pages['ta']}",
            "status": "工程化替代",
            "analysis": "MightyPPL 自身扩展 TA 为带 BDD 边标签的 TAwithBDDEdges；普通 TA/zone/fixpoint 由 MoniTAal 与 PARDIBAAL 承担。",
            "links": [
                code_link("tool/MightyPPL/TAwithBDDEdges.h", r"class\s+TAwithBDDEdges"),
                code_link("tool/MightyPPL/TAwithBDDEdges.cpp", r"bdd_edge_t"),
                code_link("tool/MoniTAal/src/monitaal/TA.h", r"class\s+TA"),
            ],
        },
        {
            "paper": f"第2.3节：compositional translation。页 {mighty_pages['translation']}",
            "status": "已实现",
            "analysis": "每个 temporal atom 生成一个或多个 tester/component TA，随后根据 noflatten/compflatten/flatten 模式输出或做同步积。",
            "links": [
                code_link("tool/MightyPPL/MightyPPL.cpp", r"build_ta_from_atom"),
                code_link("tool/MightyPPL/MightyPPL.cpp", r"build_ta_from_main"),
                code_link("tool/MightyPPL/TAwithBDDEdges.cpp", r"TAwithBDDEdges::intersection"),
            ],
        },
        {
            "paper": f"第3.1节：past MITL unilateral intervals 的 tester automata。页 {mighty_pages['past_mitl']}",
            "status": "已实现",
            "analysis": "past operators 用 Once/Historically/Since/Trigger 独立文件实现；future operators 用 Finally/Globally/Until/Release 形成对称结构。",
            "links": [
                code_link("tool/MightyPPL/Once.cpp", r"build_once"),
                code_link("tool/MightyPPL/Historically.cpp", r"build_historically"),
                code_link("tool/MightyPPL/Since.cpp", r"build_since"),
                code_link("tool/MightyPPL/Trigger.cpp", r"build_trigger"),
            ],
        },
        {
            "paper": f"第3.2节：Pnueli modalities tester automata。页 {mighty_pages['pnueli']}",
            "status": "已实现",
            "analysis": "Fn/On/Gn/Hn 分别有构造文件；实现使用 bit-vector/BDD 编码 obligations、in/out 状态，并生成顺序化辅助 automata。",
            "links": [
                code_link("tool/MightyPPL/PnueliFn.cpp", r"build_pnuelifn"),
                code_link("tool/MightyPPL/PnueliOn.cpp", r"build_pnuelion"),
                code_link("tool/MightyPPL/PnueliGn.cpp", r"build_pnuelign"),
                code_link("tool/MightyPPL/PnueliHn.cpp", r"build_pnuelihn"),
            ],
        },
        {
            "paper": f"第4节：general intervals 与 sequentialisation。页 {mighty_pages['sequential']}",
            "status": "部分实现",
            "analysis": "代码中能看到 seq_in/seq_out、projection_bdd 和 product+projection 这一工程路径；但论文中的证明、构造规范和复杂度论证没有以独立算法文档形式落在代码里。",
            "links": [
                code_link("tool/MightyPPL/PnueliHn.cpp", r"seq_in_"),
                code_link("tool/MightyPPL/PnueliHn.cpp", r"seq_out_"),
                code_link("tool/MightyPPL/TAwithBDDEdges.cpp", r"projection_bdd"),
            ],
        },
        {
            "paper": f"第5.1节：implementation，支持 Uppaal/TChecker/LTSmin 风格输出与内置 fixpoint。页 {mighty_pages['implementation']}",
            "status": "部分实现",
            "analysis": "XML/TChecker 输出和内置 fixpoint 存在；LTSmin 不作为直接输出格式实现，而是 README/论文中的外部后端工作流。",
            "links": [
                code_link("tool/MightyPPL/main.cpp", r"--tck"),
                code_link("tool/MightyPPL/main.cpp", r"--xml"),
                code_link("tool/MightyPPL/main.cpp", r"tck <<"),
                code_link("tool/MightyPPL/main.cpp", r"xml <<"),
            ],
        },
        {
            "paper": f"第5.2节：MightyL、Acacia、food/lamp/Fischer/pinwheel 等实验。页 {mighty_pages['experiments']}",
            "status": "部分实现",
            "analysis": "仓库包含 MightyL/newhoxha/acacia 输入、若干 patch 和 MightyPPL_new_* 案例快照；论文完整表格结果与自动复现实验脚本没有完整落库。",
            "links": [
                code_link("tool/MightyPPL/testcases/MightyL/A-5-12.mitl", r"."),
                code_link("tool/MightyPPL/testcases/acacia/3.mitl", r"."),
                code_link("tool/MightyPPL/food.patch", r"."),
                code_link("tool/MightyPPL/MightyPPL_new_food.cpp", r"."),
            ],
        },
    ]

    moni_map = [
        {
            "paper": f"摘要/第1节：ABRV for timed properties under partial observability。页 {moni_pages['abstract']}, {moni_pages['intro']}",
            "status": "部分实现",
            "analysis": "代码实现 timed automata monitor、正/负 automata 双监控、interval/concrete/delay/testing 状态；但论文四值 verdict 的 OUT-OF-MODEL 在公开 API 中被压缩为 Single_monitor 内部 OUT，而 Monitor 对外只有三值。",
            "links": [
                code_link("tool/MoniTAal/src/monitaal/Monitor.h", r"enum single_monitor_answer_e"),
                code_link("tool/MoniTAal/src/monitaal/Monitor.h", r"enum monitor_answer_e"),
                code_link("tool/MoniTAal/src/monitaal/Monitor.cpp", r"Monitor<state_t>::input"),
            ],
        },
        {
            "paper": f"第2节：MITL、timed words、TA preliminaries。页 {moni_pages['prelim']}",
            "status": "工程化替代",
            "analysis": "代码不直接解析 MITL 公式，而是消费已构造/UPPAAL XML 风格的 positive/negative timed automata；MITL→TA 转换在论文中作为前置，实际由外部流程或 MightyPPL 提供。",
            "links": [
                code_link("tool/MoniTAal/src/monitaal/Parser.cpp", r"Parser::parse_file"),
                code_link("tool/MoniTAal/src/monitaal/TA.h", r"class\s+TA"),
                code_link("tool/MoniTAal/README.md", r"provide two timed buchi automata"),
            ],
        },
        {
            "paper": f"第3节：monitoring under assumptions，四类 verdict。页 {moni_pages['assumptions']}",
            "status": "部分实现",
            "analysis": "正 automaton 与负 automaton 的 state estimate 同步推进；positive/negative/out 逻辑存在，但 public verdict 为 INCONCLUSIVE/POSITIVE/NEGATIVE，未直接暴露论文的 unknown/out-of-model 四值接口。",
            "links": [
                code_link("tool/MoniTAal/src/monitaal/Monitor.cpp", r"_monitor_pos"),
                code_link("tool/MoniTAal/src/monitaal/Monitor.cpp", r"_monitor_neg"),
                code_link("tool/MoniTAal/src/monitaal/Monitor.cpp", r"if \(pos == OUT"),
            ],
        },
        {
            "paper": f"第4节：zone-based monitoring algorithm。页 {moni_pages['algorithm']}",
            "status": "已实现",
            "analysis": "Single_monitor 在每个输入事件上做 delay、edge transition、guard/invariant 检查、与 accepting space 相交；Fixpoint 基于 backward transitions 计算接受状态可达空间。",
            "links": [
                code_link("tool/MoniTAal/src/monitaal/Monitor.cpp", r"Single_monitor<state_t>::input"),
                code_link("tool/MoniTAal/src/monitaal/symbolic_state_base.cpp", r"do_transition\("),
                code_link("tool/MoniTAal/src/monitaal/Fixpoint.cpp", r"buchi_accept_fixpoint"),
            ],
        },
        {
            "paper": f"第4节：zone/DBM symbolic representation。页 {moni_pages['algorithm']}",
            "status": "已实现",
            "analysis": "状态封装 PARDIBAAL Federation/DBM；symbolic_state、delay_state、testing_state、concrete_state 分别覆盖区间时间、延迟/抖动、输入输出部分可观测和具体时间点。",
            "links": [
                code_link("tool/MoniTAal/src/monitaal/types.h", r"using Federation"),
                code_link("tool/MoniTAal/src/monitaal/state.h", r"struct symbolic_state_t"),
                code_link("tool/MoniTAal/src/monitaal/state.h", r"struct delay_state_t"),
                code_link("tool/MoniTAal/src/monitaal/state.h", r"struct testing_state_t"),
            ],
        },
        {
            "paper": f"第5节：evaluation，assumptions 可提前 verdict/处理不可观测行为。页 {moni_pages['evaluation']}",
            "status": "部分实现",
            "analysis": "仓库有 presentation examples、DelayTest、Monitor_test 和 gear controller benchmark；论文表格级实验结果与 UPPAAL 集成脚本不完整，部分实验材料以 C++ benchmark/header 与 XML 形式存在。",
            "links": [
                code_link("tool/MoniTAal/test/DelayTest.cpp", r"delay_test1"),
                code_link("tool/MoniTAal/test/Presentation_examples.cpp", r"presentation_interval"),
                code_link("tool/MoniTAal/benchmark/main.cpp", r"main"),
                code_link("tool/MoniTAal/benchmark/gear-control-properties.xml", r"."),
            ],
        },
        {
            "paper": f"第6-7节：related work/conclusion。页 {moni_pages['related']}, {moni_pages['conclusion']}",
            "status": "未发现实现",
            "analysis": "相关工作和结论是论文论述，不对应可执行代码；报告中只保留它们对实现边界的启示。",
            "links": [],
        },
    ]

    cross_map = [
        [
            "构建依赖",
            "MightyPPL 直接使用相邻 MoniTAal 工作树，构建时安装 MoniTAal headers/libs 到 MightyPPL external/monitaal。",
            code_link("tool/MightyPPL/CMakeLists.txt", r"SOURCE_DIR .*MoniTAal"),
        ],
        [
            "TA 数据结构",
            "MightyPPL 生成 BDD-labelled TA；在投影/输出/内置检查时转换或复用 MoniTAal TA。",
            code_link("tool/MightyPPL/TAwithBDDEdges.h", r"class\s+TAwithBDDEdges")
            + "<br>"
            + code_link("tool/MoniTAal/src/monitaal/TA.h", r"class\s+TA"),
        ],
        [
            "Zone/Fixpoint",
            "MightyPPL 无输出文件时把构造出的 automaton 交给 MoniTAal Fixpoint 做 satisfiability/backward analysis。",
            code_link("tool/MightyPPL/main.cpp", r"Fixpoint<monitaal::symbolic_state_t>")
            + "<br>"
            + code_link("tool/MoniTAal/src/monitaal/Fixpoint.cpp", r"Fixpoint<state_t>::reach"),
        ],
        [
            "实验/测试关系",
            "MightyPPL testcases 对应论文 verification benchmarks；MoniTAal tests/benchmark 对应 runtime monitoring examples。",
            code_link("tool/MightyPPL/testcases/MightyL/A-5-12.mitl", r".")
            + "<br>"
            + code_link("tool/MoniTAal/test/Monitor_test.cpp", r"BOOST_AUTO_TEST_CASE"),
        ],
    ]

    gaps = [
        [
            badge("部分实现"),
            "MightyPPL 论文实验表格与所有外部后端命令没有完整自动复现脚本；仓库保留输入、patch 和案例快照。",
            code_link("tool/MightyPPL/testcases/MightyL/A-5-12.mitl", r".") + "<br>" + code_link("tool/MightyPPL/MightyPPL_new_food.cpp", r"."),
        ],
        [
            badge("未发现实现"),
            "MightyPPL 论文中的完整证明、复杂度论证、可读算法编号没有作为代码注释/文档实现；代码主要是构造器实现。",
            code_link("tool/MightyPPL/PnueliFn.cpp", r"build_pnuelifn"),
        ],
        [
            badge("部分实现"),
            "MoniTAal 论文四值 verdict（含 unknown/out-of-model）在对外 Monitor API 中不是四值枚举；内部 Single_monitor 有 OUT，最终 Monitor 暴露三值。",
            code_link("tool/MoniTAal/src/monitaal/Monitor.h", r"enum single_monitor_answer_e") + "<br>" + code_link("tool/MoniTAal/src/monitaal/Monitor.h", r"enum monitor_answer_e"),
        ],
        [
            badge("工程化替代"),
            "MoniTAal 不直接解析 MITL 公式，而是要求正/负 timed automata；这与论文方法链一致，但公式到 automata 的步骤在本仓库外部。",
            code_link("tool/MoniTAal/README.md", r"provide two timed buchi automata"),
        ],
        [
            badge("论文未覆盖但代码存在"),
            "MightyPPL 有多个 `MightyPPL_new_*` 和 `.patch` 文件，像是实验模型快照/调试材料，论文未逐文件解释。",
            code_link("tool/MightyPPL/MightyPPL_new_lamp.cpp", r".") + "<br>" + code_link("tool/MightyPPL/lamp.patch", r"."),
        ],
        [
            badge("论文未覆盖但代码存在"),
            "MoniTAal 包含 CLI 交互逻辑、输入 parser 单元测试、gear controller benchmark 转换辅助脚本；这些是工程化外围。",
            code_link("tool/MoniTAal/src/monitaal-bin/main.cpp", r"interactive_monitoring") + "<br>" + code_link("tool/MoniTAal/benchmark/uctr-to-monpoly.py", r"."),
        ],
    ]

    mighty_dirs = rows([[html.escape(k), str(v)] for k, v in inv["mighty_groups"].items()])
    moni_dirs = rows([[html.escape(k), str(v)] for k, v in inv["monitaal_groups"].items()])

    mighty_sections = [
        ("Abstract", "工具目标、支持表达力、输出 backends、实验概述", mighty_pages["abstract"]),
        ("1 Introduction", "MITL 局限、Pnueli modalities 动机、完整验证目标", mighty_pages["intro"]),
        ("2 Preliminaries", "MTLPPL、Timed Automata、组合式翻译背景", mighty_pages["prelim"]),
        ("3 Past MITL and Pnueli Modalities", "past tester 与 Pnueli tester 构造", mighty_pages["past_pnueli"]),
        ("4 General Time Intervals and Sequentialisation", "一般区间、转换、顺序化", mighty_pages["sequential"]),
        ("5 Implementation and Experiments", "实现模式、后端、benchmark/case studies", mighty_pages["implementation"]),
        ("6 Conclusion", "贡献总结与边界", mighty_pages["conclusion"]),
    ]
    moni_sections = [
        ("Abstract", "assumption-based runtime verification 概要", moni_pages["abstract"]),
        ("1 Introduction", "partial observability、prognosis/diagnosis 动机", moni_pages["intro"]),
        ("2 Preliminaries", "timed words、MITL、TA 背景", moni_pages["prelim"]),
        ("3 Monitoring Under Assumptions", "ABRV 问题定义与 verdict", moni_pages["assumptions"]),
        ("4 A Zone-Based Monitoring Algorithm", "zone/state estimate 算法", moni_pages["algorithm"]),
        ("5 Evaluation", "case studies 与响应时间结果", moni_pages["evaluation"]),
        ("6 Related Work / 7 Conclusion", "边界与定位", moni_pages["related"]),
    ]

    css = """
    :root{--bg:#f7f8fb;--panel:#fff;--ink:#182235;--muted:#667085;--line:#d8dde8;--blue:#1d5fd1;--green:#15803d;--amber:#a15c00;--red:#b42318;--violet:#6d28d9}
    *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    header{padding:32px 40px;background:#111827;color:#fff} header h1{margin:0 0 8px;font-size:30px} header p{margin:0;color:#d1d5db;max-width:1120px}
    nav{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);z-index:2;padding:10px 40px;display:flex;gap:14px;flex-wrap:wrap} nav a{color:var(--blue);text-decoration:none;font-weight:600}
    main{max-width:1280px;margin:0 auto;padding:28px 28px 80px} section{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:0 0 24px;padding:24px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
    h2{margin:0 0 16px;font-size:24px} h3{margin:26px 0 10px;font-size:19px} h4{margin:0 0 6px;font-size:16px} p{margin:8px 0} .muted{color:var(--muted)} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
    .card{border:1px solid var(--line);border-radius:8px;padding:14px;background:#fbfcff}.card p{margin:0}.kpi{font-size:28px;font-weight:800;color:#111827}.code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#0f4fb5;text-decoration:none;word-break:break-all}
    table{width:100%;border-collapse:collapse;margin:10px 0 18px;background:#fff} th,td{border:1px solid var(--line);padding:9px 10px;vertical-align:top} th{background:#eef2f8;text-align:left} tr:nth-child(even) td{background:#fcfdff}
    .badge{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:700;white-space:nowrap}.ok{background:#dcfce7;color:#166534}.partial{background:#fef3c7;color:#92400e}.missing{background:#fee2e2;color:#991b1b}.extra{background:#ede9fe;color:#5b21b6}
    .diagram{width:100%;max-width:1120px;border:1px solid var(--line);border-radius:8px;background:#fff;margin:12px 0}.matrix td:first-child{font-weight:700}.small{font-size:13px}.toc-list{columns:2}.warn{border-left:5px solid var(--amber);padding:10px 12px;background:#fff7ed}.good{border-left:5px solid var(--green);padding:10px 12px;background:#f0fdf4}
    details{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:10px 0;background:#fcfdff} summary{font-weight:700;cursor:pointer}
    """

    workflow_svg = """
    <svg class="diagram" viewBox="0 0 1100 260" role="img" aria-label="overall workflow">
      <defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#1d5fd1"/></marker></defs>
      <rect x="30" y="40" width="170" height="70" rx="8" fill="#e0f2fe" stroke="#0284c7"/><text x="115" y="72" text-anchor="middle" font-weight="700">MITPPL 公式</text><text x="115" y="94" text-anchor="middle" font-size="13">MightyPPL 输入</text>
      <rect x="250" y="40" width="190" height="70" rx="8" fill="#eef2ff" stroke="#4f46e5"/><text x="345" y="72" text-anchor="middle" font-weight="700">Parser + Visitors</text><text x="345" y="94" text-anchor="middle" font-size="13">typing / NNF / IDs / BDD</text>
      <rect x="490" y="40" width="190" height="70" rx="8" fill="#fef3c7" stroke="#d97706"/><text x="585" y="72" text-anchor="middle" font-weight="700">Tester TAs</text><text x="585" y="94" text-anchor="middle" font-size="13">MITL / Past / Pnueli</text>
      <rect x="730" y="40" width="160" height="70" rx="8" fill="#dcfce7" stroke="#16a34a"/><text x="810" y="72" text-anchor="middle" font-weight="700">TA Product</text><text x="810" y="94" text-anchor="middle" font-size="13">flatten / projection</text>
      <rect x="930" y="20" width="140" height="55" rx="8" fill="#fae8ff" stroke="#a21caf"/><text x="1000" y="53" text-anchor="middle" font-weight="700">XML/TCK</text>
      <rect x="930" y="95" width="140" height="55" rx="8" fill="#fae8ff" stroke="#a21caf"/><text x="1000" y="128" text-anchor="middle" font-weight="700">Fixpoint</text>
      <rect x="360" y="170" width="390" height="60" rx="8" fill="#ecfeff" stroke="#0891b2"/><text x="555" y="198" text-anchor="middle" font-weight="700">MoniTAal / PARDIBAAL</text><text x="555" y="218" text-anchor="middle" font-size="13">TA, DBM/Federation, online monitor, accepting-space fixpoint</text>
      <path d="M200 75 H250" stroke="#1d5fd1" stroke-width="3" marker-end="url(#a)"/><path d="M440 75 H490" stroke="#1d5fd1" stroke-width="3" marker-end="url(#a)"/><path d="M680 75 H730" stroke="#1d5fd1" stroke-width="3" marker-end="url(#a)"/><path d="M890 75 C910 75 910 48 930 48" stroke="#1d5fd1" stroke-width="3" fill="none" marker-end="url(#a)"/><path d="M890 75 C910 75 910 123 930 123" stroke="#1d5fd1" stroke-width="3" fill="none" marker-end="url(#a)"/><path d="M585 110 V170" stroke="#0891b2" stroke-width="3" marker-end="url(#a)"/><path d="M810 110 C810 205 750 200 750 200" stroke="#0891b2" stroke-width="3" fill="none" marker-end="url(#a)"/>
    </svg>
    """

    mon_svg = """
    <svg class="diagram" viewBox="0 0 980 260" role="img" aria-label="monitor loop">
      <defs><marker id="b" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#15803d"/></marker></defs>
      <rect x="35" y="45" width="165" height="66" rx="8" fill="#e0f2fe" stroke="#0284c7"/><text x="118" y="75" text-anchor="middle" font-weight="700">Timed input</text><text x="118" y="96" text-anchor="middle" font-size="13">concrete / interval</text>
      <rect x="250" y="45" width="170" height="66" rx="8" fill="#fef3c7" stroke="#d97706"/><text x="335" y="75" text-anchor="middle" font-weight="700">State estimate</text><text x="335" y="96" text-anchor="middle" font-size="13">delay + transition</text>
      <rect x="470" y="20" width="170" height="58" rx="8" fill="#dcfce7" stroke="#16a34a"/><text x="555" y="54" text-anchor="middle" font-weight="700">Positive TA</text>
      <rect x="470" y="105" width="170" height="58" rx="8" fill="#fee2e2" stroke="#dc2626"/><text x="555" y="139" text-anchor="middle" font-weight="700">Negative TA</text>
      <rect x="705" y="45" width="220" height="66" rx="8" fill="#ede9fe" stroke="#7c3aed"/><text x="815" y="75" text-anchor="middle" font-weight="700">Verdict</text><text x="815" y="96" text-anchor="middle" font-size="13">POSITIVE / NEGATIVE / INCONCLUSIVE</text>
      <rect x="315" y="180" width="350" height="48" rx="8" fill="#ecfeff" stroke="#0891b2"/><text x="490" y="210" text-anchor="middle" font-weight="700">Accepting-space backward fixpoint</text>
      <path d="M200 78 H250" stroke="#15803d" stroke-width="3" marker-end="url(#b)"/><path d="M420 78 H470" stroke="#15803d" stroke-width="3" marker-end="url(#b)"/><path d="M640 49 C680 49 680 65 705 65" stroke="#15803d" stroke-width="3" fill="none" marker-end="url(#b)"/><path d="M640 134 C680 134 680 91 705 91" stroke="#15803d" stroke-width="3" fill="none" marker-end="url(#b)"/><path d="M490 180 C455 150 440 95 420 78" stroke="#0891b2" stroke-width="3" fill="none" marker-end="url(#b)"/>
    </svg>
    """

    heat_rows = [
        ["MightyPPL parser/visitors", badge("已实现"), "强"],
        ["MightyPPL past modality testers", badge("已实现"), "强"],
        ["MightyPPL Pnueli/sequentialisation", badge("部分实现"), "中-强"],
        ["MightyPPL experiment reproduction scripts", badge("部分实现"), "中"],
        ["MoniTAal zone algorithm", badge("已实现"), "强"],
        ["MoniTAal four-valued ABRV API", badge("部分实现"), "中"],
        ["MoniTAal UPPAAL-based paper implementation", badge("部分实现"), "中"],
        ["MoniTAal formula-to-automata frontend", badge("未发现实现"), "弱"],
    ]

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MightyPPL / MoniTAal 论文-代码完整映射报告</title>
  <style>{css}</style>
</head>
<body>
<header>
  <h1>MightyPPL / MoniTAal 论文-代码完整映射报告</h1>
  <p>生成时间：{html.escape(stat['generated_at'])}。分析对象是当前工作树：<code>/home/lqq/download/TAFuzz/tool/MightyPPL</code> 与 <code>/home/lqq/download/TAFuzz/tool/MoniTAal</code>。报告只摘要论文，不复制长段原文。</p>
</header>
<nav>
  <a href="#overview">总览</a><a href="#papers">论文章节</a><a href="#mighty">MightyPPL</a><a href="#monitaal">MoniTAal</a><a href="#cross">交叉关系</a><a href="#gaps">缺口</a><a href="#inventory">代码全景</a><a href="#verification">验证</a>
</nav>
<main>
<section id="overview">
  <h2>1. 项目总览</h2>
  <div class="grid">
    <div class="card"><h4>MightyPPL 论文</h4><p><b>MightyPPL: Verification of MITL with Past and Pnueli Modalities</b><br>PDF 页数：<span class="kpi">{mighty_pdf['page_count']}</span></p></div>
    <div class="card"><h4>MoniTAal 论文</h4><p><b>Exploiting Assumptions for Effective Monitoring of Real-Time Properties Under Partial Observability</b><br>PDF 页数：<span class="kpi">{moni_pdf['page_count']}</span></p></div>
    <div class="card"><h4>代码规模</h4><p>MightyPPL：<b>{len(inv['mighty_files'])}</b> 个 tracked/source 文件<br>MoniTAal：<b>{len(inv['monitaal_files'])}</b> 个 tracked/source 文件</p></div>
  </div>
  <p class="good">当前实现关系：MightyPPL 通过相对路径直接构建相邻 MoniTAal 工作树；MoniTAal 提供 TA、zone/DBM 状态、backward fixpoint 与 online monitor 基础设施。下图是整体工作流图。</p>
  {workflow_svg}
</section>

<section id="papers">
  <h2>2. 论文章节覆盖</h2>
  <div class="grid">
    <div>
      <h3>MightyPPL 论文主章节</h3>
      <table><thead><tr><th>章节</th><th>内容</th><th>页</th></tr></thead><tbody>{rows([[html.escape(a), html.escape(b), str(c or '未定位')] for a,b,c in mighty_sections])}</tbody></table>
    </div>
    <div>
      <h3>MoniTAal 论文主章节</h3>
      <table><thead><tr><th>章节</th><th>内容</th><th>页</th></tr></thead><tbody>{rows([[html.escape(a), html.escape(b), str(c or '未定位')] for a,b,c in moni_sections])}</tbody></table>
    </div>
  </div>
  <p class="muted">页码由 `pypdf` 对本地 Zotero PDF 抽取文本后定位，详见 <code>analysis/data/paper_sections.json</code> 和 <code>*_paper_pages.json</code>。</p>
</section>

<section id="mighty">
  <h2>3. MightyPPL 专章：论文方法与代码实现映射</h2>
  <p>MightyPPL 的实现不是一个单体算法文件，而是一条 compiler-style pipeline：ANTLR grammar → visitors → temporal atom tester builders → BDD-labelled TA → product/projection/output/fixpoint。</p>
  {section_table("3.1 逐章节映射", mighty_map)}
  <h3>3.2 MightyPPL pipeline 图</h3>
  {workflow_svg}
  <details open><summary>实现判断摘要</summary>
    <ul>
      <li>语法与 modal coverage 较完整：`Mitl.g4` 和 visitor 类覆盖论文中的主要 operators。</li>
      <li>论文的理论构造被工程化拆分到 `Finally/Once/.../Pnueli*.cpp`，没有统一的“算法编号”实现文件。</li>
      <li>BDD transition encoding 是代码的重要工程贡献，对应论文中 symbolic encoding/状态压缩叙述。</li>
      <li>实验输入存在，但完整论文实验流水线与外部后端复现实验未完整脚本化。</li>
    </ul>
  </details>
</section>

<section id="monitaal">
  <h2>4. MoniTAal 专章：论文方法与代码实现映射</h2>
  <p>MoniTAal 当前仓库更像 timed automata monitor kernel：它不从 MITL 文本直接生成 automata，而是解析/接收 positive 和 negative timed automata，再对 timed observations 做在线状态估计与 verdict 更新。</p>
  {section_table("4.1 逐章节映射", moni_map)}
  <h3>4.2 MoniTAal monitor loop 图</h3>
  {mon_svg}
  <details open><summary>实现判断摘要</summary>
    <ul>
      <li>zone-based monitoring 主循环和 accepting-space fixpoint 有明确代码实现。</li>
      <li>partial observability/assumption 论文中的概念在代码里主要体现为 `delay_state_t`、`testing_state_t`、positive/negative automata state estimates。</li>
      <li>公开 verdict API 是三值，论文四值 ABRV 接口没有原样暴露。</li>
      <li>UPPAAL XML parsing 与 CLI 是工程接口，支撑论文实验但不是理论核心。</li>
    </ul>
  </details>
</section>

<section id="cross">
  <h2>5. 交叉映射：MightyPPL 如何复用 MoniTAal</h2>
  <table><thead><tr><th>关系</th><th>分析</th><th>代码证据</th></tr></thead><tbody>{rows(cross_map)}</tbody></table>
</section>

<section id="gaps">
  <h2>6. 缺口、偏差与论文未覆盖代码</h2>
  <table><thead><tr><th>状态</th><th>说明</th><th>证据</th></tr></thead><tbody>{rows(gaps)}</tbody></table>
  <h3>6.1 论文章节到代码模块覆盖矩阵与实现/未实现热力图</h3>
  <table class="matrix"><thead><tr><th>主题</th><th>状态</th><th>覆盖强度</th></tr></thead><tbody>{rows(heat_rows)}</tbody></table>
</section>

<section id="inventory">
  <h2>7. 代码全景：不能只看论文对应部分</h2>
  <div class="grid">
    <div>
      <h3>MightyPPL 文件分布</h3>
      <table><thead><tr><th>分组</th><th>文件数</th></tr></thead><tbody>{mighty_dirs}</tbody></table>
    </div>
    <div>
      <h3>MoniTAal 文件分布</h3>
      <table><thead><tr><th>分组</th><th>文件数</th></tr></thead><tbody>{moni_dirs}</tbody></table>
    </div>
  </div>
  <details><summary>MightyPPL 全文件清单</summary><p class="small">{'<br>'.join(html.escape(x) for x in inv['mighty_files'])}</p></details>
  <details><summary>MoniTAal 全文件清单</summary><p class="small">{'<br>'.join(html.escape(x) for x in inv['monitaal_files'])}</p></details>
</section>

<section id="verification">
  <h2>8. 验证与复查材料</h2>
  <table><thead><tr><th>项目</th><th>结果</th></tr></thead><tbody>
    <tr><td>MightyPPL git status</td><td><pre>{html.escape(stat['mighty_status'])}</pre></td></tr>
    <tr><td>MoniTAal git status</td><td><pre>{html.escape(stat['monitaal_status'])}</pre></td></tr>
    <tr><td>mitppl --help</td><td><pre>{html.escape(stat['mitppl_help'][:1200])}</pre></td></tr>
  </tbody></table>
  <p class="warn">未重新验证项：本报告没有重新运行完整 spec-based 语义测试，也没有复现论文实验表格。它记录当前已知 `mitppl --help` 可运行，并把完整复现实验列为缺口。</p>
  <p>中间数据：{code_link('analysis/data/paper_sections.json', r'.', 'paper_sections.json')}，
  {code_link('analysis/data/code_inventory.json', r'.', 'code_inventory.json')}，
  {code_link('analysis/data/status_snapshot.json', r'.', 'status_snapshot.json')}。</p>
</section>
</main>
</body>
</html>
"""

    REPORT.write_text(html_doc, encoding="utf-8")

    mapping_data = {
        "mighty_map": mighty_map,
        "monitaal_map": moni_map,
        "cross_map": cross_map,
        "gaps": gaps,
        "note": "HTML fields contain already-rendered links/badges for the static report.",
    }
    (DATA_DIR / "mapping_summary.json").write_text(json.dumps(mapping_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(REPORT)


if __name__ == "__main__":
    main()
