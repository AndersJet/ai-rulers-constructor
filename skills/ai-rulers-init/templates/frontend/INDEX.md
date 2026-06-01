# 前端规范索引

```yaml
metadata:
  applies_to:
    - frontend/**
    - client/**
    - ui/**
  trigger_keywords:
    - frontend
    - client
    - ui
    - web
    - app
    - design
    - 前端
    - 客户端
    - 界面
    - 页面
    - 组件
    - 设计
  must_load_with:
    - ../AGENTS.md
    - ../core/HARD_CONSTRAINTS.md
```

---

## 1. 平台路由

将此索引用于客户端应用工作。默认平台名称 `web` 和 `app` 是常见目标形态的占位符；生成的项目可在 bootstrap 期间删除、重命名或裁剪它们。

| 任务条件 | 还需加载 |
| --- | --- |
| 共享视觉基础、设计 token、跨平台 UI 一致性 | [common/INDEX.md](common/INDEX.md) |
| 面向浏览器或桌面端的前端平台工作 | [web/INDEX.md](web/INDEX.md) |
| 移动端或触控优先的前端平台工作 | [app/INDEX.md](app/INDEX.md) |

---

## 2. 激活说明

- 仅加载与目标项目匹配的平台规则。
- 如果项目只有一个前端平台，将其映射到最接近的模板平台，或在生成期间移除未使用的平台目录。
- 跨平台 UI 变更必须先检查共享设计基础，再修改平台专属规则。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将默认前端平台名称、路径、框架名称、包管理器、命令、设计来源、token 名称和约定替换为目标项目事实。除非这些事实已观察到或经人工确认，否则保持生成的规则技术栈中立。
