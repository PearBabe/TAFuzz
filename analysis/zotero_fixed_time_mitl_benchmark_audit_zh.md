# Zotero 固件模糊测试与分布式实时系统固定时间 MITL 基准独立重审

审计日期：2026-07-23（中国标准时间）  
工作区：`/home/lqq/project/TAFuzz`  
ArduPilot 冻结提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`  

独立性说明：本报告的判断只依据本轮重新读取的 Zotero 原始目录/全文快照、PGFuzz
原论文 PDF、当前冻结源码、官方文档、法规原文和公开基准源码。既有分析报告、既有
PGFuzz 整理清单、历史项目结论和历史记忆不作为结论证据。后文提到既有本地文件时，
仅把当前源码或公开模型本身作为一手实现证据。

## 1. 结论先行

这次完整审计了 Zotero 中两个目标目录的全部顶层条目：

- “模糊测试/固件 fuzz 综述”：34/34 条；
- “运行时验证/分布式实时系统”：13/13 条；
- 合计 47/47 条，没有只凭标题抽样。

筛选条件是：背景不以网络协议为主；存在可观察的系统行为；时间界是固定数值；
数值有可追溯来源；性质可写成 MTL 或 MITL；最好已有模糊测试、性质证伪或模型测试
论文将该系统作为实验对象。

最重要的结论如下。

1. **ArduPilot 还能新增至少 6 组有固定秒数的候选性质。** 其中振动故障保护
   的 1 秒触发与 15 秒恢复、坠毁检查的 2 秒、EKF 故障保护的 1 秒，是最干净的
   正向基准。地形数据、遥控杆解除电机和自动降落伞则出现了官方文字与冻结源码
   的静态差异，适合做差分实验，但在实际运行前只能标作候选冲突，不能声称已经
   发现运行时违反。
2. **PGFuzz 的 ArduPilot/PX4 共 51 条性质确实缺少固定有界时间。** 51 条中只有
   5 条印刷公式
   使用有界 `F`，其中仅 `A.FLIPGeneral` 直接写了固定数值 `[0,2.5]`；另外 3 条
   ArduPilot 公式使用未公开经验量 `k`，1 条 PX4 公式使用参数加 `k`。所以用户的
   观察是准确的。
3. **两个 Zotero 目录中没有一篇文献同时满足所有强条件**：非网络协议、已有
   模糊测试基准、时间常量来自外部规范、可直接形成 MITL。最接近“立即能做实验”
   的是 Mecel 齿轮控制器；最接近“有真实 fuzz 底座”的是 CPFuzz、DICE 和
   LawBreaker；它们的时间值多为论文或模型实例常量，而不是外部法规。
4. **如果允许换背景，推荐两条路线。**
   - 最低接入成本：继续 ArduPilot，先做振动保护，再做地形/左舵/降落伞差分。
   - 更强的外部规范来源：联合国第 152 号法规下的自动紧急制动系统，以及美国
     铁路道口预警。前者有自动驾驶仿真模糊测试生态，后者的固定时间规范最清楚，
     但需要自行把经典时间自动机/模型测试对象接入模糊测试器。
5. **建议把实验语料分层，不能混报。** `NORMATIVE_FIXED` 表示外部规范固定数值；
   `BENCHMARK_FIXED` 表示论文/基准模型固定数值；`IMPLEMENTATION_DERIVED` 表示
   源码实现常量；`PARAMETERIZED` 表示运行参数。自动检查只产生一致性证据，不等于
   法规、设计要求或官方行为规范的符合性结论。

## 2. 术语与判断图例

- **MTL（Metric Temporal Logic，度量时序逻辑）**：给“始终、最终、直到”等
  时序算子附加数值时间区间；本任务用它描述被测系统在多少秒或毫秒内必须发生
  或不得发生什么行为。
- **MITL（Metric Interval Temporal Logic，度量区间时序逻辑）**：MTL 的区间
  片段，通常排除 `[t,t]` 这种只包含单个时间点的精确等式区间。本任务优先使用
  有非零宽度的区间或“过去一段时间始终成立”的表达。
- **STL（Signal Temporal Logic，信号时序逻辑）**：信号时序逻辑，直接对速度、
  距离、温度等实值信号写阈值性质。转换成事件型 MITL 时必须冻结采样、阈值和
  事件抽象，不能静默改变语义。
- **RV（Runtime Verification，运行时验证）**：根据实际执行轨迹在线或离线判定
  性质。本报告把监视器性能实验与被测系统模糊测试分开。
- **SUT（System Under Test，被测系统）**：真正接收变异输入并产生被监控轨迹的
  系统或模型。
- **SITL（Software In The Loop，软件在环仿真）**：在主机上运行真实飞控软件并
  注入传感器、执行器或环境输入；ArduPilot 候选主要通过 SITL 复现。
- **EKF（Extended Kalman Filter，扩展卡尔曼滤波器）**：ArduPilot 的状态估计器；
  其方差、创新量和故障保护状态是候选性质的源端观测量。
- **falsification（性质证伪或反例搜索）**：用优化或搜索寻找违反时序性质的轨迹；
  它与基于变异和覆盖反馈的模糊测试不同，但可提供现成模型、输入空间和性质集合。
- `G φ`：始终满足 `φ`；`F_I φ`：在时间区间 `I` 内最终满足 `φ`；
  `H_I φ`：在过去时间区间 `I` 内一直满足 `φ`。
- `implementation_satisfaction=NOT_ASSESSED`：尚未评价当前实现是否满足性质。
  本审计发现静态差异时仍保持该边界，实际运行前不写成 `FAIL` 或“已违反”。

### 2.1 证据状态

| 状态 | 中文含义 | 能否作为外部固定规范 |
|---|---|---|
| `NORMATIVE_FIXED` | 官方文档、法规或明确设计要求直接给出固定时间 | 可以，但仍需绑定版本、适用条件和时钟 |
| `BENCHMARK_FIXED` | 论文或公开基准模型固定了数值 | 可做算法基准，不能宣称法规/产品符合性 |
| `IMPLEMENTATION_DERIVED` | 只有源码或执行观察中出现常量 | 只能测实现回归，不能反向发明需求 |
| `PARAMETERIZED` | 时间由用户、任务或运行配置给定 | 不符合本轮“固定且非参数”条件 |
| `SPEC_SOURCE_CONFLICT` | 官方文字与冻结源码静态上给出不同时间/连续性语义 | 高价值差分候选；运行前仍是未评估 |
| `INCONCLUSIVE` | 缺原文、单位、时钟或事件映射 | 保留未知，不能补数值 |

## 3. Zotero 审计范围、快照与可重复性

本轮通过 Zotero 本地应用程序接口重新读取两个目录，并把目录元数据和已建立索引的全文
冻结到工作区。Zotero 的条目键是本地稳定标识；它不是论文 BibTeX 引用键。

- 只读抓取脚本：`analysis/scripts/snapshot_zotero_collections.py`
- 固件目录快照：
  `analysis/data/zotero_mtl_source_snapshot/firmware_fuzz_review/manifest.json`
- 分布式实时系统快照：
  `analysis/data/zotero_mtl_source_snapshot/distributed_realtime_systems/manifest.json`
- 全文证据位于两个快照目录各自的 `fulltext/` 下。

两个目标目录均无下级子目录。固件目录 34 条中，25 条有本地索引全文，共 27 个文本
附件；9 条无本地全文。分布式
实时系统目录 13 条中也有缺全文条目；相应结论只使用元数据并标为未决。这里的“全部
分析”指 47 条顶层条目全部分类，不代表为所有缺失附件补取了付费或不可访问全文。

## 4. PGFuzz 固定时间公式现状

本轮直接用 `pypdf` 从原论文
`baseline/pgfuzz/Kim 等 - 2021 - PGFUZZ Policy-guided fuzzing for robotic vehicles.pdf`
第 18 页提取并逐行复核表 XII，没有读取既有公式清单。原表共 56 条：ArduPilot
30 条、PX4 21 条、Paparazzi 5 条。用户当前比较的 ArduPilot/PX4 子集是 51 条；
其中逐式可见 5 条使用有界最终算子：

| 性质 | 印刷时间区间 | 来源判断 |
|---|---:|---|
| `A.FLIP3` | `[0,k]` | `k` 是未公开经验/调度余量，不是外部固定规范 |
| `A.FLIPGeneral` | `[0,2.5]` | 唯一直接出现固定数值的有界 `F` |
| `A.BRAKE1` | `[0,k]` | 同上 |
| `A.DRIFT1` | `[0,k]` | 同上 |
| `PX.GPS.FS1` | `[0,COM_POS_FS_DELAY+k]` | 时间参数加未公开余量，不是固定常量 |

因此不能通过给原有无界公式随意加秒数来扩大实验集。正确做法是从官方行为文字或
外部法规独立提取新性质，再做当前源码绑定；源码常量只能用于检查实现映射和发现差异。
Paparazzi 的 5 条也没有增加固定有界最终公式。

## 5. ArduPilot 新增固定时间性质

### 5.1 总表

| 优先级 | 行为 | 固定时间 | 状态 | 价值 |
|---:|---|---:|---|---|
| 1 | 振动故障保护启用/恢复 | 1 s / 15 s | `NORMATIVE_FIXED`，但阈值开闭和采样边界需测 | 最适合先跑通监控与引导闭环 |
| 2 | 地形数据丢失故障保护 | 文档 2 s / 源码 5 s | `SPEC_SOURCE_CONFLICT` | 易得到清楚的定时差分轨迹 |
| 3 | 左舵解除电机 | 文档 2 s / 源码 3 s | `SPEC_SOURCE_CONFLICT` | 输入简单、稳定复现概率高 |
| 4 | 自动降落伞连续失控 | 文档连续 1 s | `SPEC_SOURCE_CONFLICT` 候选 | 可探索“异常—短恢复—异常”序列 |
| 5 | Crash Check 坠毁检查 | 2 s | `NORMATIVE_FIXED`，需补定时测试 | 固定连续窗口，条件组合丰富 |
| 6 | EKF 故障保护 | 1 s | `NORMATIVE_FIXED`，有替代触发路径 | 是 PGFuzz GPS 性质的定时精化 |

官方网页当前仍明确给出这些时间：[振动故障保护](https://ardupilot.org/copter/docs/vibration-failsafe.html)、
[降落伞](https://ardupilot.org/copter/docs/common-parachute.html)、
[坠毁检查](https://ardupilot.org/copter/docs/crash_check.html)、
[EKF 故障保护](https://ardupilot.org/copter/docs/ekf-inav-failsafe.html)、
[地形跟随与地形数据丢失](https://ardupilot.org/copter/docs/terrain-following.html)、
[电机解锁与解除](https://ardupilot.org/copter/docs/arming_the_motors.html)。

### 5.2 振动故障保护：首个正向实验

官方要求三项异常至少连续 1 秒后启用振动补偿，EKF 恢复正常 15 秒后关闭。
冻结源码 `ArduCopter/ekf_check.cpp:267-322` 分别使用 `1000 ms` 和 `15000 ms`。

```text
BadVibe :=
    IVD > 0
  ∧ IPD > 0
  ∧ VelocityVariance >= 1
  ∧ Armed
  ∧ ¬ManualThrottleMode
  ∧ FS_VIBE_ENABLE

