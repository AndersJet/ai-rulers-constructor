# Rulers 模板导航

> **Version**: v1.0.0
> **Role**: 通用 rulers 模板导航

---

## 从这里开始

- 模板入口与激活门禁：[AGENTS.md](AGENTS.md)
- 项目事实 schema：[PROJECT_PROFILE.template.md](PROJECT_PROFILE.template.md)
- 棕地 discovery 指南：[bootstrap/PROJECT_DISCOVERY.md](bootstrap/PROJECT_DISCOVERY.md)

---

## 目录地图

```text
documents/rulers/
├── AGENTS.md
├── INDEX.md
├── PROJECT_PROFILE.template.md
├── core/
├── backend/
├── database/
├── frontend/
│   ├── common/
│   ├── web/
│   └── app/
├── bootstrap/
└── scripts/
```

---

## 领域入口

| 入口 | 用途 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 渐进加载入口、激活门禁与任务路由。 |
| [core/HARD_CONSTRAINTS.md](core/HARD_CONSTRAINTS.md) | 全局安全、测试、禁令与完成约束。 |
| [core/WORKFLOW.md](core/WORKFLOW.md) | 标准实施工作流与推理顺序。 |
| [core/DOC_GOVERNANCE.md](core/DOC_GOVERNANCE.md) | 维护 ruler 文档的治理规则。 |
| [core/RULER_MAINTENANCE.md](core/RULER_MAINTENANCE.md) | 修改规则与索引的决策树。 |
| [core/GIT_COMMIT_CONVENTION.md](core/GIT_COMMIT_CONVENTION.md) | Git 提交规范，中文 subject，英文 type。 |
| [backend/INDEX.md](backend/INDEX.md) | 后端领域路由与必需后端叶子规则。 |
| [database/INDEX.md](database/INDEX.md) | 数据库 schema、migration、seed 与持久化路由。 |
| [frontend/INDEX.md](frontend/INDEX.md) | 前端领域路由与共享前端规则。 |
| [frontend/common/INDEX.md](frontend/common/INDEX.md) | 共享前端设计 token、样式与无障碍规则。 |
| [frontend/web/INDEX.md](frontend/web/INDEX.md) | Web/管理端前端路由。 |
| [frontend/app/INDEX.md](frontend/app/INDEX.md) | 移动 app/H5 前端路由。 |
| [bootstrap/PROJECT_DISCOVERY.md](bootstrap/PROJECT_DISCOVERY.md) | 用于创建 `PROJECT_PROFILE.md` 的棕地 discovery 流程。 |
| [bootstrap/BROWNFIELD_RULE_GENERATION.md](bootstrap/BROWNFIELD_RULE_GENERATION.md) | 根据已观察事实生成项目专属规则的流程。 |
| [bootstrap/ACTIVATION_LEVELS.md](bootstrap/ACTIVATION_LEVELS.md) | 激活等级定义与晋级标准。 |
| [bootstrap/RULES_COMPLETENESS_CHECKLIST.md](bootstrap/RULES_COMPLETENESS_CHECKLIST.md) | 判断生成规则是否足够完整并可激活的检查清单。 |

---

## 模板采用路径

```text
复制 documents/rulers/ → 放入目标项目 documents/ → 确认目录名 → 替换占位符 → 创建 PROJECT_PROFILE.md → 生成领域规则 → 校验 → 按等级激活
```