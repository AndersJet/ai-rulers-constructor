# CHANGELOG 维护规范

> **角色**: 项目变更记录的标准格式、更新时机与 AI 行为约束。

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

### 1.3 条目规范

- 使用中文，动宾结构，不以句号结尾。
- 每个条目描述"改了什么"，必要时说明"为什么"。
- 条目按类型分组（Added/Changed/Fixed 等）。

---

## 2. 更新时机

### 2.1 Commit 前强制更新

AI 在执行 `git commit` **之前**，必须：

1. **审阅暂存区变更**：分析本次 commit 涉及的文件和变更类型。
2. **判断记录必要性**：

   | 提交类型 | 必须记录？ | 目标分类 |
   |---|---|---|
   | `feat` | ✅ 必须 | `Added` |
   | `fix` | ✅ 必须 | `Fixed` |
   | `docs` | 如影响用户可见文档 | `Changed` |
   | `refactor` | 如影响外部行为 | `Changed` |
   | `test` / `chore` / `build` / `ci` | ❌ 通常不记录 | — |

3. **更新 `CHANGELOG.md`**：在 `[Unreleased]` 下追加适当条目。
4. **一并暂存**：将 `CHANGELOG.md` 与代码变更一起 `git add`。
5. **一并提交**：CHANGELOG 更新与代码变更进入**同一个 commit**。

### 2.2 禁止行为

- ❌ 不得在 commit **之后**单独为 CHANGELOG 创建额外 commit。
- ❌ 不得遗漏面向用户的 `feat` 和 `fix` 的 CHANGELOG 记录。
- ❌ 不得在 CHANGELOG 条目中泄露敏感信息（如密钥、内部路径、客户数据）。

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