# 文件功能：后向 Priced-DBM 算法的数学语义、论文逐项映射与正确性证明

本文档是 `src/TAMonitor/PTA` 实现的形式化契约。主依据是 Parrot–Lime，
*Backward Symbolic Optimal Reachability in Weighted Timed Automata*
（FORMATS 2020）。实现若与本文档不一致，应视为实现缺陷；不能以测试通过替代
这里列出的语义条件。

## 1. 记号、目标值与论文映射

### 1.1 WTA 及具体语义（Definition 1–2）

加权时间自动机为

\[
\mathcal A=(L,l_0,X,E,Inv,weight),
\]

其中边为 \(e=(l,g,R,l')\)，位置费率 \(p_l=weight(l)\in\mathbb Z\)，
边权 \(c_e=weight(e)\in\mathbb Z\)。估值 \(v:X\to\mathbb R_{\ge0}\)，
统一延时记为 \((v+d)(x)=v(x)+d\)，reset 记为 \(v[R]\)。具体转移为

\[
(l,v,c)\xrightarrow d(l,v+d,c+p_ld),
\]

\[
(l,v,c)\xrightarrow e(l',v[R],c+c_e).
\]

源点、终点以及延时区间内均须满足相应 invariant。由于论文的 invariant 只含
单时钟上界，端点满足即可推出中间点满足；工程实现仍显式保留完整的
`delay stays in invariant` 语义。

给定目标位置集合 \(Goal\)，真正希望得到的是

\[
V_l(v)=\inf\{Cost(\rho)\mid \rho:(l,v)\leadsto Goal\}.
\]

不可达时 \(V=+\infty\)；若成本可任意下降，则 \(V=-\infty\)。论文反向保存的
不是 \(V\)，而是其相反数

\[
\boxed{W_l(v)=-V_l(v)}.
\]

因此论文中“更优”是更大的 \(W\)，合并是 `max/sup`；公共查询转回 \(V\)，
“更优”才是更小的 cost。后文所有不等号均遵守这一约定。

### 1.2 Weighted zone（Definition 3）

一个 weighted zone 为

\[
\mathcal Z=(Z,w,r),\qquad r\in\mathbb Z^X,
\]

语义为定义在 DBM zone \(Z\) 上的仿射函数

\[
W(v,\mathcal Z)=w+\sum_{x\in X}r_x(v_x-\Delta_Z(x)).
\]

\(\Delta_Z\) 是各坐标下确界构成的 offset。对严格 DBM，它可以只位于
\(cl(Z)\)；这不妨碍它作为仿射函数的归一化点。一个位置可有多个重叠
weighted zones，其语义是逐点上包络

\[
W_l(v)=\sup_{\mathcal Z_i:v\in Z_i}W(v,\mathcal Z_i),
\]

等价地，\(V_l(v)=\inf_i(-W(v,\mathcal Z_i))\)。所以普通 Federation 的纯几何
合并不能用作 priced-piece 合并。

### 1.3 论文 Definition 1–10 / Theorem / Lemma 对照

| 论文条目 | 本实现中的含义 |
|---|---|
| Definition 1 | `WeightedAutomatonView`：位置、时钟、入边、invariant、整数 rate/edge cost |
| Definition 2 | 具体延时和离散转移及其累积成本 |
| Definition 3 | `WeightedZone/PricedPiece`：DBM、offset weight、整数 gradient |
| Definition 4 | `actionPredecessor` 与 `timePredecessor` 的集合/最优值语义 |
| Definition 5 | DBM 相交后的精确 rebase |
| Definition 6 | 从 canonical DBM 单时钟上下界生成 lower/upper facets |
| Definition 7 | `restrict(R==0)` 后 `free(R)` 的 inverse reset，reset 斜率清零 |
| Definition 8 | facet weighted-past 及其新斜率、新 offset weight |
| Definition 9 | 反向跨边执行 \(w\leftarrow w-c_e\) |
| Theorem 1 | action predecessor 的精确闭包性 |
| Lemma 1 | 普通 past 由原 zone/lower facets 或 upper facets 覆盖 |
| Lemma 2 | lower facet 给最早 delay，upper facet 给最晚 delay |
| Lemma 3 | facet-past 仿射函数等于具体延时后的反向 weight |
| Theorem 2 | 按 \(p_l\) 与 \(\sum r_x\) 比较选择 lower/upper facets |
| Definition 10 | zone inclusion 与全域 weight dominance 联合 subsumption |
| Algorithm 1 | 从 Goal 开始、沿原 TA 入边展开的 FIFO label-correcting 固定点 |

## 2. 基本 weighted-zone 运算及证明

### 2.1 相交与 rebase（Definition 5）

设 \(Z''=Z\cap A\ne\varnothing\)。保持斜率 \(r''=r\)，并定义

\[
w''=W(\Delta_{Z''},\mathcal Z)
=w+\sum_xr_x(\Delta_{Z''}(x)-\Delta_Z(x)).
\]

则对任意 \(v\in Z''\)：

\[
\begin{aligned}
W(v,(Z'',w'',r))
&=w''+\sum_xr_x(v_x-\Delta_{Z''}(x))\\
&=w+\sum_xr_x(v_x-\Delta_Z(x))\\
&=W(v,\mathcal Z).
\end{aligned}
\]

故相交只缩小定义域，不改变保留点的值。所有 guard、invariant、facet 和
严格可行域相交都必须经过该 rebase，不能仅替换 DBM。

### 2.2 Facet（Definition 6）

先 canonicalize DBM。每个有效单时钟 lower bound \(x\succeq n\) 产生

\[
F=cl(Z)\cap\{x=n\}\in LF(Z),
\]

每个有效 upper bound \(x\preceq n\) 产生相应 \(F\in UF(Z)\)。对角约束
\(x-y\preceq c\) 不产生 time facet，因为统一延时保持 \(x-y\) 不变。
重复或空 facet 必须去重/丢弃。

### 2.3 Inverse reset（Definition 7）

几何定义是

\[
R^{-1}(Z)=relax_R(Z\cap\{R=0\}).
\]

DBM 中精确实现为：

1. 对每个 \(x\in R\) restrict \(x=0\)；
2. 若为空则无 predecessor；
3. 对每个 \(x\in R\) 执行 `free(x)`，但保留时钟非负约束。

集合等价性为

\[
\begin{aligned}
u\in relax_R(Z\cap R=0)
&\iff \exists z\in Z:\ z_R=0\land
   \forall x\notin R,u_x=z_x\\
&\iff u[R]\in Z.
\end{aligned}
\]

成本函数必须做复合 \(W_R(u)=W(u[R],\mathcal Z)\)。由于
\(Z\cap R=0\ne\varnothing\)，对每个 \(x\in R\) 都有
\(\Delta_Z(x)=0\)。而对任意 \(y\notin R\)，在 canonical DBM 中加入
\(x=0\) 不会加强 \(y\) 的 lower bound：任何新路径
\(0\to x\to y\) 的界已由原 DBM 闭包的三角不等式蕴含；反向包含又由求交的
单调性给出。因此

\[
\Delta_{relax_R(Z\cap R=0)}(y)=\Delta_Z(y),\qquad y\notin R.
\]

这给出

\[
r'_x=\begin{cases}0,&x\in R,\\r_x,&x\notin R,\end{cases}
\qquad w'=w
\]

实际代码忠实执行论文 Definition 7：先整体 restrict \(R=0\) 并判空，再
`free(R)`，保持 \(w\) 不变并把 reset gradient 清零；没有执行一个文档外的
中间 rebase。由上面的 offset 不变引理，对任意 inverse-reset valuation \(u\)，

\[
W(u,\mathcal Z[R]^{-1})=W(u[R],\mathcal Z).
\]

这同时证明 reset 前时钟值不应继续影响剩余成本。

### 2.4 反向减边权（Definition 9）

若目标 piece 保存后缀相反成本 \(W'=-V'\)，跨越成本为 \(c_e\) 的边后：

\[
V(u)=c_e+V'(u[R]),
\]

故

\[
W(u)=-V(u)=W'(u[R])-c_e.
\]

因此只需 \(w\leftarrow w-c_e\)，斜率不变。

## 3. Action predecessor（Theorem 1）

对入边 \(e=(l,g,R,l')\) 和 target piece
\(S'=(l',\mathcal Z')\)，假设 \(Z'\subseteq Inv(l')\)，定义

\[
\boxed{
Pre_e(S')=
\left(l,
  \bigl(\mathcal Z'[R]^{-1}-c_e\bigr)
  \cap g\cap Inv(l)
\right).
}
\]

若 target piece 的 invariant 不变量尚未由调用者保证，应先与
\(Inv(l')\) 相交。

**几何正确性。** 对任意 \(u\)：

\[
u\in Inv(l)\cap g\cap R^{-1}(Z')
\iff
(l,u)\xrightarrow e(l',u[R])\land u[R]\in Z'.
\]

**权重正确性。** 由 inverse reset 和 Definition 9：

\[
W(u,Pre_e(\mathcal Z'))
=W(u[R],\mathcal Z')-c_e.
\]

转成直接 cost：

\[
-W(u)=c_e+(-W(u[R])),
\]

恰为“一步边成本 + target 剩余成本”。Definition 5 又保证 guard/invariant
相交不改变保留估值的值。因此 action predecessor 既 sound 又 complete，且一个
target weighted zone 只产生至多一个 action-pre piece。

## 4. Time predecessor（Definition 4、8，Lemma 1–3，Theorem 2）

### 4.1 最优化式和符号

位置费率为 \(p\)，target piece 为 \(\mathcal Z=(Z,w,r)\)。反向值是

\[
W_{pre}(v)=
\sup_{\substack{d\ge0\\v+d\in Z\\[v,v+d]\subseteq Inv(l)}}
\left(W(v+d,\mathcal Z)-pd\right).
\]

等价的 cost-to-go 是

\[
V_{pre}(v)=
\inf_d\left(pd+V(v+d)\right).
\]

对固定 \(v\)，有

\[
W(v+d,\mathcal Z)-pd
=W(v,\mathcal Z)+d\left(\sum_xr_x-p\right).
\]

记

\[
m=\sum_xr_x-p.
\]

于是连续最优化退化为可行 delay 区间上的一维仿射函数：

- \(m\le0\)（论文写作 \(p\ge\sum r_x\)）：取最小可行 delay；
- \(m>0\)（\(p<\sum r_x\)）：取最大可行 delay；
- \(m>0\) 且无有限最大 delay：\(W=+\infty\)，即 \(V=-\infty\)。

### 4.2 Lemma 1：facet 对普通 past 的覆盖

统一延时不改变任何对角差。对每个单时钟 lower bound \(x_i\ge n_i\)，进入
闭包所需 delay 的下界是 \(n_i-v_i\)，所以最早进入时间是

\[
d_{min}=\max(0,\max_i(n_i-v_i)).
\]

若 \(d_{min}=0\)，则 \(v\in Z\)（严格性另见 4.5）；否则至少一个 lower bound
取等，落在某个 lower facet。因此

\[
Z^\downarrow\subseteq Z\cup\bigcup_{F\in LF(Z)}F^\downarrow.
\]

若存在 upper bounds \(x_i\le N_i\)，可行 delay 的上界为

\[
d_{max}=\min_i(N_i-v_i),
\]

至少一个 upper bound 取等，故

\[
Z^\downarrow\subseteq\bigcup_{F\in UF(Z)}F^\downarrow.
\]

这就是论文 Lemma 1 的两个覆盖方向；反向包含在 exact-domain 相交后显然成立。

### 4.3 Lemma 2：facet 对应最早/最晚 delay

若 facet 由 \(y=n\) 定义，任何从 \(v\) 到该 facet 的 delay 唯一为

\[
d_F=n-v_y.
\]

若它是 lower facet，任何更小 delay 都违反 \(y\ge n\)，所以 \(d_F=d_{min}\)；
若它是 upper facet，任何更大 delay 都违反 \(y\le n\)，所以
\(d_F=d_{max}\)。当多个约束同时取等时会产生等价候选 piece，去重不改变
上包络。

### 4.4 Definition 8 与 Lemma 3：facet-past 的权重传播

设 facet \(F=cl(Z)\cap\{y=n\}\)，其 weighted rebase 为
\((F,w_F,r)\)。Definition 8 定义

\[
r'_x=r_x\quad(x\ne y),
\]

\[
\boxed{r'_y=p-\sum_{x\ne y}r_x},
\]

以及

\[
\boxed{
w'=w_F+
\sum_xr'_x(\Delta_{F^\downarrow}(x)-\Delta_F(x)).
}
\]

对 \(v\in F^\downarrow\)，代入 \(d_F=n-v_y\)：

\[
\begin{aligned}
W(v+d_F,\mathcal Z)-pd_F
&=w_F+\sum_xr_x(v_x+d_F-\Delta_F(x))-pd_F\\
&=w_F+\sum_{x\ne y}r_x(v_x-\Delta_F(x))\\
&\quad+\left(p-\sum_{x\ne y}r_x\right)
       (v_y-\Delta_F(y))\\
&=w_F+\sum_xr'_x(v_x-\Delta_F(x))\\
&=w'+\sum_xr'_x(v_x-\Delta_{F^\downarrow}(x))\\
&=W(v,F_p^\downarrow).
\end{aligned}
\]

这证明 Lemma 3。论文把该 Lemma 的 \(p\) 写成 \(\mathbb N\)，但 Definition 1
允许 \(p\in\mathbb Z\)；上述纯代数证明对任意整数（乃至有理数）\(p\) 成立，
实现按 WTA 定义支持整数 rate。

### 4.5 严格约束与 infimum 是否达到

closure 只用于求连续仿射函数的 supremum/infimum 值；predecessor 的定义域仍须
存在真正的 \(d\) 使 \(v+d\in Z\)。例如 \(Z=\{0\le x<1\}\) 的 upper facet
past 包含 \(x=1\)，但 \(x=1\notin Z^\downarrow\)。若直接返回
\(F^\downarrow\)，会制造虚假 predecessor。

因此实现使用

\[
Domain_F=F^\downarrow\cap Z^\downarrow\cap Inv(l),
\]

其中 \(Z^\downarrow\) 保留原 DBM 的 strictness，\(F\) 则来自 \(cl(Z)\)。
值仍按连续性在 facet 上计算。若最优端点只在 closure 中，记录
`attained=false`；这表示数值是严格正确的 infimum，但 witness 必须取
\(\varepsilon\)-近似 delay。

这是对论文 Theorem 2 在严格 DBM 情形的必要语义补全，不改变闭 zone 情形。

### 4.6 Theorem 2

综合 4.1–4.5，精确 time predecessor 为

\[
Pred_\delta((l,\mathcal Z))=
\begin{cases}
(l,\mathcal Z\cap Inv(l))\ \cup
\displaystyle\bigcup_{F\in LF(Z)}
(l,F_p^\downarrow\cap Z^\downarrow\cap Inv(l)),
&p\ge\sum_xr_x,\\[2ex]
\displaystyle\bigcup_{F\in UF(Z)}
(l,F_p^\downarrow\cap Z^\downarrow\cap Inv(l)),
&p<\sum_xr_x.
\end{cases}
\]

第一分支由 Lemma 1 覆盖所有最小 delay 候选，Lemma 2 说明候选确为最小端点，
Lemma 3 给出正确值；第二分支同理使用最大端点。因此每个具体 predecessor
valuation 都至少被一个输出 piece 覆盖（complete），每个输出 valuation 也存在
合法 delay（sound），且 piece 的值恰为最优值（optimal）。

若第二分支没有有限 upper facet，可沿时间无限增大 \(W\)，故在精确
\(Z^\downarrow\cap Inv(l)\) 定义域上 \(W=+\infty,V=-\infty\)。论文为保持普通
weighted-zone 类型而把该结果写成空集；本实现必须产生并继续传播特殊的
`UNBOUNDED_BELOW` piece，不能把它误报为 `UNREACHABLE`。只有该 piece（或它的
某个 predecessor）覆盖初始配置时，全局初始查询才是 `UNBOUNDED_BELOW`；仅在
不可达位置发现它不能据此误报初始最优值。

### 4.7 为什么输出仍是有限个 DBM-affine pieces

canonical DBM 只有有限个单时钟 facets。统一延时保持对角约束，最早/最晚
endpoint 只可能由某个单时钟 bound 激活；“哪个 bound 激活”的比较仍是差约束，
例如

\[
n_i-v_i\ge n_j-v_j
\iff v_i-v_j\le n_i-n_j.
\]

每个 facet substitution 又由 Lemma 3 得到仿射函数。因此一个 weighted zone 的
time predecessor 是有限个 DBM-affine pieces。不同 pieces 的仿射值交界未必是
DBM 超平面，所以实现允许重叠并在查询时取上包络，不能强行几何并集。

## 5. Subsumption（Definition 10）

同位置的新状态 \(S=(l,Z,W)\) 可被已访问状态
\(S'=(l,Z',W')\) 剪枝，当且仅当

\[
Z\subseteq Z'
\quad\land\quad
\forall v\in Z:\ W(v)\le W'(v).
\]

第二项在实现中以精确 QF_LRA 判定：检查

\[
Z\land(W(v)>W'(v))
\]

是否不可满足。浮点采样或只比较 offset 均不构成证明。

**剪枝正确性。** 若 \(f\le g\)，则 action predecessor 只做函数复合和减常数，
所以 \(Pre_e(f)\le Pre_e(g)\)。time predecessor 对候选值逐点取 supremum，
所以

\[
\sup_d(f(v+d)-pd)\le\sup_d(g(v+d)-pd).
\]

两个 predecessor 算子均单调。已有 \(S'\) 在新状态的全部定义域上至少同样大
（即 cost 至少同样小），继续向前驱传播后仍然如此，因此丢弃 \(S\) 不会丢失
更优解。

## 6. Algorithm 1 与全局正确性

### 6.1 精确算法

每个 goal location 的初始 piece 是

\[
(l,Inv(l)\cap\mathbb R_{\ge0}^X,0,\vec0).
\]

算法维护 FIFO `Waiting` 和按位置分组的 `Passed`：

```text
best := +infinity
Waiting := all zero-weight goal pieces
Passed := empty

while Waiting not empty:
    S := pop_front(Waiting)
    if S covers (l0, 0):
        best := min(best, -W(0, S))
    if no S' in Passed dominates S:
        insert S into Passed
        for each original incoming edge e=(src,g,R,S.location):
            A := actionPredecessor(e, S)
            enqueue every piece in timePredecessor(src, A)
return best/status
```

这是异步 Bellman–Ford/label-correcting 固定点，不是 Dijkstra。FIFO 是可复现的
调度策略，不参与正确性。

### 6.2 按离散边数量归纳

令 \(V_l^{(k)}(v)\) 表示从 \((l,v)\) 到 Goal、最多使用 \(k\) 条离散边的
最小成本。零边时只有立即处于 Goal（若目标推广为 goal zone，则可先 delay
进入 goal zone）：

\[
V_l^{(0)}=0_{Goal_l}.
\]

定义直接 cost 版本的算子

\[
(\mathcal D_eH)(u)=
\begin{cases}
c_e+H(u[R]),&u\in Inv(l)\cap g,\ u[R]\in Inv(l'),\\
+\infty,&\text{otherwise},
\end{cases}
\]

\[
(\mathcal T_lF)(v)=
\inf_{d\text{ legal}}\{p_ld+F(v+d)\}.
\]

则

\[
V_l^{(k+1)}=min\left(
V_l^{(k)},
\min_{e\in Out(l)}\mathcal T_l(\mathcal D_eV_{l'}^{(k)})
\right).
\]

**基础步。** \(k=0\) 正好是零离散边可达目标的所有运行。

**归纳步。** 任意非空、至多 \(k+1\) 条边的运行唯一分解为“source delay \(d\)
+ 第一条边 \(e\) + 至多 \(k\) 条边的 suffix”。成本可加，故固定 \(e,d\) 的
最优 suffix 由归纳假设给出；对所有合法 \(d,e\) 取 inf/min 即上式。反之，
上式每个有限候选都能把合法 delay、边和 suffix 拼接成具体运行。

所以

\[
V_l(v)=\inf_{k\ge0}V_l^{(k)}(v),
\]

而 Algorithm 1 的 worklist 恰好异步枚举这些有限 suffix families；Theorem 1、2
保证每次符号 predecessor 与具体分解等价，Definition 10 的单调性证明保证剪枝
不改变下确界。算法终止且状态为 `COMPLETE` 时，返回值即全局最优 infimum。

### 6.3 论文 Algorithm 1 的位置变量歧义

论文第 11 行写作对 \(e=(l,g,R,l')\) 调用 \(Pre_e(S)\)，而第 5 行又把当前
状态位置命名为 \(l\)。按 Theorem 1，\(Pre_e(S)\) 的 `S.location` 必须是边的
目标 \(l'\)，所以实现必须遍历

\[
e=(l_{src},g,R,l_{current}),
\]

即 `edges_to(current_location)`。把边和状态简单反向、或遍历当前位置的出边，
都不等价于论文 predecessor。

### 6.4 Goal seed 与一次 source-time predecessor

论文目标是“到达 goal location”，所以目标位置的任意 invariant 合法估值都可
零成本结束；seed 必须是 \(Inv(goal)\cap\mathbb R_{\ge0}^X\)，不是忽略 invariant
的真正全集。

已存 piece 表示从它开始的完整 suffix cost。跨一条入边时先做 action predecessor，
再做一次源位置 time predecessor。target 内未来 delay 已经包含在 target piece
中，不应再以普通几何 `past()` 扩张而漏记 cost。若某实现维护显式 time-closed
不变量，第二次 priced-time closure 因 Bellman 算子的幂等性只会冗余；但绝不能
做“不带 cost 的 target past”。

## 7. 终止性、负权和完整性状态

局部闭包性与全局最优性证明本身不推出 worklist 一定终止。论文假设所有到
Goal 的相关运行成本存在统一下界；它排除了能反复降低并最终到达 Goal 的负环。
在该假设及论文引用的后向 zone 终止结果下，不需要 forward extrapolation/
normalization。

实现必须区分：

- `COMPLETE`：固定点完成且所需 lower-bound 契约成立；
- `UNREACHABLE`：完整固定点证明初态不在任何 co-reachable piece；
- `UNBOUNDED_BELOW`：发现 time-unbounded 下降，或已证明相关负环；
- `ASSUMPTION_REQUIRED`：含负 rate/edge cost，但用户未声明 lower-bounded；
- `INCOMPLETE_RESOURCE_LIMIT`：timeout/piece limit，中间值不能宣称全局最优。

timeout 是整个固定点的 wall-clock 契约。每次 Z3 dominance 使用当时剩余预算，
每个不可中断的 DBM/Federation 原语返回后立即重查 deadline；即使最后一次操作
刚好清空 worklist，只要已经越过 deadline，也必须报告资源不完整而非
`COMPLETE`。

论文没有给出一般负离散环检测算法。本实现若只接受
`--pta-assume-lower-bounded`，该标志是显式前提契约，不是程序完成了负环证明。
默认 MightyPPL 模式 \(p_l=1,c_e=0\) 天然无负成本环，求得的是最短剩余时间。

## 8. 实现必须保持的可检验不变量

1. 每个 piece 的 DBM canonical、非空且包含于该位置 invariant。
2. `w/r/offset` 的求值在任何 rebase 前后逐点相同。
3. action-pre 的几何投影等于普通 DBM inverse-reset predecessor。
4. time-pre 输出几何并集等于 exact \(Z^\downarrow\cap Inv(l)\)，不能等于一个
   更大的 closure past。
5. 每个 witness 的 `attained` 与严格边界一致；未达到的值只能作为 infimum。
6. 同位置 pieces 只按 Definition 10 剪枝，不能按纯 Federation inclusion 合并。
7. 查询 \(V\) 必须取所有覆盖 pieces 中 \(-W\) 的最小值，并返回对应 witness。
8. 任何资源中断或未满足前提都必须传播到 snapshot 和 JSON，禁止输出
   `complete/optimal`。
9. `-infinity` marker 第一次产生时记录真正的无界 delay；继续跨更早边传播时，
   当前 delay 必须是可重放的 zero/lower-facet 规则，并通过 successor-region ID
   指向无界发生的后缀，不能把每一层都伪标成当前 delay 无界。

## 9. 独立验证义务

- 论文 Figure 1 的初始最优成本为 9。
- Figure 2 必须触发原 zone 与两个 lower-facet 过去分区，并逐点符合 Lemma 3。
- 每个原语分别覆盖正、零、负 delay slope，单/多 reset，严格上下界和无界下降。
- 关闭 subsumption、改变 FIFO 中同层插入顺序后，完整模型的查询结果不变。
- 非负 rate、零 edge cost 时，用不 reset 的 observer clock 或独立有界路径
  QF_LRA 编码验证最短时间。
- Romeo artifact 只验证论文原实现的 forward/backward 一致性；它是 Petri-net
  mixed forward/backward 实现，不能替代本模块自身的 DBM 单元测试。

## 10. Roméo-style exact mixed forward/backward

本节给出 `ReachableZoneGraph.cpp` 和 `MixedPricedSolver.cpp` 的实际语义。
前半部分先在未定价 TA 上构造 exact reachable-zone graph；只有当该图
完整时，后半部分才在图节点上运行 Parrot--Lime priced
predecessor。“mixed”指前向限定实际运行域、后向求剩余成本；两个阶段都是
exact DBM 运算，不做 extrapolation。

### 10.1 Goal-terminal 具体语义

设 \(G\subseteq L\) 为 Goal locations。实现分析的是自动机

\[
\mathcal A_G=\mathcal A\setminus
\{e\in E\mid source(e)\in G\},
\]

即 forward reachable-space 中进入 Goal 后仍可在该 location 内延时，但不再走离散出边。这正是
`ReachableZoneGraph.cpp` 在将新 target 扩张为 `post_zone` 之后，对
`is_goal` 节点停止展开的顺序。成本目标另采用终端（first-hit）Goal 语义：
运行第一次进入 Goal 即可且必须停止累计成本。因此

\[
V_G(l,v)=\inf\{Cost(\rho)\mid
 \rho:(l,v)\leadsto G\text{ in }\mathcal A_G,
 \rho\text{ stops at its first }G\text{ configuration}\}.
\]

从 Goal 本身出发立即结束，因此 \(V_G(l,v)=0\)（\(l\in G\)），即使 Goal
location 的 rate 为负也不允许先在 Goal 内等待以继续降价。forward 中对 Goal
`entry_zone` 计算的 `post_zone` 只扩大可达 Goal 查询域；后向跨入边时会重新交
该 arc 的 `entry_zone`，所以这段 Goal 内时间闭包不作为带成本的 continuation。
这一语义适合“剩余成本到违规”：违规一旦到达即终止评分。

必须区分另一种问题：若允许运行先到 Goal，再离开 Goal 经过负成本路径后
回到 Goal，则得到的非终端值可能严格小于 \(V_G\)。因此本节的
`mixed = full` 定理中，`full` 始终指不先做 reachable-space 裁剪、但使用
同一 \(\mathcal A_G\) 终端语义的全局后向值。若要与保留 Goal 出边的纯后向
solver 直接对比，还需满足以下任一条件：

1. 所有 rate/edge cost 非负（MightyPPL 默认模型满足）；
2. Goal 本来就无出边；
3. 已另行证明 Goal 终端化不改变最优值。

### 10.2 Exact delay 和 Post 算子

对 \(A\subseteq Inv(l)\) 定义合法时间后继

\[
\uparrow_l A=
\{v+d\mid v\in A, d\ge0,
             \forall t\in[0,d],\ v+t\in Inv(l)\}.
\]

DBM zone 和 invariant 都是凸集。因此对 \(v\in A\subseteq Inv(l)\)，
\(v+d\in Inv(l)\) 当且仅当整个线段 \(v+[0,d]\) 都在 invariant 中。
Pardibaal 的精确 `future()` 所以满足

\[
Future(A)\cap Inv(l)=\uparrow_l A. \tag{10.1}
\]

对边 \(e=(l,g,R,l')\) 和 source zone \(Z\subseteq Inv(l)\)，定义

\[
F_e(Z)=Z\cap g, \tag{10.2}
\]

\[
E_e(Z)=Reset_R(F_e(Z))\cap Inv(l'), \tag{10.3}
\]

\[
P_e(Z)=\uparrow_{l'}E_e(Z). \tag{10.4}
\]

实现顺序与此完全一致：复制 `source.zone`后交 guard 得
`fire_zone`；对所有 reset clocks 执行 `assign(clock,0)` 并交 target
invariant 得 `entry_zone`；最后 `future()` 并再交 target invariant 得
`post_zone`。多个时钟都赋值为零，所以这些 assignment 的顺序不改变同时
reset 的像。

**Post soundness。** 若 \(q\in P_e(Z)\)，则存在 \(u\in F_e(Z)\)、
\(q_0=u[R]\in Inv(l')\) 和 \(d'\ge0\)，使 \(q=q_0+d'\) 且 target
delay 合法。因此从 \(u\) 真实执行 \(e\) 后延时可达 \(q\)。

**Post completeness。** 任意从 \(Z\) 中估值执行 \(e\)、再在 \(l'\) 合法延时得到的
\(q\)，其边前估值必在 (10.2)，reset 后估值必在 (10.3)，从而由
(10.1) 有 \(q\in P_e(Z)\)。所有 DBM intersection、`assign`、`future`
均保留 strict bound，因此上述是真正集合的等价，不是拓扑闭包的等价。

初始 zone 的实际顺序是

\[
Z_0=\uparrow_{l_0}
\bigl(\{\mathbf0\}\cap Inv(l_0)\bigr). \tag{10.5}
\]

代码先用 zero DBM 交 invariant；若为空则精确可达集为空。非空时再
`future()` 和第二次 invariant intersection。因此不会从一个违反初始
invariant 的虚假零估值开始。

### 10.3 Goal 截断 reachable space 的 least fixed point

对按 location 索引的集合族 \(S=(S_l)_{l\in L}\)，定义单调算子

\[
\Phi_G(S)_{l'}=
S_{l'}\cup I_{l'}\cup
\bigcup_{\substack{e=(l,g,R,l')\\l\notin G}}P_e(S_l), \tag{10.6}
\]

其中 \(I_{l_0}=Z_0\)，其余 \(I_l=\varnothing\)。由 intersection、reset image
和 time successor 对并集的可分配性，

\[
Reach_G=\mu S.\Phi_G(S) \tag{10.7}
\]

恰是 \(\mathcal A_G\) 的可达集。进入 Goal 的 Post 仍完成 (10.4)，所以
Goal location 内的合法时间后继位于 \(Reach_G\)；但 (10.6) 不使用
Goal 作为离散边源点。

设算法当前所有 node zone 的 location-wise 并为 \(U\)。下述循环不变式成立：

1. 每个 node zone 中的每个估值都由某条 \(\mathcal A_G\) 具体前缀可达，
   即 \(U\subseteq Reach_G\)；
2. 每个入队 node 都在有限次 \(\Phi_G\) 迭代中产生；
3. 每个出队非 Goal node 都对其全部出边按稳定 `EdgeId` 顺序计算了
   (10.2)--(10.4)。

基础情形由 (10.5) 成立。Post soundness 和 completeness 保证每次
扩展保持不变式。若新 \(P_e(Z)\) 被某个同 location 旧节点包含，则复用
旧 node 不改变 \(U\)；否则创建新 node，恰好把该 exact Post 加入
\(U\)。

若 FIFO 自然穷尽，则每个已生成的非 Goal zone 都已展开，其每个 Post
要么本身是 node，要么包含于旧 node，所以 \(\Phi_G(U)=U\)。由
\(U\subseteq Reach_G\) 且 \(U\) 是包含初始集的不动点，最小不动点性质又给出
\(Reach_G\subseteq U\)。故

\[
\boxed{U=Reach_G}. \tag{10.8}
\]

这个结论只在 worklist 穷尽时成立；资源中断时仅有声音的单向结论
\(U\subseteq Reach_G\)，不能声称已覆盖全部可达域。

### 10.4 One-way inclusion 和带域 graph path

对 candidate \(P\) 只检查

\[
P\subseteq Z_m \quad\text{for an existing node }m
\tag{10.9}
\]

并复用按创建顺序遇到的第一个覆盖 node。实现不做反向 inclusion 删除，
不用新的较大 zone 替换或重连旧 node。这不仅保持 (10.8)，还保持已经
分发的 NodeId、ArcId 和 backward delta 的含义。

即使 (10.9) 成立，实现仍为该次 Post 新建 arc \(a\)，并单独保存

\[
F_a=F_e(Z_n),\qquad
E_a=E_e(Z_n),\qquad
P_a=P_e(Z_n), \tag{10.10}
\]

其中

\[
E_a\subseteq P_a\subseteq Z_m. \tag{10.11}
\]

所以 arc 不表示“从 \(Z_n\) 可一步到达整个 \(Z_m\)”，而表示带
`fire/entry/post` 域的关系 (10.10)。单看 NodeId 序列的裸 graph walk
可能因为 inclusion reuse 而缺少可组合的估值；实现从不把这种裸 walk
当作具体运行。

带域的 graph path 是一个 arc 序列 \(a_1,\ldots,a_k\) 及估值/延时
见证，每一步满足：边前估值在 \(F_{a_i}\)，reset 后在 \(E_{a_i}\)，
下一个离散步前的合法时间后继在 \(P_{a_i}\)。由 Post soundness，每个
这样的 path 是一条具体 \(\mathcal A_G\) 运行。反过来，由 Post completeness
和完整图中每个非 Goal node 都已展开，每条具体 \(\mathcal A_G\)
运行都可按每步所在 node 映射成至少一条带域 graph path。

### 10.5 Node-scoped Goal seed 和 arc priced predecessor

对可达节点 \(n\) 记其 location 为 \(l_n\)、zone 为 \(Z_n\)。每个
\(l_n\in G\) 的 Goal node 以

\[
\mathcal G_n=(Z_n,0,\vec0,attained=true) \tag{10.12}
\]

播种。因此只有真实可达的 Goal valuation 进入 mixed 快照；不使用整个
location invariant 伪造前缀可达性。

考虑 arc \(a:n\xrightarrow e m\)，其域如 (10.10)，边为
\(e=(l_n,g,R,l_m)\)。对 target node \(m\) 上已接受的 priced piece
\(\mathcal Z_m\)，实现严格按以下顺序计算：

\[
\mathcal Z_0=\mathcal Z_m\cap E_a, \tag{10.13}
\]

\[
\mathcal Z_1=
\Bigl((\mathcal Z_0[R]^{-1}-c_e)\cap g\cap Z_n\Bigr), \tag{10.14}
\]

\[
MPre_a(\mathcal Z_m)=
TimePre_{Z_n,p_{l_n}}(\mathcal Z_1). \tag{10.15}
\]

(10.13) 通过 priced `intersection` 重新定基，所以仅缩小定义域而不改变
保留估值的 \(W\)。(10.14) 的实际代码是 `action_predecessor`：先
inverse reset，再减 edge cost，再交 guard，最后交作为
`source_invariant` 参数传入的 `source_node.zone`。因为
\(F_a=Z_n\cap g\)，后两次相交精确等价于限制到 `fire_zone`；代码无需
再交一次已保存的 \(F_a\)。

(10.15) 先再次将 target 交 \(Z_n\)，然后求 exact past domain 并交
\(Z_n\)，最后按第 4 节的 slope/facet 规则传播权重。把 \(Z_n\) 作为
delay invariant 是精确的：\(Z_n\) 是在 location invariant 内得到的 time-closed
凸 DBM。对 \(v,u=v+d\in Z_n\)，整个线段在 \(Z_n\) 中；反之，
从 \(v\in Z_n\) 合法延时到 \(u\in Inv(l_n)\) 仍属于 time-closed \(Z_n\)。

`entry_zone` 而不是 target node 的大 zone 必须用于 (10.13)：immediate
reset valuation 必须是本 arc 的实际像。`post_zone` 不在后向式中再做一次
不定价 `past`；target piece 已经给出从 entry valuation 开始、包含后续
target-location delay 的剩余值。

**几何等价。** 对 \(v\in Z_n\)，有 \(v\in Dom(MPre_a(\mathcal Z_m))\)
当且仅当存在 \(d\ge0\)，令 \(u=v+d\)，使得

\[
v+[0,d]\subseteq Z_n,\quad
u\in g,\quad
u[R]\in E_a\cap Dom(\mathcal Z_m). \tag{10.16}
\]

当 (10.16) 成立时，从 \(v\) 延时、执行 \(e\)、再跟随 target piece 是一条
真实 suffix；任意以 arc \(a\) 为第一条离散边的真实 suffix 又必满足
(10.16)。因此 predecessor sound 且 complete。

**权重等价。** 使用 \(W=-V\) 时，(10.13)--(10.15) 在 \(v\) 处表示

\[
W_a(v)=
\sup_{d\text{ satisfies }(10.16)}
\left(
W_m((v+d)[R])-c_e-p_{l_n}d
\right). \tag{10.17}
\]

这恰是“source delay cost + edge cost + target suffix cost”的相反数。第 2--4 节
已分别证明 rebase、inverse reset、edge subtraction 和 facet time predecessor
保持 (10.17)，故 arc predecessor 同时具有 soundness、completeness 和
optimality。

对 \(V=-\infty\) region，实现以零 rate/零 gradient/零 edge cost 复用同一顺序
只计算几何 predecessor；因为任意有限成本与 \(-\infty\) 相加仍为
\(-\infty\)，这一省略不改变值。新的无界 delay 只在有限 piece 的
`time_predecessor` 检测到时产生；其更早前驱保留 successor-region witness。

### 10.6 FIFO fixed point 与 node-local dominance

对每个 graph node \(n\)，令 \(V_n^{(k)}(v)\) 为从 \((l_n,v)\) 出发、在带域
graph 中最多经过 \(k\) 条离散 arc 到 Goal 的最小成本。初值为

\[
V_n^{(0)}(v)=
\begin{cases}
0,&l_n\in G,\ v\in Z_n,\\
+\infty,&\text{otherwise}.
\end{cases} \tag{10.18}
\]

并有 Bellman 迭代

\[
V_n^{(k+1)}=
\min\left(
V_n^{(k)},
\min_{a\in Out(n)} MPre_a(V_{target(a)}^{(k)})
\right). \tag{10.19}
\]

这里 `MPre` 在直接 cost 记号下理解为 (10.17) 的相反数。对离散
arc 数做归纳：(10.18) 正是零 arc suffix；任意非空 suffix 唯一分解为
“source delay + 第一条 arc + 余下 suffix”，由 10.5 节可得 (10.19)。
因此

\[
V_n=\inf_{k\ge0}V_n^{(k)}. \tag{10.20}
\]

`MixedPricedSolver.cpp` 是 (10.19) 的异步 label-correcting 求值：先把每个 Goal
seed 放入 FIFO；每个新接受的 label 作为 delta，恰好沿该 node 已记录的
`incoming_arcs` 各传播一次。在两类 waiting queue 穷尽且下界/终止前提
满足时，其上包络 \(W=\sup_k(-V^{(k)})\) 即 (10.20) 的相反数。

有限 piece 的支配只在相同 `ReachNodeId` 内判定。候选
\(C=(Z_C,W_C,a_C)\) 可被旧 piece \(D=(Z_D,W_D,a_D)\) 剪枝的实际充分
条件是

\[
Z_C\subseteq Z_D,\qquad
\forall v\in Z_C:\ W_C(v)\le W_D(v),\qquad
\neg(a_C\land\neg a_D). \tag{10.21}
\]

第二项由 Z3 QF_LRA 精确检查
\(Z_C\land(W_C>W_D)\) 不可满足；`UNKNOWN` 不剪枝。第三项是对
`attained` witness 的保守加强：它可能少剪一些严格更差的候选，但不会丢失
同值可达见证。

(10.21) 的安全性来自 10.5 节 predecessor 对 \(W\) 的单调性：函数复合、减
同一 edge cost 和对 delay 取 supremum 均保序。同 node 的新旧 label 将沿完全
相同的 incoming-arc 集合继续传播，所以丢弃 \(C\) 不改变更早节点的
上包络。不允许跨 node 剪枝：即使两个同 location node 在交叠估值上有
相同或支配值，它们的 incoming arcs 不同，在一个 node 上丢弃 label 会少向
该 node 的真实前驱传播。

无界 region 同样只在相同 node 内按纯几何 inclusion 剪枝。因为它们在全部
定义域上的值均为 \(V=-\infty\)，较大旧域精确支配较小新域。

### 10.7 \(V_{mixed}=V_{full}\) on the reachable domain

令 \(V_{full}=V_G\) 是在完整 \(\mathcal A_G\) 上不先做 reachable-space 裁剪而定义的
终端 Goal 剩余成本，\(V_{mixed}\) 是只允许带域 graph path 的剩余成本。
当 forward snapshot 完整时，对任意 \((l,v)\in Reach_G\)，有

\[
\boxed{V_{mixed}(l,v)=V_{full}(l,v)}. \tag{10.22}
\]

**证明。** mixed 允许的每条带域 path 都是 \(\mathcal A_G\) 运行，所以其候选
运行集是 full 候选集的子集，故
\(V_{mixed}\ge V_{full}\)。

反过来，因为 \((l,v)\) 可达，选一条从初始配置到它的真实前缀。对从
\((l,v)\) 出发的任意 full suffix，把它接在该前缀后，在到达 Goal 之前
遇到的所有配置仍属于 \(Reach_G\)。由 (10.8) 和 10.4 节，该 suffix 的
每一步都映射到一条保留 exact arc domains 的 graph path，且成本未改变。
因此 mixed 包含 full 的每个候选 suffix，得
\(V_{mixed}\le V_{full}\)。两个方向合并即 (10.22)。证明对只能由无限候选
序列趋近的 infimum 和 \(V=-\infty\) 同样成立，因为两边的具体有限
suffix 集合完全一致。

查询时，同一 \((l,v)\) 可被多个 node 覆盖。实现在所有这些 node 的
pieces 上取最大 \(W\)（即最小 \(V\)），相同 \(W\) 先选 `attained=true`，再用
PieceId 稳定破同。由 (10.22)，不同 node 在交叠估值上最终都表示同一
具体 suffix 最优值；取上包络仍是正确的，也能对中间未剪掉的冗余
labels 保持健壮。

### 10.8 几何支持定理

定义 mixed snapshot 的几何支持为所有有限 pieces 和 \(V=-\infty\) regions
的 location-wise 并：

\[
Support_{mixed}(l)=
\bigcup_{n:l_n=l}
\left(
\bigcup_{P\in Pieces(n)}Dom(P)
\cup
\bigcup_{B\in Unbounded(n)}B
\right). \tag{10.23}
\]

当 forward 和 backward 都完整时，

\[
\boxed{
Support_{mixed}(l)=Reach_G(l)\cap Pre_{\mathcal A_G}^{*}(G)(l)
}. \tag{10.24}
\]

**Soundness。** Goal seed 在 \(Reach_G\cap G\) 内。每次 (10.13)--(10.15) 一方面
把定义域限制在 source node \(Z_n\subseteq Reach_G\)，另一方面为每个保留点
构造一条到 successor piece 的真实步骤。因此 (10.23) 左边包含于右边。

**Completeness。** 任意 \(s\in Reach_G\cap Pre^*(G)\) 都有某条使用有限条离散边
的 goal-reaching suffix。按该 suffix 的离散边数归纳，Goal seed 给出基础步，
10.5 节的 complete predecessor 给出归纳步。已支配的 label 只被定义域更大且
值不差的同 node label 代替，不会丢失几何覆盖。故右边也包含于左边。

这一定理解释 API 的三种区分：

- 若 exact forward 中 \(v\notin Reach_G(l)\)，返回
  `OutsideReachableDomain + Unknown`，不把“前缀根本不可达”误写为 \(+\infty\)；
- 若 \(v\in Reach_G(l)\) 但 \(v\notin Pre^*(G)\)，完整后向快照精确返回
  \(V=+\infty\)；
- 若任一完整性前提不成立，除已有 exact \(-\infty\) certificate 覆盖的点外，
  查询返回 `Unknown`。

### 10.9 Strict boundary 和 `attained`

forward 阶段的 zero/intersection/assign/future 直接操作 strict DBM，所以
`fire_zone`、`entry_zone`、`post_zone` 和 node zone 都保留原真正可达域的
\(<\) / \(\le\) 差异。`relation()` 的 inclusion 也在这些 strict DBM 上判定。

backward 阶段只在计算线性目标的边界值时使用 topological closure facet；
输出定义域始终交回 `exact_past_domain`。对非平坦 delay objective，
`actual_facet_past` 进一步区分哪些 source valuations 真能到达 strict endpoint；
Federation 差集把一个几何 piece 拆成 attained/unattained 子域。因此：

- 最优端点属于真实 zone 且 successor 值已达到时，`attained=true`；
- 仅 closure endpoint 可达时，值仍是正确 infimum，但 `attained=false`；
- 当 \(p=\sum r_x\) 时 delay objective 平坦，可以选内部真实 delay，因此继承
  successor 的 `attained`；
- 无有限 upper facet 且目标沿 delay 严格下降时返回
  \(V=-\infty\) region，它不是一个“未达到的有限 infimum”。

priced intersection、inverse reset 和 edge subtraction 都传递 `attained`。查询在同值
pieces 中优先选择 `attained=true`；支配检查按 (10.21) 禁止用同值
unattained witness 覆盖 attained witness。

### 10.10 资源、终止和对外完整性边界

exact forward 没有使用 \(M/LU\) extrapolation。即使某个 TA 的抽象 region
graph 有限，exact DBM Post 序列仍可能产生无限多个互不包含的 zones。因此
forward 只在下列情况声明 `complete/exact`:

1. 初始 zero 与 invariant 的交为空，从而可达集精确为空；或
2. FIFO 自然穷尽，且最后一次超时检查未触发。

node limit 在创建新 node 前检查；arc limit 在已发现非空 Post、但尚未
创建 target node 和 arc 时检查，因而不会留下无入边的虚假 target。任一
node/arc/timeout 上限命中均得到
`incomplete_forward_resource_limit`。

`ReachabilitySnapshot` 保留生成它的只读 TA 结构副本。`solve_mixed`
首先逐项精确校验 dimension、initial location、location IDs/invariants，以及
EdgeId/endpoints/guards/resets/labels；DBM 必须集合相等。cost model 可以变更，因为
它不参与可达图构造。这个绑定阻止把由 guard (x\ge5) 的自动机生成的
graph 误用于同拓扑但 guard (x\ge1) 的另一自动机，从而伪造 `exact`
结果。结构校验通过后，求解器遵守
下列顺序：

1. forward 不 exact：不播种任何 Goal piece，直接返回
   `incomplete_forward_resource_limit`；
2. 存在负 rate/edge cost 且未声明 lower-bounded 契约：返回
   `assumption_required`；
3. 从 `SolverOptions.timeout_ms` 减去 forward snapshot 记录的 elapsed，剩余值才是
   backward 预算；
4. 只在 finite-piece 和 unbounded-region 两个 waiting queue 都穷尽，且最终
   deadline 复查未超时时，才设置 `exact=true`。

piece limit 对已接受有限 pieces 与已接受 unbounded regions 的和计数。
timeout 或 piece limit 命中得到 `incomplete_backward_resource_limit`；已存的
有限 label 只是当前上界，查询不得把它对外声称为最优值。已接受且
覆盖查询点的 \(V=-\infty\) region 是独立 certificate，可在其余 worklist 未穷尽
时仍精确返回。

本算法的后向终止条件与第 7 节相同：存在可达且 co-reachable 的无限
下降负环时，普通 finite-piece worklist 未必终止。
`--pta-assume-lower-bounded` 是用户提供的数学前提，不是实现已自动完成负环
证明。当工作队列完整穷尽后，snapshot 对全部 reachable valuations 是
exact；顶层 status 另按初始零估值区分有限 `complete`、`unreachable`
和 `unbounded_below`。

## 参考资料

- Rémi Parrot, Didier Lime. *Backward Symbolic Optimal Reachability in
  Weighted Timed Automata*. FORMATS 2020. DOI: 10.1007/978-3-030-57628-8_3.
- Patricia Bouyer, Thomas Brihaye, Nicolas Markey 等 priced-zone 工作，以及
  Bouyer–Colange–Markey 2016 的前向隐式抽象，只作为前向算法和 subsumption
  背景；本实现的 action/time predecessor 以 Parrot–Lime 2020 为准。
