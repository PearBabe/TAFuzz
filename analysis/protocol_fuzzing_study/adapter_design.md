# 协议适配与数据流设计

固定通路：报文/定时器 → SIP 解析与事务关联 → `ProtocolEvent` → 按性质投影 → 完整 valuation timed word → 正/负自动机 → MoniTAal → PTA prefix cost-to-go → 变异/种子调度。

事务键采用 `session_id + top Via branch + CSeq number/method`，必要时加入 sent-by；先关联再投影。事件 JSONL 只携带动态 ID 字段，AP 仍是固定布尔字母表。相同回调内的 timer-fire、send 和 interval-update 合并为一个位置；跨回调竞争按 `(time_tick, microstep, capture_sequence)` 稳定排序。

建议分数：`w_code*C_code + w_proto*C_state + w_aut*C_automaton + w_cost*(1-normalized_cost)`。各项先在当前 campaign 内归一化；MITL verdict 单独记录，不能由该分数替代。
