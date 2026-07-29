# 统计协议

每个 target×fuzzer×variant 报告中位数、IQR 和按 run 重采样的 bootstrap 95% CI。成对方法比较使用双侧 Mann–Whitney U；同一指标族用 Holm 校正；效应量报告 Vargha–Delaney A12 及方向。覆盖时间序列同时报告终点和 AUC，不能把每分钟采样点当作独立重复。

crash 先按栈签名/根因去重，MITL violation 按 `(property_id, normalized transaction prefix, terminal transition)` 去重。超时/启动失败保留为失败 run，不静默重跑。所有分析脚本在看到 full 数据前冻结。
