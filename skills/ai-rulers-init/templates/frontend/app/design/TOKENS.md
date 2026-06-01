# App Token 规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
    - design-system/**
  trigger_keywords:
    - mobile tokens
    - token adaptation
    - theme
    - color
    - spacing
    - typography
    - 移动端 token
    - token 适配
    - 主题
    - 颜色
    - 间距
    - 字体排版
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - ../../common/DESIGN_TOKENS.md
```

---

## 1. Token 所有权

- 移动端 token 使用必须遵循 [../../common/DESIGN_TOKENS.md](../../common/DESIGN_TOKENS.md) 和目标项目的平台 token 权威来源。
- 平台 token 覆盖必须有已记录的所有者和原因。
- 不得在此通用模板中定义具体 token 值。

---

## 2. 移动端适配

- 只能通过目标项目认可的 token 机制，针对触控密度、移动端视口约束、对比度和平台约定适配 token。
- 当权威 token 存在时，不得硬编码视觉值。
- Token 变更必须评估消费它们的 Web、移动端、共享组件和生成资产。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写移动端 token 来源、共享 token 来源、平台覆盖策略、token 名称、设计工具来源和验证命令。在确认前，将未知 token 值排除在生成规则之外。
