from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .common import load_json


STATUS_ZH = {
    "CONFIRMED_EFFECT": "确认影响：至少两次重复方向一致，输入和恢复均得到验证。",
    "LEGACY_ONLY_CANDIDATE": "仅旧规则候选：只有 PGFuzz 标准差规则命中。",
    "NO_OBSERVED_EFFECT": "未观测到影响：仅限本次模式、取值和时间窗。",
    "INCONCLUSIVE": "无法判断：输入、消息、重复或恢复证据不足。",
}

EXECUTION_CLASS_ZH = {
    "READY_SAFE": "具备受支持的合法取值和恢复方法，可进入默认计划。",
    "REQUIRES_PRECONDITION": "需要模式、设备或状态准备，默认不执行。",
    "REQUIRES_RESTART": "需要重启才能可靠生效，默认不执行。",
    "DISRUPTIVE_EXCLUDED": "会擦除、关机、终止或格式化，默认排除。",
    "UNKNOWN_METADATA": "类型、范围或可写性证据不足，默认不执行。",
}


def write_report(run_dir: Path) -> Path:
    catalog = load_json(run_dir / "input_catalog.json")
    plan = load_json(run_dir / "experiment_plan.json") if (run_dir / "experiment_plan.json").exists() else None
    effects_doc: dict[str, Any] = ({"effects": []} if not (run_dir / "input_state_effects.json").exists()
                                   else load_json(run_dir / "input_state_effects.json"))
    effects = effects_doc.get("effects", [])
    input_types = Counter(row["input_type"] for row in catalog["inputs"])
    classes = Counter(row["execution_class"] for row in catalog["inputs"])
    statuses = Counter(row["status"] for row in effects)
    lines = [
        "# PGFuzz 当前 ArduCopter 动态输入—状态报告", "",
        "## 术语与状态", "",
        "- **PGFuzz**：`Policy-Guided Fuzzing`，策略引导模糊测试。", 
        "- **SITL**：`Software in the Loop`，软件在环仿真。", 
        "- **INPUT_P**：普通配置参数输入；**INPUT_C**：用户命令输入；"
        "**INPUT_E**：仿真环境参数输入。", 
    ]
    for status, explanation in STATUS_ZH.items():
        lines.append(f"- `{status}`：{explanation}")
    for execution_class, explanation in EXECUTION_CLASS_ZH.items():
        lines.append(f"- `{execution_class}`：{explanation}")
    lines.extend([
        "", "## 当前输入目录", "",
        f"- `INPUT_P`：{input_types['INPUT_P']}；`INPUT_C`：{input_types['INPUT_C']}；"
        f"`INPUT_E`：{input_types['INPUT_E']}。",
        "- 执行分类：" + "，".join(f"`{key}`={value}" for key, value in sorted(classes.items())) + "。",
    ])
    if plan:
        lines.extend([
            "", "## 实验计划", "",
            f"- 分片：{plan['shard_index'] + 1}/{plan['shard_count']}；工作项：{plan['work_item_count']}。",
            f"- 每项重复：{plan['repetitions']}；每个观测窗口：{plan['window_seconds']} 秒。",
        ])
    lines.extend([
        "", "## 结果", "",
        f"- 已汇总工作项：{len(effects)}。",
        "- 状态分布：" + ("，".join(f"`{key}`={value}" for key, value in sorted(statuses.items()))
                         if statuses else "尚未执行动态工作项。"),
        "", "## 证据边界", "",
        "主机单调时钟只用于发送、接收和窗口顺序；消息自带飞控时间字段原样保存。"
        "主机接收时间不是飞控内部事件真实发生时间。当前结果只适用于记录的提交、"
        "SITL 模型、输入值、模式和前置状态，不构成真实硬件或性质符合性结论。", "",
    ])
    if effects:
        lines.extend(["## 逐输入摘要", ""])
        for effect in effects:
            protocol_field = effect.get("protocol_field")
            field_text = f"；协议字段=`{protocol_field}`" if protocol_field else ""
            lines.append(
                f"- `{effect['input_name']}` / `{effect['mutation_value']}`："
                f"`{effect['status']}`；确认状态={effect.get('confirmed_groups', [])}；"
                f"旧规则状态={effect.get('legacy_groups', [])}{field_text}。")
        lines.append("")
    path = run_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
