# Tool 项目深度分析报告：MightyPPL 与 MoniTAal

生成时间：2026-07-04 23:14 CST  
工作目录：`/home/lqq/project/TAFuzz`  
分析目的：为后续实现 `TAMonitor` 自动化运行时验证流程准备工程级上下文。  

本报告只基于当前仓库中的源码、README、测试和 benchmark 材料整理。没有运行新的源码构建、语义测试或论文实验复现；未验证的内容不会写成已验证结论。

## 1. 项目总览与当前工作树事实

### 1.1 工作区结构

当前 TAFuzz 工作区不是顶层 Git 仓库管理的普通单仓结构；`tool/` 下有两个独立工具项目：

- `tool/MightyPPL`
  - MITPPL/MITL 公式到 timed automata 的转换器。
  - 当前构建目标是 `mitppl`。
  - 主要依赖 ANTLR4 C++ runtime、BuDDy BDD、MoniTAal、PARDIBAAL。
- `tool/MoniTAal`
  - Timed Buchi automata 的 runtime monitoring 库和 CLI。
  - 核心库目标是 `MoniTAal`。
  - 可选构建 `MoniTAal-bin`、benchmark、tests。

本次检查时两个嵌套仓库状态为干净：

```bash
git -C tool/MightyPPL status --short
git -C tool/MoniTAal status --short
```

两条命令均无输出。旧交接文件中记录的 `/home/lqq/download/TAFuzz` 路径和若干本地修改状态是上一工作区快照的历史状态；当前线程以 `/home/lqq/project/TAFuzz` 为准。

### 1.2 现有分析产物

`analysis/` 中已有：

- `analysis/mightyppl_monitaal_paper_code_report.html`
- `analysis/scripts/generate_paper_code_report.py`
- `analysis/data/*.json`

这些更偏论文-代码映射和静态 HTML 展示。本报告补充的是面向改代码的 Markdown 工程分析，重点关注入口、接口、数据结构、串联风险和 TAMonitor 切入点。

## 2. MightyPPL 深度分析

### 2.1 真实构建入口

MightyPPL 当前真实构建入口在 `tool/MightyPPL/CMakeLists.txt`：

- `antlr_target(MitlGrammar Mitl.g4 VISITOR ...)` 生成 MITL 语法相关 C++ 文件。
- `add_subdirectory(${EXTERNAL_INSTALL_LOCATION}/buddy buddy)` 构建 BuDDy。
- `ExternalProject_add(monitaal SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../MoniTAal ...)` 使用相邻的 MoniTAal 工作树。
- `add_executable(mitppl main.cpp ... MightyPPL.cpp ... modality files ... ${ANTLR_MitlGrammar_CXX_OUTPUTS})` 生成 CLI。
- `target_link_libraries(mitppl antlr4_static buddy MoniTAal pugixml pardibaal)` 链接关键后端。

因此后续改 TAMonitor 时不要误以为 `MightyPPL` 是纯命令行脚本；它已经深度链接 MoniTAal 的 C++ TA/DBM/Fixpoint 能力。

### 2.2 不应误改的历史/实验副本

`tool/MightyPPL` 下存在多个大文件：

- `MightyPPL_new_4.cpp`
- `MightyPPL_new_5.cpp`
- `MightyPPL_new_6.cpp`
- `MightyPPL_new_7.cpp`
- `MightyPPL_new_food.cpp`
- `MightyPPL_new_lamp.cpp`
- `MightyPPL_new_original.cpp`

这些文件体量接近或超过当前 `MightyPPL.cpp`，但没有进入当前 `add_executable(mitppl ...)` 的编译列表。它们更像历史快照、实验模型或论文 benchmark 临时版本。后续实现应以这些文件作为参考材料，而不是默认改造入口。

当前真实核心是：

- `tool/MightyPPL/main.cpp`
- `tool/MightyPPL/MightyPPL.cpp`
- `tool/MightyPPL/MightyPPL.h`
- `tool/MightyPPL/TAwithBDDEdges.{h,cpp}`
- `tool/MightyPPL/Mitl.g4`
- `tool/MightyPPL/Mitl*Visitor.{h,cpp}`
- `tool/MightyPPL/Finally.cpp`、`Until.cpp`、`PnueliFn.cpp` 等 modality 构造文件

### 2.3 CLI 行为与模式

`tool/MightyPPL/main.cpp` 当前 CLI 形态：

```text
mitppl <in_spec_file> --{fin|inf} [out_file --{tck|xml} [--{noflatten|compflatten}]] [--debug] [--noback]
```

