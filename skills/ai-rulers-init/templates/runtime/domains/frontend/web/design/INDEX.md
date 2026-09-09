# Web 设计规范索引

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
    - design-system/**
  trigger_keywords:
    - web design
    - visual system
    - component pattern
    - accessibility
    - responsive
    - theme
    - Web 设计
    - 视觉系统
    - 组件模式
    - 无障碍
    - 响应式
    - 主题
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/web/INDEX.md
    - {{RULERS_DIR}}/frontend/common/DESIGN_TOKENS.md
```

---

## 1. 条件加载

Web 页面、组件、布局、响应式行为、主题和无障碍工作先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| 视觉层级、布局、间距、响应式、主题 | [{{RULERS_DIR}}/frontend/web/design/VISUAL_SYSTEM.md]({{RULERS_DIR}}/frontend/web/design/VISUAL_SYSTEM.md) |
| 组件、变体、复用模式、设计系统组件 | [{{RULERS_DIR}}/frontend/web/design/COMPONENT_PATTERNS.md]({{RULERS_DIR}}/frontend/web/design/COMPONENT_PATTERNS.md) |
| 键盘、焦点、语义、标签、对比度、减少动态效果 | [{{RULERS_DIR}}/frontend/web/design/ACCESSIBILITY.md]({{RULERS_DIR}}/frontend/web/design/ACCESSIBILITY.md) |

---

## 2. 范围

设计规则治理视觉层级、可复用组件模式和无障碍。仅实施相关的关注点通过 [{{RULERS_DIR}}/frontend/web/develop/INDEX.md]({{RULERS_DIR}}/frontend/web/develop/INDEX.md) 路由。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写真实设计来源名称、组件库约定、token 名称、响应式断点、无障碍标准和视觉 QA 流程。
