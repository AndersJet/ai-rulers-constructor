# Git 提交规范

```yaml
metadata:
  applies_to:
    - .git/**
    - "**/*"
  trigger_keywords:
    - git
    - commit
    - staged diff
    - 提交
    - 暂存区差异
    - changelog
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
```

## 提交范围与授权

1. 检查 `git status`、`git diff` 和 `git diff --cached`，确认本次提交范围及文件归属。
   用户限定“已暂存内容”时仅处理暂存区；需要补充 CHANGELOG 或发现混合修改时，先说明范围变化。
2. 仅暂存已授权范围。保留用户、其他 Agent 和未知归属的修改；同文件混合修改用最小范围暂存，
   无法安全拆分时展示差异并请求裁决。
3. 按 `CHANGELOG_MAINTENANCE.md` 检查记录。feat/fix 必须更新 `[Unreleased]`，与实现进入同一提交；
   其他变更按该文件的适用条件处理。
4. 读取完整相关暂存差异，生成文件清单和提交信息草案，并执行项目规定的门禁。
   明确提交授权且范围未变时，展示后直接执行；项目另设确认门禁时遵守该门禁。
   未获提交授权、范围不明或发生变化时，先取得针对具体范围的授权。

提交、推送、PR/MR、合并、修订、变基、强制操作和分支清理分别依据项目约定及当前授权执行。
提交授权不覆盖其他动作；实际 hook、CI 必需检查和审阅门禁保持有效。门禁失败时报告失败，
完成必要修复和验证后继续，不能为提交绕过检查。破坏性操作须针对确切动作授权。

## 提交信息

格式：`<type>[optional scope]: <subject>`。

| type | 变更 |
| --- | --- |
| feat | 新功能 |
| fix | 缺陷修复 |
| docs | 文档 |
| refactor | 不改变外部行为的结构调整 |
| test | 测试 |
| chore | 依赖、构建、CI 等维护 |

- type 使用英文，按实际变更性质选择；scope 在有助于识别影响范围时填写。
- subject 使用中文动宾结构，不超过 50 字，准确描述改了什么。
- body 使用中文，说明改了什么、为什么及影响范围。适用时说明兼容变化。
- 清单、提交信息和 CHANGELOG 不包含密钥、凭据或敏感数据。

```text
fix(settings): 保留通知偏好设置

- 改了什么：保存用户通知偏好并补充读取回归。
- 为什么：修复刷新后偏好丢失。
- 影响范围：设置页及偏好持久化接口。
```

提交前核对格式、已授权暂存范围和 CHANGELOG；完成后报告实际提交结果及未覆盖事项。
