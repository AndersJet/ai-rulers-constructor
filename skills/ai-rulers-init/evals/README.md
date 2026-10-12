# 有限模型回放

evals.json 是 33 个场景定义，不是已运行成绩。前 18 项为生命周期/加载场景；19–22 为
规划、继续/分叉、重建/归档、访谈组合；23–27 为跨目录加载、条件核心、独立推进、研究停点和最小候选；28–33 为原始证据发现、业务边界、冲突/绿地、连续维护、工作流适配和文档交付。发布检查与模型证据边界见
[发布验证记录](../../../docs/validation/1.0.0.md)。评测定义和执行工具可以独立使用，
历史回放不自动成为当前版本的验证成绩。

从仓库根运行 `python3 scripts/prepare_interop_eval.py --help`：指定 baseline 或最终候选
解压 Skill、全局技能只读源、全新目标路径及目标外的 evidence 路径。夹具保留 Git、项目
workflow/tracker/domain 权威和公开 CLI 的 candidate/runtime/context/load/noop 记录。
synthetic-interop-fixture 审阅身份仅为测试，不代表人类批准。named 与 detached 两种约定
只写在项目正文，Profile 保存指针；夹具构造不证明 AI 发现/生成的语义正确性。

评分标准、根因分析、前次结论放在目标之外。受测者只看到自然任务、项目规则和技能；
baseline/candidate 使用相同输入与外部技能内容。保存输入 hash、源码及包身份、前后
Git/worktree/upstream、公开事件、最终文本、产物 hash和评分依据。报告模型 requested/resolved
身份；resolved 未公开时写 unknown，不从配置或默认值推断。技能 source hash 前后核验。

CLI 用 `python3 -m scripts.run_interop_replay --target ABS --prompt ABS --evidence NEW_ABS`
执行；它保留默认配置与 workspace-write 沙箱，不设置 bypass。执行失败及重试分目录保存，
评分检查事件和真实文件，不把 exit=0 当作行为通过。执行者需要本机正常认证和权限；失败
时记录实际原因，不能用关闭规则、绕过 hook 或伪造答案制造通过。

Desktop 采用无实施历史的新子代理执行，记录工具轨迹与宿主差异。由技能触发的研究可委派，
已受委派 worker直接调查；至少一个场景在 Desktop 验证。合成根无法绑定到 Desktop 的
managed-worktree工具时保留未覆盖项；shell detached 和CLI结果不能代表该工具通过。

固定历史回答须标明原会话与回答文件来源，只称回答后的步骤回放。未回答的 HITL 选择
保持待答，实时全流程须真实用户参与；代理不能扮演人类。有限样本只说明本次路径，
不推导长期质量、Token/成本优势或所有第三方技能的兼容性。

## 加载与完成边界对照

`scripts/prepare_loading_replay.py --skill ABS --target NEW_ABS --scenario fix|blocked-choice|research --evidence NEW_ABS`
通过公开初始化 CLI 生成有真实代码、项目规则与未决选择的隔离目标。fixture.json 和自然任务
保存在目标外；评分答案不注入代理。构造夹具不等于验证模型会自行发现/生成这些规则。

为基线、仅协议去重、完整候选分别准备全新目标；相同任务至少重复两次作为 smoke 回放，
需要因果或小幅收益结论时另作样本量设计和留出任务。固定模型、宿主版本、权限与 effort，
可用 `scripts.run_interop_replay --model MODEL --effort medium` 保存公开事件。
模型未公开解析身份时保持 unknown；执行失败、超时及重试分别保存。跨模型入口不可用时
标记未覆盖，不将另一模型替作该模型的成绩。

评分独立检查隐藏输入上的正确性、手续费待决状态、研究阶段是否改代码、无关文件是否保留、
是否未经授权提交，以及测试/加载的实际工具事件。分别记录执行次数、工具输出字节、usage
和耗时；总 token、计费金额、独立文件读取量不可互相替代。仅由路径清单推算的字节不是实际读取。

`scripts.report_context_budget --rule PATH` 可测叶子；显式模块目标可传 `--module` 和 workspace
选择器。模块目标不运行复制目录式增长实验，报告 skipped；其实际快照加载量仍被测量。
`--read-trace PATH` 接受脱敏公开轨迹整理的 `[{"path":"…","output_bytes":123}]`，累计输出字节
并列重复路径；未提供则为未测。`scripts.report_task_budgets` 检查七类模板正文任务的完整加载链，
包括分隔标记；这是结构预算，不是模型正确率。

## 原始证据与连续维护

`python3 -m scripts.prepare_rule_quality_replay --skill ABS --target NEW_ABS --scenario minimal|boundary|conflict|greenfield|maintenance --evidence NEW_ABS`
准备隔离输入。前四类没有预写 Profile 或规则答案；maintenance 的合成批准只建立遗留规则前态，
不代表模型完成真实审阅。模型先准备候选与差异，真实人类选择保持待答。

连续维护按同义请求、路由修正、范围变化、合并/移动、删除、升级分别保留前后证据；
语义评分区分退款与回执等不同作用域，不能仅凭短语出现或字数减少判断正确。新夹具的
公开 CLI 回归见 `tests.test_rule_quality`；模型成绩独立记录，夹具通过不等于发现生成有效。
