# TAMonitor 使用文档入口

- 完整手册：`TAMonitor_User_Manual.md`
- 最终实验结果入口：
  `/home/lqq/project/TAFuzz/test/TARV/results/FINAL_RESULTS_README.md`
- 最终审查工作簿：
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx`

当前 TAMonitor v1 的正式运行时验证能力是：

1. MightyPPL 解析用户 MITL 公式并构造 flatten 时间自动机。
2. 将 MightyPPL 的 BDD 边标签按 proposition valuation 投影为 MoniTAal 可匹配的 `bits:<valuation>` 标签。
3. 用 MoniTAal 正/负自动机 monitor 执行三值运行时验证。
4. 输出逐步 verdict、最终 verdict、公式可满足性、构造和监控统计、CSV/JSON/XLSX 报告；需要在终端同步查看逐步 verdict 时使用 `--print-steps`。

BDD-native runtime 和 compflatten runtime 是 v1 保留接口，不声称已实现。
