# Migration 规范

```yaml
metadata:
  applies_to:
    - db/**
    - database/**
    - migrations/**
    - schema/**
  trigger_keywords:
    - migration
    - migrate
    - rollback
    - compatibility
    - destructive
    - 迁移
    - 回滚
    - 兼容性
    - 破坏性变更
    - 数据库
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/database/INDEX.md
```

---

## 1. Migration 质量

- Migration 必须确定性且可审阅。
- Migration 的顺序、命名和所有权必须遵循目标项目既有约定。
- 除非明确批准并记录，否则生成的 migration 必须避免依赖环境的行为。

---

## 2. 安全与兼容性

- 破坏性变更需要明确的人工确认。
- 当新旧应用版本可能重叠运行时，必须评估向后兼容性。
- 对生产有影响的 migration，必须在适用时识别预期数据量、锁定行为、持续时间和运维风险。

---

## 3. 恢复

- 对生产有影响的 migration 必须记录回滚或恢复策略。
- 如果回滚不安全或不实际，必须记录前向修复步骤以及所需备份或还原点。
- 当应用行为受到影响时，migration 验证必须同时包含结构检查和应用行为检查。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的 migration 路径、命名约定、migration 工具术语、兼容性规则、备份或还原机制和验证命令。如果 migration 事实未经观察或人工确认，则保持生成规则的通用性，并要求在 migration 变更前进行审阅。
