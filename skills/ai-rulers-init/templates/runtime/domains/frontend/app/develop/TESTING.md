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
    - {{RULERS_DIR}}/frontend/app/develop/INDEX.md
```

## 移动端专项验证

通用测试意图、回归与报告要求遵循核心 WORKFLOW。按移动端变更影响选择 lint、typecheck、test 或 build，并执行项目必需门禁；不因命令存在而重跑全套。

- 导航、状态、API、授权用户体验、表单和交互变更验证受影响用户流程。
- 影响弱网、离线、重试、恢复或设备差异时，覆盖对应路径。
- 可见或交互行为变化时，使用 Profile 中可用的真机、模拟器、仿真器或浏览器指引验证，记录环境、设备类别、场景和可见结果。
- 验证命令与设备范围引用 Profile 或项目权威配置。

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写准确质量命令、测试框架名称、设备或浏览器验证流程、支持的设备类别和报告期望。
