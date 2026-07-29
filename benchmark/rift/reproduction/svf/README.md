# SVF 3.2 官方基线复现记录

## 结论

复现状态为 `REPRODUCED_MINIMAL_WPA_SVFG_SMOKE`。

官方 `SVF-3.2` tag 在 commit
`197a6590bd9c695a9c3daf52622dea912ef9a002` 上使用 Clang/LLVM 18.1.8、
Z3 4.8.12 和 CMake 3.28.6 完成 124/124 个构建目标，全程没有修改官方源码。
最小 `wpa -ander -alias-check -svfg -stat` 用例同时通过一个跨函数
`MAYALIAS` 和一个独立对象 `NOALIAS` oracle，并实际构造了 MemorySSA 与完整
SVFG。

这证明 SVF 3.2 可以作为 RIFT 的通用 value-flow 基础和强基线；它不证明
SVF 自身已经提供 AP 绑定、外部可控性、异步/生命周期语义、MITL residual 或
mutation recipe，也不是 RIFT 方法的实现。

## 冻结身份与构建环境

| 项目 | 冻结值 |
|---|---|
| 官方仓库 | `https://github.com/SVF-tools/SVF.git` |
| tag / commit | `SVF-3.2` / `197a6590bd9c695a9c3daf52622dea912ef9a002` |
| Git tree | `dab507aca71987a0988ac9deef45b6da9e14e4b2` |
| 源码状态 | clean；无 patch |
| OS | Ubuntu 22.04.5 LTS / WSL2 x86_64 |
| 编译器与 LLVM | Clang 18.1.8 / LLVM 18.1.8，RTTI on |
| Z3 | system `libz3-dev` 4.8.12 |
| 构建器 | Ninja 1.10.1，4 jobs |
| 资源上限 | `ulimit -v 12582912`，即 12 GiB |

系统 CMake 3.22.1 低于 SVF `cmake_minimum_required(VERSION 3.23)`，因此没有
放宽上游约束，而是临时使用 Kitware 官方 CMake 3.28.6。下载包 SHA-256 为
`931e3c0d546ee03ca72bb147ccd9b49e3b6252f765f66bf21b9d165519940458`，
与同一 release 的官方 checksum 文件一致；二进制没有复制进 workspace。

官方 tag 的 `build.sh` 已把 `MajorLLVMVer=18` 固定为 LLVM 18。本次使用系统
LLVM 18 package 而非脚本下载的预编译包，按同一 CMake 配置接口构建；官方源码
无需兼容性 patch。完整配置见 `build/CMakeCache.txt` 和 `raw/configure.log`。

## 原始构建结果

```text
configure: exit 0, wall 6.40 s, peak RSS 89,652 KiB
build:     exit 0, 124/124 targets, wall 134.72 s, peak RSS 696,096 KiB
install:   exit 0, wall 0.04 s, peak RSS 9,336 KiB
```

核心产物：

- `build/bin/wpa`；
- `build/lib/libSvfCore.so.3.2`；
- `build/lib/libSvfLLVM.so.3.2`；
- `build/lib/extapi.bc`；
- 安装树的 `SVF::SvfCore`、`SVF::SvfLLVM` CMake targets。

tag 快照不包含 `Test-Suite` 目录或 gitlink。上游 CMake 只在该目录存在时注册
CTest，因此 `ctest -N` 合法返回 `Total Tests: 0`。本记录没有把“零测试”写成
Test-Suite 通过，而是按照 M1 允许条件运行官方 `wpa` 的最小可验证用例。

## 最小 WPA / SVFG smoke

输入 `cases/alias_valueflow_smoke.c` 使用 SVF
`PointerAnalysis::validateTests` 原生识别的 `MAYALIAS` 和 `NOALIAS` 函数名。
它包括跨函数 pointer return、写入和两个不同全局对象。该文件只编译为 bitcode，
不链接或执行：

