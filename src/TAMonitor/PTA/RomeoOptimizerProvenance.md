# Roméo DBM 仿射优化器来源与重写边界

## 来源

- 参考实现：Roméo 3.10.12，`tool/Romeo/romeo-cli/dbm.cc` 中
  `DBM::min/max`（当前树约第 657--991 行）。
- 官方 3.10.12 源归档 SHA-256：
  `8f04ecdc141c622a700fe065ca567c4cebbf6d94b58c2820e967d3c4467e0050`。
- 当前工作区 `dbm.cc` SHA-256：
  `b4c30da4662ec1ae2b66d198c29e7714cf6aad2b240f221d79aa85ca8ba9a600`。
- Roméo 源码许可证：CeCILL；许可证全文位于
  `tool/Romeo/Licence_CeCILL-US.txt` 和 `Licence_CeCILL-FR.txt`。
- 当前 Roméo 树包含项目既有的 backward-cost 修复，见
  `tool/Romeo/REPAIR_NOTES.md`；本模块不链接其 production binary，也不修改该树。

## 迁移的数学方法

对 canonical DBM

\[
x_i-x_j\le b_{ij}
\]

上的线性目标 \(c^Tx\)，加入参考节点系数
\(c_0=-\sum_{i>0}c_i\)，把对偶写成无容量上限的最小费用转运：

\[
\min\sum_{ij}b_{ij}f_{ij},\qquad
\sum_j f_{ij}-\sum_j f_{ji}=c_i,\quad f_{ij}\ge0.
\]

生产实现重写这一数学算法，使用 successive shortest augmenting paths、
Bellman--Ford/potentials 和 residual reverse arcs。对偶不可行精确对应原目标
无界。有限对偶值再由共享 QF_LRA equality checker 认证 closure optimizer 与
原严格域 attained。

## 未复制的实现细节

本项目不复制 Roméo 的 `DBM`/`Avalue` 类、变长栈数组、固定宽度
`cvalue`、饱和 epsilon 或被注释掉的启发式无界检测。生产数值使用
`BigInt/BigRational`；严格约束的 attained 由精确 QF_LRA 检查，而不是依赖
Roméo 的有限 epsilon 编码。

因此这是受 Roméo 算法启发的数学重写，不是把 Roméo 源文件编译进 TAMonitor。
原版对照仅用于测试安全整数范围内的数值一致性；发布或再分发时仍应由项目维护者
对根项目许可证与 CeCILL 兼容性做最终法律审查。
