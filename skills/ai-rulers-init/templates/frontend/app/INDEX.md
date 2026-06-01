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
    - ../../AGENTS.md
    - ../../core/HARD_CONSTRAINTS.md
    - ../INDEX.md
```

---

## 1. 必需加载表

| 任务条件 | 还需加载 |
| --- | --- |
| App 代码、导航、状态、API、测试 | [develop/INDEX.md](develop/INDEX.md) |
| 移动端布局、触控交互、安全区域、主题、无障碍 | [design/INDEX.md](design/INDEX.md) |

---

## 2. 平台说明

`app` 名称是移动端或触控优先前端平台的默认占位符。生成期间，将其替换为目标项目的实际平台名称；如果不存在此类平台，则移除此索引。

---

## 3. AI_FILL 指引

使用 `PROJECT_PROFILE.md` 填写真实移动端平台路径、导航约定、框架名称、包管理器命令、测试命令、设备或浏览器验证方式、设计来源和命名约定。
