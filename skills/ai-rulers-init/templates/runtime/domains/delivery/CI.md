# CI 与质量门禁

```yaml
metadata:
  applies_to:
    - ".github/**"
    - ".gitlab-ci.yml"
  trigger_keywords:
    - ci
    - quality gate
    - build pipeline
    - 持续集成
  must_load_with:
    - "{{RULERS_DIR}}/delivery/INDEX.md"
```

- CI 任务、工作目录、运行时版本和必需检查必须来自仓库配置证据。
- 不得绕过测试、静态检查、安全检查或必需审阅门禁。
- 修改流水线时验证正常、失败、取消和重试路径。
- 产物生成必须可追溯到源码版本，敏感值不得进入日志或产物。