关键语义：

- `--fin`：有限 timed word，可达接受位置即可。
- `--inf`：无限 timed word，使用 Buchi 接受/fixpoint。
- 不传 `out_file --xml/--tck`：
  - 构造 flatten 后的产品 TA。
  - 直接调用 MoniTAal `Fixpoint` 做可满足性检查。
  - finite 用 `Fixpoint<symbolic_state_t>::reach(accept_states(pos), pos)`。
  - infinite 用 `Fixpoint<symbolic_state_t>::buchi_accept_fixpoint(pos)`。
- 传 `out_file --xml/--tck`：
  - 输出 UPPAAL XML 或 TChecker 风格文件。
  - 根据 `--noflatten` / `--compflatten` / 默认 flatten 决定输出结构。
  - 同时生成用于外部可满足性检查的提示命令或 query 文件。

对 TAMonitor 的启示：

- “可满足性检查”已经有现成入口，不能重新发明语义。
- 但当前入口是 CLI + 全局状态 + stdout 输出，后续最好拆出库级 API，返回结构化结果。
- 如果先用子进程跑 `mitppl`，可以快速验证流程；科研级长期实现应改为直接调用 C++ API。

### 2.4 MITL/MITPPL 语法入口

语法定义在 `tool/MightyPPL/Mitl.g4`，支持：

- 布尔连接：`!`、`&&`、`||`、`<->`、`->`
- future：`F`、`G`、`U`、`R`
- past：`O`、`H`、`S`、`T`
- Pnueli modalities：`Fn`、`On`、`Gn`、`Hn`
- counting-style modalities：`CFn`、`COn`、`CGn`、`CHn`
- starred weak semantics：`F*`、`U*` 等
- interval：`[l,u]`、`(l,u]`、`[l,u)`、`(l,u)`，其中上界可为 `infty`
- proposition identifier：小写字母开头的 `Idfr`

README 明确说明 MightyPPL 默认使用 strict semantics；weak semantics 通过 starred modalities 表示。后续 TAMonitor 的公式输入必须忠于这套语法和语义，不能为了兼容 MoniTAal benchmark 随意换写公式含义。

### 2.5 公式预处理与 visitor 流程

`build_ta_from_main` 位于 `tool/MightyPPL/MightyPPL.cpp`，是公式到 TA 的主流程。核心步骤：

1. 打印/读取原始 parse tree。
2. `MitlTypingVisitor` 做类型检查和语义约束检查。
3. `MitlCheckNNFVisitor` 检查是否已经 NNF。
4. `MitlToNNFVisitor` 转换成 NNF。
5. 重新 parse NNF。
6. `MitlAtomNumberingVisitor` 编号 atomic propositions 与 temporal atoms。
7. `MitlCollectTemporalVisitor` 收集 temporal subformula。
8. 计算 interval 常数 GCD，用于 time divergence TA 和部分缩放。
9. `bdd_setvarnum(num_all_props + 1)` 初始化 BDD 变量数量。
10. `MitlGetBDDVisitor` 为公式和子公式生成 BDD 标签。
11. 生成 `TA_0`、`TA_div`、每个 temporal tester/component TA、模型 `M`。
12. 根据 flatten/compflatten/noflatten 模式输出或同步积。

对后续代码改造的重点：

- visitor 链是理论语义的主干，不能绕开或替换成简单字符串解析。
- `num_all_props`、`props_to_keep`、`temporal_components` 等全局状态必须在每次 TAMonitor 调用前后重置。
- 需要保留 NNF、编号、BDD 生成、TA 构造的顺序，否则容易破坏论文定义。

### 2.6 BDD 标签与 TAwithBDDEdges

MightyPPL 用 `tool/MightyPPL/TAwithBDDEdges.{h,cpp}` 扩展 MoniTAal 的 `TA`：

- `bdd_edge_t` 继承 `monitaal::edge_t`，但额外保存 `bdd_label_t`。
- `TAwithBDDEdges` 维护按 location 索引的 `_forward_bdd_edges` 与 `_backward_bdd_edges`。
- `intersection(const std::vector<TAwithBDDEdges>&)` 在 BDD 标签可满足时同步边，并合并 clocks、guards、resets。
- `projection(const std::set<int>& props_to_remove)` 把 BDD 边标签 existential projection 后转成普通 `monitaal::TA` 的字符串 label。
- `projection_bdd(...)` 保留 BDD 形式，只投影 BDD 变量。
- `time_divergence_ta(...)` 构造时间发散约束 TA。

