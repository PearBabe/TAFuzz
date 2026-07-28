# CCFA 类对比实验设计

研究问题：在相同 Kamailio SUT、seed、reset、硬件和预算下，MITL 自动机覆盖与 PTA cost-to-go 是否改善协议状态/代码覆盖、真实性质违反发现速度和独特性？

主 baseline：AFLnwe、AFLNet、StateAFL。消融：无 MITL、Boolean verdict、自动机覆盖、PTA cost-to-go、完整 TAFuzz。指标：edge/branch、协议状态/转移、自动机状态/边/region、unique violation、unique crash、time-to-first、exec/s、monitor overhead。

工程 smoke 为 1h×1，仅排错；pilot 为 2h24m×3（24h 的 10%）；full 为 24h×4，复用 StateAFL/NSFuzz 对 ProFuzzBench 的公开规模。进入 full 前必须完成 20 条人工签字和 baseline adapter smoke。
