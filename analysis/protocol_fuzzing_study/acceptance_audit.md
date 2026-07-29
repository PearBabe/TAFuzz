# 计划验收审计

| 验收项 | 结果 | 证据/限制 |
|---|---|---|
| CCFA 身份核验 | PASS_WITH_CAVEAT | 未找到唯一论文；操作性定义已显式记录 |
| 协议硬门 | PASS | SIP；同 SUT 三条直接 baseline 路径 |
| 20 条主性质 | PASS | 恰好 20 个唯一 ID，均有 RFC 锚点与固定 commit 位置 |
| MightyPPL 构造 | PASS 20/20 | finite + flatten + build-only |
| 正反 trace oracle | PASS 20/20 | symbolic 与 concrete 均为预期 verdict |
| Punctual 排除 | PASS | 主目录 0 条 singleton；失败探针记录在 semantic_exclusions.md |
| 动态 ID 不入 alphabet | PASS | correlation 字段与 AP map 分离 |
| PTA prefix cost | NOT_RUN_BY_DESIGN | 尚无人审 property-specific cost model |
| SUT 构建/长 campaign | NOT_RUN_BY_DESIGN | 用户批准前明确禁止 |
| 工作簿 QA | PASS | 9/9 sheet 已渲染检查；XLSX unzip 无错误；公式错误标记为 0 |
| 人工签字 | BLOCKED | 20 条均为 PENDING，实施门保持关闭 |

本审计中的 PASS 只覆盖研究文件、公式构造与手工 trace oracle，不声称已对真实 Kamailio 运行时行为完成 conformance 验证。
