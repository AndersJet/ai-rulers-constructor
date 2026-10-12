# 项目规则维护

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
  trigger_keywords:
    - rule maintenance
  must_load_with: []
```

通过 ai-rulers-init 的 maintenance reference 执行增删改、移动、合并与拆分。
先说明原因、作用域、证据、冲突和验证，再审阅候选目录的正文与索引差异。
全局入口仅管加载；领域 INDEX 管条件路由；叶子管专题约束；事实进入 Profile。
使用 rules-plan/rules-apply 同步文件、链接、清单与删除记录；变化领域审阅后再激活。
模板升级保留项目定制；不得把意外文件丢失当作批准删除。
