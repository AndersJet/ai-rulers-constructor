# 共享设计 Token 规范

```yaml
metadata:
  applies_to:
    - frontend/**
    - client/**
    - ui/**
    - design-system/**
  trigger_keywords:
    - design tokens
    - token
    - color
    - spacing
    - typography
    - radius
    - shadow
    - theme
    - 设计 token
    - token
    - 颜色
    - 间距
    - 字体排版
    - 圆角
    - 阴影
    - 主题
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/common/INDEX.md
```

---

## 1. Token 权威来源

- 设计 token 必须只有一个权威来源。
- 生成的项目规则必须识别该权威来源是设计文件、代码文件、包、文档来源，还是另一个项目认可的来源。
- 扩展或消费既有 token 时，不得创建第二套 token 来源。

---

## 2. 跨平台影响

- Token 变更必须评估所有消费它们的平台。
- 实施前，token 变更必须识别受影响的组件、页面、主题和生成资产。
- 除非目标项目明确的平台覆盖规则另有定义，否则平台专属适配必须保留共享 token 的含义。

---

## 3. 通用模板限制

- 具体颜色、间距、字体排版、圆角和阴影值属于生成的项目规则，不属于此通用模板。
- 此模板可以描述分类和治理，但不得定义品牌值或项目专属 token 名称。

---

## 4. 保持无障碍

UI 变更必须保留目标项目定义的无障碍对比度和交互可感知性要求。如果目标项目未定义标准，在批准视觉基线变更前必须要求人工确认。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写真实设计权威来源、token 位置、命名约定、支持的平台、无障碍对比度标准和验证命令。对未知值保持通用表述，并标记为需要确认。
