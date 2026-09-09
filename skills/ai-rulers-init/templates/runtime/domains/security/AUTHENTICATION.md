# 认证规则

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - authentication
    - login
    - session
    - token
    - 认证
    - 登录
  must_load_with:
    - "{{RULERS_DIR}}/security/INDEX.md"
```

- 认证机制、令牌来源、过期策略和撤销流程必须来自项目画像证据。
- 在服务端或可信边界强制验证身份，不依赖客户端状态作为授权证据。
- 失败响应不得泄露账户存在性、令牌内容或内部认证实现。
- 修改认证行为前定义兼容性、回滚和安全验证命令。
- 缺少认证事实或审阅证据时保持 Level 0。
