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
  must_load_with: []
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 共享视觉基础、设计 token、跨平台 UI 一致性 | [common/INDEX.md]({{RULERS_DIR}}/frontend/common/INDEX.md) |
| 面向浏览器或桌面端的前端平台工作 | [web/INDEX.md]({{RULERS_DIR}}/frontend/web/INDEX.md) |
| 移动端或触控优先的前端平台工作 | [app/INDEX.md]({{RULERS_DIR}}/frontend/app/INDEX.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 将默认前端平台名称、路径、框架名称、包管理器、命令、设计来源、token 名称和约定替换为目标项目事实。除非这些事实已观察到或经人工确认，否则保持生成的规则技术栈中立。
