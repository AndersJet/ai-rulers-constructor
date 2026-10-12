# CHANGELOG 维护规范

```yaml
metadata:
  applies_to:
    - CHANGELOG.md
    - "**/CHANGELOG.md"
  trigger_keywords:
    - changelog
    - change log
    - release notes
    - 变更记录
    - 更新日志
    - 发布说明
    - 版本记录
    - unreleased
  must_load_with:
    - {{RULERS_DIR}}/AGENTS.md
    - {{RULERS_DIR}}/core/HARD_CONSTRAINTS.md
    - {{RULERS_DIR}}/core/GIT_COMMIT_CONVENTION.md
```

---

## 1. 格式标准

项目根目录的 `CHANGELOG.md` 必须遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

### 1.1 文件结构

```markdown
# Changelog

## [Unreleased]

### Added
- 新增功能描述

### Changed
- 变更描述

### Deprecated
- 即将移除的功能

### Removed
- 已移除的功能

### Fixed
- 修复描述

### Security
- 安全相关修复
```

### 1.2 版本号

- 采用 [语义化版本](https://semver.org/lang/zh-CN/)：MAJOR.MINOR.PATCH
- 发布新版本时，将 `[Unreleased]` 内容迁移到新版本号小节，并标注日期：
  ```markdown
  ## [1.2.0] - 2026-06-03
  ```

条目使用中文动宾结构，不以句号结尾，描述改了什么，必要时说明原因，按类型分组。

---

## 2. 更新时机

按 GIT_COMMIT_CONVENTION 核对授权和暂存范围，并据实际变更选择记录：

| 提交类型 | 记录条件 | 分类 |
| --- | --- | --- |
| `feat` | 必须 | `Added` |
| `fix` | 必须 | `Fixed` |
| `docs` | 影响用户可见文档 | `Changed` |
| `refactor` | 影响外部行为 | `Changed` |
| `test` / `chore` / `build` / `ci` | 通常不记录 | — |

需要记录时，在提交前更新 `[Unreleased]`，与对应变更进入同一提交；不在该提交之后
单独补交 CHANGELOG。条目排除密钥、内部路径和客户数据等敏感信息。

---

## 3. 版本发布

当用户要求发布新版本时：

1. 确认当前 `[Unreleased]` 下所有条目已分类正确。
2. 根据变更内容确定新版本号（遵循语义化版本规则）。
3. 将 `[Unreleased]` 内容复制到新版本号小节，并标注日期 `YYYY-MM-DD`。
4. 清空 `[Unreleased]` 下的各分类，保留空分类作为占位。
5. 如有对应的 git tag，在版本号后追加链接：
   ```markdown
   ## [1.2.0] - 2026-06-03
   [1.2.0]: https://github.com/用户名/仓库名/releases/tag/v1.2.0
   ```

---

## 4. 冲突处理

如 `CHANGELOG.md` 在提交前发生合并冲突：

1. 保留两个分支的条目。
2. 去重完全相同的条目。
3. 按类型重新分组排序。
4. 解决后重新暂存。
