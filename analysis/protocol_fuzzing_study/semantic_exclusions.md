# 语义与版本排除

本文件记录跨协议目录共同适用、且不能靠改写一句自然语言消除的语义边界。协议或版本专属的排除理由见各目录的 `excluded_properties.md`。

## 当前监控语义

- 不使用 `[a,a]` singleton。当前 MightyPPL 对试探公式 `G* (x -> F [500,500] y)` 返回 `map::at`；主目录仅接纳宽度大于零的区间或非定界全局投影，不擅自加入 epsilon。
- 不引入 STL/ZOH/连续信号语义。输入仍是 finite pointwise timed word；同一协议回调内的事件先原子合并，确有顺序差异时使用已声明的确定 microstep。
- `mathematical_mitl` 的外层使用普通 MITL `G`；可执行 `mightyppl_formula` 使用 MightyPPL 的 weak finite-word `G*`。每条有界验证词都延伸到最大 deadline 之后，且只包含一个 correlation 后的 obligation generation；不能把一次 finite-prefix `POSITIVE` 写成对任意未来的无限词证明。
- `SHOULD/SHOULD NOT` 和实现 profile 条目分别标注软规范或受控配置，不等同于普适协议违反、安全漏洞或 crash oracle。

## 已复现的重叠触发限制

对公式 `G* (a -> (G [0,200) (!b) && F [0,200] b))`，第二个 `a` 在第一个义务尚未结束时再次出现，会暴露当前 flatten monitor 的重叠义务问题：

| Trace | 数学预期 | symbolic | concrete |
|---|---|---|---|
| `0:a, 300:b, 301:{}` | NEGATIVE | NEGATIVE | NEGATIVE |
| `0:a, 100:a, 300:b, 301:{}` | NEGATIVE | **POSITIVE** | **POSITIVE** |

复现材料位于 `semantic_regressions/overlapping_trigger/`；使用的 TAMonitor SHA-256 为 `e2dc4f9a77c49fe900e80d544078d9215c01d894a9396e689dd6fab6dd91d7f4`。四次运行均为 `--word finite --build-mode flatten`，两个 state mode 结果一致。

因此当前目录实行以下硬性接入契约：

1. 每个 monitor 实例只接收一个事务、timer generation、lease generation 或其他单一义务实例；trace 中触发 AP 至多出现一次。
2. adapter 先用连接/事务/动态 token 等关联键分流，再删除动态标识并生成该实例的完整 AP valuation。
3. 新 generation、重启或并发请求必须新建 monitor 实例；不能把多个尚未终止的触发压入同一个 `G*` monitor。
4. 若将来需要单 monitor 原生处理重叠义务，必须先修复 MightyPPL，并把本目录两条 trace 作为回归测试；在此之前不得把这种运行结果当作形式 verdict。

## 暂不执行的分析

- 未运行 PTA prefix cost：当前阶段没有经人工审核的 property-specific cost model。正式 verdict 仅由通过正/负 timed-word 检查的 MITL monitor 给出；统一伪造权重会把启发式误写成形式结论。