G(H_[0,1s] BadVibe -> HighVibes)
G(HighVibes ∧ H_[0,15s] ¬BadVibe -> ¬HighVibes)
```

源码另有 `ahrs.is_vibration_affected()` 触发通道，实验必须记录释放原因或分开建模。
本轮直接重读源码还发现两个边界细节：官方文字是速度方差“1 或更高”，源码使用
`vel_variance_filt.get() > 1.0f`；计时判断使用 `>1000` 和 `>15000`，动作发生在越过
阈值后的首次 10 Hz 检查，而不是数学上的精确 1.000/15.000 秒。不能自行补一个
0.1 秒容差；应记录源端检查时刻，并把“连续满阈值”与“下一次调度检查执行动作”分成
要求时钟和实现采样语义。

官方 SITL 测试位于 `Tools/autotest/arducopter.py:1651-1677`，可变异三组加速度计
Z 轴偏置；应插桩内部 `high_vibes` 和源端单调时钟。地面站文字消息的接收时间不能
代替内部状态切换时间。

### 5.3 自动降落伞：连续性的高价值差分

官方要求所有失控条件完整连续 1 秒。冻结源码
`ArduCopter/crash_check.cpp:234-331` 固定 `1 s`，但姿态误差暂时恢复时把计数减 1，
没有直接清零。由此得到两个候选性质：

```text
AutoChuteCond :=
    Armed ∧ ¬Landed ∧ Mode∉{FLIP,ACRO}
  ∧ AttitudeError>30deg ∧ ¬Climbing ∧ StartAboveCHUTE_ALT_MIN

