"""Human review projection of consolidated initialization changes."""

import base64
import json
from difflib import unified_diff
from pathlib import Path


def review_markdown(plan):
    lines = [
        "# 初始化审阅计划",
        "",
        f"状态：{plan['status']}；模式：{plan['mode']}",
        "",
        "批准范围包含下列主、子工程写入。待处理项保持原规则；没有跨仓库原子 Git 提交。",
        "",
    ]
    for item in plan["preparation"]:
        lines.append(f"- 待处理 {item['scope']}：{item['reason']}")
    for name, scope in plan["changes"].items():
        lines.extend(
            [
                "",
                f"## {name}",
                "",
                f"代码根：`{scope['path'] or '.'}`；规则目录：`{scope['rulers_dir']}`",
                "",
            ]
        )
        for path, encoded in scope["files"].items():
            action = (
                "删除"
                if encoded is None
                else "修改"
                if (Path(plan["project_root"]) / scope["path"] / path).exists()
                else "新增"
            )
            lines.append(f"- {action} `{path}`")
        for path, encoded in scope["files"].items():
            if path.endswith("/source.json") and encoded is not None:
                packet = json.loads(base64.b64decode(encoded))
                facts = {
                    k: packet[k]
                    for k in (
                        "commands",
                        "evidence",
                        "core_decisions",
                        "profile_scopes",
                    )
                }
                facts["source"] = {
                    k: packet["source"][k]
                    for k in ("head", "dirty", "rulers_dir", "manifest")
                }
                lines.extend(
                    [
                        "",
                        f"### {path}：来源与适用依据",
                        "",
                        "```json",
                        json.dumps(facts, ensure_ascii=False, indent=2),
                        "```",
                    ]
                )
            if path.endswith("/RULERS_STATE.json") and encoded is not None:
                state = json.loads(base64.b64decode(encoded))
                summary = {
                    "policy": state["policy"].get("id"),
                    "profile": state["profile"]["status"],
                    "domains": {
                        d: v.get("level", 0) for d, v in state["domains"].items()
                    },
                    "modules": {
                        n: v.get("phase") for n, v in state.get("modules", {}).items()
                    },
                }
                lines.extend(
                    [
                        "",
                        f"### {path}：批准后状态",
                        "",
                        "```json",
                        json.dumps(summary, ensure_ascii=False, indent=2),
                        "```",
                    ]
                )
            if (not path.endswith(".md") and path != ".gitignore") or "/core/" in path:
                continue
            old = Path(plan["project_root"]) / scope["path"] / path
            before = (
                old.read_bytes().decode("utf-8", errors="backslashreplace")
                if old.is_file()
                else ""
            )
            after = (
                base64.b64decode(encoded).decode("utf-8", errors="backslashreplace")
                if encoded is not None
                else ""
            )
            diff = "".join(
                unified_diff(
                    before.splitlines(keepends=True),
                    after.splitlines(keepends=True),
                    fromfile="current/" + path,
                    tofile="candidate/" + path,
                )
            )
            lines.extend(["", f"### {path}", "", "```diff", diff.rstrip(), "```"])
    lines.extend(
        [
            "",
            "框架 core 和脚本更新按同一 Skill 来源列出；具体正文可从计划 changes 解码核对。State 和来源快照的审阅身份将在应用时记录。",
            "",
        ]
    )
    return "\n".join(lines)
