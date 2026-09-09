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
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/web/INDEX.md
```

---

## 1. 条件加载

Web 前端实施任务先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| 路由、页面、组件边界、模块结构 | [{{RULERS_DIR}}/frontend/web/develop/ARCHITECTURE.md]({{RULERS_DIR}}/frontend/web/develop/ARCHITECTURE.md) |
| API 客户端、请求响应、错误处理、契约 | [{{RULERS_DIR}}/frontend/web/develop/API_INTEGRATION.md]({{RULERS_DIR}}/frontend/web/develop/API_INTEGRATION.md) |
| 权限、守卫、角色、访问控制用户体验 | [{{RULERS_DIR}}/frontend/web/develop/AUTHORIZATION.md]({{RULERS_DIR}}/frontend/web/develop/AUTHORIZATION.md) |
| store、缓存、服务端数据、本地状态、失效 | [{{RULERS_DIR}}/frontend/web/develop/STATE_MANAGEMENT.md]({{RULERS_DIR}}/frontend/web/develop/STATE_MANAGEMENT.md) |
| 行为变更、回归修复、质量门禁或浏览器验证 | [{{RULERS_DIR}}/frontend/web/develop/TESTING.md]({{RULERS_DIR}}/frontend/web/develop/TESTING.md) |

---

## 2. 范围

这些规则覆盖面向浏览器的前端平台的实施结构、客户端契约、授权用户体验、状态所有权和验证。视觉系统规则通过 [{{RULERS_DIR}}/frontend/web/design/INDEX.md]({{RULERS_DIR}}/frontend/web/design/INDEX.md) 路由。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将 Web 路径、路由约定、框架名称、状态工具、API 契约来源、授权模型、命令和可运行验证流程替换为目标项目事实。
