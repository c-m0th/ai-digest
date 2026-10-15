"""多 API 摘要：独立进程硬超时、批次预算、失败接口熔断及内容快照。"""
import json
import multiprocessing
import os
import re
import time
from pathlib import Path

import requests
from src.utils.logger import get_logger

logger = get_logger("summarizer")

PROVIDERS = [
    {"name": "DeepSeek", "env_key": "DEEPSEEK_API_KEY", "type": "openai_compat",
     "model": "deepseek-chat", "model_env": "DEEPSEEK_MODEL",
     "base_url": "https://api.deepseek.com/v1"},
    {"name": "Gemini", "env_key": "GEMINI_API_KEY", "type": "gemini",
     "model": "gemini-3.8-flash", "model_env": "GEMINI_MODEL"},
    {"name": "Claude", "env_key": "ANTHROPIC_API_KEY", "type": "claude",
     "model": "claude-sonnet-4-20250514", "model_env": "ANTHROPIC_MODEL"},
    {"name": "GPT-4o-mini", "env_key": "OPENAI_API_KEY", "type": "openai_compat",
     "model": "gpt-4o-mini", "model_env": "OPENAI_MODEL",
     "base_url": "https://api.openai.com/v1"},
    {"name": "Groq", "env_key": "GROQ_API_KEY", "type": "openai_compat",
     "model": "llama-3.3-70b-versatile", "model_env": "GROQ_MODEL",
     "base_url": "https://api.groq.com/openai/v1"},
]


def _seconds(name, default, minimum, maximum):
    try:
        value = float(os.environ.get(name, default))
        if not minimum <= value <= maximum:
            raise ValueError
        return value
    except (ValueError, TypeError):
        logger.warning("[%s] 数值无效，使用默认值 %s", name, default)
        return float(default)


def _get_available_providers():
    """有非空密钥只表示已配置，不代表认证或模型已经测试成功。"""
    available = []
    for config in PROVIDERS:
        key = os.environ.get(config["env_key"], "").strip()
        if not key or key.lower() in {"***", "your-api-key", "your_api_key"}:
            continue
        provider = dict(config)
        provider["model"] = os.environ.get(config["model_env"], "").strip() or config["model"]
        available.append(provider)
    logger.info("[Summarizer] 已配置 providers（尚未验证）: %s", [p["name"] for p in available])
    return available


class ProviderResponseError(RuntimeError):
    """错误信息只包含安全的类别，不带原始响应、URL 或密钥。"""


def _response_json(response):
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        raise ProviderResponseError("invalid_json") from None
    if not isinstance(payload, dict):
        raise ProviderResponseError("invalid_response_type")
    if payload.get("error"):
        # 不记录原始错误消息，避免网关在消息中回显凭证或请求正文。
        raise ProviderResponseError("api_error_payload")
    return payload


def _call_openai_compat(api_key, base_url, model, prompt):
    with requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 1000},
        timeout=(10, 60),
    ) as response:
        payload = _response_json(response)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderResponseError("missing_choices")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ProviderResponseError("empty_content")
    return content.strip()


def _call_gemini(api_key, model, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with requests.post(
        url, headers={"x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 2048}},
        timeout=(10, 60),
    ) as response:
        payload = _response_json(response)
    candidates = payload.get("candidates") or []
    if not candidates or not isinstance(candidates[0], dict):
        raise ProviderResponseError("missing_candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    result = "\n".join(p["text"] for p in parts if isinstance(p, dict)
                       and isinstance(p.get("text"), str) and not p.get("thought")).strip()
    if not result:
        raise ProviderResponseError("empty_content")
    return result


def _call_claude(api_key, model, prompt):
    import anthropic
    with anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=0) as client:
        response = client.messages.create(
            model=model, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
    text = "\n".join(block.text for block in response.content
                     if getattr(block, "type", "") == "text").strip()
    if not text:
        raise ProviderResponseError("empty_content")
    return text


def _call_provider(provider, prompt):
    key = os.environ.get(provider["env_key"], "").strip()
    if not key:
        raise ProviderResponseError("missing_api_key")
    if provider["type"] == "openai_compat":
        return _call_openai_compat(key, provider["base_url"], provider["model"], prompt)
    if provider["type"] == "gemini":
        return _call_gemini(key, provider["model"], prompt)
    if provider["type"] == "claude":
        return _call_claude(key, provider["model"], prompt)
    raise ProviderResponseError("unknown_provider_type")


def _provider_worker(connection, provider, prompt):
    try:
        result = _call_provider(provider, prompt)
        connection.send({"ok": True, "text": result})
    except Exception as exc:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None) or getattr(exc, "status_code", None)
        detail = str(exc) if isinstance(exc, ProviderResponseError) else "request_failed"
        connection.send({"ok": False, "error": type(exc).__name__,
                         "status": status, "detail": detail})
    finally:
        connection.close()


def _run_provider(provider, prompt, timeout_seconds):
    """主进程计时；即使服务器持续发送心跳，也会终止超时子进程。"""
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_provider_worker, args=(sender, provider, prompt), daemon=True)
    started = time.monotonic()
    try:
        process.start()
        sender.close()
        remaining = max(0, timeout_seconds - (time.monotonic() - started))
        if not receiver.poll(remaining):
            return {"ok": False, "error": "HardTimeout", "status": None,
                    "detail": "provider_deadline_exceeded"}
        result = receiver.recv()
        if not isinstance(result, dict) or "ok" not in result:
            raise ValueError("invalid_worker_result")
        return result
    except (EOFError, OSError, ValueError):
        return {"ok": False, "error": "WorkerError", "status": None,
                "detail": "worker_failed"}
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            if not process.is_alive():
                process.close()


