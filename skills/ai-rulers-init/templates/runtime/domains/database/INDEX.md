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
  must_load_with: []
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 表、集合、字段、索引、约束或关系设计 | [database/SCHEMA_DESIGN.md]({{RULERS_DIR}}/database/SCHEMA_DESIGN.md) |
| migration、回滚、兼容性或破坏性变更 | [database/MIGRATION.md]({{RULERS_DIR}}/database/MIGRATION.md) |
| 种子数据、引用数据、角色或权限绑定、backfill | [database/DATA_SEED.md]({{RULERS_DIR}}/database/DATA_SEED.md) |
| 数据库变更收尾、审阅或完成声明 | [database/REVIEW_CHECKLIST.md]({{RULERS_DIR}}/database/REVIEW_CHECKLIST.md) |
| 应用行为或持久化模型变更 | [backend/INDEX.md]({{RULERS_DIR}}/backend/INDEX.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将通用数据库路径、schema 位置、migration 工具术语、数据存储名称、审阅负责人和验证命令替换为目标项目事实。