这是 TAMonitor 的核心交界点：

- 如果采用“投影成 MoniTAal 可识别命题”的路线，应明确 BDD valuation 到 MoniTAal `label_t` 的编码。
- 如果保留 BDD 标签，为未来 BDD runtime monitor 做准备，应把 `TAwithBDDEdges` 作为新 monitor 接口的一等输入，而不是经由 MoniTAal 当前 `edge_t::label()`。

### 2.7 flatten / compflatten / noflatten 的工程含义

当前模式含义：

- 默认 flatten：
  - 构造所有 component automata 的同步积。
  - 对 BDD 标签投影后返回一个普通 `monitaal::TA`。
  - 无输出文件时用于内置可满足性检查。
- `--compflatten`：
  - 每个 temporal subformula 尽量压成一个 tester TA。
  - 仍保留组合结构，输出用于外部后端。
- `--noflatten`：
  - 更细粒度地输出 individual tester/component TAs。

代码中 `comp_flatten` 会影响 Pnueli/counting modalities 生成几个 automata、是否生成 `seq_in` / `seq_out` 辅助 automata，以及输出文件的 `turn` 同步逻辑。

风险点：

- 当前 flatten 路径和导出路径不是同一套完全独立的数据结构；部分导出逻辑与 `out_format`、`out_flatten` 全局变量交织。
- 后续 TAMonitor 若需要 both flatten 与 compflatten，都应先抽象出 `BuildMode` 和结构化产物，而不是继续从 stdout 或文件反推。
- `TAwithBDDEdges::intersection` 中有 TODO/Assert 提到 MoniTAal 某 commit 引入的 clock off-by-one 调整，这属于必须保留并验证的兼容风险。

### 2.8 MightyPPL 当前模型 M

`build_ta_from_main` 末尾硬编码模型 `M`：

- 一个 accepting location `s0`
- 一个 `true` 自环

README 也说明模型检查中的模型 `M` 当前可以通过编辑生成的 XML/TCK 或硬编码在 `MightyPPL.cpp` 中指定。

对 TAMonitor 的影响：

- 原始用户目标是运行时验证给定路径是否满足公式，不一定需要模型检查中的系统模型 `M`。
- 现有 MightyPPL 可满足性检查把 `formula && TA_div && M` 作为产品的一部分。
- TAMonitor 若把 trace/path 作为在线输入，需要明确 `M` 是否继续作为 trivial model，只用于保持原构造一致，还是拆成“公式 automaton + trace monitor”。
- 不能为了工程便利删除 `TA_div` 或 `M`，除非有严格数学理由说明 runtime verification 语义下它们的替代物。

### 2.9 MightyPPL 主要工程风险

1. 全局状态污染
   - `main.cpp` 和 `MightyPPL.cpp` 依赖 `spec_file`、`out_file`、`out_format`、`out_flatten`、`comp_flatten`、`out_fin`、`debug`、`back`、`gcd`、`num_all_props`、`props_to_keep`、`sat_paths`、`temporal_components`、`varphi`、`div`、`model` 等全局变量。
   - 一次进程只跑一个公式时问题较少；TAMonitor 若在同一进程批量处理多个公式，必须做上下文封装或严格 reset。

2. BuDDy BDD 生命周期
   - 当前 CLI 在 `main.cpp` 中 `bdd_init(1000, 100)`，结束时 `bdd_done()`。
   - 库化后需要明确 BDD manager 生命周期，不能在 nested call 中重复 init/done 导致未定义行为。

3. stdout 不是稳定接口
   - 当前很多阶段用 `std::cout` 打印结构信息。
   - TAMonitor 的科研级结果不能靠解析这些文本判定 SAT/UNSAT 或 automaton 统计，应使用结构化返回值。

4. 导出 XML 不等于 MoniTAal 可解析语义
   - MightyPPL 的 XML 输出偏 UPPAAL flat system，其中状态常用 `int loc` 变量编码。
   - MoniTAal Parser 读取的是显式 location/edge/synchronisation 子集，不解释整数状态变量的赋值语义。
   - 直接把 MightyPPL XML 交给 MoniTAal Parser 会有严重语义丢失风险。

5. BDD projection 结果不是天然的事件命题
   - `projection()` 当前把 BDD allsat pattern 拼成字符串 label。
   - MoniTAal Monitor 当前用字符串相等判断 `edge.label() == input.label`。
   - timed word 中的 proposition set 如何编码成与 edge label 相同的字符串，需要专门定义。

## 3. MoniTAal 深度分析

### 3.1 构建结构

