import json
import os
import urllib.error
import urllib.request


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

请固定按下面 3 段输出：
1. 这条错误更像什么问题
2. 你应该先看哪几处
3. 如果你刚在改某个模块，最可能漏改哪里
"""


def ai_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


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


def run_ai_analysis(payload_json: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AIConfigError(
            "当前还没有配置 OPENAI_API_KEY，所以现在只能查看 AI 预览，不能调用真实 AI。"
        )

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("KEIL_ERROR_HELPER_OPENAI_MODEL", "gpt-5.2")

    user_prompt = (
        "请根据下面结构化错误信息，给出适合蓝桥杯单片机新手的深入分析。\n\n"
        f"{payload_json}"
    )

    body = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": user_prompt,
        "text": {"verbosity": "low"},
        "reasoning": {"effort": "none"},
    }

    req = urllib.request.Request(
        url=f"{base_url}/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise AIRequestError(f"AI 请求失败（HTTP {exc.code}）。\n\n{details}") from exc
    except urllib.error.URLError as exc:
        raise AIRequestError(f"AI 请求失败，网络不可用或服务不可达：{exc}") from exc
    except Exception as exc:
        raise AIRequestError(f"AI 请求过程中发生异常：{exc}") from exc

    result = _extract_output_text(response_data)
    return f"AI 深入分析结果\n模型：{model}\n\n{result}"
