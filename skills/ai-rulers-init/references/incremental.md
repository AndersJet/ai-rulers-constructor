# 统一 Reconcile 参考

当项目证据或已批准决策发生变化时，通过 reconcile 流程更新受影响的领域规则。

## 触发条件

- 新增代码目录、框架或基础设施
- 已批准架构决策变更（approved evidence 改变）
- 依赖、工具链或 CI/CD 变化
- 新领域变得相关（数据库、认证、部署等）

## 流程

1. plan --operation reconcile --candidate-profile PATH --changed-path PATH...
2. 审阅 Context 输出的 affected_domains 和 domain_actions
3. apply --plan plan.json --reviewed-by NAME --evidence REF
4. 验证 Context 刷新后 load graph 正确

## 约束

- evidence-only 变更不降级领域
- affected active domain 降为 Draft/Level0 需重新审阅
- retired domain 保留文件但移除 route
- 全局 phase 保持 runtime_ready
- 没有事实、策略或模板版本变化时必须零 diff
