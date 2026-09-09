# 授权规则

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - authorization
    - permission
    - role
    - tenant
    - 授权
    - 权限
  must_load_with:
    - "{{RULERS_DIR}}/security/INDEX.md"
```

- 授权必须在受信边界执行，并以资源和动作作为判定输入。
- 默认拒绝未记录权限；不得把路由隐藏或客户端守卫当成最终授权。
- 多租户访问必须校验租户边界，禁止仅依赖用户提交的租户标识。
- 权限变更必须覆盖拒绝路径、越权路径和审计记录验证。