G(H_[0,1s] AutoChuteCond -> AutoAttitudeRelease)
G(AutoAttitudeRelease -> H_[0,1s] AutoChuteCond)
```

第二式检查“不得在从未连续异常满 1 秒时触发”。首个定向输入可以是：

```text
异常 0.7 s -> 正常 0.1 s -> 异常 0.4 s
```

这只是基于静态代码的反例候选。还要关闭或单独标记超速下降释放路径，并把性质后件
绑定为“自动释放已发起”，不能绑定物理伺服动作，因为 `CHUTE_DELAY_MS` 是参数。

### 5.4 坠毁检查：连续 2 秒

官方要求相关条件持续完整 2 秒后解除电机。规范必要条件与当前实现充分触发条件应
分别保留：

```text
CrashDocCond :=
    Armed ∧ ¬Landed ∧ Mode∉{ACRO,FLIP}
  ∧ Acceleration<3m/s^2 ∧ AttitudeError>30deg

G(CrashDisarm -> H_[0,2s] CrashDocCond)

CrashImplCond :=
    CrashDocCond ∧ LeanAngle>15deg
  ∧ (VelocityUnavailable ∨ Speed<10m/s)
  ∧ ¬Standby ∧ CrashCheckEnabled

G(H_[0,2s] CrashImplCond -> CrashDisarm)
```

第二条是实现绑定后的测试性质，不能冒充纯外部规范。冻结源码证据是
`ArduCopter/crash_check.cpp:3-97`；现有官方自动测试没有断言 2 秒窗口，需要新增
源端计时测试。

### 5.5 EKF 故障保护：两类方差连续越限 1 秒

官方行为是罗盘、位置、速度三类 EKF 方差中任意两类高于运行配置阈值，持续 1 秒
后触发。时间是固定的；阈值 `FS_EKF_THRESH` 是谓词配置，不是时间参数。

```text
TwoVarianceBad :=
    Count{MagVariance>=theta,
          PositionVariance>=theta,
          VelocityVariance>=theta} >= 2

