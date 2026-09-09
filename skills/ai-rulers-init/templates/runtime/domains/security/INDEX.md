# 安全领域路由

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - security
    - authentication
    - authorization
    - secrets
    - 安全
    - 认证
    - 授权
  must_load_with:
    - "{{RULERS_DIR}}/AGENTS.md"
    - "{{RULERS_DIR}}/RULERS_STATE.json"
```

| 任务条件 | 还需加载 |
| --- | --- |
| 登录、令牌、会话、身份验证 | `AUTHENTICATION.md` |
| 权限、角色、资源访问、租户隔离 | `AUTHORIZATION.md` |
| 密钥、凭据、环境配置、敏感日志 | `SECRETS.md` |

只有 `RULERS_STATE.json` 将 security 标为 reviewed/Level 2 时，才允许安全行为变更。
