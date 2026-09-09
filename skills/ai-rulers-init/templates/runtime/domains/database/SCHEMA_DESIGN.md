# Schema 设计规范

```yaml
metadata:
  applies_to:
    - db/**
    - database/**
    - migrations/**
    - schema/**
  trigger_keywords:
    - schema
    - table
    - collection
    - index
    - constraint
    - foreign key
    - 表
    - 集合
    - 索引
    - 约束
    - 外键
    - 表结构
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/database/INDEX.md
```

---

## 1. 设计理由

- 每个表、集合、索引、唯一约束和外键都必须有记录的访问或完整性理由。
- 未记录所有权、刷新行为和一致性预期时，不得新增反规范化、派生或重复数据。
- 当存在目标项目约定时，命名、类型选择和关系模式必须遵循这些约定。

---

## 2. 语义与兼容性

- 可空性和默认值必须保留既有数据语义。
- Schema 变更必须识别读取路径、写入路径和 migration 影响。
- 约束变更必须在实施前识别受影响的既有数据和应用行为。

---

## 3. 审阅输入

- 对新增或变更的结构，必须在相关时识别预期基数、访问频率、保留策略和所有权。
- 当应用持久化行为发生变化时，schema 变更必须与后端数据访问规范协同。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的 schema 路径、命名约定、存储引擎术语、关系约定、审阅负责人和验证命令。如果 schema 事实未经观察或人工确认，则保持生成规则的通用性，并要求在 schema 变更前进行审阅。
