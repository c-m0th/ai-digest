"""
fetchers/youtube.py — 抓取 YouTube 频道最新视频及字幕

策略：
1. 通过 YouTube 频道的 RSS Feed 获取最新视频列表（无需 API Key）
2. 用 youtube-transcript-api 提取字幕
3. 无字幕时返回视频描述作为备用
"""
from __future__ import annotations

import re
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from src.utils.logger import get_logger
from src.utils.database import is_processed

logger = get_logger("youtube")

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def _get_video_id(url: str) -> str | None:
    match = re.search(r"[?&]v=([^&]+)", url)
    return match.group(1) if match else None


def _get_transcript(video_id: str) -> str | None:
    """尝试获取字幕，优先中文，其次英文"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # 优先手动字幕，再自动生成
        for lang in ["zh-Hans", "zh", "en"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                segments = transcript.fetch()
                return " ".join(s["text"] for s in segments)
            except Exception:
                continue
        # 兜底：任意语言
        transcript = next(iter(transcript_list))
        segments = transcript.fetch()
        return " ".join(s["text"] for s in segments)
    except (NoTranscriptFound, TranscriptsDisabled):
        logger.warning(f"[YouTube] 视频 {video_id} 无字幕")
        return None
    except Exception as e:
        logger.warning(f"[YouTube] 字幕获取失败 {video_id}: {e}")
        return None


def fetch_channel(channel_config: dict, days_lookback: int, max_items: int) -> list[dict]:
    """
    抓取频道最新视频
    Returns: list of content dicts
    """
    channel_id = channel_config["channel_id"]
    name = channel_config["name"]
    results = []

    rss_url = YOUTUBE_RSS.format(channel_id=channel_id)
    feed = feedparser.parse(rss_url)

    if not feed.entries:
        logger.warning(f"[YouTube] {name} 无法获取 RSS，跳过")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback + 1)
    count = 0

    for entry in feed.entries:
        if count >= max_items:
            break

        video_url = entry.get("link", "")
        video_id = _get_video_id(video_url)
        if not video_id:
            continue

        # 检查发布时间
        published = entry.get("published_parsed")
        if published:
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue

        # 去重
        if is_processed(video_url):
            logger.info(f"[YouTube] 已处理，跳过: {entry.get('title', '')}")
            continue

        logger.info(f"[YouTube] 处理: {entry.get('title', '')} ({name})")

        transcript = _get_transcript(video_id)
        description = entry.get("summary", "")

        content_text = transcript or description or ""
        if not content_text.strip():
            continue

        # 提取缩略图
        thumbnail = ""
        media = entry.get("media_thumbnail", [])
        if media:
            thumbnail = media[0].get("url", "")

        results.append({
            "platform": "YouTube",
            "source_name": name,
            "title": entry.get("title", "无标题"),
            "url": video_url,
            "thumbnail": thumbnail,
            "published": entry.get("published", ""),
            "content": content_text,
            "content_type": "video_transcript" if transcript else "description",
        })
        count += 1

    logger.info(f"[YouTube] {name} 获取 {len(results)} 条")
    return results
