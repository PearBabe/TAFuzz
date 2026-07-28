# Benchmark schemas

- `property.schema.json`：单条性质的完整证据、IR、TimeContract、MITL、AP、源码/MAVLink 绑定和验证接口。
- `catalog.schema.json`：系统级性质目录。
- `docgraph.schema.json`：里程碑 3 的文档节点/边 JSONL 记录。
- `candidate.schema.json`：关键词预筛命中；它不是已接受性质。
- `timed_trace.schema.json`：TAMonitor 前的带时钟域 timed trace 交换格式。
- `runtime_capture.schema.json`：冻结 SITL 的分阶段 MAVLink、运行参数和时间证据；默认流、参数下载和主动请求必须分开。

JSON Schema 只检查结构。`ACCEPTED` 的证据闭合、时间来源、源码行号、可满足性、非空洞性与监视器结果由 `benchmark/scripts/validate_benchmark.py` 的语义门槛检查；候选条目允许显式缺失并通过 `NEEDS_*` 状态保留。
