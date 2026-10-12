# App 前端规范索引

```yaml
metadata:
  applies_to:
    - frontend-mobile/**
    - touch-client/**
    - mobile-client/**
    - mobile/**
  trigger_keywords:
    - app
    - mobile
    - touch
    - navigation
    - safe area
    - mobile accessibility
    - 移动端
    - 触控
    - 导航
    - 安全区域
    - 移动端无障碍
    - 前端
  must_load_with:
    - {{RULERS_DIR}}/frontend/INDEX.md
```

按任务条件选择叶子；有效范围与激活状态由入口校验。

| 任务条件 | 还需加载 |
| --- | --- |
| App 代码、导航、状态、API、测试 | [develop/INDEX.md]({{RULERS_DIR}}/frontend/app/develop/INDEX.md) |
| 移动端布局、触控交互、安全区域、主题、无障碍 | [design/INDEX.md]({{RULERS_DIR}}/frontend/app/design/INDEX.md) |

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写真实移动端平台路径、导航约定、框架名称、包管理器命令、测试命令、设备或浏览器验证方式、设计来源和命名约定。
