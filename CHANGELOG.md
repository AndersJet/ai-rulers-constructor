# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
并采用 [语义化版本](https://semver.org/lang/zh-CN/) 进行版本号管理。

## [Unreleased]

### Changed

- 重组宣传素材至 `assets/promo/`，删除根目录 `logo.png`，README 与 README-zh 的 logo 引用改指向新海报素材
- README 目录锚点更新为带 emoji 的嵌套形式，修复跳转失效
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
