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
- 破坏性恢复、数据恢复和生产回滚须有针对确切操作的用户授权；授权范围或输入变化时重新确认。
- 准备声明明确引用已审阅的回滚规则和验证方式；Level 3 readiness 不证明某个版本或环境已完成回滚演练，实际执行结果需独立核对。
