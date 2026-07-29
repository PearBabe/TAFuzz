# Baseline 适配计划

主对比只采用能复用相同 Kamailio 容器与 seed/reset/cov 脚本的 AFLnwe、AFLNet、StateAFL。TAFuzz 只新增旁路 trace adapter 与 monitor，不改变 SUT 协议行为。NSFuzz 作为第四候选，待其 artifact 在不更换 SUT 的前提下复现后再加入；SGFuzz/ChatAFL 不进入首轮主表。

公平性记录项：baseline commit、SUT commit、编译器/flags、seed hash、CPU pinning、reset 成功率、端口、超时、coverage 采样周期、所有 patch。任何 baseline 特有修改单列，不把适配工作算作方法优势。
