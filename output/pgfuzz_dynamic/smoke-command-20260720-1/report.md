# PGFuzz 当前 ArduCopter 动态输入—状态报告

## 术语与状态

- **PGFuzz**：`Policy-Guided Fuzzing`，策略引导模糊测试。
- **SITL**：`Software in the Loop`，软件在环仿真。
- **INPUT_P**：普通配置参数输入；**INPUT_C**：用户命令输入；**INPUT_E**：仿真环境参数输入。
- `CONFIRMED_EFFECT`：确认影响：至少两次重复方向一致，输入和恢复均得到验证。
- `LEGACY_ONLY_CANDIDATE`：仅旧规则候选：只有 PGFuzz 标准差规则命中。
- `NO_OBSERVED_EFFECT`：未观测到影响：仅限本次模式、取值和时间窗。
- `INCONCLUSIVE`：无法判断：输入、消息、重复或恢复证据不足。

## 当前输入目录

- `INPUT_P`：1025；`INPUT_C`：136；`INPUT_E`：362。
- 执行分类：`DISRUPTIVE_EXCLUDED`=34，`READY_SAFE`=813，`REQUIRES_PRECONDITION`=97，`REQUIRES_RESTART`=197，`UNKNOWN_METADATA`=382。

## 实验计划

- 分片：1/1；工作项：1。
- 每项重复：3；每个观测窗口：3.0 秒。

## 结果

- 已汇总工作项：0。
- 状态分布：尚未执行动态工作项。

## 证据边界

主机单调时钟只用于发送、接收和窗口顺序；消息自带飞控时间字段原样保存。主机接收时间不是飞控内部事件真实发生时间。当前结果只适用于记录的提交、SITL 模型、输入值、模式和前置状态，不构成真实硬件或性质符合性结论。
