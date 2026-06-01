# Web 前端规范索引

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
  trigger_keywords:
    - web
    - browser
    - route
    - page
    - component
    - responsive
    - 浏览器
    - 路由
    - 页面
    - 组件
    - 响应式
    - 前端
  must_load_with:
    - ../../AGENTS.md
    - ../../core/HARD_CONSTRAINTS.md
    - ../INDEX.md
```

---

## 1. 必需加载表

| 任务条件 | 还需加载 |
| --- | --- |
| Web 代码、路由、状态、API、授权、测试 | [develop/INDEX.md](develop/INDEX.md) |
| 页面、组件、布局、响应式行为、主题、无障碍 | [design/INDEX.md](design/INDEX.md) |

---

## 2. 平台说明

`web` 名称是默认占位符。生成期间，将其替换为目标项目实际的面向浏览器平台名称；如果不存在此类平台，则移除此索引。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写真实 Web 平台路径、路由约定、框架名称、包管理器命令、测试命令、浏览器验证方式、设计来源和命名约定。
