# 密钥与敏感配置

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - secrets
    - credentials
    - sensitive configuration
    - 密钥
    - 凭据
  must_load_with:
    - "{{RULERS_DIR}}/security/INDEX.md"
```

- 不得把密钥、令牌、密码、私钥或生产标识符写入代码、规则、日志或测试夹具。
- 配置来源、轮换、撤销和本地开发替代方案必须记录在项目画像。
- 错误和日志只记录安全定位所需的最小上下文，并对敏感值脱敏。
- 新增凭据依赖时必须说明所有者、存储机制、轮换方式和验证步骤。
