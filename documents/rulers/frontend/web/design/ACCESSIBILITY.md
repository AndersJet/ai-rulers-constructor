# Web 无障碍规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
    - design-system/**
  trigger_keywords:
    - accessibility
    - a11y
    - keyboard
    - focus
    - label
    - contrast
    - reduced motion
    - 无障碍
    - 键盘
    - 焦点
    - 标签
    - 对比度
    - 减少动态效果
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - ../../common/DESIGN_TOKENS.md
```

---

## 1. 交互访问

- 交互控件必须按目标项目标准支持键盘导航。
- 焦点状态必须可见，且不得在没有无障碍替代方案的情况下移除。
- 模态框、菜单、标签页和复合交互必须保留预期的焦点移动和退出行为。

---

## 2. 语义和标签

- 控件、表单字段、导航项、状态消息和图标必须具备语义含义或无障碍标签。
- 当纯视觉提示传达状态或必需操作时，必须提供非视觉等效方式。

---

## 3. 视觉无障碍

- 文本、图标、边界和状态对比度必须满足目标项目的对比度标准。
- 相关时，动效和过渡必须尊重减少动态效果的考虑。
- 响应式变更必须保留阅读顺序和可达控件。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写目标无障碍标准、键盘期望、焦点样式来源、对比度要求、辅助技术检查和验证命令。
