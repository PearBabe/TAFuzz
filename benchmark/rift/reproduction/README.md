# RIFT-M1 复现总门禁

## 结论

RIFT-M1 的 **pre-core 总门禁为 `PASS`**。这个结论严格来自七个必需步骤：

```text
原始 LTL-Fuzzer Automata 组件 PASS
∧ public Problem1 执行 PASS
∧ libcoap Clang/LLVM 18 三次确定性编译 PASS
∧ ArduPilot Copter Clang 18 构建 PASS
∧ SVF 3.2 官方 WPA/SVFG smoke PASS
∧ portability contract pre-core PASS
∧ src/StaticAnalysis 为空 PASS
```

FGS 仍是 `BLOCKED`，PGFuzz 和 MoonShine 仍是 `PARTIAL`，完整 LTL-Fuzzer
instrumented fuzz campaign 仍是 `NOT_RUN`。它们没有被改写成成功。原始 CCF-A
artifact 的最低执行条件只由 LTL-Fuzzer 的原始 Automata 组件和公开 Problem1
共同满足。

这里的 `PASS` 只允许进入 RIFT-M2 benchmark 工作。它不表示 RIFT 已经实现，也不
支持任何静态精度、性能、AP flip、fuzz 收益或“优于既有方法”的结论。机器可读的
判定、逐项边界和证据哈希见 `m1_manifest.json`。

## 逐项状态与结论边界

| 步骤 | 状态 | M1 实际证明 | 明确没有证明 |
|---|---|---|---|
| LTL-Fuzzer original Automata | `PASS` | 原始 Automata 库在公开 Problem1 property 上消费 `iH,oZ,iB,oZ`，编译和执行均退出 0 | LLVM instrumentation 和完整 directed fuzz campaign |
| LTL-Fuzzer public Problem1 | `PASS` | Clang 18 编译并执行 shipped 1000-byte input，得到冻结输出 | target reachability、time-to-target 或 fuzz effectiveness |
| LTL AP tuple import | `PARTIAL` | 49 个 tuple 中 46 个精确解析 | Telnet 缺失 gitlink 对应的 3 个 tuple；这些 tuple 也不是 causal gold |
| PGFuzz maps | `PARTIAL` | 核对 56 条 paper policy，其中 51 条有公开 map | 缺失的 5 条 Paparazzi map、PGFuzz campaign、因果 ground truth |
| MoonShine RW | `PARTIAL` | 官方预计算表含 `mlockall→msync`，Clang micro case 复现字段交集规则 | 未公开的 Smatch extraction hooks 和原始 extractor |
| FGS FSE 2024 | `BLOCKED` | 保存 Zenodo 只有 README、镜像不可获得的完整证据 | 任何 FGS smoke、NIST、精度、时间、内存或图简化结果 |
| libcoap | `PASS` | 3 次编译的 compile DB、archive、linked bitcode hash 一致，MemorySSA 成功 | DTLS、CUnit tests、协议运行、AP binding 或 fuzz |
| ArduPilot | `PASS` | 冻结 commit 的 Copter Clang 18 build、1336-entry compile DB 和 help smoke | AP binding、GCS failsafe SITL scenario 或 fuzz |
| SVF 3.2 | `PASS` | clean official tag 无 patch 构建 124/124；WPA 的 MAYALIAS/NOALIAS、MemorySSA 和 78-node/75-edge SVFG 成功 | 上游 Test-Suite、大项目精度、AP/controllability/async/recipe；ad-hoc API diagnostic 不参与验收 |
| portability pre-core | `PASS` | core/model-pack 边界在实现前冻结，generic core 文件数为 0 | 至少三个项目上的最终 portability evaluation |
| `src/StaticAnalysis` empty | `PASS` | 捕获门禁时目录中没有实现文件 | RIFT implementation |
| RIFT-M2 gold benchmark | `NOT_RUN` | 这是下一里程碑入口 | 任何 M2 指标 |

## 关键可复核身份

- LTL-Fuzzer commit：`716ac301fa3a8ea39814bc80eeebba49c19c1378`；Automata
  binary SHA-256：`5c4fd18734fa25c9fcd14ad8df2d8f97f5f732072bf7d9725fc25c971fc6ae62`。
