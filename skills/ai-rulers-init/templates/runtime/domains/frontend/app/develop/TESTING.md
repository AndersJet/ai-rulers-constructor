# App 测试规范

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
    - tests/**
  trigger_keywords:
    - test
    - lint
    - typecheck
    - build
    - real device
    - browser verification
    - 测试
    - 静态检查
    - 类型检查
    - 构建
    - 真机
    - 浏览器验证
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/frontend/app/develop/INDEX.md
```

---

## 1. 命令驱动检查

- 针对目标移动端或触控优先前端平台，运行 `PROJECT_PROFILE.md` 中的命令驱动检查。
- 当目标项目定义了 lint、typecheck、test 和 build 命令时，将其纳入检查。
- 如果命令无法运行，报告原因和剩余风险。

---

## 2. 行为覆盖

- 导航、状态、API、授权用户体验、表单和交互变更需要在目标项目使用的层级补充测试。
- 当变更影响弱网、离线、重试和恢复路径时，必须覆盖这些行为。

---

## 3. 测试意图

- 测试必须覆盖用户流程意图、状态变化、权限边界、恢复路径或设备差异影响，而不只是断言表面返回值。
- 回归测试应在修复前失败，并覆盖导致缺陷的失败路径、边界条件或交互序列。
- 如果只能执行表面断言，必须补充更能暴露业务逻辑变化的断言，或记录替代验证和剩余风险。

---

## 4. 设备或浏览器验证

可用时，使用 `PROJECT_PROFILE.md` 中的真机、模拟器、仿真器或浏览器验证指引。报告环境、视口或设备类别、场景和可见结果。

---

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写准确质量命令、测试框架名称、设备或浏览器验证流程、支持的设备类别和报告期望。
