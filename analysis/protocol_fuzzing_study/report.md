# 协议 MITL 引导模糊测试研究结论

## Material Passport

- 研究问题：哪种协议最适合 TAFuzz 当前 pointwise timed-word、MightyPPL/MoniTAal 和 PTA cost-to-go 能力，并能按 stateful coverage-guided protocol fuzzing 的公开标准完成公平对比？
- 状态：`RESEARCH_COMPLETE / IMPLEMENTATION_BLOCKED_FOR_HUMAN_REVIEW`
- 首选：SIP 事务层与有状态代理生态。
- 主 SUT：Kamailio `2648eb330b133a20f1398d59a28c53532106cad3`。
- benchmark：ProFuzzBench `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074`。
- benchmark 端点/参考实现：PJSIP `bba95b8a95c0a9e8c1939166fd20083ae9e3e956`。
- 生成日期：2026-07-13。

## 核心结论

SIP 是本轮唯一同时满足“20 条规范级时序性质、固定可插桩源码、单机容器 benchmark、至少三个同 SUT baseline 路径”的候选。首轮公平 baseline 应限定为 AFLnwe、AFLNet 和 StateAFL；NSFuzz 可在 artifact 复现后作为第四方法，SGFuzz/ChatAFL 不应为了数量强行放进主表。

未能唯一定位一篇工具或论文名为“CCFA”的协议 fuzzing 论文。因此本研究没有虚构该缩写，而是将“CCFA 类”明确操作化为 stateful coverage-guided protocol fuzzing，并使用 AFLNet、StateAFL、NSFuzz 与 ProFuzzBench 的公开实验标准。若后续提供原文题名或截图，必须重新打开身份核验门。

## 20 条性质的实际验证结果

- 20/20 具有 RFC 3261 section、规范强度、短摘录和固定 commit 源码位置。
- 20/20 使用宽度大于零的区间或非定界事务投影；0 条使用 `[a,a]`。
- 20/20 在 `--word finite --build-mode flatten` 下构造成功。
- 20/20 正例得到 `POSITIVE`，反例得到 `NEGATIVE`。
- 20/20 symbolic/concrete verdict 一致。
- 每条结果目录保留公式、正反 trace、五条实际运行命令、TAMonitor 元数据和自动机统计。

首轮曾有 6 条“Timer fire 与 send/update 同位置”的公式在反例上得到 `INCONCLUSIVE`。最终目录没有隐藏这个问题或引入 1 ms 容差，而是改成 RFC 明确规定的 T1/2*T1 重传时序投影，因此才达到 20/20 decisive verdict。

## 需要人工决定的事项

1. `SIP-TX-05` 来源是 `SHOULD NOT`，应作为软规范违反还是论文主 oracle。
2. `SIP-TX-20` 的 RFC 条件是 Timer C 严格大于 180000 ms，而固定 Kamailio 提交的默认 lifetime 常数是 180000 ms；这可能是实现偏差、不同 timer 概念或配置前提，必须人工判定。
3. AP 使用“先 correlation、后事务投影”；Via branch、CSeq 等动态值只进入事件字段，不进入自动机 alphabet。
4. RFC 4320 的 non-INVITE 100 Trying 规则与 RFC 6026 Timer L/M 暂留 V2，因为 benchmark 固定版本的直接实现映射尚不够强。
5. PTA prefix cost 尚未运行：人工审核前没有合法的 property-specific cost model；不能用任意统一权重制造形式结论。

## 实验设计冻结项

- 工程 smoke：1 小时 × 1，仅排错。
- pilot：2 小时 24 分 × 3，即 full 预算的 10%。
- full：24 小时 × 4，沿用 StateAFL/NSFuzz 对 ProFuzzBench 的公开规模。
- 消融：无 MITL、Boolean verdict、自动机覆盖、PTA cost-to-go、完整 TAFuzz。
- 指标：代码 edge/branch、协议状态/转移、自动机状态/边/region、unique violation、unique crash、time-to-first、exec/s、monitor overhead。
- 统计：中位数、IQR、bootstrap 95% CI、Mann–Whitney U、Holm、Vargha–Delaney A12。

## 当前门禁

研究交付已完成，但代码实现门仍为 `BLOCKED_FOR_HUMAN_REVIEW`。请在 `human_review_packet.xlsx` 的 `Review Signoff` 页逐条选择状态，并完成协议、时间常数、MITL 语义、AP/correlation 与 baseline 公平性的全局签字。未签字项不得进入 harness、论文主张或长时间 fuzzing。

