import json
import os
import urllib.error
import urllib.request
import re

try:
    from core.config_store import DEFAULT_BASE_URL, DEFAULT_MODEL, load_ai_config
except ModuleNotFoundError:
    from .config_store import DEFAULT_BASE_URL, DEFAULT_MODEL, load_ai_config


class AIClientError(Exception):
    pass


class AIConfigError(AIClientError):
    pass


class AIRequestError(AIClientError):
    pass


SYSTEM_PROMPT = """你是一个面向蓝桥杯单片机新手的 Keil/C51 报错诊断助手。
你已经拿到了本地规则引擎整理好的结构化错误信息。
你的任务不是重复解释所有内容，而是：
1. 用更容易懂的话说明这条错误大概是什么意思。
2. 结合当前场景（页面、按键、参数、温度、频率、超声波、显示）给出更贴近比赛代码的排查建议。
3. 明确告诉用户先看哪一段、先做哪一步。
4. 输出尽量简洁，不要泛泛而谈，不要长篇背景解释。
5. 如果信息不够，不要编造，明确指出还缺什么。
6. 如果输入里附带了报错附近代码，优先结合代码片段来判断，而不是只泛泛解释错误码。
7. 不要编造不存在的函数、变量或行号。

请固定按下面 3 段输出：
1. 这条错误更像什么问题
2. 你应该先看哪几处
3. 如果你刚在改某个模块，最可能漏改哪里

每一段尽量控制在 2 到 4 句内，直接说重点。
"""


SECTION_PATTERNS = {
    "problem": [
        "1. 这条错误更像什么问题",
        "一、这条错误更像什么问题",
        "这条错误更像什么问题",
    ],
    "checks": [
        "2. 你应该先看哪几处",
        "二、你应该先看哪几处",
        "你应该先看哪几处",
    ],
    "miss": [
        "3. 如果你刚在改某个模块，最可能漏改哪里",
        "三、如果你刚在改某个模块，最可能漏改哪里",
        "如果你刚在改某个模块，最可能漏改哪里",
    ],
}


def get_runtime_ai_config() -> dict:
    """Resolve runtime config from local file first, then environment fallback."""
    file_config = load_ai_config()
    return {
        "api_key": file_config.get("api_key", "").strip() or os.getenv("OPENAI_API_KEY", "").strip(),
        "base_url": file_config.get("base_url", "").strip()
        or os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip()
        or DEFAULT_BASE_URL,
        "model": file_config.get("model", "").strip()
        or os.getenv("KEIL_ERROR_HELPER_OPENAI_MODEL", DEFAULT_MODEL).strip()
        or DEFAULT_MODEL,
    }


def ai_is_configured() -> bool:
    return bool(get_runtime_ai_config()["api_key"])


def _extract_output_text(response_data: dict) -> str:
    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts = []
    for item in response_data.get("output", []):
        for content in item.get("content", []):
            if "text" in content and isinstance(content["text"], str):
                texts.append(content["text"])
            elif "text" in content and isinstance(content["text"], dict):
                value = content["text"].get("value", "")
                if value:
                    texts.append(value)

    merged = "\n".join(part.strip() for part in texts if part.strip()).strip()
    if merged:
        return merged

    raise AIRequestError("AI 已返回结果，但当前版本没有成功解析出文本内容。")


def _normalize_heading(text: str) -> str:
    return re.sub(r"^[\s\-•*\d一二三四五六七八九十、.．()（）]+", "", text.strip())


NORMALIZED_SECTION_PATTERNS = {
    key: [_normalize_heading(pattern) for pattern in patterns]
    for key, patterns in SECTION_PATTERNS.items()
}

SECTION_REGEXES = {
    "problem": re.compile(r"^\s*(1|一)[、.．)\]）]?\s*"),
    "checks": re.compile(r"^\s*(2|二)[、.．)\]）]?\s*"),
    "miss": re.compile(r"^\s*(3|三)[、.．)\]）]?\s*"),
}


def _split_ai_sections(raw_text: str) -> dict:
    sections = {
        "problem": "",
        "checks": "",
        "miss": "",
    }
    current_key = ""

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        normalized = _normalize_heading(stripped)
        matched_key = None

        for key, regex in SECTION_REGEXES.items():
            if regex.match(stripped):
                matched_key = key
                break

        if not matched_key:
            for key, patterns in NORMALIZED_SECTION_PATTERNS.items():
                for pattern in patterns:
                    if normalized.startswith(pattern):
                        matched_key = key
                        break
                if matched_key:
                    break

        if matched_key:
            current_key = matched_key
            content_after_title = stripped
            content_after_title = SECTION_REGEXES.get(matched_key, re.compile(r"$")).sub("", content_after_title, count=1).strip()
            for pattern in NORMALIZED_SECTION_PATTERNS[matched_key]:
                if _normalize_heading(content_after_title).startswith(pattern):
                    content_after_title = ""
                    break
            if content_after_title:
                sections[current_key] = content_after_title
            continue

        if current_key:
            if sections[current_key]:
                sections[current_key] += "\n" + stripped
            else:
                sections[current_key] = stripped

    return sections


