# 项目规则维护

适用于新增、修改、删除、移动、合并和拆分规则。先确认本次失败案例、项目变化或用户
偏好需要哪种调整；不因一次模型疏漏直接增加全局禁令。

## 归属与粒度

- 全局入口仅放加载协议；领域 INDEX 放任务条件与导航；叶子规则放专题约束。
- 项目事实进入 Profile；领域正文不重复保存事实快照。
- core 两份最小安全/加载协议由框架升级维护；提交策略是可选策略；领域专题可裁剪。
- 每条新增要求应说明适用任务、证据或原因、验证方式；通用重复提醒优先合并或删除。

## 完整候选目录

将目标领域复制到项目中位于 rulers 之外的候选目录，例如 `.rule-drafts/backend`。
在候选目录中完成所有修改，并同步 INDEX 和 must_load_with。候选是该领域期望保留的
完整 Markdown 文件集；缺少的文件表示删除，移动表现为删除旧路径并新增新路径。
可只保留 INDEX 和实际需要的叶子，不必保留 registry 推荐的全部文件。

```bash
python3 scripts/rulers_init.py rules-plan --project-root <PROJECT_ROOT> \
  --domain backend --candidate-dir .rule-drafts/backend \
  --reason "缓存故障复盘；合并重复验证要求" --output .rule-plans/change.json
```

检查 added/deleted/modified；展示实际正文 diff。语义审阅检查：

1. 是否覆盖实际问题，位置与触发条件是否正确？
2. 是否重复、矛盾或无证据扩大约束？
3. 删除是否移除了必要的安全/业务不变量，有无替代保障？
4. 链接、依赖、验证命令和典型任务加载是否仍正确？
5. 对常驻与任务上下文成本有什么影响？

已有用户授权满足变更范围时继续，否则针对具体差异请求必要审阅。

```bash
python3 scripts/rulers_init.py rules-apply --plan <PLAN_JSON> \
  --reviewed-by <REVIEWER> --evidence <REVIEW_EVIDENCE>
```

脚本核对计划输入、原子写入、检查链接并更新受管清单及 removed_files。正文变化使领域
回到 draft；确认最终内容后 activate-domain，再运行 runtime 校验。内容检查失败会回滚。
模板升级保留 project_owned 文件；deleted 记录阻止默认文件重新出现。
新增未登记叶子可由 register-domain-candidate 采纳；删除既有文件应走此差异流程，
避免把意外丢失误认为批准删除。新增叶子必须通过领域 INDEX 链导航到达，登记、采纳和激活时检查。
父领域只比较和写入自身规则，已注册的嵌套领域子树保持独立。候选可以省略子树，或保留
与安装内容完全一致的副本；修改了其他领域的子树时应单独为那个领域创建维护计划。

## 持续优化

比较代表性任务的正确率、漏载、误放行、无必要确认和上下文成本。能力较弱的模型可
使用 validator `--mode load --domain NAME --rule PATH --format text` 获取相同规则的展开
正文，减少跳转；不降低安全标准，也不复制第二套规则。没有行为评测数据时明确标记。
