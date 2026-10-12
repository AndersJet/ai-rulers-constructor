# Web 开发规范索引

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - web development
    - route
    - state
    - api integration
    - authorization
    - test
    - Web 开发
    - 路由
    - 状态
    - API 集成
    - 授权
    - 测试
  must_load_with:
    - {{RULERS_DIR}}/frontend/web/INDEX.md
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 路由、页面、组件边界、模块结构 | [develop/ARCHITECTURE.md]({{RULERS_DIR}}/frontend/web/develop/ARCHITECTURE.md) |
| API 客户端、请求响应、错误处理、契约 | [develop/API_INTEGRATION.md]({{RULERS_DIR}}/frontend/web/develop/API_INTEGRATION.md) |
| 权限、守卫、角色、访问控制用户体验 | [develop/AUTHORIZATION.md]({{RULERS_DIR}}/frontend/web/develop/AUTHORIZATION.md) |
| store、缓存、服务端数据、本地状态、失效 | [develop/STATE_MANAGEMENT.md]({{RULERS_DIR}}/frontend/web/develop/STATE_MANAGEMENT.md) |
| 行为变更、回归修复、质量门禁或浏览器验证 | [develop/TESTING.md]({{RULERS_DIR}}/frontend/web/develop/TESTING.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将 Web 路径、路由约定、框架名称、状态工具、API 契约来源、授权模型、命令和可运行验证流程替换为目标项目事实。
