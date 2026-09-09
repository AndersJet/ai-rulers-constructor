# 回滚与恢复

```yaml
metadata:
  applies_to:
    - "deploy/**"
    - "infrastructure/**"
  trigger_keywords:
    - rollback
    - recovery
    - restore
    - 回滚
    - 恢复
  must_load_with:
    - "{{RULERS_DIR}}/delivery/INDEX.md"
```

- 回滚触发条件、负责人、命令、数据兼容性和验证信号必须明确记录。
- 回滚不得假设数据库、消息或外部集成可以无损逆转。
- 破坏性恢复、数据恢复和生产回滚必须针对确切操作获得人工确认。
- Level 3 readiness 要求回滚流程已审阅并具备可执行验证证据。
