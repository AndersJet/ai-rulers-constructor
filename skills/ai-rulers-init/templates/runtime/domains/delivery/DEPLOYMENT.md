# 部署规则

```yaml
metadata:
  applies_to:
    - "deploy/**"
    - "infrastructure/**"
  trigger_keywords:
    - deployment
    - environment promotion
    - infrastructure
    - 部署
    - 环境晋级
  must_load_with:
    - "{{RULERS_DIR}}/delivery/INDEX.md"
```

- 部署目标、环境顺序、审批人和部署后验证必须来自已审阅证据。
- 生产影响操作须有覆盖确切目标、动作与范围的用户授权；已有授权适用且输入未变时继续，范围变化时再确认。Level 3 readiness 不授予操作权限。
- 变更前说明影响范围、兼容性、回滚路径和观测信号。
- 部署后验证失败时停止晋级并执行已审阅的安全恢复路径。
