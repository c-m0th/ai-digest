# 🤖 AI Daily Digest — 每日学术摘要助理

每天自动抓取你关注的深度学习/学术博主内容，用 Claude AI 总结后发到你的邮箱。

## 支持平台（全部免费抓取）

| 平台 | 内容类型 | 抓取方式 |
|------|---------|---------|
| YouTube | 视频字幕 | youtube-transcript-api |
| Substack | 文章 | 原生 RSS |
| ArXiv | 论文 | 官方 RSS API |
| 播客 | 音频转文字 | RSS + Whisper |
| Medium | 文章 | RSS |
| Hacker News | 讨论帖 | 官方 Firebase API |

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置
```bash
cp config/sources.example.yaml config/sources.yaml
# 编辑 sources.yaml 添加你关注的博主
```

### 3. 设置环境变量
```bash
export ANTHROPIC_API_KEY="your_key_here"
export EMAIL_ADDRESS="your@gmail.com"
export EMAIL_PASSWORD="your_app_password"   # Gmail 应用专用密码
export EMAIL_TO="your@gmail.com"
```

### 4. 运行
```bash
# 立即运行一次
python main.py --run-now

# 每天 08:00 定时运行
python main.py --schedule
```

### 5. 部署到 GitHub Actions（推荐）
- Fork 本项目
- 在 Repository Settings > Secrets 添加上述环境变量
- 自动每天早 8 点运行，无需服务器

## 项目结构
```
ai-digest/
├── main.py                    # 入口
├── config/
│   └── sources.yaml           # 你的订阅源配置
├── src/
│   ├── fetchers/              # 各平台抓取器
│   │   ├── youtube.py
│   │   ├── rss.py             # Substack/Medium/播客/ArXiv
│   │   └── hackernews.py
│   ├── processors/
│   │   ├── summarizer.py      # Claude API 总结
│   │   └── email_sender.py    # 邮件发送
│   └── utils/
│       ├── database.py        # SQLite 去重
│       └── logger.py
├── templates/
│   └── email.html             # 邮件 HTML 模板
└── .github/workflows/
    └── daily_digest.yml       # GitHub Actions 定时任务
```
