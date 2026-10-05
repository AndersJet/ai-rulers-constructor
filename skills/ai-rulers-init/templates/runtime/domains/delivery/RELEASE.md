# 发布规则

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - release
    - version
    - artifact promotion
    - 发布
    - 版本
  must_load_with:
    - "{{RULERS_DIR}}/delivery/INDEX.md"
```

- 版本来源、变更记录机制、产物和审批流程必须来自项目事实。
- 发布前确认必需质量门禁、兼容性说明、迁移步骤和回滚可用性。
- 发布产物必须可复现、可追溯，并与源码和验证证据关联。
- Level 3 readiness 仅表示明确覆盖声明及关联规则审阅有效；发布仍需核对本次版本的门禁、环境与授权。没有覆盖声明时报告未评估，不从等级数字推断已准备。
