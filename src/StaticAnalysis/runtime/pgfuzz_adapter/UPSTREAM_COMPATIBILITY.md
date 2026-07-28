# PGFuzz 当前 ArduCopter 动态分析兼容契约

## 术语图例

- **PGFuzz**：`Policy-Guided Fuzzing`，策略引导模糊测试。本目录迁移的是其
  “输入会改变哪些飞控状态”的动态映射功能。
- **SITL**：`Software in the Loop`，软件在环仿真。这里运行当前 ArduCopter
  飞控逻辑，并由软件提供传感器和执行机构环境。
- **MAVLink**：`Micro Air Vehicle Link`，微型飞行器通信协议。适配器通过它
  写参数、发送命令和采集状态。
- **Git blob**：Git 文件对象。其摘要相同表示对应文件字节相同；不表示整个
  仓库工作区没有额外文件。

## 冻结依据

机器可读身份见 `data/upstream_manifest.json`。本地冻结 PGFuzz 的五个核心文件
与 GitHub `main` 对应 Git 文件对象逐一相同。原目录
`baseline/pgfuzz/ArduPilot/Dynamic analysis` 只作为论文制品，不由本适配器改写。

当前目标固定为：

- ArduPilot 提交 `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；
- MAVLink 定义提交 `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`；
- `quad` 模型的 ArduCopter SITL；
- 可执行文件 SHA-256 为
  `cc678abb89675a7c53343f25725da38eae0bbc76345fd44c5c3ffe01c0787715`。

SHA-256 是 `Secure Hash Algorithm 256-bit`，256 位安全散列算法。本任务用它
确认冒烟测试所运行的二进制身份；摘要变化时必须生成新的运行清单，不能沿用
旧结果。

## 文本输入兼容性

适配器为每个运行目录生成：

```text
cmds.txt          命令名,命令编号
envs.txt          每行一个当前 SIM_* 环境参数
params.txt        每行一个当前普通配置参数；这是迁移扩展
preconditions.txt 参数名 值
```

`cmds.txt`、`envs.txt` 和 `preconditions.txt` 保持原制品的行格式。
`params.txt` 用来补充原动态脚本没有直接分析的普通配置参数。

## 文本输出兼容性

`results/` 和 `results_legacy/` 都固定生成以下十五个文件：

```text
roll.txt pitch.txt throttle.txt yaw.txt speed.txt altitude.txt position.txt
status.txt gyro.txt accel.txt baro.txt GPS.txt parachute.txt pre_arm.txt mission.txt
```

每行仍是一个不带类型前缀的输入标识符。`results/` 只写入改进判定确认的输入；
`results_legacy/` 写入原 PGFuzz 标准差规则命中的输入。输入类型、取值、模式、
前置条件和证据另存于结构化结果，避免破坏文本消费者。

原脚本使用 `if Input in line` 去重，会把 `RC1` 和 `RC10` 当成可能重复。本迁移
改为完整标识符相等去重，但不改变输出行格式。

## 结论边界

动态结果只说明指定提交、SITL 模型、输入值、模式、前置状态和观测窗口内存在
或没有观测到影响。它不等于真实硬件验证，也不等于时间性质或飞控实现符合性。
