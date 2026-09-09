# 前端通用规范索引

```yaml
metadata:
  applies_to:
    - frontend/**
    - client/**
    - ui/**
    - design-system/**
  trigger_keywords:
    - design tokens
    - tokens
    - theme
    - shared design
    - visual foundation
    - 设计 token
    - token
    - 主题
    - 共享设计
    - 视觉基础
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/INDEX.md
```

---

## 1. 条件加载

当变更影响多个平台或改变可复用视觉决策时，先加载本索引，再按任务条件加载叶子规则：

| 任务条件 | 还需加载 |
| --- | --- |
| 设计 token、主题、跨平台视觉基础、可复用视觉决策 | [{{RULERS_DIR}}/frontend/common/DESIGN_TOKENS.md]({{RULERS_DIR}}/frontend/common/DESIGN_TOKENS.md) |

---

## 2. 范围

通用规则定义跨平台设计基础。平台专属的交互、布局、组件和无障碍细节属于相关平台设计规则。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 识别目标项目的权威设计来源、token 文件位置、token 命名约定、支持的平台和验证命令。不要在此通用模板中虚构具体 token 值。