`tool/MoniTAal/CMakeLists.txt` 提供可选构建：

- `MONITAAL_BUILD_BIN`
- `MONITAAL_BUILD_TEST`
- `MONITAAL_BUILD_BENCH`
- `MONITAAL_BUILD_ALL`
- `MONITAAL_BUILD_BUNDLE`

核心库在 `tool/MoniTAal/src/monitaal/CMakeLists.txt`：

- `add_library(MoniTAal ...)`
- 源文件包括 `TA.cpp`、`Parser.cpp`、`state.cpp`、`symbolic_state_base.cpp`、`Fixpoint.cpp`、`Monitor.cpp`、`EventParser.cpp`
- 链接 `pardibaal` 和 `pugixml`

CLI 在 `tool/MoniTAal/src/monitaal-bin/main.cpp`，benchmark 在 `tool/MoniTAal/benchmark/main.cpp`。

### 3.2 核心 TA 数据结构

`tool/MoniTAal/src/monitaal/TA.{h,cpp}` 定义：

- `location_t`
  - `accept`
  - `id`
  - `name`
  - `invariant`
- `edge_t`
  - `from`
  - `to`
  - `guard`
  - `reset`
  - `label`
- `TA`
  - clocks
  - locations
  - forward/backward edge maps
  - initial location
  - labels alphabet
  - inactive clocks

重要操作：

- `TA::intersection(const TA& other)`
  - 同步相同 label。
  - 对不在另一 automaton alphabet 中的 label 添加异步 loop 风格组合。
  - 使用双位置编码处理 Buchi 接受。
- `TA::time_divergence_ta(...)`
  - 根据 alphabet 生成时间发散 automaton。
- `TA::compute_inactive_clocks()`
  - 支持 monitor 的 clock abstraction。

对 TAMonitor 的接口意义：

- 如果要直接复用 MoniTAal Monitor，最终必须给它普通 `monitaal::TA`，其中每条边的 `label_t` 能与输入 trace event label 精确匹配。
- 如果要用 BDD 标签，需要新增或改造当前 `TA`/`Monitor` 数据结构，不能只靠 Parser。

### 3.3 Parser 的输入能力与限制

`tool/MoniTAal/src/monitaal/Parser.cpp` 解析 UPPAAL 风格 XML 的一个 template：

- `Parser::parse_file(path, template_name)`
- `Parser::parse_data(xml_string, template_name)`
- location id 形如 `id0`，通过 `parse_loc_id(input + 2)` 解析。
- accepting location 依赖 location name 以 `_a` 结尾。
- clocks 不是从全局 declaration 完整预读，而是在解析 constraints/reset 时动态发现。
- transition label 从 `kind="synchronisation"` 的 label 读取，并去掉末尾 `!` 或 `?`。
- guard/invariant 支持简单 whitespace-tokenized clock constraints。
- reset 只取 clock reset，假设赋值为 0。

关键限制：

- 不解析 UPPAAL integer variables 的状态语义。
- 不解释 `loc = ...` 这类 assignment 对 automaton location 的影响。
- 不解析 MightyPPL flat XML 中使用 `int loc` 模拟多 location 的语义。
- 不直接解析 MITL/MITPPL 公式。

因此，MightyPPL 生成的 XML 不能直接作为 MoniTAal runtime monitoring 的可靠交换格式。更稳妥的路线是：

1. 在 C++ 内存中直接把 MightyPPL 的 `TAwithBDDEdges`/`TA` 产物交给监控器。
2. 或新增一个 MoniTAal dialect exporter，把 MightyPPL automaton 写成显式 locations、显式 edges、显式 synchronisation labels 的 XML。

### 3.4 EventParser 与 timed word 输入

`tool/MoniTAal/src/monitaal/EventParser.cpp` 解析输入格式：

- concrete：`@0 a`
- interval：`@[0,10] a`
- 每个事件必须以 `@` 开头。
- observation 读取为一个字符串 label，到换行、空格、tab、下一个 `@` 为止。
- 空 observation 也可能被解析为 `label == ""`。

对 TAMonitor 路径文件的影响：

- 如果路径文件中一个时刻有多个命题同时为真，MoniTAal 当前格式没有原生 set-of-propositions 结构。
- 必须定义 canonical label，例如 `a&b`、`{a,b}`、bitstring、或多个同时间事件。
- 若采用 BDD-aware runtime，应把每个 event 解析成 proposition valuation，而不是普通字符串 label。

### 3.5 Fixpoint 可达性算法

