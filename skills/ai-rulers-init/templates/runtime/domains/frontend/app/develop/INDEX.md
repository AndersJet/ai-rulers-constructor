# App 开发规范索引

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - app development
    - mobile code
    - navigation
    - page state
    - ui pattern
    - test
    - App 开发
    - 移动端代码
    - 导航
    - 页面状态
    - UI 模式
    - 测试
  must_load_with:
    - {{RULERS_DIR}}/frontend/app/INDEX.md
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| 导航、页面状态、平台边界、离线或弱网行为 | [develop/ARCHITECTURE.md]({{RULERS_DIR}}/frontend/app/develop/ARCHITECTURE.md) |
| 交互模式、加载/空/错误状态、破坏性操作确认 | [develop/UI_PATTERNS.md]({{RULERS_DIR}}/frontend/app/develop/UI_PATTERNS.md) |
| 行为变更、回归修复、质量门禁、设备或浏览器验证 | [develop/TESTING.md]({{RULERS_DIR}}/frontend/app/develop/TESTING.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写实际移动端平台路径、导航模型、框架名称、状态约定、API 集成约定、命令和可运行验证流程。
