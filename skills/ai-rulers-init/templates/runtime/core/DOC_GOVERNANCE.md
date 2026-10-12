# 规则权威与质量

```yaml
metadata:
  applies_to:
    - "{{RULERS_DIR}}/**"
  trigger_keywords:
    - rule governance
  must_load_with: []
```

State 保存生命周期、审阅与文件所有权；Profile 保存 observed 事实与 approved 决定；
入口与 INDEX 保存路由；叶子保存专题约束。各项要求只保留一个权威正文。
冲突按宿主指令、用户批准的项目决定、适用规则的作用域与来源处理，记录被替代的要求。
不采用模板示例作为项目事实，不把仓库维护者的提交偏好强加给 project-native 项目。
每条规则说明适用任务、预期行为和可验证依据；重复或不适用的内容通过维护流程裁剪。
修改安全语义与文字澄清分别说明风险。静态结构检查不能代替语义审阅或真实模型评测。
