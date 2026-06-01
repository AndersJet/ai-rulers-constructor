# Web 视觉系统规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
    - design-system/**
  trigger_keywords:
    - visual hierarchy
    - spacing
    - responsive
    - token authority
    - theme
    - layout
    - 视觉层级
    - 间距
    - 响应式
    - token 权威来源
    - 主题
    - 布局
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - ../../common/DESIGN_TOKENS.md
```

---

## 1. 视觉层级

- 保留已建立的标题、内容分组、主要操作、次要操作和辅助信息层级。
- 新布局必须在支持的屏幕尺寸范围内明确浏览顺序和操作优先级。
- 避免与目标项目既有信息架构冲突的视觉强调。

---

## 2. 间距与响应式行为

- 使用项目认可的间距、密度和响应式规则。
- 响应式变更必须定义目标项目支持的视口范围内的行为。
- 避免产生裁切、隐藏关键控件或溢出行为不明确的布局变更。

---

## 3. Token 权威来源

- Token 使用必须遵循 [../../common/DESIGN_TOKENS.md](../../common/DESIGN_TOKENS.md)。
- 不得在此通用模板中定义具体颜色。
- 生成的项目规则只能根据目标项目的权威设计来源定义具体值。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写层级约定、断点或视口规则、间距刻度名称、token 来源、主题来源和视觉验证步骤。在项目事实确认前保持值的通用表述。
