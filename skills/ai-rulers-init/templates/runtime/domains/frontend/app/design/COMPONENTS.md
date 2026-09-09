# App 组件规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
    - design-system/**
  trigger_keywords:
    - mobile component
    - reusable component
    - variant
    - disabled
    - loading
    - error state
    - 移动端组件
    - 可复用组件
    - 变体
    - 禁用
    - 加载
    - 错误状态
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/app/design/INDEX.md
    - {{RULERS_DIR}}/frontend/app/design/TOKENS.md
```

---

## 1. 可复用组件

- 创建新组件前，先复用目标项目移动端组件。
- 新的可复用组件必须定义所有权、预期消费者和变体边界。
- 当共享组件可以安全扩展时，避免创建一次性视觉组件。

---

## 2. 状态变体

- 组件必须定义相关的默认、激活、选中、禁用、加载、空、错误和成功状态。
- 当用户可以基于禁用原因采取行动时，禁用状态必须说明操作不可用的原因。
- 加载和错误状态应在可行时保持布局稳定。

---

## 3. 契约纪律

组件 props、slots、events、callbacks 或等效扩展点必须遵循目标项目命名和所有权约定。不得通过临时样式或隐藏副作用绕过组件契约。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写组件目录、组件库约定、状态变体名称、文档位置、所有权模型和验证命令。
