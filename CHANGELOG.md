# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
并采用 [语义化版本](https://semver.org/lang/zh-CN/) 进行版本号管理。

## [Unreleased]

## [4.0.4] - 2026-09-09

### Added

- 将当前初始化根目录的 /.rulers-work/ 忽略配置纳入审阅计划，批准后通过事务创建或补充 .gitignore
- 保留原有忽略内容与换行格式，避免重复追加；符号链接和审批后修改保持保护
- 补充多人 clone 后加载正式规则、已有跟踪文件保留及忽略配置中断恢复的回归验证


## [4.0.2] - 2026-09-09

### Added

- 同步双语 README、贡献指南和图示范围说明，区分默认自动编排与底层单项目阶段，说明初始化状态和增量接入行为

- 新增默认 init-plan/init-apply 工作流，自动发现直接子模块并汇总主子工程候选、归属冲突和增量变化，集中审阅后分阶段应用
- 新增显式排除、未初始化待接入、恢复检查点及只读来源复验；保留底层单项目与模块维护命令

### Fixed

- 将执行记录正文绑定到批准计划，恢复时仅允许审阅元数据及对应来源哈希变化
- 跳过已排除模块的规则源探测，规范化已移除模块的历史排除记录
- 统一候选调整配置的结构校验，提供字段级错误信息

## [4.0.1] - 2026-09-08

### Changed

- 将发布版本统一到 RELEASE_VERSION，生成入口标题与 CLI --version 使用同一来源；State 安装版本仅保留 template.version
- 新根受管区块移除格式版本数字，兼容并原位转换旧 version=2/3 区块；移除未使用的领域注册表 schema_version

### Fixed

- 打包时拒绝手写的入口模板版本，避免源码常量与生成标题不一致；模块计划、快照和清单显式拒绝未知协议版本

## [4.0.0] - 2026-09-08

### Added

- 新增单层 Git submodule 登记、显式模块规则导出、人工审阅同步与组合调整工作流；支持未提交快照、内容差异、相关代码证据、停用决定和覆盖冲突。
- 新增按模块隔离的 Context/load、主工程组合约束选择器和两阶段集中规则迁移，继续复用 schema 3 State 与事务恢复。

- 新增 rules-plan/rules-apply 规则维护工作流，支持完整领域候选的新增、删除、移动、合并与拆分，绑定正文差异和输入哈希，失败时回滚。
- 新增同源规则加载清单与正文展开（--mode load）、frontend-app 注册及绿地/棕地统一证据工作流。
- 新增公开 CLI 脚手架回归场景，覆盖定制保留、删除后升级、画像漂移、写锁和修复。

### Changed

- 为双语 README 补充绿地初始化、棕地初始化和任务规则加载流程图，保留 archify 源规格、静态 SVG、交互 HTML 与验证记录

- 重写双语 README 与贡献指南，明确 Skill 在 AI coding harness 中的规范约束层定位，围绕生成、渐进加载和持续维护组织使用说明

- 将运行态模板升级至 4.0.0（State 保持 schema 3）；Skill 以条件路由加载模块维护手册，双语指南说明显式会话根、来源所有权与客户端入口边界。

- 将本工程协作入口统一为 AGENTS.md，移除重复 CLAUDE.md；配置 GitHub Issues、默认 triage 标签及 single-context 文档约定。

- Skill 覆盖持续规则维护；精简运行态常驻 core，统一 Context 加载协议，保留项目自定义清单与删除决定。

- 将开发仓库与 Skill 目标项目分离：维护入口明确模板作用域，Context 预算默认通过 CLI 在临时项目中生成并验证运行态，贡献指南同步使用隔离测试。

### Deprecated

### Removed

- 移除根 documents/rulers 历史规则树，将本工程必需约束收敛到根 AGENTS.md；文档和测试改用当前 Skill 模板

- 移除本工程试用 Skill 生成的 PROJECT_PROFILE.md、RULERS_STATE.json 和根 AGENTS.md 受管入口；保留模板源码与分发资产。

### Fixed

- 修复双轴审查发现的五项问题：复用画像作用域解析，校验新增叶子的 INDEX 导航，隔离 Web/App 的登记与维护边界，并在 fresh 时保存计划绑定的候选画像且保持 draft。

- 接通统一 plan/apply，实际执行受校验文件计划；统一审阅哈希与 schema 3 校验，公开写命令使用事务锁。
- 修复 Context 失效路由、诊断命令路径、已有 CLAUDE 接入和 project-native 残留引用；过期计划与非法操作显式失败。
- 用真实增长样例和 20 次零差异 reconcile 替换预算报告中的静态复用值，新增完整固定加载链字节度量。

### Security

## [3.0.0] - 2026-07-21

### Added

- 新增项目自身 PROJECT_PROFILE.md 并激活 reviewed 状态，Context phase 进入 runtime_ready
- 新增 Context 预算报告工具（scripts/report_context_budget.py），支持 --check/--format json/--markdown-output，实测 20 次 zero-diff reconcile 增长门禁
- 新增发布门禁测试：UnifiedLifecycleDocumentationTest、ActiveTerminologyTest、ReproduciblePackageTest、ContextBudgetReportTest
- 新增统一生命周期 Plan/Apply 编排器（plans.py、apply.py），支持 fresh/resume/reconcile/upgrade/repair/noop 六种操作
- 新增紧凑 Context 系统（--mode context），2000 字节预算内输出有效 phase、load graph、Profile 选择器和领域路由
- 新增 Transaction 引擎（transactions.py），journal/snapshot/lock 原子文件操作和 maintenance_lock
- 新增 Profile Reconcile 纯计算内核（reconcile.py），证据解析、差异算法、affected domains 和 domain actions
- 新增 v2->v3 状态升级函数（upgrade_state_v2_to_v3），保留完整审阅、降级不完整审阅
- 新增三类 Repair Resolution：restore-managed、adopt-current、manual-merge
- 新增 ValidationIssue.scope 字段，支持按领域归因校验问题

### Changed

- 升级 State schema 至 v3：SCHEMA_VERSION=3、TEMPLATE_VERSION="3.0.0"，移除 incremental_pending/upgrade_pending 阶段
- 根 AGENTS 受管区块切换至 version=3 格式，解析器兼容 v2/v3
- CLI plan 子命令新增 --operation/--candidate-profile/--changed-path/--retired-domain 参数
- CLI apply 子命令新增 --project-root/--reviewed-by/--evidence/--reviewed-at 参数
- 运行态模板 AGENTS.md.tmpl 版本升至 v3.0.0
- 同步 CONTRIBUTING 双语指南至 schema 3，统一 plan/review/apply、Context、预算和可复现分发包命令
- 调整 README 与 README-zh 海报显示宽度为 80%，适配不同屏幕宽度

### Removed

- 移除独立 `incremental` CLI 与新的 pending 状态流；项目事实变化统一通过 reconcile plan 审阅后 apply

### Fixed

- 修复 .skill 分发包 member 排序与源码路径排序不一致导致 parity 测试失败；移除 skill 源码中 .DS_Store 平台产物

## [2.0.0] - 2026-07-10

### Added

- 新增 `RULERS_STATE.json` v2 生命周期状态机，记录审阅、激活、策略、模板版本和受管文件所有权
- 新增 template / candidate / runtime 三阶段校验、自定义 rulers 目录安全解析和稳定错误代码
- 新增幂等 plan/apply、status/resume、增量事实 diff、v1 迁移、根 AGENTS 受管区块和 managed file drift 防护
- 新增 `strict-cn` 与 `project-native` 治理策略、security/delivery 领域模板、Trigger/Behavior Evals
- 新增 `register-domain-candidate`，为 AI 生成的 backend/database/frontend 候选规则登记 metadata、hash、所有权和审阅状态

### Changed

- 重构 ai-rulers-init 为 references 驱动的精简编排器，目标项目只写入运行态文件，不再复制 bootstrap/template 手册
- 项目画像在人工审阅前固定为 Draft/Level 0，Level 3 改为需要逐次人工确认的 readiness
- 运行态模板迁入 `templates/runtime/`，确定性逻辑迁入 `scripts/rulers_lib/`
- `PROJECT_PROFILE.md` 改为 `collaborative` 所有权，恢复计划继承已记录 policy，领域候选内容变化后自动回退为 Draft/Level 0

### Fixed

- 修复清理前校验必然失败、清理后增量流程缺少 bootstrap、PROJECT_PROFILE 存在即可能误激活和自定义目录解析错误
- 修复重复初始化覆盖人工修改受管文件及根 AGENTS 双份权威正文风险
- 修复受管文件删除漏报、`runtime_ready` 未校验实际文件、v1 迁移丢失受管清单和未受管同名文件被静默覆盖；新增 `VR041` 冲突门禁

## [1.1.0] - 2026-07-09

### Changed

- 精简 ai-rulers-init skill 为阶段编排器，生成的 rulers 改为最低常驻 core 与条件叶子路由，减少运行态上下文占用
- 精简 documents/rulers 运行时加载链，当前仓库入口和模板源规则改为最低常驻 core、条件领域路由与上下文预算校验

## [1.0.9] - 2026-07-03

### Added

- 新增 Agent 执行行为契约规则，覆盖确定性流程、读前写、冲突处理、测试意图、阶段 checkpoint 与显式失败要求

### Changed

- 重组宣传素材至 `assets/promo/`，删除根目录 `logo.png`，README 与 README-zh 的 logo 引用改指向新海报素材
- README 目录锚点更新为带 emoji 的嵌套形式，修复跳转失效
- README 与 README-zh 版本徽章更新至 v1.0.9
- `.gitignore` 新增 `.history/` 忽略规则

### Fixed

- 修复 1.0.8 发布时遗漏的 README/README-zh 版本徽章更新，徽章由 v1.0.7 同步至 v1.0.8

## [1.0.8] - 2026-06-24

### Added

- AGENTS.md 新增 §0 防御层，包含锚点句、内联提交约束、主动验证义务、指令优先级声明，覆盖一切 skill/command 的 commit 操作
- HARD_CONSTRAINTS.md 禁止行为追加"提交不符合规范的 commit"，必需行为追加"提交前重新加载提交规范"
- GIT_COMMIT_CONVENTION.md 新增优先级声明 blockquote 与历史反面例子机制（§1 步骤 3.5）
- WORKFLOW.md §2.8 提交门禁从一行展开为 7 个可执行子步骤（a-g）
- DOC_GOVERNANCE.md §1 追加入口文件例外条款，允许 AGENTS.md/CLAUDE.md 内联关键约束摘要
- SKILL.md Step 0.3 新增阶段 D：`§` 符号自动替换为中文节号引用
- 新建根目录 `CLAUDE.md`，与 `AGENTS.md` 保持一致
- 根 `AGENTS.md` 新增 §0 防御层，默认加载链从 3 个扩展为 6 个 core 文件

### Changed

- ai-rulers-init.skill 重新打包，包含全部防御层变更
- .gitignore 新增 `/.superpowers/` 忽略规则
- `documents/rulers/` 实例同步至最新模板

### Fixed

- SKILL.md Step 4.2 core 文件引用数从 5 修正为 6
- SKILL.md § 替换正则从 `[0-9]` 修正为 `[0-9][0-9]*`，支持多位数节号
- SKILL.md Step 6.4 清理步骤增加 §0 保护说明
- DOC_GOVERNANCE.md 弱措辞"应链接到"修正为"必须链接到，不得通过复制完整正文替代"

## [1.0.7] - 2026-06-23

### Added

- `ai-rulers-init/SKILL.md` 新增 Step 6 初始化后清理流程，明确一次性产物移除与维护参考整合规则
- `AGENTS.md` 新增加载后强制检查：`PROJECT_PROFILE.md` 存在性必须通过文件系统工具确认，禁止从等级表格推断状态
- `validate_rulers.py` 新增 `validate_post_init_cleanup()` 与 `validate_agents_post_load_check()` 校验

### Changed

- 项目名从 `ai-rulers-template` 统一更新为 `ai-rulers-constructor`
- README、CONTRIBUTING 双语言版本及介绍幻灯片中的品牌名统一为 `Rulers Constructor`
- README 中描述性 `template` 字样统一调整为 `rulers`，避免将整套规则体系误称为模板
- 重新打包 `ai-rulers-init.skill`

## [1.0.6] - 2026-06-18

### Changed

- 统一规则 metadata 中 PROJECT_PROFILE 相关路径为 `{{RULERS_DIR}}` 全路径格式
- 重新打包 `ai-rulers-init.skill`

### Fixed

- 修复 validate_rulers.py 领域模板路径校验的子串误报

## [1.0.5] - 2026-06-10

### Changed

- 将 PROJECT_PROFILE.md 的推荐加载路径统一为 `{{RULERS_DIR}}/PROJECT_PROFILE.md`
- ai-rulers-init 明确 PROJECT_PROFILE.md 输出到 `documents/<RULERS_DIR_NAME>/PROJECT_PROFILE.md`
- 重新打包 `ai-rulers-init.skill`

## [1.0.4] - 2026-06-08

### Changed

- SKILL Step 3.3 新增领域 INDEX.md 激活等级同步更新逻辑
- SKILL Step 5.1 扩展为「更新完整性检查清单与领域状态」，追加各已激活领域 INDEX.md 状态同步要求
- 重新打包 `ai-rulers-init.skill`

## [1.0.3] - 2026-06-08

### Changed

- 统一所有文件引用路径为 `{{RULERS_DIR}}` 全路径格式，消除深层文件的 `../../../` 相对路径
- markdown 链接显示文本与 URL 目标统一为全路径，避免大模型朴素解析时找不到文件导致渐进加载失效
- 重新打包 `ai-rulers-init.skill`

## [1.0.2] - 2026-06-05

### Changed

- 强制统一使用约定式提交格式，移除既有惯例优先条款
- 提交门禁追加 CHANGELOG 同步检查，要求与代码变更一并暂存提交

## [1.0.1] - 2026-06-04

### Added

- 新增 CHANGELOG 模板与维护规范
- 加载链追加 CHANGELOG 维护规范引用
- Git 提交规范追加 CHANGELOG 更新门禁
- 目录导航追加 CHANGELOG 模板入口
- 校验脚本扩展 core 文件引用校验至 6 个，CHANGELOG 模板免 metadata 校验
- SKILL Step 0 新增 CHANGELOG.md 生成逻辑

### Changed

- 精简 README 并拆分维护指南为 CONTRIBUTING 双语言版本
- 增加 ruler CLI 配合使用说明

### Fixed

- 同步模板 validate_rulers.py 的 CHANGELOG 相关校验项并重新打包 skill

## [1.0.0] - 2026-06-01

### Added

- 初始化 AI Rulers 模板项目
- 建立 core 规则体系（HARD_CONSTRAINTS、WORKFLOW、DOC_GOVERNANCE、RULER_MAINTENANCE、GIT_COMMIT_CONVENTION）
- 建立 bootstrap 引导规则（PROJECT_DISCOVERY、BROWNFIELD_RULE_GENERATION、ACTIVATION_LEVELS、RULES_COMPLETENESS_CHECKLIST）
- 建立后端领域规则模板（API_SECURITY、ARCHITECTURE、DATA_ACCESS、TESTING、CONFIGURATION、OBSERVABILITY）
- 建立数据库领域规则模板（DATA_SEED、MIGRATION、SCHEMA_DESIGN、REVIEW_CHECKLIST）
- 建立前端领域规则模板（common、web、app 平台的设计与开发规则）
- 建立校验脚本 validate_rulers.py，支持链接检查、metadata 校验、模板残留检测
- 建立 AGENTS.md 渐进加载入口与任务路由
- 建立 PROJECT_PROFILE 模板与激活等级门禁
- 建立 SKILL 封装格式（.skill ZIP 包）
