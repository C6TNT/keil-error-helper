from typing import Dict, Optional

from .classifier import classify_error, load_rules
from .formatter import format_result
from .parser import extract_first_error


def _detect_template_area(file_path: str) -> Optional[Dict[str, object]]:
    file_lower = file_path.replace("\\", "/").lower().lstrip("./")
    if not file_lower:
        return None

    mapping = [
        (
            "app/",
            "业务层（App）",
            [
                "优先检查页面枚举、按键逻辑、参数结构体和 App_Loop",
                "如果你刚替换了某一届示例，先看 app.c 最近改动的那几段",
                "很多综合题问题最后都会落在 App/app.c",
            ],
        ),
        (
            "bsp/",
            "板级驱动层（BSP）",
            [
                "优先检查函数声明和定义是否同步",
                "如果报错在 bsp_seg / bsp_key / bsp_uart，先看头文件原型",
                "这一层通常不需要大改，很多错误来自接口没对齐",
            ],
        ),
        (
            "devices/",
            "设备封装层（Devices）",
            [
                "优先检查器件读写函数参数和返回值",
                "如果是 DS18B20 / DS1302 / 超声波 / 频率问题，先看当前设备文件",
                "这一层更像模块功能实现，不要和页面显示逻辑混改",
            ],
        ),
        (
            "drivers/",
            "底层时序层（Drivers）",
            [
                "优先检查时序驱动函数名、头文件包含和类型定义",
                "这一层建议谨慎修改，新手优先确认是不是真的需要改这里",
                "如果只是赛题业务变化，通常不用先动 Drivers",
            ],
        ),
        (
            "examples/",
            "示例层（Examples）",
            [
                "先确认这是学习示例，不是默认稳定主工程",
                "建议对照对应 .md 说明，再把业务逻辑迁回 App/app.c",
                "如果示例报错，优先检查迁移过程中变量名和页面枚举是否同步",
            ],
        ),
    ]

    for token, area, suggestions in mapping:
        if token in file_lower:
            return {"area": area, "suggestions": suggestions}

    return None


def _detect_template_pitfall(
    error: Optional[Dict[str, str]],
    rule: Optional[Dict],
    template_hint: Optional[Dict],
) -> Optional[Dict[str, object]]:
    if not error:
        return None

    file_path = error.get("file", "").replace("\\", "/").lower()
    rule_id = "" if not rule else rule.get("id", "")

    if "app/" in file_path:
        if rule_id == "too_many_params":
            return {
                "title": "你可能只改了 .c 里的调用，没有同步 .h 里的声明。",
                "tips": [
                    "函数一旦改了参数，调用、声明、定义三处必须一致",
                    "如果你刚从 Examples 迁移代码，优先检查新旧函数原型有没有混用",
                ],
            }
        if rule_id == "undefined_identifier":
            return {
                "title": "你可能删了旧变量，但后面页面函数或按键函数还在用。",
                "tips": [
                    "先全局搜索这个名字是否还被 App_ShowXXXPage 或 App_HandleKey 使用",
                    "删变量之前最好先确认它是不是页面、参数或状态的核心变量",
                ],
            }
        return {
            "title": "业务层最常见的坑是页面、按键、参数没有同步修改。",
            "tips": [
                "新增页面后，要同步改 App_UpdateDisplay 和切页逻辑",
                "新增参数后，要同步改默认值、显示、加减和保存读取",
            ],
        }

    if "bsp/" in file_path:
        return {
            "title": "板级驱动层最常见的坑是接口原型不一致。",
            "tips": [
                "优先检查 .h 里的声明和 .c 里的定义是否完全一致",
                "如果是 bsp_seg 报错，先看参数个数和段码接口是否改乱了",
            ],
        }

    if "devices/" in file_path:
        return {
            "title": "设备层最常见的坑是把采样逻辑和页面逻辑混改。",
            "tips": [
                "Devices 更适合只做器件功能，不要直接写页面显示",
                "优先确认返回值类型和参数有没有改错",
            ],
        }

    if "drivers/" in file_path:
        return {
            "title": "底层驱动层最常见的坑是新手改了不该先改的地方。",
            "tips": [
                "如果只是赛题功能变化，通常先改 App，不要先改 Drivers",
                "真要改 Drivers，先确认是底层接口问题而不是业务逻辑问题",
            ],
        }

    if "examples/" in file_path:
        return {
            "title": "示例层最常见的坑是把学习示例直接当成最终答案使用。",
            "tips": [
                "建议先看对应 .md，再把逻辑迁回 App/app.c",
                "如果示例报错，优先检查变量名、页面枚举和参数结构体是否同步",
            ],
        }

    if template_hint:
        return {
            "title": "先不要同时大改很多地方。",
            "tips": [
                "优先只修第一条错误",
                "修完后重新编译，再看新的第一条错误",
            ],
        }

    return None


