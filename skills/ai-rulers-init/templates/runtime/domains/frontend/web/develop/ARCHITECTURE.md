# Web 架构规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - web architecture
    - route
    - page
    - component
    - module
    - boundary
    - Web 架构
    - 路由
    - 页面
    - 组件
    - 模块
    - 边界
  must_load_with:
    - {{RULERS_DIR}}/frontend/web/develop/INDEX.md
```

---

## 1. 边界

- 遵循已确认的路由、状态与组件职责；已授权的边界调整需验证受影响用户流程。
- 按目标项目约定分离页面编排、可复用组件、数据访问和局部 UI 行为。
- 当既有结构已经支持该变更时，不得虚构一套平行应用结构。

---

## 2. 变更纪律

- 优先扩展既有路由和组件模式，而不是创建一次性结构。
- 跨路由或共享组件变更必须识别下游消费者。
- 路由 metadata、布局、共享组件和平台服务沿用项目权威来源。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写真实 Web 目录、路由命名、布局约定、组件边界、模块命名和框架术语。将未知结构假设标记为需要确认。