PROMPTS = {
    "video_transcript": """你是深度学习/AI领域的学术内容助理，请总结以下YouTube视频字幕（中文输出）：
标题：{title} | 频道：{source_name}
内容：{content}

**🎯 核心论点**（3条）
**🔧 技术方法**（2条）
**💡 关键洞察**（2条）
**📌 一句话总结**""",

    "article": """你是深度学习/AI领域的学术内容助理，请总结以下文章（中文输出）：
标题：{title} | 来源：{source_name}
内容：{content}

**🎯 核心观点**（3条）
**📊 主要论据**（2条）
**💡 对从业者的启示**（1条）
**📌 一句话总结**""",

    "paper_abstract": """你是AI研究助理，请解读以下论文摘要（中文输出）：
标题：{title}
内容：{content}

**🔬 研究问题**
**🛠 方法创新**（2条）
**📈 主要结果**
**🌟 意义与影响**""",

    "podcast_summary": """请总结以下播客节目（中文输出）：
标题：{title} | 播客：{source_name}
说明：{content}

**🎙 话题与嘉宾**
**🔑 核心议题**（3条）
**💡 值得收听的理由**""",

    "hn_post": """请简要说明以下HN帖子的内容和价值（中文，2-3句话）：
标题：{title}
内容：{content}""",

    "description": """根据以下YouTube视频描述推断内容，写2-3句中文摘要：
标题：{title} | 频道：{source_name}
描述：{content}""",
}


def _fallback(item, reason):
    item["summary_success"] = False
    return (f"AI 摘要暂不可用（{reason}）。以下是原始内容节选，不是 AI 总结：\n\n"
            + (item.get("content", "")[:1800] or "请通过原文链接查看内容。"))


def summarize(item, max_content_chars=12000, language_hint="", *,
              _providers=None, _disabled=None, _deadline=None):
    item["summary_success"] = False
    providers = _get_available_providers() if _providers is None else _providers
    disabled = {} if _disabled is None else _disabled
    per_call = _seconds("AI_CALL_TIMEOUT_SECONDS", 90, 5, 300)
    template = PROMPTS.get(item.get("content_type", "article"), PROMPTS["article"])
    prompt = template.format(title=item.get("title", ""), source_name=item.get("source_name", ""),
                             content=item.get("content", "")[:max_content_chars])
    if language_hint:
        prompt += "\n\n输出要求：" + language_hint
    for provider in providers:
        if provider["name"] in disabled:
            continue
        remaining = per_call if _deadline is None else min(per_call, _deadline - time.monotonic())
        if remaining <= 0:
            return _fallback(item, "本轮 AI 时间预算已用完")
        started = time.monotonic()
        logger.info("[Summarizer] 使用 %s / %s，单次总时限 %.0fs",
                    provider["name"], provider["model"], remaining)
        result = _run_provider(provider, prompt, remaining)
        if result.get("ok") and isinstance(result.get("text"), str) and result["text"].strip():
            item["summary_success"] = True
            item["summary_provider"] = provider["name"]
            logger.info("[%s] 摘要完成，耗时 %.1fs", provider["name"], time.monotonic() - started)
            return result["text"].strip()
        # 本轮熔断，下一次 batch_summarize 会重新尝试；避免逐篇重复失败请求。
        disabled[provider["name"]] = result.get("error", "EmptyResult")
        logger.warning("[%s] 本轮停用：%s，HTTP=%s，原因=%s，耗时 %.1fs",
                       provider["name"], result.get("error", "EmptyResult"),
                       result.get("status"), result.get("detail", "empty_result"),
                       time.monotonic() - started)
    return _fallback(item, "所有已配置接口均不可用，等待下一轮重试")


def _save_checkpoint(items, checkpoint_path):
    path = Path(checkpoint_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        logger.warning("[Summarizer] 内容快照保存失败：%s", type(exc).__name__)


def batch_summarize(items, settings, checkpoint_path=None):
    if checkpoint_path is None:
        checkpoint_path = Path(__file__).resolve().parents[2] / "data" / "digest_snapshot.json"
    budget = _seconds("AI_BATCH_TIMEOUT_SECONDS", 600, 30, 1200)
    deadline = time.monotonic() + budget
    providers = _get_available_providers()
    disabled = {}
    _save_checkpoint(items, checkpoint_path)
    for i, item in enumerate(items, 1):
        logger.info("[Summarizer] %s/%s: %s", i, len(items), item.get("title", "")[:50])
        item["summary"] = summarize(
            item, settings.get("max_content_chars", 12000), settings.get("language_hint", ""),
            _providers=providers, _disabled=disabled, _deadline=deadline,
        )
        _save_checkpoint(items, checkpoint_path)
    successful = sum(bool(item.get("summary_success")) for item in items)
    logger.info("[Summarizer] AI 成功 %s/%s，其余条目保留原始内容", successful, len(items))
    return items
 