theta := 本次运行实际读取的 FS_EKF_THRESH

G(H_[0,1s] TwoVarianceBad -> EKFFailsafe)
```

冻结源码 `ArduCopter/ekf_check.cpp:10-216` 以 10 Hz 下 10 次检查实现 1 秒。源码还
有 `VelocityVariance>=2theta`、位置估计丢失、航向重置和 EKF 通道切换等替代路径，
所以在未隔离原因时不能使用反向充分必要式。

### 5.6 地形数据：官方 2 秒与冻结源码 5 秒

```text
TerrainMissingRequired :=
    MissionRequiresTerrain ∧ TerrainDataUnavailable

G(H_[0,2s] TerrainMissingRequired
  -> ((Flying ∧ Mode=RTL) ∨ (Landed ∧ ¬Armed)))
```

官方网页写连续 2 秒；冻结源码 `ArduCopter/config.h:99-102` 定义
`FS_TERRAIN_TIMEOUT_MS=5000`，`ArduCopter/events.cpp:242-306` 使用该 5 秒值。
现有 SITL 测试 `Tools/autotest/arducopter.py:1374-1402` 只等待最终触发，没有断言
2 秒或 5 秒。实验必须同时记录首次缺数、故障保护置位和模式变化的源端时间。

### 5.7 左舵解除电机：官方 2 秒与冻结源码 3 秒

```text
RudderDisarmCond :=
    Armed ∧ ThrottleZero ∧ RudderLeftHigh
  ∧ ARMING_RUDDER=ARMDISARM ∧ DisarmAllowedInCurrentState

