# 后端测试规范

```yaml
metadata:
  applies_to:
    - backend/**
    - server/**
    - services/**
  trigger_keywords:
    - test
    - verification
    - behavior
    - security
    - permission
    - 测试
    - 验证
    - 行为
    - 安全
    - 权限
    - 后端测试
  must_load_with:
    - {{RULERS_DIR}}/backend/INDEX.md
```

## 项目测试选择

通用测试意图、回归与报告要求遵循核心 WORKFLOW。复用项目的测试层级、fixture、factory 和环境设置。

- 安全、权限和数据边界变更覆盖拒绝与越权路径。
- 契约变更验证受影响消费者；持久化、并发、集成和配置变更验证对应失败行为。
- 测试不可行时记录替代验证、未覆盖风险及项目要求的审阅。
- 测试入口与命令引用 Profile 和项目权威配置。

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的测试路径、测试框架名称、fixture 约定、覆盖率预期和验证命令。
