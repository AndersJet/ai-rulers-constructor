# App 布局规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - mobile layout
    - viewport
    - safe area
    - single column
    - density
    - overflow
    - 移动端布局
    - 视口
    - 安全区域
    - 单列
    - 密度
    - 溢出
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
    - TOKENS.md
```

---

## 1. 视口和安全区域

- 布局必须考虑目标项目支持的视口和安全区域要求。
- 关键内容和控件不得被浏览器、宿主、键盘、开孔或手势区域遮挡。
- 变更必须定义高度和宽度受限场景下的行为。

---

## 2. 移动端布局默认值

- 除非目标项目定义了其他移动端模式，否则默认使用单列布局。
- 密度必须在信息可见性、文本可读性和控件可用性之间保持平衡。
- 页面结构必须让主要操作可发现且可触达。

---

## 3. 溢出行为

- 滚动容器、粘性区域、固定操作和嵌套溢出必须是有意设计的。
- 避免裁切内容、无法触达的操作或滚动陷阱。
- 长内容、动态文本和校验错误必须保持可读。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写视口矩阵、安全区域规则、密度刻度、布局原语、溢出约定和视觉验证流程。