G(H_[0,2s] RudderDisarmCond -> ¬Armed)
```

官方网页写左舵保持 2 秒解除电机；冻结源码
`libraries/RC_Channel/RC_Channels.cpp:453-516` 对左右方向统一检查 `3000 ms`。
直接变异油门和偏航遥控输入即可。官方还写右舵保持 5 秒解锁，但“保持 5 秒即可”
未必禁止提前解锁，因此不能把 3 秒解锁自动解释成违反。

### 5.8 不应升级成外部规范的 ArduPilot 常量

以下值没有找到同等强度的官方固定时间，或时间本身已经参数化：

- 仅实现常量：推力损失 1 秒、着陆检测 1/3/0.2 秒、故障保护降落暂停 4 秒、
  表面跟随坏测距 1 秒、看门狗默认 2048 毫秒、GPS 后端重检测 4 秒；
- 参数化时间：`FS_GCS_TIMEOUT`、`RC_FS_TIMEOUT`、`GUID_TIMEOUT`、
  `FS_DR_TIMEOUT`、`BATT_LOW_TIMER`、`DISARM_DELAY`、`RTL_LOIT_TIME`、
  `CHUTE_DELAY_MS` 和任务命令自带延时。

这些可以进入实现回归集，但不得标作固定规范性质。

## 6. 分布式实时系统目录：13/13 条审计

### 6.1 最强候选：Mecel 齿轮控制器

Zotero 条目 `3YKLPY84` 是目录中唯一同时具备工业控制背景、固定毫秒界、公开模型、
事件轨迹、性质自动机和测试驱动的强候选。MoniTAal 工作树已有相应模型和性质文件：

```text
G(CloseClutch -> F_[0ms,150ms] ClutchIsClosed)
G(OpenClutch  -> F_[0ms,150ms] ClutchIsOpen)
G(ReqSet      -> F_[0ms,300ms] GearSet)
G(ReqNeu      -> F_[0ms,200ms] GearNeu)
```

完整换档不能诚实地压成一条无条件的 `[150,1205]` 公式。本轮直接重读
`gear_controller_newgear_prop.h` 后发现，下界取决于请求是否经过空档以及
`UseCase1/UseCase2`：

| 请求类别 | 无附加用例事件 | `UseCase1` | `UseCase2` |
|---|---:|---:|---:|
| 非空档换档请求 | `[400,900] ms` | `[700,1055) ms` | `[750,1205] ms` |
| 涉及空档的请求 | `[150,900] ms` | `[550,1055) ms` | `[450,1205] ms` |

所以正式性质必须带请求类别、请求—响应配对和用例守卫。`UseCase1/UseCase2` 事件在
请求之后才可能出现，不能错误地写成与请求同一时刻的合取前件；应保留原时间自动机，
或增加一个保存“请求源时间 + 已确定用例”的辅助观察器后再生成 MITL 义务。未经这一步，
本报告不伪造一条看似简洁但事件顺序错误的公式。

`benchmark/main.cpp` 的测试循环只用宽包络 150--1205 ms 生成和判错，且事件标签是
通用 `ReqNewGear`；性质头文件使用 `ReqNewGear23` 等具体标签。这两者的映射需再核对，
宽包络只能作压力测试，不能替代六个精确窗口。

本地证据：

- `tool/MoniTAal/benchmark/gear_controller_newgear_prop.h:56`；
- `tool/MoniTAal/benchmark/main.cpp:404`（宽包络测试，不是六个精确窗口的替代）；
- `tool/MoniTAal/benchmark/gear-control-properties.xml:7,114,223,330`；
- `tool/MoniTAal/benchmark/engine-classic-uppaal5.xml:686-732`。

数值当前只能确认是基准模型固定常量，故状态是 `BENCHMARK_FIXED`，不能称为生产车辆
或法规规范。还需冻结重复请求的配对语义、同时间戳事件和边界开闭性，并逐个证明性质
自动机与候选 MITL 公式等价。

### 6.2 完整覆盖表

| # | Zotero 键 | 内容 | 固定时间与实验判断 |
|---:|---|---|---|
| 1 | `QQHGEDUM` | 不确定时间戳下的 MITL 监控 | 10、20、50--100、7--10 均为概念验证示例；随机轨迹只测监视器 |
| 2 | `FS52IR3S` | MITL 监控理论 | 20/30 ms、5--6、20--40 是逻辑示例；无被测系统和实现基准 |
| 3 | `YSIKACN4` | 二元决策图理论 | 无时间语义，目录污染项 |
| 4 | `3YKLPY84` | Mecel 齿轮控制器 | 本目录首选；固定模型毫秒界、UPPAAL 模型、性质与扰动测试齐全 |
| 5 | `APC9MJIX` | RV 应用域综述 | 文献地图；自身无可冻结真实系统时限 |
| 6 | `3Z9AWADA` | 定时线性时序逻辑监控 | 缺全文；无可审计数值和真实基准 |
| 7 | `TNAPDP4B` | TiPEX 定时性质执行工具 | 15--20、5/6 为工具微基准；无真实被测系统 |
| 8 | `UMUZKKL5` | 分布式定时监控理论 | 0.7 为时钟偏差假设，不是系统性质；无实验基准 |
| 9 | `37KLUP6M` | MONAA 定时模式匹配 | 自动变速器 10 秒/1 秒是强次级候选；需回原始要求解决文本与公式冲突 |
| 10 | `G7HX66LE` | 信息物理系统监控综述 | 指向自动变速器、起搏器、人工胰腺；原文未给完整固定性质 |
| 11 | `ZR5NBBSK` | 在线定时模式匹配 | 4--5、1--2、100±1 均为合成示例；真实应用留作未来工作 |
| 12 | `ZL9DXY3V` | IF 验证环境 | Ariane 5 只有名称，无性质、事件、时限和单位 |
| 13 | `KQBR3WUX` | NASA 分布式实时监控综述 | 事故中的 1/3 秒不是规范；5--20、2--10 是教程例子 |

自动变速器和人工胰腺值得追原始基准：前者已有 S-TaLiRo 性质证伪背景，后者有闭环
连续信号和多条 STL 性质。但人工胰腺的时间与阈值很可能按患者个体化，必须逐项判断，
不能把患者/控制器参数当成固定医学规范。

## 7. 固件模糊测试综述目录：34/34 条审计

### 7.1 有用但不满足全部强条件的四组条目

1. `QGXIAFZG` 多机器人运行时验证学位论文给出了本目录最直接的 MTL 公式，例如
   `G(bot_speed -> F_[0,20](bot_mem ∧ bot_cmd))`。论文以 100 ms 为实验周期，因此
   20 周期可在该实验时钟下解释为 2 秒。但正文说“未来 20 周期一直保持”，公式却用
   “最终一次成立”，存在语义冲突；100 ms 与 20 周期也是实验设定，不是外部规范。
2. `BY5TCLAB` DICE 是最值得补外部规范的固件模糊测试底座：83 个 MCU 样例、
   11 种 MCU、9 种直接存储器访问控制器，以及 Guitar Pedal、Soldering Station、
   Stepper Motor、Oscilloscope 等 7 个真实固件。论文没有给固定采样周期或截止期。
3. `GNUCP68Y` Mallory 和 `Z9KE8VD6` 中的 Chronos 有成熟的分布式故障/超时模糊
   测试对象，但 100 ms 观察周期、时钟偏差或实现超时库均是工具/配置值，不是系统规范。
4. `9YJ24CQJ` FirmFuzz 观察到某路由器守护进程每 3 分钟调用一次 `arpping`；
   180 秒来自实现观察而不是厂商规范，而且 `[180,180]` 是点区间，不能人工添加容差
   假装成 MITL。

### 7.2 完整覆盖表

| # | Zotero 键 | 类型/对象 | 结论 |
|---:|---|---|---|
| 1 | `Z9KE8VD6` | 分布式系统 fuzz 综述 | Chronos 超时无固定规范值；可复用底座 |
| 2 | `KKITREBF` | 嵌入式 fuzz 综述 | 无度量时序性质 |
| 3 | `TVYQTQPP` | 深度学习固件 fuzz | 无可核实固定时序性质 |
| 4 | `GNUCP68Y` | Mallory 分布式故障调度 | 100 ms 是工具参数；六个公开系统可作底座 |
| 5 | `KASTL2Y5` | 通用 fuzz 综述 | 无固定系统时限 |
| 6 | `LERTF2BR` | 网络协议软件 | 按背景要求排除 |
| 7 | `SEY7PJ37` | 嵌入式设备分析综述 | 无本地全文，未决且优先级低 |
| 8 | `9YJ24CQJ` | FirmFuzz | 3 分钟是实现行为，不是规范；点区间不属常规 MITL |
| 9 | `IU5YV864` | StateAFL 网络服务器 | 网络协议且无固定时限，排除 |
| 10 | `P38J8L3P` | 协议 fuzz 综述 | 网络协议，排除 |
| 11 | `BY5TCLAB` | DICE MCU/DMA 固件 | 最值得补数据手册；论文自身无固定时限 |
| 12 | `GYPKBQAQ` | AFL++ 通用基准 | 无领域时间性质 |
| 13 | `QGXIAFZG` | ROS 多机器人 RV | 有固定实验区间公式；不是 fuzz 或外部规范 |
| 14 | `VAQ7RX8U` | WingFuzz 数据库 | 无时序逻辑；实验时长不是系统性质 |
| 15 | `KU5535CN` | 智能合约 fuzz | 无固定时间性质 |
| 16 | `PV9UJ8U3` | 嵌入式 fuzz 综述 | 仅说最大执行时间可作 oracle，无数值 |
| 17 | `S2BB35DY` | 固件 fuzz 综述 | 只有无阈值心跳/活性描述 |
| 18 | `MURH655H` | 通用 fuzz 综述 | 无本地全文，未决且优先级低 |
| 19 | `W5YJY5EB` | 固件分析综述 | 只有实时行为泛称，无固定数值 |
| 20 | `PMF83B3Q` | 物联网 fuzz 综述 | 无固定响应时间 |
| 21 | `IT9WDAFI` | 信息系统 fuzz 综述 | 无本地全文/摘要，未决 |
| 22 | `AJHNXRCW` | UCRF 路由器 HTTP fuzz | 偏网络 Web，且无全文/固定规范 |
| 23 | `3MQP4AV2` | 固件分析分类综述 | “近实时”等定性描述，排除 |
| 24 | `ERCWB6UH` | 固件/二进制分析综述记录 | 无全文，疑似重复记录 |
| 25 | `YJW66TNT` | 物联网固件分析 | 无固定数值 |
| 26 | `T25TK89J` | 通用 fuzz 机制综述 | 无度量时序性质 |
| 27 | `G5FFFL3G` | 有状态协议 fuzzer 对照 | 网络协议，排除 |
| 28 | `NUHDR2L7` | 物联网 fuzz 综述 | 提到等待/响应时间但没有常量 |
| 29 | `XTZVRTCD` | 通用 fuzz 系统综述 | 无全文、无时序证据 |
| 30 | `5KRS4KNW` | 机器学习 fuzz 综述 | 无全文、无系统时间规范 |
| 31 | `93F6SRH2` | 嵌入式 fuzz 综述和实验 | 24 小时是实验预算；心跳无阈值 |
| 32 | `77TJEKSF` | 大模型生成嵌入式网络代码 | 非 fuzz 执行且无时间逻辑 |
| 33 | `YSYRFWBX` | 网络协议 fuzz 综述 | 按背景要求排除 |
| 34 | `WWX57TQW` | 网络协议 fuzz 综述 | 按背景要求排除 |

明确不计入系统性质的值包括：24/48 小时 fuzz 批次预算、测试用例超时、消息间
sleep、设备重启等待、观察器上报周期、时钟同步误差和网络延迟假设。

## 8. Zotero 之外的背景与基准生态

### 8.1 联合国第 152 号法规：自动紧急制动系统

这是“外部固定规范 + 非网络系统 + 已有自动驾驶仿真模糊测试生态”的最佳新背景。
[联合国第 152 号法规的现行欧盟文本](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A42024X2497)
包含多项固定时间：例如可预期碰撞时，碰撞警告最迟应在紧急制动开始前 0.8 秒出现；
系统未初始化时还存在累计行驶 15 秒后的状态指示要求。法规同时给出适用速度、制动
需求和试验程序。

0.8 秒性质宜使用过去时间或辅助时钟表达。若定义
`EpisodeWarningStart` 为本次碰撞情景中已完成配对的警告上升沿，可写成：

```text
G(EmergencyBrakeStart ∧ Anticipatable
  -> P_[0.8s,∞) EpisodeWarningStart)
