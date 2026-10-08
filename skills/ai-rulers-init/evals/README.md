# 有限模型回放

evals.json 是 22 个场景定义，不是已运行成绩。前 18 项为生命周期/加载场景；19–22 为
规划、继续/分叉、重建/归档、访谈组合。历史四类观察见
[旧验证记录](../../../docs/plans/2026-10-06-ai-rulers-init-validation.md)，本轮证据见
[互操作验证记录](../../../docs/plans/2026-10-08-skill-interop-validation.md)。

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
