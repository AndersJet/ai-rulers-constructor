# Seed 与 Backfill 规范

```yaml
metadata:
  applies_to:
    - db/**
    - database/**
    - migrations/**
    - schema/**
  trigger_keywords:
    - seed
    - backfill
    - reference data
    - permission
    - role
    - feature flag
    - 种子数据
    - 回填
    - 引用数据
    - 权限
    - 角色
    - 功能开关
    - 数据变更
  must_load_with:
    - ../AGENTS.md
    - ../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 幂等性

- Seed 和 backfill 操作必须具备幂等性。
- 重新运行 seed 或 backfill 不得重复数据、破坏所有权，或重置人工管理的值，除非获得明确批准。
- 在操作被视为安全前，必须理解部分失败行为。

---

## 2. 所有权与语义

- 权限、角色、菜单、功能开关和引用数据 seed 必须记录所有权。
- 当系统所有、租户所有、用户可编辑、环境特定或外部管理等区分存在时，seed 数据必须识别其归属类别。
- 对 seed 访问控制或功能启用状态的变更，需要针对安全和运维影响进行审阅。

---

## 3. 大规模数据变更

- 大规模数据变更必须识别分批、重试和恢复行为。
- Backfill 必须在适用时识别读取路径、写入路径、顺序、一致性预期，以及监控或进度信号。
- 长时间运行或运维敏感的数据变更，在执行前需要明确的人工确认。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的 seed 路径、所有权术语、数据类别、分批约定、重试或恢复机制和验证命令。如果 seed 或 backfill 事实未经观察或人工确认，则保持生成规则的通用性，并要求在数据变更前进行审阅。