```

`P_I` 表示“在过去区间 `I` 内曾经发生”。这里必须按同一碰撞情景配对，否则很久以前
其他场景的警告会造成假满足。若只支持未来 MITL，应构造显式警告时钟或时间自动机。
不能把法规中的“累计 15 秒”直接偷换成“连续 15 秒”，因为累计时钟不是普通连续
区间语义。

模糊测试底座可采用 Apollo/LGSVL 或 CARLA 场景变异。LawBreaker 使用 STL 风格语言
和仿真模糊测试检查交通法规，但其论文也明确说明部分法规未给响应时间，作者自行设定
2 秒或 3 秒。因此 [LawBreaker 论文](https://cposkitt.github.io/files/publications/lawbreaker_av_fuzzing_ase22.pdf)
适合复用输入空间和模糊测试流程，不适合把论文自设的 2/3 秒当正式规范。最严谨的做法
是“复用 LawBreaker 类模糊测试器，替换为 UN R152 原文提取的 oracle”。

### 8.2 铁路道口与列车鸣笛

铁路道口是固定时间最清楚的经典实时系统之一。美国联邦铁路管理局材料规定，恒定警告
时间检测应提供至少 20 秒预警；列车鸣笛通常要求在到达公共道口前 15--20 秒开始，
另有高速和四分之一英里等明确例外。参见
[FRA 恒定警告时间资料](https://gradecrossingtoolkit.fra.dot.gov/eLib/Details/L00072)和
[FRA 列车鸣笛规则说明](https://railroads.dot.gov/railroad-safety/divisions/crossing-safety-and-trespass-prevention/train-horn-rulequiet-zones)。

候选公式必须把例外和事件方向写清：

```text
G(NormalCrossingApproach ∧ HornStart
  -> F_[15s,20s] CrossingOccupied)

