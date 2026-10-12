# 审阅与激活

- Profile draft 只能是 Level 0。
- Profile 人工审阅后 Core 可进入 Level 1。
- 领域规则生成、校验和人工审阅后才能进入 Level 2。
- 规则准备状态只表示相关规则和准备流程经过审阅，不代替具体版本验证或生产操作授权。
- 生产动作须有覆盖确切目标、动作和范围的用户授权；已有授权仍适用且输入未变时继续，范围变化时再确认。
- 审阅记录必须包含 reviewer、时间和证据，不得由 AI 自行填写“已审阅”。
- 被拒绝或部分接受的规则保持未激活，且不进入运行态路由。

## 可选准备声明

普通 activate-domain 只形成 Level 2。需要记录生产规则准备时，在初始化候选的
`readiness: {domain: sourcePath}` 或维护计划的 `--readiness-source PATH` 中提供 JSON：

```json
{
  "security": ["documents/rulers/security/AUTHORIZATION.md"],
  "quality": ["documents/rulers/delivery/CI.md"],
  "rollback": ["documents/rulers/delivery/ROLLBACK.md"]
}
```

路径以目标项目根为基准，指向已采纳规则；使用实际目录，可由同一文件覆盖多个主题。
来源仅承载三项非空路径列表，不提供 reviewer、ready 或其他授信字段。声明、路径身份
及适用性进入同一计划审阅；没有该需求的项目不必填写。

脚本核对实际加载依赖、文件身份、Profile 和审阅绑定，仅提示未评估、依据不满足或
依据有效。旧等级数字和 ready 布尔值不单独授信；缺项不阻止健康 CI 维护。完整 runtime
对已有失效声明报告非阻断警告，无声明时不新增警告。

声明存在于采纳范围的同一 review 内。只更新准备声明时，正文原审阅人和时间保持不变，
readiness_approval 保存本次准备批准、计划和声明摘要的范围引用；它不是第二份审批账本。
初始化同时批准正文和声明时使用外层 review，不制造两份相同批准。来源模块的准备标记
不成为主工程批准；无主工程自身依据时保持未评估。
