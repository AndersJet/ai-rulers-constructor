# 交付领域路由

```yaml
metadata:
  applies_to:
    - ".github/**"
    - ".gitlab-ci.yml"
    - "deploy/**"
    - "infrastructure/**"
  trigger_keywords:
    - ci
    - deployment
    - release
    - rollback
    - 部署
    - 发布
    - 回滚
  must_load_with:
    - "{{RULERS_DIR}}/AGENTS.md"
    - "{{RULERS_DIR}}/RULERS_STATE.json"
```

| 任务条件 | 还需加载 |
| --- | --- |
| CI、质量门禁、构建流水线 | `CI.md` |
| 部署流程、环境晋级、基础设施 | `DEPLOYMENT.md` |
| 版本发布、产物推广 | `RELEASE.md` |
| 回滚、恢复、失败演练 | `ROLLBACK.md` |

delivery 审阅完成只能形成 Level 3 readiness；具体生产操作仍需针对确切动作人工确认。