G(WarningStart ∧ ApproachContinues
  -> G_[0s,20s) ¬CrossingOccupied)
```

第二式表达“预警开始后的前 20 秒不得占用道口”，是纯未来 MITL 的最低预警约束；
若还要表达道口最终被占用，需在适用条件下另加活性义务。铁路道口已有经典时间
自动机、模型检查和模型测试传统，规范来源强，但主流“性质引导模糊测试”论文链弱于
自动驾驶，需要本项目自行接入变异器和轨迹监视器。

### 8.3 CPFuzz：最容易复现实验，但不是外部规范集

[CPFuzz 代码仓库](https://github.com/shangfute/CPFuzz)把覆盖反馈模糊测试与时序鲁棒度
结合，提供 Heater、Heat、DC Motor、Fuzzy Controller/倒立摆和 SPI 三组性质。
本轮冻结只读审计的上游提交为 `54e141faed5ffe5b20b255e33b78b2e664b79739`。

其模型仿真时域分别为 10、10、1.0、0.1、50、200、500。这些值来自 `.tst` 基准
配置，性质主要是在有限时域内始终避开不安全状态。它们是很好的 `BENCHMARK_FIXED`
算法对照，却不是法规或设备厂商固定期限。适合回答“算法是否能在成熟 fuzz 基准上
找到反例”，不适合回答“实现是否符合外部固定时间规范”。

### 8.4 ARCH-COMP 与自动变速器

[ARCH-COMP 基准仓库](https://gitlab.com/goranf/ARCH-COMP)和
[汽车时序逻辑需求基准论文](https://easychair.org/publications/paper/4bfq)提供自动变速器、
发动机等成熟性质证伪基准。自动变速器性质含 20 秒、10 秒、2.5 秒等固定窗口，也有
MONAA 文献中的 10 秒/1 秒定时模式。

2019 年竞赛报告给出的代表性公式包括：

```text
AT1:  G_[0s,20s](vehicle_speed < 120)
AT2:  G_[0s,10s](engine_rpm < 4750)
AT51--AT54:
      G_[0s,30s](gear_entry_i -> G_[0s,2.5s] gear_i)
