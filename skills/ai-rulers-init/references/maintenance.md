# 项目规则维护

适用于新增、修改、删除、移动、合并和拆分规则。先确认本次失败案例、项目变化或用户
偏好需要哪种调整；不因一次模型疏漏直接增加全局禁令。
规则变化统一走 rules-plan/rules-apply；同一不可变差异与明确范围的一次批准可覆盖采纳、校验和目标单域激活。

规划、研究或访谈技能组合的约定变化时，先读 [skill-interop.md](skill-interop.md)，核对是否
实际改变已绑定画像或规则。仅补 ticket、术语或候选讨论且无有效约束差异时，在所属文档完成，
无需启动规则维护；有差异时按本流程展示并采纳受影响范围。

## 归属与粒度

- 全局入口仅放加载协议；领域 INDEX 放任务条件与导航；叶子规则放专题约束。
- 项目事实进入 Profile；领域正文不重复保存事实快照。
- core 两份最小安全/加载协议由框架升级维护；提交策略是可选策略；领域专题可裁剪。
- 每条新增要求应说明适用任务、证据或原因、验证方式；通用重复提醒优先合并或删除。

## 完整候选目录

将目标领域复制到项目中位于 rulers 之外的候选目录，例如 `.rule-drafts/backend`。
在候选目录中完成所有修改，并同步 INDEX 和 must_load_with。候选是该领域期望保留的
完整 Markdown 文件集；缺少的文件表示删除，移动表现为删除旧路径并新增新路径。
可只保留 INDEX 和实际需要的叶子，不必保留 registry 推荐的全部文件。

```bash
python3 scripts/rulers_init.py rules-plan --project-root <PROJECT_ROOT> \
  --domain backend --candidate-dir .rule-drafts/backend \
  --reason "缓存故障复盘；合并重复验证要求" --output .rule-plans/change.json
```

需在同一批准内完成目标域激活时，规划阶段追加 `--activate-on-apply`。计划列明完整
候选差异、实际依赖、受影响域和唯一激活范围；执行时不能追加激活选项或扩大范围。
无该选项的旧调用仍只采纳候选并保留 draft，不自动激活。

检查 added/deleted/modified、activation_scope、affected_domains；展示实际正文 diff。
存在 supersedes 时，一并展示旧待激活记录及替换恢复依据的影响；批准新计划才可替换，
不自动激活或回滚旧计划已采纳的内容。语义审阅检查：

1. 是否覆盖实际问题，位置与触发条件是否正确？
2. 是否重复、矛盾或无证据扩大约束？
3. 删除是否移除了必要的安全/业务不变量，有无替代保障？
4. 链接、依赖、验证命令和典型任务加载是否仍正确？
5. 对常驻与任务上下文成本有什么影响？

已有用户授权满足变更范围时继续，否则针对具体差异请求必要审阅。

```bash
python3 scripts/rulers_init.py rules-apply --plan <PLAN_JSON> \
  --reviewed-by <REVIEWER> --evidence <REVIEW_EVIDENCE>
```

脚本核对 Skill、State、候选、依赖及可选准备来源的身份，原子采纳正文、检查链接并更新
受管清单及 removed_files。正文变化使目标和实际受影响的依赖方回到 draft，保留项目的
目标目录、加载依赖和已批准删除。校验只阻塞全局问题、本域及真实加载依赖；无关领域
问题仍保留在完整 runtime 诊断中，不把它当成本次健康范围采纳失败。

`--activate-on-apply` 计划分两段事务：第一段采纳与校验，失败恢复旧内容和状态；第二段
只激活计划中的目标域。第二段失败保留第一段已批准内容和待激活记录；用同一计划及
原 reviewer/evidence 重跑，只继续第二段。候选、来源、有效依赖、Skill 或非本计划的
State 输出变化时须重新计划。无正文差异但目标仍 draft 的显式激活计划也可以执行。
没有激活选项时，确认最终内容后另行 activate-domain；完整 runtime 用于报告全部问题。

State 的单条 maintenance_execution 保存当前或最近计划的原批准、阶段及输出身份，
last_operation 仅用于诊断。成功重复调用不改文件、审阅时间或再次写入批准。中断仅在
同计划 journal、原批准和实际输出都能核对时恢复；活跃写入者、其他事务和无法证明的
变更保持阻塞，使用 lifecycle 的明确恢复路径，不清理未知内容。
恢复按原计划保存的前态推导每一段应产生的内容；不得手改 State 或其自报摘要使旧批准重新生效。

模板升级保留 project_owned 文件；deleted 记录阻止默认文件重新出现。
新增未登记叶子可由 register-domain-candidate 采纳；删除既有文件应走此差异流程，
避免把意外丢失误认为批准删除。新增叶子必须通过领域 INDEX 链导航到达，登记、采纳和激活时检查。
父领域只比较和写入自身规则，已注册的嵌套领域子树保持独立。候选可以省略子树，或保留
与安装内容完全一致的副本；修改了其他领域的子树时应单独为那个领域创建维护计划。

## 可选生产规则准备声明

已有需要时，在项目内独立 JSON 文件声明 security、quality、rollback 三个非空路径列表，
路径使用项目相对的已采纳规则坐标。允许自定义路径及同一文件覆盖多项；语义充分性由
用户审阅。来源不得提供 ready、reviewer 或其他字段，也不得引用越界、符号链接或未采纳内容。

```bash
python3 scripts/rulers_init.py rules-plan --project-root <PROJECT_ROOT> \
  --domain delivery --candidate-dir .rule-drafts/delivery \
  --reason "补充已批准生产规则覆盖" --activate-on-apply \
  --readiness-source .rule-readiness/delivery.json --output .rule-plans/readiness.json
```

`--readiness-source` 必须同时选择激活，来源路径、哈希和脚本编译的覆盖绑定进入同一
计划。只更新准备声明、正文和实际依赖未变且目标已有有效 Level 2 时，保留原正文审阅
与依赖方状态；在同一 review 中记录本次准备范围的实际批准来源，不冒充新的正文审阅。
准备更新失败不撤销原普通规则可信度。不提供声明只形成 Level 2。
规则准备状态只证明生产相关规则和流程已审阅，不证明具体版本或环境可发布，也不授予生产操作权限。

## 持续优化

比较代表性任务的正确率、漏载、误放行、无必要确认和上下文成本。能力较弱的模型可
使用 validator `--mode load --domain NAME --rule PATH --format text` 获取相同规则的展开
正文，减少跳转；不降低安全标准，也不复制第二套规则。没有行为评测数据时明确标记。
