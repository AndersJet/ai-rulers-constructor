# ai-rulers-init 阶段与跨技能适配验证

日期：2026-10-08。前述方案 B 的实施与回放阶段只维护源码和本地候选，未提交、推送、发布、
修改全局安装或回改 trae-hooks。源码基线 `b8954ce37eb4f3f311e9081d66bd7d658b9d4f4d`，
初始工作区干净。该阶段版本为 4.1.0，候选身份由源码差异和包 hash 区分。
后续用户授权提交、推送、创建到 main 的 PR 并发布 4.1.1；发布准备检查另见文末，
既有模型观察继续绑定原候选，不改写为 4.1.1 模型重跑成绩。

## 改动与归属

- core/WORKFLOW：增加本轮阶段、完成停点与项目/宿主工作区适配，常驻增量 180 UTF-8 bytes。
- discovery/generation/maintenance：条件引用 skill-interop；项目 workflow/tracker/domain 正文保留在项目，Profile 只保存指针。
- skill-interop：一次委派、未决人类停点、ticket/ADR/CONTEXT/Profile 归属、地图来源及资产回收；不进入运行态常驻加载。
- 22 项 eval 定义及合成目标/CLI执行支持；测试输出与模型轨迹分别保存。State/schema、事务、哈希、所有权、依赖和审批实现无变化。

## 本地交付入口

稳定交付目录：[interop-delivery](/Users/liujie/.codex/visualizations/2026/10/08/01a11937-5902-7252-ab37-3d4d0a309369/interop-delivery)。
其中 packages 保存 baseline、最终候选及解压目录；inputs 保存自然任务；targets 保留隔离
项目、原始来源、文档与 .git；evidence 保存静态日志、前后状态、公开事件、产物身份及评分。
不自动清理合成目标，避免证据随临时目录退出失效。

候选：[ai-rulers-init-4.1.0-interop-candidate.skill](/Users/liujie/.codex/visualizations/2026/10/08/01a11937-5902-7252-ab37-3d4d0a309369/interop-delivery/packages/ai-rulers-init-4.1.0-interop-candidate.skill)。
SHA-256：`3b42f1dd23bffdde77ca3953175e821a366ac8874f1f01a2507f26533a238150`。
该阶段跟踪分发包、稳定候选与重复构建结果字节一致；候选中的 eval 开发资产继续排除。
源码内容清单及含新增文件的 patch 身份见交付目录 `source-identity.json`、`source.patch`。

使用者可直接读取已解压的 `packages/candidate/ai-rulers-init`，或将候选解压到新的目录；
从其中的 `scripts/rulers_init.py` 运行目标项目 plan，并核对真实 review diff。不要覆盖全局
Skill 或直接手改 managed WORKFLOW/State。相同版本号仍由模板 fingerprint 检出升级。
合成 upgrade-check 已从 baseline 经候选公开 CLI 升级；保留画像审阅、项目正文和未知修改，
candidate/runtime/context/load 通过，再次 plan 为 noop。多余 review-profile 调用曾因
runtime_ready 被拒绝（exit 2），无审阅改写；记录保留在 evidence/upgrade-check.json。

## 脚本与结构证据

- template 校验通过。
- 首轮原套件 239 项通过（312.865 秒）；新增双策略夹具及相关检查 24 项通过。
- 双策略夹具通过公开 CLI 生成 candidate、审阅、runtime_ready、Context/load 和重复 noop。
  named 项目使用 task/map；detached 项目使用 topic/decision-map；分支名只在项目权威正文，
  画像和通用 WORKFLOW 没有复制任一策略。这是确定性夹具检查，不是 AI 发现/生成效果。
- Context 663 bytes；固定 backend 加载链 6926 / 16000 bytes；Skill 78 行。
  附加 1–100 文件与实际 20 次 reconcile 的 Context 增长均为 0。
- 最终全量 240 项通过（325.918 秒）；夹具最后增加 strict-cn 策略及修正历史回答摘要后，定向 1 项再次通过（3.037 秒）。
- 最终解压包的 module_workflows/auto_initialization 27 项公开流程通过（134.782 秒）；113 个发布成员与源码逐字节一致。
- strict-cn-upgrade-check 通过公开 CLI 从基线升级；策略、画像审阅、提交格式、CHANGELOG、项目正文及未知草稿保留，candidate/runtime/context/load 与再次 noop 通过。

## 执行身份与证据限制

