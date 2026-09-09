# App 交互规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - touch target
    - feedback
    - gesture
    - form
    - navigation flow
    - interaction
    - 触控目标
    - 反馈
    - 手势
    - 表单
    - 导航流程
    - 交互
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/app/design/INDEX.md
    - {{RULERS_DIR}}/frontend/app/design/ACCESSIBILITY.md
```

---

## 1. 触控目标和反馈

- 触控目标必须满足目标项目定义的最小尺寸和间距标准。
- 交互控件必须为按下、加载、禁用、成功和失败状态提供及时反馈。
- 避免将破坏性或高风险操作放在容易误触的位置。

---

## 2. 手势和表单

- 手势必须可发现，或与已建立的平台约定保持一致。
- 当手势不够明显或对目标项目而言不够无障碍时，必须提供手势替代方案。
- 表单必须定义校验时机、键盘行为、输入格式化、错误展示和提交状态。

---

## 3. 导航流程

- 导航流程必须保留用户上下文，并提供清晰返回路径。
- 多步骤流程必须定义取消、确认、返回导航和部分进度行为。
- 避免在没有可见恢复路径的情况下将用户困在流程中。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写触控目标标准、手势规则、表单模式、导航流程约定、触觉或视觉反馈约定和验证命令。
