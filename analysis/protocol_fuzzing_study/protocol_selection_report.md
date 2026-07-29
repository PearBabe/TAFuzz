# 协议筛选结论

首选是 **SIP 事务层/有状态代理生态**，主 SUT 为 ProFuzzBench 固定的 Kamailio，PJSIP 为同 benchmark 的端点/参考实现。它是候选中唯一同时通过四个关键门的协议：20 条 RFC 级性质、固定可插桩源码、单机容器 benchmark、至少 AFLnwe/AFLNet/StateAFL 三条同 SUT 路径。

CoAP 的 MITL 性质质量最高，但不在原始 ProFuzzBench 目标集中，首轮无法低成本获得三个公平 baseline；因此列为备用协议。DTLS/TinyDTLS 的 benchmark 成熟，但 ProFuzzBench 固定实现与较新的 DTLS 定时规范版本不齐，列为第二备用。

评分是研究决策量表，不是统计测量。硬门优先于总分；完整分项见 `protocol_scorecard.csv`。
