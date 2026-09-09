# App 设计规范索引

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
    - design-system/**
  trigger_keywords:
    - app design
    - mobile layout
    - touch interaction
    - safe area
    - accessibility
    - App 设计
    - 移动端布局
    - 触控交互
    - 安全区域
    - 无障碍
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/app/INDEX.md
    - {{RULERS_DIR}}/frontend/common/DESIGN_TOKENS.md
```

---

## 1. 条件加载

移动端布局、触控交互、安全区域、主题和无障碍工作先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| token、主题、颜色、间距、字体排版、平台 token 适配 | [{{RULERS_DIR}}/frontend/app/design/TOKENS.md]({{RULERS_DIR}}/frontend/app/design/TOKENS.md) |
| 视口、安全区域、布局、密度、溢出 | [{{RULERS_DIR}}/frontend/app/design/LAYOUT.md]({{RULERS_DIR}}/frontend/app/design/LAYOUT.md) |
| 组件、变体、复用、禁用/加载/错误状态 | [{{RULERS_DIR}}/frontend/app/design/COMPONENTS.md]({{RULERS_DIR}}/frontend/app/design/COMPONENTS.md) |
| 触控目标、反馈、手势、表单、导航流程 | [{{RULERS_DIR}}/frontend/app/design/INTERACTION.md]({{RULERS_DIR}}/frontend/app/design/INTERACTION.md) |
| 标签、焦点、屏幕阅读器、对比度、动效、触控目标无障碍 | [{{RULERS_DIR}}/frontend/app/design/ACCESSIBILITY.md]({{RULERS_DIR}}/frontend/app/design/ACCESSIBILITY.md) |

---

## 2. 范围

设计规则治理移动端 token 适配、布局、可复用组件、交互和无障碍。仅实施相关的关注点通过 [{{RULERS_DIR}}/frontend/app/develop/INDEX.md]({{RULERS_DIR}}/frontend/app/develop/INDEX.md) 路由。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写移动端设计来源、token 名称、安全区域约定、组件模式、交互标准、无障碍标准、设备类别和视觉 QA 流程。
