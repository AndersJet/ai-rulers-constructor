# 审阅与激活

- Profile draft 只能是 Level 0。
- Profile 人工审阅后 Core 可进入 Level 1。
- 领域规则生成、校验和人工审阅后才能进入 Level 2。
- delivery/security/rollback/quality gate 审阅完成后只能记录 `Level 3 readiness`；每次生产操作仍需针对确切动作再次确认。
- 审阅记录必须包含 reviewer、时间和证据，不得由 AI 自行填写“已审阅”。
- 被拒绝或部分接受的规则保持未激活，且不进入运行态路由。
