# Issue tracker: GitHub

本项目使用 GitHub Issues：`AndersJet/ai-rulers-constructor`。使用 `gh` CLI，显式指定 `--repo AndersJet/ai-rulers-constructor`，避免多个 remote 导致歧义。

## 操作约定

- 读取：`gh issue view <number> --repo AndersJet/ai-rulers-constructor --comments`。
- 列表：`gh issue list --repo AndersJet/ai-rulers-constructor --state open --json number,title,body,labels`。
- 创建：将正文写入临时文件，再运行 `gh issue create --repo AndersJet/ai-rulers-constructor --title "..." --body-file <path>`。
- 评论：`gh issue comment <number> --repo AndersJet/ai-rulers-constructor --body-file <path>`。
- 标签：`gh issue edit <number> --repo AndersJet/ai-rulers-constructor --add-label "..."` 或 `--remove-label "..."`。
- 关闭：`gh issue close <number> --repo AndersJet/ai-rulers-constructor`。

配置只规定操作方式，不构成发布、评论或修改远端资源的授权。按当前任务中的用户授权执行写操作。

## Skills 语义

- “publish to the issue tracker”：创建 GitHub Issue。
- “fetch the relevant ticket”：读取指定 Issue 及评论。
- 本地方案可直接作为 review 的 Spec 来源，不必为了评审额外发布 Issue。

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub Issue 和 PR 共享编号；编号对应 PR 时读取 PR 正文与 diff。

## Wayfinding

- Map：带 `wayfinder:map` 标签的 Issue，保存笔记、已作决定和待解决问题。
- Child：独立 Issue，通过 GitHub sub-issue 关联；不可用时在 Map 的任务列表中链接，并在子任务正文记录 `Part of #<map>`。
- 类型：`wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling`、`wayfinder:task`。
- 阻塞：优先使用原生 Issue dependencies；不可用时用正文 `Blocked by: #<number>` 表达。
- 可领取任务：Map 中尚未关闭、没有未解决阻塞且未分配负责人的子任务，按 Map 顺序处理。
- Claim：授权后使用 `gh issue edit <number> --repo AndersJet/ai-rulers-constructor --add-assignee @me`。
- Resolve：授权后补充结果、关闭任务，并在 Map 中记录结果摘要与链接。
