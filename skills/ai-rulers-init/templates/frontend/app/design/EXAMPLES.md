# App 设计示例

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - mobile examples
    - app examples
    - pattern example
    - non-authoritative
    - design example
    - 移动端示例
    - App 示例
    - 模式示例
    - 非权威
    - 设计示例
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 权威声明

本文件中的示例均为非权威示例。它们用于说明可能的移动端模式，但不得覆盖本目录规则、共享设计 token 规则、生成的项目规则或目标项目设计来源。

---

## 2. 示例使用规则

- 仅在加载相关权威规则文件后使用示例。
- 将示例适配到目标项目的 token、组件、无障碍标准和交互约定。
- 当示例结构、文案、布局或取值与项目规则冲突时，不得复制它们。

---

## 3. 示例模式分类

生成的项目可以添加以下非权威示例：

- 列表、详情、编辑和空状态流程。
- 加载、重试、离线和弱网状态。
- 破坏性操作确认和撤销流程。
- 移动端表单、校验和键盘行为。
- 感知安全区域的页头、页脚和固定操作。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 基于观察到的组件、设计来源、token 名称、文案约定和验证期望生成项目专属示例。保持示例明确标记为示例，绝不能作为事实来源。
