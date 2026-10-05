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
- 修改流水线时按实际变更验证受影响的触发、任务依赖、失败处理和产物路径；取消或重试行为变化时覆盖对应路径。
- 本地检查、CI 触发、观察、诊断和合并责任遵循项目工作流权威指针；只运行受影响的必要检查及项目必需门禁，无法执行时列明覆盖缺口。
- 产物生成必须可追溯到源码版本，敏感值不得进入日志或产物。
