# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
并采用 [语义化版本](https://semver.org/lang/zh-CN/) 进行版本号管理。

## [Unreleased]

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
