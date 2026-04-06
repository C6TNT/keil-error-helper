from typing import Dict, List, Optional


def _format_list(title: str, items: List[str]) -> List[str]:
    lines: List[str] = []
    if not items:
        return lines

    lines.append(title)
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return lines


def format_result(
    error: Optional[Dict[str, str]],
    rule: Optional[Dict],
    template_hint: Optional[Dict],
    pitfall_hint: Optional[Dict],
) -> str:
    if not error:
        return (
            "没有识别到明确的 Keil error。\n\n"
            "建议：\n"
            "1. 确认你粘贴的是完整编译输出\n"
            "2. 确认输出里真的包含 error 行\n"
            "3. 如果只有 warning，请先看是否已经 0 error"
        )

    lines: List[str] = []
    lines.append("第一条关键错误")
    lines.append(error.get("raw", ""))
    lines.append("")

    if error.get("file"):
        lines.append(f"文件：{error['file']}")
    if error.get("line"):
        lines.append(f"行号：{error['line']}")
    if error.get("code"):
        lines.append(f"错误码：{error['code']}")

    if not rule:
        lines.append("")
        lines.append("暂未命中内置规则。")

        if template_hint:
            lines.append("")
            lines.append("模板定位建议：")
            lines.append(f"- 当前更像是 {template_hint['area']} 的问题")
            for item in template_hint.get("suggestions", []):
                lines.append(f"- {item}")

        if pitfall_hint:
            lines.append("")
            lines.append("模板常见坑点提醒：")
            lines.append(f"- {pitfall_hint['title']}")
            for item in pitfall_hint.get("tips", []):
                lines.append(f"- {item}")

        lines.append("")
        lines.append("建议：先检查最近改动的代码，并优先处理第一条 error。")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"错误类型：{rule['title']}")
    lines.append(f"解释：{rule['summary']}")
    lines.append("")
    lines.extend(_format_list("最可能原因：", rule.get("causes", [])))
    lines.extend(_format_list("建议先检查：", rule.get("checks", [])))

    if template_hint:
        lines.append("模板定位建议：")
        lines.append(f"- 当前更像是 {template_hint['area']} 的问题")
        for item in template_hint.get("suggestions", []):
            lines.append(f"- {item}")
        lines.append("")

    if pitfall_hint:
        lines.append("模板常见坑点提醒：")
        lines.append(f"- {pitfall_hint['title']}")
        for item in pitfall_hint.get("tips", []):
            lines.append(f"- {item}")
        lines.append("")

    lines.append(f"下一步：{rule.get('next_step', '')}")
    return "\n".join(lines)