def _build_feedback_text(
    error: Optional[Dict[str, str]],
    rule: Optional[Dict],
    template_hint: Optional[Dict],
    pitfall_hint: Optional[Dict],
) -> str:
    if not error:
        return (
            "我这里编译报错了，但工具还没有从这段输出里提取到明确的第一条 error。\n\n"
            "建议我补充：\n"
            "1. 完整的 Keil 编译输出\n"
            "2. 我刚改了哪个文件\n"
            "3. 我是直接改主模板，还是替换了某一届示例代码"
        )

    file_text = error.get("file", "未识别")
    line_text = error.get("line", "未识别")
    raw_text = error.get("raw", "未识别")
    rule_title = "暂未匹配到规则"
    if rule:
        rule_title = str(rule.get("title", rule_title))

    template_area = "暂未定位到模板层"
    template_suggestions = []
    if template_hint:
        template_area = str(template_hint.get("area", template_area))
        template_suggestions = list(template_hint.get("suggestions", []))

    pitfall_title = "暂未识别到额外坑点"
    pitfall_tips = []
    if pitfall_hint:
        pitfall_title = str(pitfall_hint.get("title", pitfall_title))
        pitfall_tips = list(pitfall_hint.get("tips", []))

    checks = []
    if rule:
        checks = list(rule.get("checks", []))

    lines = [
        "我这里编译报错了，整理后的关键信息如下：",
        "",
        f"报错文件：{file_text}",
        f"行号：{line_text}",
        f"第一条错误：{raw_text}",
        f"错误类型：{rule_title}",
        f"模板定位：{template_area}",
        "",
        "建议我先检查：",
    ]

    if checks:
        for index, item in enumerate(checks, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("1. 先只看第一条错误，不要先处理后面的连带报错")
        lines.append("2. 先检查最近修改过的那个文件")

    if template_suggestions:
        lines.append("")
        lines.append("模板层建议我优先看：")
        for index, item in enumerate(template_suggestions[:3], start=1):
            lines.append(f"{index}. {item}")

    lines.extend(
        [
            "",
            f"工具提醒我最可能踩到的坑：{pitfall_title}",
        ]
    )

    if pitfall_tips:
        for index, item in enumerate(pitfall_tips, start=1):
            lines.append(f"{index}. {item}")

    lines.extend(
        [
            "",
            "我刚改的内容：",
            "（这里自己补一句，比如：我刚把某一届示例代码替换进了 App/app.c）",
        ]
    )

    return "\n".join(lines)


def _apply_scene_hint(
    scene: str,
    rule: Optional[Dict],
    template_hint: Optional[Dict],
) -> Optional[Dict[str, object]]:
    if not scene or scene == "none":
        return None

    scene_map = {
        "page": [
            "页面",
            "优先检查页面枚举、切页逻辑和 App_UpdateDisplay 是否同步",
            "如果新增了页面，确认是否补了对应的显示函数和切换入口",
        ],
        "key": [
            "按键",
            "优先检查按键值映射、按键事件函数和当前界面下的按键分支",
            "如果用了单击/双击/长按，确认拿的是对的接口",
        ],
        "param": [
            "参数",
            "优先检查参数默认值、加减逻辑、显示逻辑和保存读取是否同步",
            "参数页报错很容易来自结构体成员名改了但旧代码还在引用",
        ],
        "temp": [
            "温度",
            "优先检查 DS18B20 读取函数、温度变量类型和显示格式",
            "如果是温度报警题，再检查阈值比较逻辑是否同步",
        ],
        "freq": [
            "频率",
            "优先检查频率测量接口、校准值计算和显示位数是否同步",
            "如果题目带 DAC，再检查频率和 DAC 对应关系是否一起改了",
        ],
        "ultra": [
            "超声波",
            "优先检查超声波测距函数、距离变量和运动状态判断逻辑",
            "如果题目带接近/运动状态，别只改显示，记得改判定阈值",
        ],
        "display": [
            "显示",
            "优先检查数码管段码、页面显示函数和显示缓冲区赋值",
            "如果是字符显示问题，先看 SEG 枚举和显示接口参数是否匹配",
        ],
    }

    scene_info = scene_map.get(scene)
    if not scene_info:
        return None

    scene_label = scene_info[0]
    tips = scene_info[1:]
    title = f"你当前选择的是“{scene_label}”场景，建议优先按这个方向排查。"
    if rule and rule.get("id") == "undefined_identifier" and scene in ("page", "param", "display"):
        tips = [
            "这个报错很可能是你改了名字，但页面函数或参数结构体里还有旧名字",
            *tips,
        ]

    if template_hint and template_hint.get("area") == "业务层（App）" and scene in ("page", "key", "param"):
        tips = [
            "当前又定位在 App 层，这通常说明问题就在 app.c 最近改动的那几段",
            *tips,
        ]

    return {"title": title, "tips": tips[:3]}


def _build_cards(
    error: Optional[Dict[str, str]],
    rule: Optional[Dict],
    template_hint: Optional[Dict],
    scene_hint: Optional[Dict[str, object]],
) -> Dict[str, str]:
    if not error:
        return {
            "card_error": "没有识别到第一条明确错误",
            "card_type": "请先确认你粘贴的是完整 Build Output",
            "card_checks": "先检查编译输出里是否真的有 error 行",
            "card_next": "重新复制完整编译输出后再分析",
        }

    error_raw = error.get("raw", "未识别")
    error_type = "暂未匹配到规则"
    checks_text = "先检查最近改动的文件"
    next_text = "先只修第一条错误"

    if rule:
        error_type = str(rule.get("title", error_type))
        checks = list(rule.get("checks", []))
        if checks:
            checks_text = " / ".join(checks[:3])
        next_text = str(rule.get("next_step", next_text))

    if template_hint:
        area = str(template_hint.get("area", ""))
        if area:
            error_type = f"{error_type} | {area}"
    if scene_hint:
        title = str(scene_hint.get("title", ""))
        if title:
            checks_text = f"{checks_text} / {title}"

    return {
        "card_error": error_raw,
        "card_type": error_type,
        "card_checks": checks_text,
        "card_next": next_text,
    }


def _build_priority_hint(
    error: Optional[Dict[str, str]],
    rule: Optional[Dict],
    pitfall_hint: Optional[Dict],
) -> Dict[str, str]:
    if not error:
        return {
            "priority_level": "请补完整编译输出",
            "priority_text": "当前还没有提取到明确的第一条 error，先重新复制完整 Build Output。",
        }

    level = "先修这条"
    text = "这就是你现在最该先修的错误，后面很多报错可能只是它连带出来的。"

    if rule and rule.get("id") in (
        "too_many_params",
        "undefined_identifier",
        "syntax_error",
        "bit_member_struct",
        "unknown_control",
    ):
        level = "高概率问题"
        text = "这类错误通常定位很集中，修掉它之后，后面一串连带报错往往会明显减少。"

    if pitfall_hint:
        text = f"{text} 当前还检测到一个模板常见坑点，建议优先按提示检查。"

    return {"priority_level": level, "priority_text": text}


def analyze_text(text: str, scene: str = "none") -> Dict[str, str]:
    rules = load_rules()
    error = extract_first_error(text)
    rule = classify_error(error, rules) if error else None
    template_hint = _detect_template_area("" if not error else error.get("file", ""))
    pitfall_hint = _detect_template_pitfall(error, rule, template_hint)
    scene_hint = _apply_scene_hint(scene, rule, template_hint)
    report = format_result(error, rule, template_hint, pitfall_hint)
    feedback_text = _build_feedback_text(error, rule, template_hint, pitfall_hint)
    cards = _build_cards(error, rule, template_hint, scene_hint)
    priority_hint = _build_priority_hint(error, rule, pitfall_hint)

    if scene_hint:
        scene_lines = ["", "当前场景加权建议：", f"- {scene_hint['title']}"]
        for item in scene_hint.get("tips", []):
            scene_lines.append(f"- {item}")
        report = report + "\n" + "\n".join(scene_lines)

    return {
        "error_found": "yes" if error else "no",
        "report": report,
        "feedback_text": feedback_text,
        "card_error": cards["card_error"],
        "card_type": cards["card_type"],
        "card_checks": cards["card_checks"],
        "card_next": cards["card_next"],
        "priority_level": priority_hint["priority_level"],
        "priority_text": priority_hint["priority_text"],
        "error_code": "" if not error else error.get("code", ""),
        "error_file": "" if not error else error.get("file", ""),
        "error_line": "" if not error else error.get("line", ""),
        "rule_id": "" if not rule else rule.get("id", ""),
        "template_area": "" if not template_hint else str(template_hint.get("area", "")),
        "pitfall_title": "" if not pitfall_hint else str(pitfall_hint.get("title", "")),
        "scene_title": "" if not scene_hint else str(scene_hint.get("title", "")),
    }