CLI 为 0.160.0，保持正常配置和 workspace-write；首次外层沙箱阻止 app-server 初始化，
exit 1且没有模型事件；正常权限审阅后执行成功。保留失败和重试独立目录，未设置 bypass。
官方 [Skill 评测说明](https://developers.openai.com/blog/eval-skills)用于确认公开 JSONL 记录方式；
本机 flags 以实际 help 为准。

所有已记录执行及研究后代的 session turn_context 均报告 gpt-6.1-sol / high；模型/effort 单独保留在 evidence/public-traces/index.json；
这是 harness 选择记录，provider resolved model仍 unknown。CLI JSONL 包含部分工具和 usage；
补充保存同一执行及后代的公开函数/工具事件。Desktop公开轨迹来自本机相同宿主，未导出私有
analysis；宿主封装的 opaque payload 只保留 hash。原始 session 文件路径供本机追溯。

受测者只得到自然任务、目标规则和原全局技能副本；未注入评分答案、根因或旧结论。全局
wayfinder/research/grilling/grill-with-docs/domain-modeling 内容在 preparation 中逐文件留 hash，
12 个外部技能源文件前后 hash 一致，副本与原文件最终核对。已安装 ai-rulers-init 仅记录
114 个最终文件 hash，缺少初始全量快照；本轮没有安装或写入该目录的动作。固定回答来源为源会话
`01a11755-4bfa-7fe2-9929-cc272b82832e` 的 implementation-decisions.md 第一轮 Q1。
其业务 Destination 和合成任务来源分别标注；没有伪造人类答案或实时交互。

## 有限回放与未覆盖项


| 场景 | 宿主 | 基线 | 候选 | 证据范围 |
| --- | --- | --- | --- | --- |
| 建图/并行研究 | Desktop子代理 | 有限路径通过 | 有限路径通过 | 各一次委派两位worker，无同题再委派；两份独立报告回收，新的 HITL 待答 |
| 继续/分叉 | CLI | 有限路径通过 | 有限路径通过 | 核验当前/fork来源，复用工作区，只闭所选研究票；首批摘要输入缺口另列 |
| 重建/归档 | CLI | 工作区适配偏离 | 有限路径通过 | 旧材料/未知草稿保留，新 Destination 生效，命名 clone 与无 Git 临时报告目录分别观察 |
| 访谈/闭票 | CLI | 有限路径通过 | 有限路径通过 | 历史四项选择已解决，删除时机保持待答，CONTEXT有术语，受管 rules/State 保持原字节 |

8 个完成样本及其 8 个研究 worker 的公开身份/轨迹保留在 public-traces；每个 CLI 执行
exit 0，初次沙箱启动失败另记 exit 1。评分核对实际 HEAD、refs/upstream/worktree、
受管规则与输入来源 hash、未知草稿、资产链接和一次委派记录；评分者是实施协调者，
不是盲评第三方。没有实时人类回答，不将这些合成票的问题转交为本项目的新审批。

结果在 evidence/grading.json 中按工具事件、Git状态和实际产物评分，exit=0本身不代表通过。
建图/并行研究与继续/分叉的基线、候选均完成有限路径。重建场景中，基线额外创建了
`research/git-remote-attribution` 命名分支的临时 clone，偏离项目的规划分支复用/detached
约定；候选使用来源/报告临时目录并记录回收前后 hash，没有新建研究分支。两个版本
都保留旧快照、未知草稿与退休指针，待人类问题保持开放。该差异仅为一次观察，不能
归因为模板的确定性效果。固定回答后的步骤与未答
停点观察不等于实时 HITL 全流程。首批 continue/rebuild 夹具的 map 摘要把合成的规格范围写成了历史
回答摘要；ticket 正文保存的 Q1 原文正确并标明合成 Destination。旧样本输入和前态
未回写，历史回答范围保真不计通过；后续夹具已修正，访谈两组在执行前修正并留原/新
快照。这是输入构造缺口，与模型行为评分分别报告。

每个 baseline/candidate 仅一个有限样本，不作因果、
长期质量或 Token/成本优势结论。

Desktop 合成根与当前 chat绑定的 repository不同，managed-worktree工具不能忠实绑定它；
若使用 shell worktree或复用现有根，仅证明相应路径。managed创建/归档恢复的完整原故障
路径、真实用户连续 HITL、真实外部 tracker/API/业务项目、所有第三方技能组合均未覆盖。
旧八分支没有操作；未把目录缺失推导成删除或材料已保全。

## 4.1.1 发布准备

用户已授权提交、推送、创建到 main 的 PR 与发布 4.1.1。GitHub 为本仓库托管平台，
因此 MR 交付对应 GitHub Pull Request。标签与 Release 将绑定同一已核验的发布提交；
PR 创建与合并分别报告。

版本仅修改 `scripts/rulers_lib/version.py` 中的 RELEASE_VERSION，数据协议版本保持原契约；
CHANGELOG 将待发布的阶段与互操作修正归入 4.1.1。重新构建正式包，实际检查结果：

- 源码与解压包 CLI 均为 4.1.1，template 校验通过。
- 全量回归 240 项通过（319.280 秒）；最终解压包公开流程 27 项通过（147.595 秒）。
- 113 个包成员与当前源码逐字节一致，重复构建字节一致。正式包 SHA-256：
  `52a16e043ca92b38159239c1ccd8ea9694948baa8d3938408aa5b865d411dbb4`。
- 与模型受测的 4.1.0 互操作候选比较，只有 `scripts/rulers_lib/version.py` 的 RELEASE_VERSION 内容变化；
  规则正文不变，仍不宣称新版模型重跑。
- 最终解压包实际生成 project-native 新安装并升级 strict-cn 临时目标，State 版本为 4.1.1；
  candidate/runtime/context/load 及重复 noop 通过，提交约定、CHANGELOG、项目正文和未知草稿保留。
- 常驻预算通过：Context 663 bytes，固定 backend 加载链 6926 / 16000 bytes；
  1–100 附加文件与20次 reconcile 均零增长。57 个本地文档链接有效，凭据模式检查无命中。

本机发布准备原始记录位于 `release-4.1.1` 交付目录；确认提交草案后再执行远端交付。

本文中的 interop-delivery 为本机保留证据，不是 GitHub 公开下载地址；Release 附件以
公开的 ai-rulers-init.skill 与 SHA256SUMS 为准。旧候选 SHA 与轨迹仍只说明前述有限观察，
实时 HITL、Desktop managed-worktree 原故障路径及首批夹具输入缺口继续保留未验证状态。
