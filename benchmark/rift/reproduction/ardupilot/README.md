# ArduPilot RIFT-M1 源码与 Clang 18 构建基线

## 结论

在不修改 ArduPilot 源码、不覆盖现有 GCC 构建目录、也不改变既存
`modules/CrashDebug` 状态的前提下，冻结 commit
`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` 已成功完成：

- 现有 GCC SITL compile database 的冻结、解析和一致性检查；
- 使用 Clang/Clang++ 18.1.8 的独立 ArduCopter SITL configure；
- 使用 Clang 18 的完整 1,350-task Copter 构建；
- 新鲜 Copter-only Clang compile database 的冻结和解析；
- 生成的 `arducopter --help` 可执行 smoke。

本结果只是 `BUILD_BASELINE_SUCCESS`。没有运行 AP 自动绑定、依赖切片、RIFT、
GCS failsafe SITL 场景或 fuzz campaign，不能用本报告声称 RIFT 正确或有效。

## 冻结身份与保护结果

| 项目 | 观测值 |
|---|---|
| upstream | `https://github.com/ArduPilot/ardupilot.git` |
| commit | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` |
| tree | `0233e86a885e339242cdae2e7510bf12eae1502d` |
| Waf submodule | `35eadbb64e2052099a853b571e507c33032b392c` |
| CrashDebug gitlink/checkout | `599965086437137ec0fe66e185611f43f335f889` |
| 工作树状态（前/后） | 均仅为 ` m modules/CrashDebug` |
| 标准 Waf lock SHA-256（前/后） | 均为 `b28422dd…f9ee9d4` |

`CrashDebug` 内部已有的 `CrashCatcher` 和 `mri` 子模块修改状态同样被保留；没有执行
clean、reset、checkout、submodule update 或源码格式化。

完整证据见 `raw/source-freeze.txt`、`raw/source-preservation-configure.txt` 和
`raw/source-preservation-build.txt`。

## Compile database 基线

### 既存 GCC 数据库

原始文件：`baseline/ardupilot/build/sitl/compile_commands.json`

| 指标 | 值 |
|---|---:|
| 原始 SHA-256 | `57c2097fbe9dc7fa60c143a2ff2552d926a7cc4de2610db0bda09cf25cca6c60` |
| 原始大小 | 4,619,645 B |
| entries / unique files | 1,543 / 1,543 |
| `/usr/bin/gcc` | 333 |
| `/usr/bin/g++` | 1,210 |
| C / C++ | 333 / 1,210 |
| 缺失源文件/工作目录 | 0 / 0 |

这是任务开始前已存在的数据，未在本任务中重新生成。Waf 的数据库写入器按文件合并
旧记录，因此该快照是累积数据库：含生成文件、1,118 个 library 条目、74 个
ArduCopter、64 个 ArduPlane 和 38 个 Rover 条目。不能把 1,543 直接与下方
Copter-only Clang 数量比较。

可移植快照：`gcc_existing_compile_commands.json.gz`，其 gzip SHA-256 为
`cd97e25e…9712b2d`；解压后与原始 SHA-256 完全相同。

### 独立 Clang 18 数据库

原始文件：`/tmp/rift-ardupilot-clang/build/sitl/compile_commands.json`

| 指标 | 值 |
|---|---:|
| 原始 SHA-256 | `e3bde40c679fb01db8b16b22f75e225c50804fcf8ddf9b05b132fc159e0d9083` |
| 原始大小 | 4,735,810 B |
| entries / unique files | 1,336 / 1,336 |
| `/usr/bin/clang-18` | 262 |
| `/usr/bin/clang++-18` | 1,074 |
| C / C++ | 262 / 1,074 |
| 缺失源文件/工作目录（观测时） | 0 / 0 |

其中 1,159 个 source-file identities 与既存 GCC 数据库相交，另外 177 个是当前
独立 build root 中生成的源文件。1,159 个源码 `file` 字段是绝对路径；生成文件依赖
`/tmp/rift-ardupilot-clang/build/sitl`。因此保存的数据库是可审计快照，不是可以搬到
任意机器直接运行的数据库。RIFT 必须支持 build-root/source-root 重定位并验证生成
头文件，不能硬编码这些绝对路径。

可移植快照：`clang18_compile_commands.json.gz`，gzip SHA-256 为
`134e1dc5…723236a`；解压后与原始 SHA-256 完全相同。

## Clang 18 隔离构建

为避免 Waf 从源码根加载现有 GCC lock，使用独立 `WAFLOCK`、显式 top/out，以及
Waf 隐藏的 no-lock 选项：

```sh
cd /home/lqq/project/TAFuzz/baseline/ardupilot

env \
  WAFLOCK=.lock-waf_rift_clang_build \
  CC=/usr/bin/clang-18 \
  CXX=/usr/bin/clang++-18 \
  AP_NO_COMPILE_COMMANDS=1 \
  /home/lqq/anaconda3/bin/python ./waf \
  -o /tmp/rift-ardupilot-clang/build \
  -t /home/lqq/project/TAFuzz/baseline/ardupilot \
  --no-lock-in-top --no-lock-in-run \
  configure --board sitl --disable-tests

