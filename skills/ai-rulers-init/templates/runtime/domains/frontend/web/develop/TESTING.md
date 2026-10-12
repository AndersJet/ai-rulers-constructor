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
    - {{RULERS_DIR}}/frontend/web/develop/INDEX.md
```

## Web 专项验证

通用测试意图、回归与报告要求遵循核心 WORKFLOW。按 Web 变更影响选择 lint、typecheck、test 或 build，并执行项目必需门禁；仅提交或推送不触发无关全套检查。

- API、授权、路由、状态和组件交互变更覆盖相关成功与失败路径。
- UI 的可见或交互行为变化且项目可运行时，进行浏览器验证，记录路由、视口或响应式条件及可见结果；纯注释等不影响 UI 的改动无需浏览器回放。
- 验证命令、启动流程和支持的视口引用 Profile 或项目权威配置。

## AI_FILL

使用 `PROJECT_PROFILE.md` 填写准确的 Web 质量命令、测试框架名称、浏览器启动流程、支持的视口矩阵和报告期望。