`tool/MoniTAal/src/monitaal/Fixpoint.cpp` 提供：

- `reach(states, T)`
  - 从给定 states 做 backward reachability。
  - 对每条 incoming edge 执行 backward transition、限制 source invariant。
  - 用 inclusion 跳过已覆盖状态。
- `accept_states(T)`
  - 为每个 accepting location 构造 unconstrained state。
- `buchi_accept_fixpoint(T)`
  - 先求接受状态可回达空间。
  - 反复只保留 accepting locations，再做 reach，直到 fixpoint。

MightyPPL 的可满足性检查已经直接调用这些函数。TAMonitor 后续如果要输出“公式是否可满足”，应复用同一算法路径，避免用 runtime trace verdict 替代 satisfiability。

### 3.6 Monitor 三值判定

`tool/MoniTAal/src/monitaal/Monitor.{h,cpp}` 定义：

- `single_monitor_answer_e`
  - `ACTIVE`
  - `OUT`
- `monitor_answer_e`
  - `INCONCLUSIVE`
  - `POSITIVE`
  - `NEGATIVE`
- `Single_monitor<state_t>`
  - 维护一个 automaton 的当前 state estimate。
  - 初始化时计算 `_accepting_space = Fixpoint<...>::buchi_accept_fixpoint(automaton)`。
  - 每个 input 上执行 delay、guard/invariant、edge transition、accepting space intersection。
  - 若 next states 为空，则 status 变成 `OUT`。
- `Monitor<state_t>`
  - 同时维护 positive automaton 和 negative automaton。
  - positive OUT -> overall `NEGATIVE`
  - negative OUT -> overall `POSITIVE`
  - 两者都 ACTIVE -> `INCONCLUSIVE`

这与用户目标中的“三值判定”天然接近：

- `POSITIVE`：当前前缀所有无限扩展满足公式。
- `NEGATIVE`：当前前缀所有无限扩展违反公式。
- `INCONCLUSIVE`：当前前缀尚无法确定。

但要注意论文级映射：

- MoniTAal 论文中可能讨论四值或 out-of-model 类别。
- 当前 public API 只有三值，内部 `OUT` 是单 automaton 层状态。
- TAMonitor 报告结果时必须说明采用 MoniTAal 当前 public API 三值，还是扩展出论文四值/附加 out-of-model 标记。

### 3.7 状态与 DBM/Federation

`tool/MoniTAal/src/monitaal/state.{h,cpp}` 与 `symbolic_state_base.{h,cpp}` 封装 PARDIBAAL：

- `symbolic_state_t`
  - interval timed input 的 zone/federation state。
- `concrete_state_t`
  - concrete timestamp valuation。
- `delay_state_t`
  - latency/jitter 相关扩展。
- `testing_state_t`
  - input/output latency/jitter、测试模式扩展。
- `symbolic_state_map_t`
  - location -> state/federation 的 map。

`symbolic_state_base::do_transition` 和 `do_transition_backward` 是核心 zone 变换：

- forward transition：
  - 检查 from location。
  - 检查 guard。
  - restrict guard。
  - reset clocks。
  - 更新 location。
- backward transition：
  - 从 target 回到 source。
  - past/down、restrict reset to zero、free reset、restrict guard、down。

对 TAMonitor 的工程要求：

- 不要绕开 `Monitor` 自己实现 clock update。
- 任何新 BDD-aware Monitor 都应复用这些 state transition 操作，只替换 label matching 逻辑。

### 3.8 CLI 与文件监控

`tool/MoniTAal/src/monitaal-bin/main.cpp` 当前 CLI：

- `--pos <template> <xml>`
- `--neg <template> <xml>`
- `--type concrete|interval`
- `--input <path>`
- `--inclusion`
- `--clock-abstraction`
- `--verbose`
- `--print-dot`
- `--div <labels...>`

CLI 读取 XML 中 positive/negative automata，构造 `Interval_monitor` 或 `Concrete_monitor`，然后从文件或交互输入 timed word。

后续 TAMonitor 不建议 shell 调用 `MoniTAal-bin` 作为长期架构，因为：

- 结果只有文本输出。
- 不返回每一步结构化 verdict。
- 无法直接消费 MightyPPL 内存 automata。
- 无法处理 BDD valuation。

但它适合作为早期 sanity check 和对照测试。

### 3.9 benchmark 与测试资源

MoniTAal 可用验证材料：

