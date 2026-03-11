"""
processors/email_sender.py — 渲染并发送摘要邮件
"""
from __future__ import annotations

import os
import smtplib
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.utils.logger import get_logger

logger = get_logger("email")

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

PLATFORM_ICONS = {
    "YouTube": "🎬",
    "Blog/Newsletter": "📝",
    "ArXiv": "📄",
    "Podcast": "🎙",
    "Hacker News": "🔶",
    "Hacker News AI": "🔶",
}

PLATFORM_BADGE_CLASS = {
    "YouTube": "youtube",
    "Blog/Newsletter": "blog",
    "ArXiv": "arxiv",
    "Podcast": "podcast",
    "Hacker News": "hn",
}


def _group_by_platform(items: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for item in items:
        grouped[item["platform"]].append(item)
    return dict(grouped)


def render_email(items: list[dict]) -> str:
    """渲染 HTML 邮件"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("email.html")

    grouped = _group_by_platform(items)

    return template.render(
        date=datetime.now().strftime("%Y年%m月%d日"),
        total_items=len(items),
        grouped_items=grouped,
        platform_icons=PLATFORM_ICONS,
        platform_badge=PLATFORM_BADGE_CLASS,
    )


def send_email(items: list[dict]) -> bool:
    """发送摘要邮件，返回是否成功"""
    if not items:
        logger.info("[Email] 没有新内容，跳过发送")
        return False

    email_from = os.environ.get("EMAIL_ADDRESS", "")
    email_password = os.environ.get("EMAIL_PASSWORD", "")
    email_to = os.environ.get("EMAIL_TO", email_from)
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not email_from or not email_password:
        logger.error("[Email] 未设置 EMAIL_ADDRESS 或 EMAIL_PASSWORD 环境变量")
        return False

    html_body = render_email(items)
    today = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📚 每日学术摘要 | {today} | {len(items)}篇精选"
    msg["From"] = f"AI Digest <{email_from}>"
    msg["To"] = email_to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(email_from, email_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(email_from, email_password)
                server.send_message(msg)
        logger.info(f"[Email] 成功发送至 {email_to}，共 {len(items)} 条内容")
        return True
    except Exception as e:
        logger.error(f"[Email] 发送失败: {e}")
        return False
