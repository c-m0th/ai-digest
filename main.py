#!/usr/bin/env python3
"""
main.py — AI Daily Digest 入口

用法:
  python main.py --run-now          # 立即运行一次
  python main.py --schedule         # 按配置时间每天定时运行
  python main.py --dry-run          # 只抓取不发邮件（调试用）
  python main.py --preview          # 生成 preview.html 本地预览
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import schedule
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 把项目根目录加入 sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.fetchers.youtube import fetch_channel
from src.fetchers.rss import fetch_blog, fetch_podcast, fetch_arxiv
from src.fetchers.hackernews import fetch_hn
from src.processors.summarizer import batch_summarize, _get_available_providers
from src.processors.email_sender import send_email, render_email
from src.utils.database import init_db, mark_delivered, record_run, get_recent_fingerprints
from src.utils.dedup import deduplicate_items
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger("main")

CONFIG_PATH = ROOT / "config" / "sources.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        example = ROOT / "config" / "sources.example.yaml"
        if example.exists():
            import shutil
            shutil.copy(example, CONFIG_PATH)
            logger.info(f"已从示例文件创建配置: {CONFIG_PATH}")
        else:
            raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_all(config: dict) -> list[dict]:
    """从所有来源抓取内容"""
    settings = config.get("settings", {})
    days = settings.get("days_lookback", 1)
    max_items = settings.get("max_items_per_source", 5)
    all_items = []

    # ── YouTube ──────────────────────────────
    for ch in config.get("youtube", []):
        try:
            items = fetch_channel(ch, days_lookback=days, max_items=max_items)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[YouTube] {ch.get('name')} 抓取异常: {e}")

    # ── 博客 / Substack / Medium ─────────────
    for src in config.get("rss_blogs", []):
        try:
            items = fetch_blog(src, days_lookback=days, max_items=max_items)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[Blog] {src.get('name')} 抓取异常: {e}")

    # ── 播客 ─────────────────────────────────
    for src in config.get("podcasts", []):
        try:
            items = fetch_podcast(src, days_lookback=days, max_items=1)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[Podcast] {src.get('name')} 抓取异常: {e}")

    # ── ArXiv ─────────────────────────────────
    for src in config.get("arxiv", []):
        try:
            items = fetch_arxiv(src, days_lookback=days)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[ArXiv] {src.get('name')} 抓取异常: {e}")

    # ── Hacker News ───────────────────────────
    hn_config = config.get("hackernews", {})
    if hn_config.get("enabled", False):
        try:
            items = fetch_hn(hn_config, days_lookback=days)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[HN] 抓取异常: {e}")

    logger.info(f"[Main] 共抓取到 {len(all_items)} 条新内容")
    return all_items


def run(dry_run: bool = False, preview: bool = False):
    """主流程"""
    logger.info("=" * 50)
    logger.info("🚀 AI Daily Digest 开始运行")
    logger.info("=" * 50)

    # 检查 API Key
    if not _get_available_providers():
        logger.error("未配置有效的非空 API Key，请至少配置一个摘要服务。")
        sys.exit(1)

    config = load_config()
    settings = config.get("settings", {})
    init_db(days=settings.get("dedup_days", 3))

    # 1. 抓取
    items = fetch_all(config)
    if not items:
        logger.info("📭 今日没有新内容，任务结束")
        return

    # 去重放在所有模型调用之前：当天跨源重复 + 最近三天已投递内容。
    items, dedup_stats = deduplicate_items(items, get_recent_fingerprints())
    logger.info("[Dedup] 候选 %s 条，当天重复 %s 条，近期已推送 %s 条，保留 %s 条",
                dedup_stats["input"], dedup_stats["same_batch"],
                dedup_stats["recent"], dedup_stats["kept"])
    if not items:
        logger.info("[Dedup] 全部是重复内容，本轮无需 AI 摘要或发送邮件")
        record_run(0, False)
        return

    # 2. AI 总结
    logger.info(f"🤖 开始 AI 总结 {len(items)} 条内容...")
    items = batch_summarize(items, settings)

    # 3. 发邮件 / 预览
    if preview:
        html = render_email(items)
        preview_path = ROOT / "preview.html"
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"🖥  预览文件已生成: {preview_path}")

    email_sent = False
    if not dry_run and not preview:
        email_sent = send_email(items)
    elif dry_run:
        logger.info("🔍 [Dry Run] 跳过发送邮件")

    # 已发送的原文节选也算已推送，避免模型失败时每天重发同一篇。
    # 发信失败、预览和 dry-run 不写投递历史。
    if email_sent:
        mark_delivered(items)

    # 5. 记录运行
    record_run(len(items), email_sent)

    logger.info(f"✅ 任务完成！处理 {len(items)} 条，邮件{'已发送' if email_sent else '未发送'}")


def main():
    parser = argparse.ArgumentParser(description="AI Daily Digest — 每日学术摘要助理")
    parser.add_argument("--run-now", action="store_true", help="立即运行一次")
    parser.add_argument("--schedule", action="store_true", help="每天定时运行")
    parser.add_argument("--dry-run", action="store_true", help="运行但不发邮件")
    parser.add_argument("--preview", action="store_true", help="生成本地预览 HTML")
    parser.add_argument("--time", default="08:00", help="定时运行时间，格式 HH:MM（默认 08:00）")
    args = parser.parse_args()

    if args.run_now or args.dry_run or args.preview:
        run(dry_run=args.dry_run, preview=args.preview)

    elif args.schedule:
        logger.info(f"⏰ 定时模式启动，每天 {args.time} 运行")
        schedule.every().day.at(args.time).do(run)
        # 启动时也先跑一次
        run()
        while True:
            schedule.run_pending()
            time.sleep(30)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
