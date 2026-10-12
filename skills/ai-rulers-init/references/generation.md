# 候选规则生成

为已观察到的领域或用户已批准的绿地设计领域生成规则。先根据画像证据列出必要约束，再按需参考 registry、INDEX 与叶子模板；以证据支持的最小候选集为默认，不先铺满模板目录再裁剪。
按 [rule-quality.md](rule-quality.md) 筛选内容、确定归属并复核最终候选。
将 discovery 中相关业务证据转成触发条件、受保护行为、来源与可观察验证；已有契约
和领域文档继续保存知识正文。未知事实不以通用模板补齐，也不据此追加整域人工审阅。

生成结果必须：

- INDEX 只负责条件路由。
- 叶子规则保存专题约束、适用的审阅触发条件和验收要求；命令引用 Profile 或项目权威配置，不复制第二份命令清单。通用验证要求由 WORKFLOW 承载。
- 删除 AI_FILL、模板路径和生成元指令。
- 未确认事实留在 PROJECT_PROFILE，不写成强制规则。
- 项目已有分支、worktree、PR/MR 和 CI 约定由 WORKFLOW 消费 Profile 的权威指针；
  叶子只补本任务所需专题约束，不生成第二份通用 Git 流程。project-native 和 strict-cn
  都遵循项目工作流；strict-cn 只增加提交格式与 CHANGELOG 政策。
- 验证要求按变更影响和项目必需门禁生成，不将画像中所有命令、流水线所有路径作为每次任务的固定前置。
- 未审阅领域保持 Level 0，且不能从运行态 AGENTS/INDEX 到达。
- security 负责跨领域安全策略；backend API security 只负责服务端执行细节。
- delivery 负责 CI、部署、发布、回滚和部署后验证。

生成后运行 candidate 校验。相同错误集合连续两次没有减少时停止自动修复并报告阻塞。

## 跨技能工作流适配

项目确有外部工作流技能组合时，读取 [skill-interop.md](skill-interop.md)，结合 discovery
所得证据生成阶段、停点及保存/恢复条件。Profile 保留项目 tracker/domain/Git 权威指针；
具体分支策略由项目正文承载，通用模板只约束适配方式。未使用该组合的项目无需新增互操作叶子，
Skill 的互操作 reference 不进入运行态常驻加载清单。

## 候选采纳与底层登记

默认初始化将最小完整候选目录交给 init-plan 的 domains 输入；已安装领域的裁剪走
rules-plan/rules-apply。这两条路径按实际候选建立清单，不要求保留 registry 的推荐全集。
旧的 register-domain-candidate 是登记既定清单的底层入口：首次使用时要求 registry 文件集，
已有领域要求原已采纳文件存在。它不表达删除决定，不用于最小候选初始化或裁剪。

- registry 中 `render_mode: deterministic` 的领域使用 `render-domain-candidate`，脚本负责渲染与受管 hash。
- 仅在确需保留既定清单的底层流程中，为 `render_mode: project-generated` 领域准备该清单全部文件；清除占位符后运行：

  ```bash
  python3 scripts/rulers_init.py register-domain-candidate \
    --project-root <PROJECT_ROOT> \
    --rulers-dir documents/rulers \
    --domain <DOMAIN>
  ```

- 登记命令只采纳现有候选文件，不生成内容；缺文件、AI_FILL 或未展开路径会阻止登记。
- 已登记文件发生变化时，领域自动回到 draft / Level 0，必须重新审阅。