- `tool/MoniTAal/test/Monitor_test.cpp`
- `tool/MoniTAal/test/DelayTest.cpp`
- `tool/MoniTAal/test/EventParserTest.cpp`
- `tool/MoniTAal/test/Presentation_examples.cpp`
- `tool/MoniTAal/test/models/*.xml`
- `tool/MoniTAal/test/models/*input.txt`
- `tool/MoniTAal/benchmark/main.cpp`
- `tool/MoniTAal/benchmark/gear-control-properties.xml`
- `tool/MoniTAal/benchmark/gear-control-input.txt`
- `tool/MoniTAal/benchmark/b_live_a_freq.h`
- `tool/MoniTAal/benchmark/gear_controller_*.h`

这些材料适合 TAMonitor 后续 benchmark 准备：

- 先用 MoniTAal 原生 XML + input 确认 monitor verdict 序列可复现。
- 再尝试从 XML/template 反推或人工标注对应 MITL 公式。
- 不应自动声称 XML 已成功转换为 MITL，除非建立可检验的反向映射规则。

## 4. 两项目串联可行性分析

### 4.1 可行的理论链路

用户目标的理想链路可以拆成：

```text
MITL/MITPPL formula
  -> MightyPPL parse/type/NNF/BDD
  -> tester/component TAwithBDDEdges
  -> flatten or compflatten product/collection
  -> satisfiability check
  -> runtime monitor over timed word prefix
  -> per-step verdict + final verdict + Excel/visualization
```

理论上可行，因为：

- MightyPPL 已能从公式构造 timed automata，并已复用 MoniTAal Fixpoint。
- MoniTAal 已能对 positive/negative timed Buchi automata 做在线三值监控。
- 两者已经在 C++ 层共享 `monitaal::TA`、`Fixpoint`、PARDIBAAL zone 表示。

真正难点不在“能否链接”，而在“标签语义和 automaton 接口是否一致”。

### 4.2 最大接口错位：BDD labels vs string labels

MightyPPL 的边标签是 BDD：

- 表示 formula atoms / temporal atoms / propositions 的 Boolean 约束。
- 一条边可能接受许多 proposition valuations。

MoniTAal 当前边标签是字符串：

- `edge_t::label()` 是 `std::string`。
- `Single_monitor::input` 只在 `edge.label() == input.label` 时尝试 transition。

因此，TAMonitor 必须在两条路线中选一条：

#### 路线 A：BDD 投影成 MoniTAal 可识别命题

需要完成：

- 定义 timed word 中 proposition set 的规范编码。
- 将 BDD edge label 按实际 atomic propositions 投影。
- 把每个可满足 valuation 枚举/压缩成 MoniTAal label。
- 将 path event 转成同一 label。
- 保证同一时刻多个命题的组合不会被错误拆成多个独立事件。

风险：

- valuation 枚举可能指数爆炸。
- 当前 `projection()` 生成的是 BDD pattern 字符串，不是现成的 MoniTAal proposition set label。
- 如果用多个同时间事件模拟 proposition set，MoniTAal 的 transition semantics 会变化。

适合 v1 目标：

- 先支持小 alphabet benchmark。
- 明确 label 编码，例如 bitstring `p1=1,p2=0,...` 或 canonical set `{a,b}`。
- 把每个 BDD edge 展开为若干普通 MoniTAal edges。

#### 路线 B：先不投影，保留 BDD-aware runtime 接口

需要完成：

- 定义 `BDDTimedInput`，输入是 time + proposition valuation。
- 新增 `BDDMonitor` 或 label predicate 层。
- transition 时用 `bdd_restrict`/`bdd_satcount`/BDD evaluation 判断 edge label 是否接受当前 valuation。
- 复用 MoniTAal state transition、zone、Fixpoint 算法。

风险：

- 改动比路线 A 深，会触及 Monitor 模板和 TA representation。
- 需要谨慎设计 BDD manager 生命周期。
- 需要 positive/negative automata 的 BDD 构造和补公式构造都严格对应。

适合长期论文级实现：

- 避免 BDD 展开爆炸。
- 更忠于 MightyPPL 的符号标签结构。
- 可作为 TAMonitor 的创新点之一。

### 4.3 第二个接口错位：MightyPPL XML vs MoniTAal XML

不要直接把 MightyPPL 当前 XML 输出交给 MoniTAal Parser 当作完整语义输入。原因：

- MightyPPL XML 常用单 UPPAAL location `id0` + integer variable `loc` 编码 automaton state。
- transition guard 中有 `loc == ...`，assignment 中有 `loc = ...`。
- MoniTAal Parser 不解释 integer `loc` 变量。
- MoniTAal Parser 主要依赖 XML 中显式 `<location>`、`<transition>` 和 `synchronisation` label。

