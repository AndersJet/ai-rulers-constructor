# 候选规则生成

为已观察到的领域或用户已批准的绿地设计领域生成规则。生成前读取项目画像、领域 registry、目标 INDEX 模板和相关叶子模板。模板清单是推荐起点；裁剪后的完整候选可通过 maintenance 的 rules-plan/rules-apply 采纳。

生成结果必须：

- INDEX 只负责条件路由。
- 叶子规则包含可执行约束、验证命令、审阅触发条件和退出检查。
- 删除 AI_FILL、模板路径和生成元指令。
- 未确认事实留在 PROJECT_PROFILE，不写成强制规则。
- 未审阅领域保持 Level 0，且不能从运行态 AGENTS/INDEX 到达。
- security 负责跨领域安全策略；backend API security 只负责服务端执行细节。
- delivery 负责 CI、部署、发布、回滚和部署后验证。

生成后运行 candidate 校验。相同错误集合连续两次没有减少时停止自动修复并报告阻塞。

## 候选登记

- registry 中 `render_mode: deterministic` 的领域使用 `render-domain-candidate`，脚本负责渲染与受管 hash。
- registry 中 `render_mode: project-generated` 的领域由 AI 根据项目证据生成全部必需文件；清除占位符后运行：

  ```bash
  python3 scripts/rulers_init.py register-domain-candidate \
    --project-root <PROJECT_ROOT> \
    --rulers-dir documents/rulers \
    --domain <DOMAIN>
  ```

- 登记命令只采纳现有候选文件，不生成内容；缺文件、AI_FILL 或未展开路径会阻止登记。
- 已登记文件发生变化时，领域自动回到 draft / Level 0，必须重新审阅。
