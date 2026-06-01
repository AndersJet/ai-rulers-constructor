# App 无障碍规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
    - design-system/**
  trigger_keywords:
    - mobile accessibility
    - label
    - focus
    - screen reader
    - contrast
    - motion
    - touch target
    - 移动端无障碍
    - 标签
    - 焦点
    - 屏幕阅读器
    - 对比度
    - 动效
    - 触控目标
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - TOKENS.md
```

---

## 1. 标签和屏幕阅读器支持

- 交互控件、图标、表单字段、状态消息和导航项必须具备无障碍标签或语义等效方式。
- 屏幕阅读器顺序必须与预期视觉流程和任务流程一致。
- 当目标项目要求时，动态状态更新必须被播报。

---

## 2. 焦点和导航

- 适用时，焦点行为必须支持键盘、辅助技术和平台导航模式。
- 对话框、面板、菜单和多步骤流程必须定义进入、退出和返回焦点行为。

---

## 3. 对比度、动效和触控目标

- 对比度必须满足目标项目的无障碍标准。
- 相关时，动效和动画必须尊重减少动态效果要求。
- 触控目标最小值必须遵循目标项目标准；如果缺失，在批准新的移动端无障碍基线前要求确认。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写无障碍标准、触控目标最小值、屏幕阅读器检查、焦点规则、对比度要求、减少动态效果策略和验证命令。