def _format_ai_sections(raw_text: str) -> str:
    sections = _split_ai_sections(raw_text)

    if not any(sections.values()):
        cleaned = raw_text.strip()
        return (
            "AI 深入分析结果\n\n"
            "学长版回复整理：\n"
            f"{cleaned}"
        )

    def ensure_text(value: str, fallback: str) -> str:
        return value.strip() or fallback

    problem = ensure_text(sections["problem"], "AI 没有明确展开这一段，建议先按第一条错误附近继续排查。")
    checks = ensure_text(sections["checks"], "AI 没有明确列出检查点，建议先看报错文件、对应头文件和最近改动处。")
    miss = ensure_text(sections["miss"], "AI 没有明确指出漏改点，建议先检查声明、定义、调用和页面逻辑是否同步。")

    return (
        "AI 深入分析结果\n\n"
        "1. 这条错误更像什么问题\n"
        f"{problem}\n\n"
        "2. 你应该先看哪几处\n"
        f"{checks}\n\n"
        "3. 如果你刚在改某个模块，最可能漏改哪里\n"
        f"{miss}"
    )


def build_ai_cards(raw_text: str) -> dict:
    sections = _split_ai_sections(raw_text)

    return {
        "problem": sections["problem"].strip() or "AI 暂时没有单独提炼出这一段，建议先看完整结果。",
        "checks": sections["checks"].strip() or "AI 暂时没有明确列出检查点，建议先看报错文件、头文件和最近改动处。",
        "miss": sections["miss"].strip() or "AI 暂时没有明确指出漏改点，建议先检查声明、定义、调用和页面逻辑是否同步。",
    }


def _post_json(path: str, body: dict) -> dict:
    config = get_runtime_ai_config()
    api_key = config["api_key"]
    if not api_key:
        raise AIConfigError("当前还没有在应用里配置 API Key。")

    base_url = config["base_url"].rstrip("/")
    req = urllib.request.Request(
        url=f"{base_url}/{path.lstrip('/')}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise AIRequestError(f"AI 请求失败（HTTP {exc.code}）。\n\n{details}") from exc
    except urllib.error.URLError as exc:
        raise AIRequestError(f"AI 请求失败，网络不可用或服务不可达：{exc}") from exc
    except Exception as exc:
        raise AIRequestError(f"AI 请求过程中发生异常：{exc}") from exc


def test_ai_connection() -> str:
    """Run a tiny request to confirm API key/base URL/model are usable."""
    config = get_runtime_ai_config()
    if not config["api_key"]:
        raise AIConfigError("当前还没有在应用里配置 API Key。")

    body = {
        "model": config["model"],
        "input": "Reply with OK only.",
        "text": {"verbosity": "low"},
        "reasoning": {"effort": "none"},
    }

    response_data = _post_json("responses", body)
    result_text = _extract_output_text(response_data)
    return (
        "AI 连接测试成功\n"
        f"Base URL：{config['base_url']}\n"
        f"Model：{config['model']}\n"
        f"返回结果：{result_text}"
    )


def run_ai_analysis(payload_json: str) -> str:
    config = get_runtime_ai_config()
    if not config["api_key"]:
        raise AIConfigError(
            "当前还没有在应用里配置 API Key，所以现在只能查看 AI 预览，不能调用真实 AI。"
        )

    body = {
        "model": config["model"],
        "instructions": SYSTEM_PROMPT,
        "input": "请根据下面结构化错误信息，给出适合蓝桥杯单片机新手的深入分析。\n\n"
        f"{payload_json}",
        "text": {"verbosity": "low"},
        "reasoning": {"effort": "none"},
    }

    response_data = _post_json("responses", body)
    result = _extract_output_text(response_data)
    formatted_result = _format_ai_sections(result)
    return (
        f"AI 深入分析\n"
        f"模型：{config['model']}\n"
        "说明：下面是基于规则分析 + 你提供的上下文生成的辅助建议，优先还是先修第一条错误。\n\n"
        f"{formatted_result}"
    )
