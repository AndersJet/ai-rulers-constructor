# 数据访问规范

```yaml
metadata:
  applies_to:
    - backend/**
    - server/**
    - services/**
  trigger_keywords:
    - persistence
    - repository
    - data
    - query
    - mapping
    - transaction
    - 持久化
    - 仓储
    - 数据
    - 查询
    - 映射
    - 事务
    - 数据访问
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/backend/INDEX.md
```

---

## 1. 持久化边界

- 必须将数据访问逻辑保持在项目既有的持久化边界之后。
- 当存在既有仓储、网关、数据映射器、事务和工作单元约定时，必须复用这些约定。
- 除非目标项目已经将持久化专有结构视为契约类型，否则不得将其泄露到公共契约中。

---

## 2. 查询与行为安全

- 避免在缺少测试或审阅的情况下修改会改变基数、唯一性或锁定行为的查询。
- 查询变更必须在相关时识别预期结果规模、排序、过滤、一致性和失败行为。
- 影响事务、并发、隔离或重试行为的变更需要明确审阅和验证。

---

## 3. 数据库协同

- 未记录访问模式时，不得新增索引、约束或反规范化字段。
- 持久化模型变更必须与数据库规范协同。
- 处理 schema、migration、seed、backfill、索引或约束工作时，加载 [{{RULERS_DIR}}/database/INDEX.md]({{RULERS_DIR}}/database/INDEX.md)。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的持久化路径、仓储术语、事务约定、查询工具、数据映射规则和验证命令。如果数据访问事实未经观察或人工确认，则保持生成规则的通用性，并要求在影响生产数据行为的变更前进行审阅。
