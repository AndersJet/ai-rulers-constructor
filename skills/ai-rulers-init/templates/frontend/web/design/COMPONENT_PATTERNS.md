# Web 组件模式规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
    - design-system/**
  trigger_keywords:
    - component
    - pattern
    - variant
    - reuse
    - design system
    - 组件
    - 模式
    - 变体
    - 复用
    - 设计系统
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - ../../common/DESIGN_TOKENS.md
```

---

## 1. 复用优先

- 创建新视觉模式前，先复用既有组件。
- 优先扩展已记录的变体，而不是创建一次性组件外观。
- 新组件必须识别其归属位置和消费者。

---

## 2. 变体纪律

- 在生成的项目规则或项目拥有的组件文档中记录支持的变体、状态、尺寸和响应式行为。
- 禁用、加载、空、错误、选中和激活状态必须与既有模式一致。
- 避免未经项目批准就使用样式覆盖绕过可复用组件契约。

---

## 3. 审阅期望

组件变更必须考虑复用影响、无障碍、token 使用、交互状态和视觉回归风险。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写组件库名称、共享组件路径、变体命名、文档位置、审阅所有者和视觉验证命令。不要在通用模板中命名具体库。