- libcoap commit：`94bacc8939dd6711169cd2332a002a361ec62531`；三次 linked
  bitcode SHA-256 均为
  `08ead6a83ce230fab63eb028c9eec21fb0b2e23e79dd6270c8ee78e43b12c61d`。
- ArduPilot commit：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；Clang 18
  compile DB SHA-256：
  `e3bde40c679fb01db8b16b22f75e225c50804fcf8ddf9b05b132fc159e0d9083`。
- SVF tag/commit：`SVF-3.2` / `197a6590bd9c695a9c3daf52622dea912ef9a002`；
  official `wpa` SHA-256：
  `4d9c0b7d7f9c5176f304b03edb5a8a90e2abaf011c9db4110d1920f1e76f49f5`。
- FGS child status：`BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE`；四个 success
  boolean 全为 `false`。

`m1_manifest.json` 另外冻结了 19 个顶层证据锚点，包括每个子 manifest、说明、
validator 和 portability contract 的 SHA-256。

## 一键总验证

在 TAFuzz 根目录运行：

```bash
cd /home/lqq/project/TAFuzz
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/validate_m1.py
```

总验证器执行以下只读操作：

1. 校验 aggregate schema、13 个步骤的规范化状态、七个必需门禁和 19 个 SHA-256
   锚点；
2. 直接检查 LTL-Fuzzer、PGFuzz、MoonShine、FGS、libcoap、ArduPilot 和 SVF 的
   machine-readable oracle；
3. 调用 literature、FGS checksum、ArduPilot、SVF 和 portability 子验证器；
4. 确认 `src/StaticAnalysis` 仍为空；
5. 逐项输出 `STEP`/`CHILD` 状态，最后必须出现：

```text
TOTAL PASS required_steps=7/7 ... failures=0
```

这个命令不联网，也不重建 libcoap、ArduPilot 或 SVF。literature validator 只在
`/tmp` 编译很小的 Problem1/Automata smoke，SVF validator 只实时重跑约 0.1 秒的
official WPA smoke。

只检查已保存材料而不执行子验证器时可用：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/validate_m1.py --stored-only
```

该模式故意输出 `TOTAL PARTIAL`，不能替代 fresh `TOTAL PASS`。

## 子项重跑命令

这些命令都从 `/home/lqq/project/TAFuzz` 开始执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/literature_baselines/validate_literature_baselines.py

(cd benchmark/rift/reproduction/fgs && sha256sum -c SHA256SUMS)

PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/ardupilot/validate.py

PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/svf/validate_reproduction.py

PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/validate_portability_contract.py --phase pre-core
```

libcoap 的完整三次编译会重建临时产物，因此不在总验证器中自动执行。需要从头重跑
时使用一个临时输出，确认新结果的三个核心 hash 与冻结 manifest 一致：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/reproduction/libcoap/reproduce_clang18.py \
  --output /tmp/rift-libcoap-observed.json
```

ArduPilot 的完整隔离构建命令及 `/tmp` binary 强验证见
`ardupilot/README.md`；常规总门禁只验证保存的 compile DB、退出码、live source
identity 和现有临时 binary（若仍存在），不会重新编译 1350 个 Waf task。

## RIFT-M2 入口

M1 `TOTAL PASS` 后，下一步不是先写目标特化分析逻辑，而是完成可机械检查的 influence
gold benchmark：

1. 冻结共同 Property IR、source/frontier/recipe result schema 和 may/must evidence
   规则；
2. 用模板生成并机械标注 data、control、alias、field/object、configuration、parser、
   timer/callback/queue、prerequisite、timing/order、negative control、one-to-many 和
   joint-influence cases；
3. 固定生成器 seed、case/source SHA-256、ground-truth derivation 和 validator；
4. M2 门禁通过后再按同一 schema 实现弱基线，之后才实现 RIFT core。

`validate_m1.py` 是历史性的 pre-core 门禁：一旦 `src/StaticAnalysis` 开始出现实现
文件，它应当失败，而不是在事后把“实现前为空”的条件悄悄放宽。M1 的通过事实由本
manifest、验证输出和里程碑交接文件共同保留。
