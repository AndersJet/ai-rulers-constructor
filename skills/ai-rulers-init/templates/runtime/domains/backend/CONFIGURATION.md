# 配置规范

```yaml
metadata:
  applies_to:
    - backend/**
    - server/**
    - services/**
  trigger_keywords:
    - configuration
    - environment
    - secret
    - feature flag
    - runtime
    - 配置
    - 环境
    - 密钥
    - 功能开关
    - 运行时
    - 后端配置
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/backend/INDEX.md
```

---

## 1. 密钥处理

- 密钥必须来自目标项目批准的密钥机制。
- 不得提交真实密钥、凭据、私钥、生产端点或敏感令牌。
- 不得记录已解析的密钥值，也不得通过诊断、错误、健康检查或生成文档暴露这些值。

---

## 2. 环境行为

- 不得将环境特定配置硬编码到源码中。
- 配置变更必须在存在默认、开发、测试和生产环境时说明对这些环境的影响。
- 默认值必须安全、可观测，并兼容目标项目的本地与自动化验证工作流。

---

## 3. 审阅要求

- 安全相关配置需要人工审阅。
- 对功能开关、发布控制、集成端点、资源限制或运维开关的变更，必须在适用时识别故障模式和回滚行为。

---

## AI_FILL

根据 `PROJECT_PROFILE.md` 生成项目特定的配置路径、环境名称、密钥机制名称、功能开关约定、运行时术语和验证命令。如果配置事实未经观察或人工确认，则保持生成规则的通用性，并要求在安全相关配置变更前进行审阅。
