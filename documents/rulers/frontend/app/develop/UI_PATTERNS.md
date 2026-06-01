# App UI 模式规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - mobile interaction
    - ui pattern
    - loading state
    - empty state
    - destructive action
    - confirmation
    - 移动端交互
    - UI 模式
    - 加载状态
    - 空状态
    - 破坏性操作
    - 确认
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 交互一致性

- 移动端交互必须与已建立的目标项目模式保持一致。
- 对点击、长按、滑动手势、面板、对话框、列表、表单和导航反馈使用既有模式。
- 当既有模式已覆盖需求时，避免引入新的交互模式。

---

## 2. 状态模式

- 加载、空、禁用、错误、重试和成功状态必须显式表达。
- 适用时，空状态应说明条件和可用的下一步操作。
- 错误状态必须可操作，并且不得暴露敏感数据。

---

## 3. 破坏性操作

破坏性或不可逆操作需要确认，或采用等效的项目认可保护措施。确认文案和恢复行为必须遵循目标项目约定。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写交互约定、可复用 UI 模式位置、文案标准、确认行为、状态组件和验证命令。
