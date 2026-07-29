# CCFA 身份核验

结论：截至 2026-07-13，以 CCFA、协议模糊测试、coverage-guided/stateful protocol fuzzing 等组合检索，未能唯一解析出一篇题名或工具名为 **CCFA** 且满足用户描述的公开论文。现有 TAFuzz 调研中的“CCF-A-facing”是实验标准定位，不是论文缩写。

因此本研究采用可审计的操作性定义：**CCFA 类 = 面向有状态网络协议、使用代码或协议状态反馈进行种子/状态调度，并按高水平安全/软件工程论文 artifact 标准比较的 coverage-guided fuzzing**。主比较锚点为 AFLNet、StateAFL、NSFuzz 与 ProFuzzBench；SGFuzz、ChatAFL 只作次级方法，因为并非都能直接复用同一 Kamailio SUT。

该定义不是声称存在“CCFA 方法”，而是消除缩写歧义。若用户能提供原论文题名/截图，应重新打开此门并更新矩阵。
