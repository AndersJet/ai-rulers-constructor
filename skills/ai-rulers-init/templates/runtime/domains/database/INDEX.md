# 数据库规范索引

```yaml
metadata:
  applies_to:
    - db/**
    - database/**
    - migrations/**
    - schema/**
  trigger_keywords:
    - database
    - schema
    - migration
    - seed
    - backfill
    - index
    - constraint
    - 数据库
    - 表结构
    - 迁移
    - 种子数据
    - 回填
    - 索引
    - 约束
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
```

---

## 1. 条件加载

处理 schema、migration、索引、约束、seed 和 backfill 任务时，先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| 表、集合、字段、索引、约束或关系设计 | [{{RULERS_DIR}}/database/SCHEMA_DESIGN.md]({{RULERS_DIR}}/database/SCHEMA_DESIGN.md) |
| migration、回滚、兼容性或破坏性变更 | [{{RULERS_DIR}}/database/MIGRATION.md]({{RULERS_DIR}}/database/MIGRATION.md) |
| 种子数据、引用数据、角色或权限绑定、backfill | [{{RULERS_DIR}}/database/DATA_SEED.md]({{RULERS_DIR}}/database/DATA_SEED.md) |
| 数据库变更收尾、审阅或完成声明 | [{{RULERS_DIR}}/database/REVIEW_CHECKLIST.md]({{RULERS_DIR}}/database/REVIEW_CHECKLIST.md) |
| 应用行为或持久化模型变更 | [{{RULERS_DIR}}/backend/INDEX.md]({{RULERS_DIR}}/backend/INDEX.md) |

---

## 2. 激活要求

数据库 schema、migration、seed 和 backfill 任务需要数据库领域达到 Level 2 或更高等级。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用数据库路径、schema 位置、migration 工具术语、数据存储名称、审阅负责人和验证命令替换为目标项目事实。如果数据库事实未经观察或人工确认，则将数据库保持在 Level 0 或 Level 1，不授权 schema、migration、seed 或 backfill 变更。