env \
  WAFLOCK=.lock-waf_rift_clang_build \
  CC=/usr/bin/clang-18 \
  CXX=/usr/bin/clang++-18 \
  AP_NO_COMPILE_COMMANDS=1 \
  /home/lqq/anaconda3/bin/python ./waf -j8 \
  -o /tmp/rift-ardupilot-clang/build \
  -t /home/lqq/project/TAFuzz/baseline/ardupilot \
  --no-lock-in-top --no-lock-in-run \
  copter
```

结果：

| 项目 | configure | Copter build |
|---|---:|---:|
| exit code | 0 | 0 |
| Waf wall time | 2.360 s | 122.449 s |
| 外层计时 wall time | 2.81 s | 126.42 s |
| GNU time max RSS | 100,572 KiB | 181,948 KiB |

构建以 `-j8` 执行。GNU time 的 `ru_maxrss` 是所观测进程中的最大值，不是八个并发
编译器的 RSS 总和；因此这里只报告观测值，不冒充严格的 aggregate 12 GiB cgroup
测量。构建日志有 31 条非致命 Clang warning diagnostic lines，没有 fatal error。

生成二进制：

| 属性 | 值 |
|---|---|
| path | `/tmp/rift-ardupilot-clang/build/sitl/bin/arducopter` |
| size | 5,855,128 B |
| SHA-256 | `ad040e179db3acfb21cec966d5fb2a75b026b746c0cc6e50c0cb50df654ac4f4` |
| ELF Build ID | `2d53ff404a0fd9371861267571bb1258a27a0129` |
| `--help` | exit 0，正常列出 SITL 参数 |

`/tmp` 二进制不是提交产物；它可通过上述命令重建。`raw/clang18-artifacts.txt`、
`raw/clang18-copter.*` 和 `raw/clang18-arducopter-help.*` 保留构建与 smoke 证据。

## GCS failsafe 只读源码事实

这一步没有运行 RIFT，只人工确认了后续 benchmark 所需的事实链：

```text
accepted HEARTBEAT / RC override / MANUAL_CONTROL
  → sysid_mygcs_seen(timestamp)
  → global designated-GCS last-seen time
  → three_hz_loop (registered at 3 Hz)
  → failsafe_gcs_check
  → elapsed time and FS_GCS_TIMEOUT comparison
  → set_failsafe_gcs
  → failsafe.gcs and AP_Notify flag
  → separate action-selection guards
```

必须保留的边界事实：

- `FS_GCS_ENABLE=DISABLED` 或 last-seen 为零时直接返回；
- 恢复条件是严格 `< timeout`，触发条件是严格 `> timeout`；相等时没有显式分支；
- `HEARTBEAT` 不是唯一 timestamp refresh 来源，RC override 和 manual control 也可能刷新；
- failsafe state 与后续动作不是同一个 AP：armed/landed、mode、battery 和
  `FS_OPTIONS` 影响 action，但不应被错误描述成全部都直接决定 state bit；
- 现有 `GCSFailsafe` autotest 已覆盖 heartbeat rate、动态 timeout、enable/action 和
  options，当前仅把它记录为未来行为 oracle 候选，没有执行测试。

结构化事实与候选见 `gcs_failsafe_source_facts.json`，原始行号证据见
`raw/gcs-failsafe-source-evidence.txt`。

## 可移植性边界

RIFT 核心只能实现通用 AST/IR、value/control/call/alias/event-graph 和约束能力。
以下内容必须由版本化 project/framework model 或源码索引提供，不能写死在核心：

- `SCHED_TASK` 的频率和调度语义；
- `AP_HAL::millis` 的 clock domain 与 wrap 语义；
- AP_Param 名称、单位、持久化及外部 parameter-update 通道；
- MAVLink dispatch、source-system-ID 策略及哪些消息刷新生命周期 timestamp；
- SITL reset/process epoch/simulated-time 语义；
- ArduPilot 文件路径、symbol/field 名、参数默认值、3 Hz、严格比较符；
- autotest helper 名和本机 build/out 路径。

compile database 本身也必须视为带 provenance 的输入：分析器需记录 source commit、
build config、生成文件 hash 和 root relocation，不能用条目数量或绝对路径推断项目
语义。

## 验证

完整验证：

```sh
cd /home/lqq/project/TAFuzz/benchmark/rift/reproduction/ardupilot
python3 validate.py --require-temp-build
```

迁移到没有 `/tmp` 构建产物的机器后，可验证保存材料和 live source：

```sh
python3 validate.py --repo /path/to/frozen/ardupilot
```

只验证保存快照：

```sh
python3 validate.py --skip-live-source
```

机器可读总表见 `build_manifest.json`。