```sh
/usr/bin/clang-18 -g -O0 -fno-discard-value-names -emit-llvm -c \
  benchmark/rift/reproduction/svf/cases/alias_valueflow_smoke.c \
  -o benchmark/rift/reproduction/svf/results/alias_valueflow_smoke.bc

cd benchmark/rift/reproduction/svf/results
../build/bin/wpa -ander -alias-check -svfg -stat alias_valueflow_smoke.bc
```

观测结果：

```text
exit = 0
MAYALIAS = SUCCESS
NOALIAS = SUCCESS
MemorySSA = 8 regions, 10 LoadMu, 8 StoreChi
SVFG = 78 nodes, 75 edges (44 direct, 31 indirect)
wall = 0.07 s
peak RSS = 55,976 KiB
```

输出开头有两条 `npm: not found`。它来自 SVF 的 package-metadata probe；oracle、
MemorySSA、SVFG 和退出码均正常，因此作为非致命环境噪声原样保留，没有删除。

## 对 RIFT 的可移植接口边界

可直接放进项目无关 core adapter 的接口：

- `LLVMModuleSet`：读取一个或多个 LLVM 18 bitcode module；
- `SVFIRBuilder` / `SVFIR`：PAG、statement、abstract object；
- `ICFG` 与 call graph；
- `AndersenWaveDiff` 的 points-to set 和 alias query；
- `MemorySSA`、`SVFGBuilder::buildFullSVFG` 和 SVFG node/edge traversal；
- 安装包导出的 `SVF::SvfCore` 与 `SVF::SvfLLVM`。

必须留在外部、版本化 model pack 的事实：

- typed MITL AP role 到 source/SVF node 的绑定；
- 配置、协议字段、传感器等 fuzzable source 与 framework entry；
- timer、scheduler、callback、queue 的事件语义；
- object instance、phase、session、scope 和 generation；
- libcoap/MQTT/MAVLink/ArduPilot parser、dispatcher、parameter store；
- mutation direction、deadline window 和 prerequisite sequence。

硬约束是通用 SVF adapter 不得编译进任何 libcoap、MQTT、MAVLink 或 ArduPilot
符号。SVF 的 external API model（`extapi.bc`）可作为框架机制，但具体 SUT 语义仍
必须由 model pack 提供并记录 provenance。

`cases/api_consumer` 另做了一个不修改上游的安装包 compile/link 检查，确认外部
CMake target 可消费。之后的临时 runtime diagnostic 能加载 bitcode 并构造对象，
但 `getTotalEdgeNum()` 返回 0，而官方 `wpa -svfg -stat` 报告 75 条边；因此该 API
计数被明确排除在 acceptance 之外，不据此声称 traversal 正确。本次 SVFG 正确性
证据只采用官方 `wpa` 的 78 nodes/75 edges 原始输出。诊断命令和精简输出保存在
`raw/api-runtime-diagnostic.txt`。

## 结论边界

本次支持的结论只有：

1. 冻结的官方 SVF 3.2 源码可在 LLVM 18.1.8 上无 patch 构建；
2. 官方 `wpa` 可完成 AndersenWaveDiff、两个 alias oracle、MemorySSA 和完整 SVFG；
3. 这些接口适合作为统一 schema 下的通用 value-flow baseline/substrate。

尚未支持：

- 官方 Test-Suite 或大型真实项目的精度、时间和内存结论；
- SVF backward slice 对 RIFT-M2 gold corpus 的 recall/precision；
- AP truth-change、external frontier、control/event/timing/lifecycle 或 recipe 能力；
- RIFT 相对 SVF 的任何优势结论。

## 验证

在 TAFuzz 根目录执行：

```sh
python3 benchmark/rift/reproduction/svf/validate_reproduction.py
```

validator 会检查 tag/commit/tree、官方源码 clean 状态、冻结文件哈希、LLVM 18
配置证据、124/124 build、12 GiB 资源上限、bitcode 有效性和动态库解析，并实时
重跑最小 `wpa` oracle。机器可读事实位于 `artifact_manifest.json`，原始输出位于
`raw/`。