可行替代：

1. 内存直连：MightyPPL 构造完 `monitaal::TA` 或 `TAwithBDDEdges` 后直接传给 TAMonitor。
2. 新增 exporter：把 automaton 写成 MoniTAal Parser 真正能读的 XML dialect。
3. 扩展 Parser：让 MoniTAal Parser 支持 MightyPPL flat XML 的 int-state 编码。这个复杂且容易引入语义错误，不建议作为 v1。

### 4.4 positive/negative automata 问题

MoniTAal Monitor 构造需要：

- positive automaton：接受公式语言。
- negative automaton：接受公式否定语言。

MightyPPL 当前 CLI 对一个输入公式构造对应 automaton。TAMonitor 后续需要明确：

- 对 `phi` 调一次 MightyPPL 得到 positive。
- 对 `!(phi)` 或 NNF-negated formula 调一次 MightyPPL 得到 negative。
- 两次构造必须共享同一 proposition ordering / label encoding，或在 wrapper 层建立一致映射。

这是三值 runtime verdict 的必要条件。只拿一个 automaton 不能完整复用 MoniTAal `Monitor<state_t>` 的三值语义。

## 5. TAMonitor 改造建议

### 5.1 推荐 v1 架构

建议先实现一个最小但真实的 v1：

```text
TAMonitor CLI
  -> parse config/options
  -> read formula
  -> build positive automaton through MightyPPL API
  -> build negative automaton through MightyPPL API
  -> run satisfiability check on formula
  -> parse timed word/path
  -> feed events into MoniTAal monitor
  -> collect per-step verdicts
  -> write CSV/Markdown/Excel summary under test/TARV
```

为了尽快跑通，同时避免伪实现：

- v1 可以先实现路线 A：BDD 展开/投影为普通 labels。
- 路线 B 预留接口，但明确返回 `NOT_IMPLEMENTED`，不假装支持。
- 所有无法保证数学语义的转换必须显式失败，而不是默默 fallback。

### 5.2 推荐新增接口边界

MightyPPL 侧应新增库级接口，而不是把 `main.cpp` 的逻辑继续扩大：

- `TAMonitorBuildOptions`
  - `word_kind`: finite / infinite
  - `build_mode`: flatten / compflatten
  - `label_mode`: projected / bdd
  - `debug`
  - `backward_pruning`
- `TAMonitorBuildResult`
  - `positive_ta`
  - `negative_ta`
  - `positive_bdd_ta` 可选
  - `negative_bdd_ta` 可选
  - `proposition_map`
  - `satisfiable`
  - `construction_stats`
  - `warnings`

MoniTAal/TAMonitor 侧应新增运行结果：

- `TimedObservation`
  - `time` 或 `interval`
  - `propositions`
  - `raw_label`
  - `canonical_label`
- `StepVerdict`
  - `step_index`
  - `time`
  - `input`
  - `verdict`
  - `positive_state_count`
  - `negative_state_count`
- `TAMonitorResult`
  - `formula_satisfiable`
  - `per_step`
  - `final_verdict`
  - `output_files`

### 5.3 推荐文件切入点

MightyPPL：

- 从 `tool/MightyPPL/main.cpp` 抽出 CLI 参数解析和 I/O，保留 CLI 兼容。
- 在 `tool/MightyPPL/MightyPPL.cpp` 附近新增可重入构造接口，或新增 `TAMonitorMightyAdapter.{h,cpp}`。
- 在 `tool/MightyPPL/TAwithBDDEdges.{h,cpp}` 附近新增 BDD label projection/export helper。
- 避免改动 `MightyPPL_new_*`。

MoniTAal：

- 先不改核心库时，可在 TAMonitor wrapper 中使用 `Monitor<symbolic_state_t>` / `Monitor<concrete_state_t>`。
- 如果路线 B，要在新文件中实现 BDD-aware monitor，复用 `symbolic_state_base::do_transition`，不要复制 DBM 算法。
- `Parser.cpp` 不建议先扩展为 MightyPPL XML parser，优先内存直连或 exporter。

TAFuzz 顶层：

- 用户原目标中提到在 `src` 下新建 `TAMonitor`。当前顶层未见稳定 `src` 结构，后续执行前应先确认顶层构建系统。
- 输出目录建议固定为 `test/TARV`，并提供可配置 output path。

### 5.4 benchmark 准备建议

阶段化 benchmark：

