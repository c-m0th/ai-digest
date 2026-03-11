"""
processors/summarizer.py — 用 Claude API 总结内容
"""
from __future__ import annotations

import os
import anthropic
from src.utils.logger import get_logger

logger = get_logger("summarizer")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# 每种内容类型的提示词模板
PROMPTS = {
    "video_transcript": """你是一个深度学习/AI领域的学术内容助理。
请对以下YouTube视频字幕进行结构化总结，用中文输出：

视频标题：{title}
频道：{source_name}
字幕内容：{content}

请严格按以下格式输出（每项不超过3条）：

**🎯 核心论点**
- ...

**🔧 技术方法/工具**
- ...

**💡 关键洞察**
- ...

**📌 一句话总结**
（用一句话说明为什么值得看这个视频）""",

    "description": """你是一个AI内容助理。
请根据以下YouTube视频描述，推断视频内容并写一个简短摘要：

视频标题：{title}
频道：{source_name}
描述：{content}

请用中文写2-3句话的摘要，说明视频可能涵盖的内容和价值。""",

    "article": """你是一个深度学习/AI领域的学术内容助理。
请对以下文章进行结构化总结，用中文输出：

文章标题：{title}
来源：{source_name}
文章内容：{content}

请严格按以下格式输出：

**🎯 核心观点**
- ...（最多3条）

**📊 主要论据/数据**
- ...（最多2条）

**💡 对从业者的启示**
- ...（1-2条）

**📌 一句话总结**
（这篇文章最重要的一个takeaway）""",

    "paper_abstract": """你是一个深度学习/AI领域的研究助理。
请对以下论文摘要进行解读，用中文输出：

论文标题：{title}
来源：{source_name}
摘要：{content}

请严格按以下格式输出：

**🔬 研究问题**
（这篇论文解决什么问题？1句话）

**🛠 方法创新**
- ...（1-2条核心方法创新点）

**📈 主要结果**
- ...（关键实验结果或性能提升）

**🌟 意义与影响**
（为什么这篇论文值得关注？1-2句话）""",

    "podcast_summary": """你是一个AI内容助理。
请根据以下播客节目说明，写一个摘要：

节目标题：{title}
播客：{source_name}
节目说明：{content}

请用中文输出：

**🎙 嘉宾与话题**
（主要嘉宾和讨论话题）

**🔑 核心议题**
- ...（2-3个主要讨论点）

**💡 值得收听的理由**
（1句话）""",

    "podcast_transcript": """你是一个AI内容助理。
请对以下播客转录文字进行总结：

节目标题：{title}
播客：{source_name}
转录内容：{content}

请用中文按以下格式输出：

**🎯 核心讨论主题**
- ...（3条）

**💬 关键观点**
- ...（3-4条最值得记录的观点）

**📌 一句话总结**""",

    "hn_post": """你是一个AI内容助理。
请对以下Hacker News帖子进行简短说明：

标题：{title}
内容：{content}

请用中文写2-3句话，说明这个帖子讨论的内容和为什么值得关注。""",
}

DEFAULT_PROMPT = PROMPTS["article"]


def summarize(item: dict, max_content_chars: int = 12000, language_hint: str = "") -> str:
    """
    调用 Claude API 总结单条内容
    Returns: 总结文字
    """
    content_type = item.get("content_type", "article")
    prompt_template = PROMPTS.get(content_type, DEFAULT_PROMPT)

    # 截断内容避免超出 token 限制
    content = item.get("content", "")[:max_content_chars]

    prompt = prompt_template.format(
        title=item.get("title", ""),
        source_name=item.get("source_name", ""),
        content=content,
    )

    if language_hint:
        prompt += f"\n\n（输出语言提示：{language_hint}）"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except anthropic.RateLimitError:
        logger.warning("[Summarizer] 触发 Rate Limit，等待 30s 后重试...")
        import time
        time.sleep(30)
        return summarize(item, max_content_chars, language_hint)
    except Exception as e:
        logger.error(f"[Summarizer] Claude API 调用失败: {e}")
        return f"（总结失败：{str(e)}）"


def batch_summarize(items: list[dict], settings: dict) -> list[dict]:
    """批量总结，结果写入 item['summary']"""
    max_chars = settings.get("max_content_chars", 12000)
    lang = settings.get("language_hint", "")
    total = len(items)

    for i, item in enumerate(items, 1):
        logger.info(f"[Summarizer] 总结 {i}/{total}: {item['title'][:50]}...")
        item["summary"] = summarize(item, max_chars, lang)

    return items