```

其中 `gear_entry_i` 在原基准中由一个 0.001--0.1 秒的短“最终”窗口定义。竞赛报告
明确说明这些参数被选择为“具有一定证伪难度”，所以数值来源是基准构造，不是车辆
制造商规范。

但这些数值常由基准作者为难度或模型实例选择，不是制造商规范。因此它们应进入
`BENCHMARK_FIXED` 对照组。优点是模型、输入、性质和多工具结果齐全，最容易获得有
统计意义的基准数量；缺点是不能作为外部规范符合性实验。

## 9. 推荐实验方案

### 9.1 第一阶段：保持 ArduPilot 背景，扩到 6 组固定时间性质

建议顺序：

1. **振动保护**：先完成一条官方文字、冻结源码、官方 SITL 路径三者一致的正向
   基准，验证源端时钟、监视器和变异引导链；
2. **地形 2/5 秒差分**：输入和现有测试路径清楚，最可能得到稳定时间反例；
3. **左舵 2/3 秒差分**：遥控输入简单，适合验证边界搜索；
4. **降落伞连续性序列**：检验模糊测试器是否能组合“异常—恢复—异常”状态；
5. **坠毁检查和 EKF**：扩大多条件、替代触发和源端状态组合。

每条性质建立四层文件，不把它们混成一份公式：

```text
requirement.md              外部官方文字、版本、适用条件、固定时间
formula.mitl                经人工审核的正式性质
observation_plan.json       原子命题到当前源码和源端时钟的绑定
campaign_manifest.json      参数、输入范围、提交、SITL 配置和结果状态
```

### 9.2 第二阶段：加入一个成熟模型基准和一个外部规范背景

- 算法横向对照：Mecel 齿轮控制器或 CPFuzz；
- 外部规范泛化：UN R152 自动紧急制动系统；
- 若更看重形式化清晰度而非已有 fuzz 论文：铁路道口。

这形成三类互补实验：飞控真实源码、成熟公开模型、法规来源行为规范。论文中应分别
报告，不能把基准常量与法规常量混成一个“固定时间规范”统计量。

### 9.3 最小数据字段

每条性质至少记录：

- `time_source_kind`：时间来源类别；
- `time_source_quote`：短证据摘要与页/行；
- `time_bound` 和单位；
- 区间开闭性；
- `clock_semantics`：仿真时间、飞控单调时间、事件产生时间或监控接收时间；
- `parameter_dependency`：是否依赖参数；
- `applicability_guard`：适用条件和例外；
- `implementation_binding`：当前提交的源码映射；
- `implementation_satisfaction`：初始保持 `NOT_ASSESSED`；
- `runtime_evidence_status`：是否已实跑、重放和最小化。

## 10. 本轮验证与限制

已完成：

- Zotero 两目录 47/47 顶层条目分类；
- 两个冻结快照和全文索引导出；
- 从 PGFuzz 原论文 PDF 第 18 页重新复核表 XII 的 56 条公式，并单独统计其中
  ArduPilot/PX4 51 条的有界 `F`；
- ArduPilot 官方网页、冻结源码和现有 SITL 路径只读交叉核对；
- Mecel/MoniTAal 本地模型和性质文件只读核对；
- CPFuzz 仓库和外部法规/基准网页只读核对；
- `snapshot_zotero_collections.py` 通过 Python 语法编译检查。

未完成：

- 没有运行任何完整模糊测试批次；
- 没有实跑 ArduPilot 的 2/5 秒、2/3 秒或降落伞连续性候选；
- 没有把上述候选正式转换、编译并证明等价于 TAMonitor 当前接受的未来 MITL；
- 没有证明 Mecel 的全部性质自动机与所列 MITL 简式完全等价；
- 没有获得缺失的 Zotero 附件全文；
- 没有作法规或产品符合性结论。

因此本报告交付的是“候选语料与实验路线审计”，不是运行时违反报告，也不是符合性
认证。最合理的下一项实现工作是先把 ArduPilot 振动保护的两条性质做成完整
`requirement -> formula -> observation plan -> SITL trace` 代表案例。
