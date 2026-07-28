# Milestone 5：冻结当前源码的 AP 多对多绑定

本阶段只回答“命题对应当前源码的什么语义实体、在哪里、怎样观察”，没有从实现控制流生成或修改性质，也没有判断实现是否满足性质。

## 结果

| 系统 | 性质 | AP | source bindings | MAVLink observations | compile DB |
|---|---:|---:|---:|---:|---|
| ArduPilot | 7 | 25 | 107 | 43 | 1,543 entries |
| PX4 | 6 | 21 | 120 | 34 | 868 entries / 826 unique files |
| 合计 | 13 | 46 | 227 | 77 | — |

性质状态：ArduPilot 为 6 条 `REVIEW_READY`、1 条低权威 `CANDIDATE`；PX4 为 3 条 `REVIEW_READY`、3 条 `NEEDS_CONTEXT`。没有 `ACCEPTED` 性质，所有记录仍为 `implementation_satisfaction: NOT_ASSESSED`。

AP 观测分类：`DIRECT=9`、`DERIVED=6`、`CONDITIONAL=13`、`INSTRUMENTATION_REQUIRED=16`、`UNRESOLVED=2`。这 77 条消息/字段记录全部是固定 XML 与源码的静态证据，运行时状态均为 `NOT_RUN_NO_CAPTURE`。

## 编译与语义核验

- ArduPilot：保留既有 Copter build，再用 `/home/lqq/anaconda3/bin/python ./waf plane rover` 成功补齐 Plane/Rover；compile database 覆盖所选 Copter、Plane、Rover 与 AP_BattMonitor 单元。
- PX4：固定 v1.17.0 gitlink 初始化 6 个构建必需 submodule，`make px4_sitl_default -j2` 完成 1095/1095；没有更新到 gitlink 之外的提交。
- 38 个直接出现在 compile database 的所选翻译单元通过 clangd 语义解析。ArduPilot 23/23 为 `PASS`；PX4 14 为 `PASS`，`Commander.cpp` 为 `PASS_WITH_TWEAK_DIAGNOSTICS`（只有 ExtractFunction code-action 对 break/continue 的诊断，无 AST/compile error）。
- PX4 的 `commander_params.c`、`rtl_params.c` 是参数生成输入而非普通编译单元；它们的路径、行号、参数名与生成的 parameters metadata 独立校验，不冒充直接 compile entry。

## 文件

- `ardupilot_binding_audit.json`：25/25 AP、107 个绑定及逐 AP 未决项。
- `px4_binding_audit.json`：21/21 AP、120 个绑定及逐 AP 未决项。
- `mavlink_ap_observation_audit.json`：46 个 AP 的静态 MAVLink/插桩分类。
- `compile_database_manifest.json`：编译库哈希、构建结果、固定 submodule 和审计验证。
- `source_binding_validation_summary.json`：统一验证统计与 clangd 结果。

复现：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_mavlink_ap_observations.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 5
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 5
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_source_bindings.py --run-clangd
```