1. 基础正确性
   - 用简单公式，如 `F[0,10] a`、`G[0,5] !b`、`a U[1,3] b`。
   - 手工给定 timed word，确认每步三值判定。

2. MightyPPL 自带 formula
   - 使用 `tool/MightyPPL/testcases/MightyL/*.mitl`。
   - 先跑可满足性检查，记录 SAT/UNSAT 与构造统计。

3. MoniTAal 原生 benchmark
   - 使用 `tool/MoniTAal/test/models/*.xml` 和 `benchmark/*`。
   - 先保持 XML 原生 monitor 结果作为 baseline。
   - 再人工或半自动建立 MITL 公式映射。

4. 论文级实验
   - 输出 `test/TARV` 下 CSV/Excel/Markdown。
   - 记录命令、机器信息、构建 hash、输入公式、路径、模式、耗时、state counts。

必须避免：

- 只为了 benchmark 结果“好看”而跳过 negative automaton。
- 只根据最终 verdict 验证，不验证 per-step verdict。
- 把 MoniTAal XML 反推公式的人工假设当成自动转换成功。

## 6. 工程风险清单

### 6.1 高风险

- BDD 标签到 MoniTAal 字符串 label 的语义不一致。
- MightyPPL XML 输出与 MoniTAal Parser 输入子集不兼容。
- Positive/negative automata 的 proposition ordering 不一致。
- MightyPPL 全局状态导致批量运行污染。
- `bdd_init` / `bdd_done` 生命周期错误。
- 无限词/有限词接受条件混用。
- 用户路径文件中的 proposition set 语义未定义。

### 6.2 中风险

- flatten 产品状态爆炸。
- compflatten 输出结构需要同步 `turn`，不适合直接 MoniTAal Parser。
- MoniTAal public 三值 verdict 与论文四值表述存在差异。
- Parser 对 XML constraints/reset 的支持较窄，格式稍变可能解析错误。
- `--noback`、backward pruning 与后续 runtime monitor 的状态空间保留关系需要验证。

### 6.3 低风险但应整理

- README 和交接文件路径仍可能残留旧 `/home/lqq/download/TAFuzz`。
- MightyPPL 历史副本文件容易让后续 agent 误入。
- 现有分析 HTML 与新 Markdown 的定位需要在交接文件中说明。

## 7. 验证建议

### 7.1 文档级验证

本报告落盘后应检查：

```bash
test -s analysis/tool_projects_deep_analysis.md
rg -n "MightyPPL|MoniTAal|TAMonitor|BDD|flatten|compflatten|Fixpoint|Monitor|风险" analysis/tool_projects_deep_analysis.md
git -C tool/MightyPPL status --short
git -C tool/MoniTAal status --short
```

### 7.2 后续实现前验证

在写 TAMonitor 代码前建议先跑：

```bash
tool/MightyPPL/build/mitppl tool/MightyPPL/testcases/MightyL/E-5-12.mitl --inf
```

并记录：

- 是否 SAT。
- fixpoint 用时。
- 构造 locations/clocks 数。

如果 build 目录不存在，应先从 `tool/MightyPPL/build` 重新构建，不要在顶层误跑 root git 或 root build。

### 7.3 后续实现验收标准

TAMonitor 最小完整实现应至少满足：

- 同一 CLI 能读取 formula 文件和 path 文件。
- 能选择 finite/infinite。
- 能选择 flatten/compflatten，若某模式尚不支持 runtime，明确失败。
- 在正式 runtime monitor 前输出 satisfiability。
- 对每一步 timed word 前缀输出三值 verdict。
- 输出最终 verdict。
- 输出 CSV/Excel/Markdown 到 `test/TARV`。
- 所有 verdict 来自真实 automata + MoniTAal/Fixpoint 算法，不允许硬编码测试答案。

## 8. 当前结论

两个项目串联成 TAMonitor 是可实现的，但不是简单“把 MightyPPL XML 扔给 MoniTAal CLI”。当前最稳妥路线是：

1. 从 MightyPPL 抽出结构化构造 API。
2. 对公式和否定公式分别构造 automata。
3. 明确定义 proposition valuation 到 runtime event 的 label/BDD 语义。
4. v1 先做小 alphabet 的 BDD 投影到普通 label，保证流程跑通和判定正确。
5. 预留 BDD-aware runtime monitor 接口，作为后续论文级创新和性能改进方向。

只要先解决标签语义、XML 不兼容、全局状态和 positive/negative 双 automata 这四个问题，TAMonitor 可以在现有代码基础上增量实现，而不需要推倒重写 MightyPPL 或 MoniTAal。
