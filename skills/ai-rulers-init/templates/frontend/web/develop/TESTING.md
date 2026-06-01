# Web 测试规范

```yaml
metadata:
  applies_to:
    - frontend-browser/**
    - browser/**
    - browser-client/**
    - tests/**
  trigger_keywords:
    - test
    - lint
    - typecheck
    - build
    - browser verification
    - quality gate
    - 测试
    - 静态检查
    - 类型检查
    - 构建
    - 浏览器验证
    - 质量门禁
  must_load_with:
    - ../../../AGENTS.md
    - ../../../core/HARD_CONSTRAINTS.md
    - INDEX.md
```

---

## 1. 命令驱动检查

- 当 `PROJECT_PROFILE.md` 为目标 Web 平台定义了 lint、typecheck、test 和 build 命令时，运行这些命令。
- 当目标项目定义了规范质量门禁时，不得虚构替代命令。
- 如果命令无法运行，报告原因和剩余风险。

---

## 2. 测试覆盖期望

- 行为变更需要在目标项目使用的层级补充测试。
- API、授权、路由、状态和组件交互变更应在可行时覆盖成功和失败路径。
- 回归修复应包含一个在修复前会失败的测试。

---

## 3. 浏览器验证

当目标项目可运行时，UI 变更需要浏览器验证。记录已测试的路由、视口或响应式条件，以及可见结果。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写准确的 Web 质量命令、测试框架名称、浏览器启动流程、支持的视口矩阵和报告期望。将缺失命令标记为需要项目确认。
