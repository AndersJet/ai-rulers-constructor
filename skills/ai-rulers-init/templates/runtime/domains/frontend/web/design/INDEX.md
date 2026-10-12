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
    - {{RULERS_DIR}}/frontend/web/INDEX.md
    - {{RULERS_DIR}}/frontend/common/DESIGN_TOKENS.md
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 视觉层级、布局、间距、响应式、主题 | [design/VISUAL_SYSTEM.md]({{RULERS_DIR}}/frontend/web/design/VISUAL_SYSTEM.md) |
| 组件、变体、复用模式、设计系统组件 | [design/COMPONENT_PATTERNS.md]({{RULERS_DIR}}/frontend/web/design/COMPONENT_PATTERNS.md) |
| 键盘、焦点、语义、标签、对比度、减少动态效果 | [design/ACCESSIBILITY.md]({{RULERS_DIR}}/frontend/web/design/ACCESSIBILITY.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写真实设计来源名称、组件库约定、token 名称、响应式断点、无障碍标准和视觉 QA 流程。
