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
    - ../AGENTS.md
    - ../core/HARD_CONSTRAINTS.md
```

---

## 1. 必读文档

处理 schema、migration、索引、约束、seed 和 backfill 任务时，加载以下数据库规范：

- [SCHEMA_DESIGN.md](SCHEMA_DESIGN.md)
- [MIGRATION.md](MIGRATION.md)
- [REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md)

---

## 2. 条件加载

| 任务条件 | 还需加载 |
| --- | --- |
| 种子数据、引用数据、角色或权限绑定、backfill | [DATA_SEED.md](DATA_SEED.md) |
| 应用行为或持久化模型变更 | [../backend/INDEX.md](../backend/INDEX.md) |

---

## 3. 激活要求

数据库 schema、migration、seed 和 backfill 任务需要数据库领域达到 Level 2 或更高等级。

---

## 4. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用数据库路径、schema 位置、migration 工具术语、数据存储名称、审阅负责人和验证命令替换为目标项目事实。如果数据库事实未经观察或人工确认，则将数据库保持在 Level 0 或 Level 1，不授权 schema、migration、seed 或 backfill 变更。
