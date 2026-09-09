# 生命周期与恢复

用户初始化默认从 initialization reference 的 init-plan/init-apply 进入；本文介绍底层单项目生命周期。

State schema 3。绿地、棕地使用同一状态和命令。发布版本通过 `python3 scripts/rulers_init.py --version` 查询；它与 State、计划、Context 等数据协议版本分别管理。

fresh → profile_draft → profile_reviewed → rules_candidate → runtime_ready。
日常规则变化走 rules-plan；事实变化走 reconcile；模板/策略变化走 upgrade；漂移走 repair。

## Plan / Apply

`plan --project-root ROOT` 输出摘要和不可变 plan_path；有事实输入时追加
`--operation reconcile --candidate-profile PATH [--changed-path PATH] [--retired-domain NAME]`。
fresh 也可用 `--candidate-profile PATH` 提供初始画像，apply 原样保存并保持 draft，随后审阅激活。
候选画像放在目标项目内、已安装画像之外。不要直接编辑已审阅画像后冒充未变化。
无变化返回 noop；候选内容、模板或目标文件变化后必须重新计划。

`apply --plan PATH` 执行 fresh/resume；reconcile/upgrade/repair 还需
`--reviewed-by NAME --evidence REF`。审阅对应具体变更，不构成未来操作永久授权。

## 升级与修复

模板或策略变化由 plan 检出 upgrade；明确策略切换时用 `--operation upgrade --policy ID`。
升级保留 collaborative/project-owned 内容和领域自定义清单。安装版本统一记录在 State 的 `template.version`；升级时移除旧 `template_version` 字段，旧根区块原位转换为无版本边界。旧画像不满足新契约时保持
文件内容，降为 draft，按当前画像结构补充后重新审阅；不制造审阅事实。

受管漂移先查 runtime 详情，再计划 repair 并用
`--resolution <项目相对文件路径>=restore-managed` 恢复框架模板，或
`--resolution <路径>=adopt-current` 采纳人工修订。不能确定的内容先人工合并再重新计划。
有未完成事务时 repair 恢复 journal/snapshot 后要求重新计划；活跃写入者不能被恢复。

## 日常 Context

运行目标目录 `scripts/validate_rulers.py --mode context --domain NAME`。
blocked、非零或非法 JSON 时只诊断/恢复；健康输出给出有效路由和画像选择范围。
需要更少跳转时用 `--mode load --domain NAME --rule PATH --format text` 获取同源正文。
