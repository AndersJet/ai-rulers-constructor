# Contributing to Rulers Constructor

感谢你对 Rulers Constructor 的兴趣！本文档面向希望修改模板规则、维护 skill 或贡献代码的开发者。

---

## 修改模板规则

1. **了解治理规则**：修改前请先加载 `documents/rulers/core/DOC_GOVERNANCE.md`，了解规范文档的治理原则。
2. **评估影响**：执行 ruler impact assessment（详见 `documents/rulers/core/RULER_MAINTENANCE.md`），评估变更对现有规则的影响范围。
3. **运行校验**：修改后运行校验脚本，确保结构完整性：
   ```bash
   python3 documents/rulers/scripts/validate_rulers.py
   ```
4. **遵循提交规范**：见下文「Commit Conventions」。

## 修改 ai-rulers-init Skill

1. 编辑 `skills/ai-rulers-init/SKILL.md` 修改工作流逻辑。
2. 编辑 `skills/ai-rulers-init/templates/` 更新内嵌模板内容。
3. 重新打包（需要安装 `skill-creator`）：
   ```bash
   python -m scripts.package_skill skills/ai-rulers-init
   ```
4. 用新生成的包替换 `skills/ai-rulers-init.skill`。

## Commit Conventions

- **`type`**: 英文，可选值：`feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `build` / `ci`
- **`subject`**: 中文，动宾结构，不以句号结尾
- **`body`**: 中文，说明「改了什么」和「为什么」
- **Format**: `<type>[optional scope]: <subject>`

示例：
```
feat(validate): core 文件引用校验扩展为 6 个

原校验逻辑仅检查 4 个 core 文件，现增加 CHANGELOG 模板和
激活等级文档的引用检查，避免遗漏新引入的权威文档。
```

---

如有疑问，欢迎通过 [Issue](https://github.com/AndersJet/ai-rulers-constructor/issues) 或 [Pull Request](https://github.com/AndersJet/ai-rulers-constructor/pulls) 交流。
