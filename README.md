# 🤖 AI Daily Digest — 每日学术摘要助理

每天自动抓取你关注的深度学习/医学信号处理领域博主、论文、播客内容，用 AI 总结后发送到你的邮箱。**完全免费部署，无需服务器，无需编程经验。**

本文档面向**零基础用户**，每一步都会说清楚"在哪个网站、点哪个按钮、改哪个文件"。请耐心按顺序操作，全程大约 30-40 分钟。

---

## 📋 目录

- [这个项目能做什么](#这个项目能做什么)
- [支持的平台](#支持的平台)
- [开始之前你需要准备什么](#开始之前你需要准备什么)
- [第一部分：注册必要账号并获取密钥](#第一部分注册必要账号并获取密钥)
- [第二部分：把代码放到 GitHub](#第二部分把代码放到-github)
- [第三部分：配置密钥（Secrets）](#第三部分配置密钥secrets)
- [第四部分：自定义你关注的内容源](#第四部分自定义你关注的内容源)
- [第五部分：手动运行测试](#第五部分手动运行测试)
- [第六部分：开启每天自动运行](#第六部分开启每天自动运行)
- [常见问题排查](#常见问题排查)
- [项目结构说明](#项目结构说明)
- [进阶设置](#进阶设置)

---

## 这个项目能做什么

每天早上 8 点（可自定义时间），程序会自动：

1. 抓取你在配置文件里指定的 YouTube 频道、学术博客、播客、ArXiv 论文、Hacker News 热帖
2. 用 AI（Claude / Gemini / GPT 等，任选其一或多个备用）把每条内容总结成中文摘要
3. 把所有摘要整理成一封 HTML 邮件，发送到你指定的一个或多个邮箱
4. 全程运行在 GitHub 提供的免费服务器上，**你自己的电脑不需要开机**

---

## 支持的平台

| 平台 | 内容类型 | 抓取方式 |
|------|---------|---------|
| YouTube | 视频字幕 | yt-dlp（备用 youtube-transcript-api） |
| Substack / Medium / 博客 | 文章 | 原生 RSS |
| ArXiv | 论文摘要 | 官方 API |
| 播客 | 节目说明/转录 | RSS |
| Hacker News | 技术讨论帖 | 官方 API |
| 科学网 / 生物谷 / XMOL / 艾思科蓝 / 小木虫 | 中文科研资讯 | RSS |
| 医学期刊（JACC / Neurology / Lancet 等） | 论文速递 | RSS |

---

## 开始之前你需要准备什么

- 一个邮箱（推荐 Gmail 或 QQ 邮箱，用来发送和/或接收摘要）
- 一个 GitHub 账号（用来免费托管和定时运行代码）
- 至少一个 AI 服务的 API Key（推荐先用免费的 Google Gemini）

以上都不需要付费，下面会逐一教你注册。

---

## 第一部分：注册必要账号并获取密钥

### 1.1 注册 GitHub 账号

如果还没有账号：

1. 打开 [github.com](https://github.com)
2. 点击右上角 **"Sign up"**
3. 按提示填写邮箱、密码、用户名，完成注册
4. 登录邮箱验证账号

---

### 1.2 获取 AI API Key（至少配置一个）

推荐优先申请 **Google Gemini**，因为完全免费。

#### 方式A：Google Gemini

1. 打开 [aistudio.google.com](https://aistudio.google.com)
2. 用 Google 账号登录（没有就先注册一个 Google 账号）
3. 左侧菜单点击 **"Get API key"**
4. 点击 **"Create API key"**
5. 复制生成的密钥（以 `AIzaSy` 开头），**先粘贴到记事本暂存**，后面要用

#### 方式B：Deepseek

1. 打开 [https://platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)
2. 注册/登录账号
3. 左侧菜单点击 **"API Keys"**
4. 点击 **"创建 API Key"**
5. 复制密钥（以 `sk-ant-` 开头），暂存到记事本

> 💡 两个都申请也没问题，程序会自动优先用前面的api key，失败了自动切换到后面的，提高成功率。

---

### 1.3 获取邮箱发送密码

**⚠️ 重要：不能用邮箱登录密码，必须用"应用专用密码"或"授权码"，否则发送会失败！**

#### 如果用 Gmail：

1. 打开 [myaccount.google.com](https://myaccount.google.com)
2. 左侧点击 **"安全性"（Security）**
3. 找到 **"两步验证"（2-Step Verification）**，如果显示"关闭"，点进去按提示开启（需要绑定手机号）
4. 两步验证开启后，回到"安全性"页面顶部搜索框，输入 **"应用专用密码"**（App passwords）
5. 应用名称填 `ai-digest`，点击 **"创建"**
6. 会显示一个 **16 位密码**（形如 `abcd efgh ijkl mnop`），复制下来，**去掉中间的空格**，暂存到记事本

#### 如果用 QQ 邮箱（更简单，推荐国内用户）：

1. 打开 [mail.qq.com](https://mail.qq.com) 并登录
2. 点击顶部 **"设置"** → **"账户"**
3. 往下滑找到 **"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务"**
4. 点击 **"开启"** IMAP/SMTP 服务旁边的按钮
5. 按提示用手机发送短信验证
6. 验证后会显示一个 **16 位授权码**，复制暂存

---

到这一步，你的记事本里应该已经暂存了这些内容（示例）：

```
Gemini API Key: AIzaSy...
Gmail 地址: yourname@gmail.com
Gmail 应用专用密码: abcdefghijklmnop
```

---

## 第二部分：把代码放到 GitHub

### 2.1 创建新仓库

1. 登录 GitHub，点击右上角 **"+"** 号 → **"New repository"**
2. **Repository name** 填写：`ai-digest`
3. 选择 **Private**（私有，这样你的配置不会被别人看到）
4. 其他选项保持默认，点击绿色按钮 **"Create repository"**

---

### 2.2 上传项目文件

1. 解压你下载的 `ai-digest.zip` 压缩包到电脑任意位置
2. 回到刚创建的 GitHub 仓库页面，点击 **"uploading an existing file"**（如果没看到，点击 **"Add file"** → **"Upload files"**）
3. 打开解压后的文件夹，**把里面所有文件和文件夹（包括看起来是隐藏文件的 `.github`、`.gitignore`、`.env.example`）全部拖拽到网页的上传框中**

> ⚠️ 注意：网页上传对多层文件夹的支持可能不完整。如果发现 `src/fetchers/`、`.github/workflows/` 这些子文件夹里的文件没有正确上传，请打开对应的子文件夹，把里面的文件单独拖进去，保证路径完全一致。

4. 拖拽完成后，滑到页面底部，点击绿色按钮 **"Commit changes"**

---

### 2.3 检查文件是否上传完整

上传完成后，在仓库首页应该能看到这样的文件结构：

```
ai-digest/
├── .github/
│   └── workflows/
│       └── daily_digest.yml    ← 关键：这个文件必须存在，否则无法自动运行
├── config/
│   └── sources.example.yaml
├── src/
│   ├── fetchers/
│   ├── processors/
│   └── utils/
├── templates/
├── main.py
├── requirements.txt
└── README.md
```

点开 `.github` 文件夹 → `workflows` 文件夹，确认里面有 `daily_digest.yml` 文件。**这是最容易漏传的文件，请务必检查。**

---

## 第三部分：配置密钥（Secrets）

这一步是把你在第一部分暂存的密钥，安全地告诉 GitHub，代码本身不会包含任何密码。

1. 进入你的仓库页面
2. 点击顶部菜单栏的 **"Settings"**（设置，一个齿轮图标）
3. 在左侧菜单找到 **"Secrets and variables"** → 点击展开 → 点击 **"Actions"**
4. 点击右上角绿色按钮 **"New repository secret"**

现在按下表逐一添加（每添加一个都要点一次 **"New repository secret"**）：

| Name（名称，必须完全一致） | Secret（值） |
|---|---|
| `GEMINI_API_KEY` | 你的 Gemini 密钥（AIzaSy开头） |
| `ANTHROPIC_API_KEY` | 你的 Claude 密钥（sk-ant-开头，如果有） |
| `EMAIL_ADDRESS` | 你的发件邮箱，例如 `yourname@gmail.com` |
| `EMAIL_PASSWORD` | 应用专用密码/授权码（16位，无空格） |
| `EMAIL_TO` | 收件邮箱，可以和发件邮箱相同；多个收件人用英文逗号分隔，例如 `a@gmail.com,b@qq.com` |

**如果你用的是 QQ 邮箱发送**，还需要额外添加两个：

| Name | Secret |
|---|---|
| `SMTP_HOST` | `smtp.qq.com` |
| `SMTP_PORT` | `465` |

每个填完点击绿色 **"Add secret"** 保存。全部添加完后，在这个页面应该能看到 4-7 行密钥列表（值是隐藏的，只显示名称）。

---

## 第四部分：自定义你关注的内容源

项目自带了一份心脑医学信号处理 + 深度学习方向的示例配置，你可以直接使用，也可以修改。

### 4.1 找到配置文件

在仓库页面，点击进入 `config` 文件夹，你会看到 `sources.example.yaml` 文件。

### 4.2 复制并重命名为正式配置文件

因为程序实际读取的是 `sources.yaml`（不是 example 版本），需要复制一份：

**方法：直接在网页上创建**

1. 点开 `sources.example.yaml`，点击右上角的 **铅笔图标（Edit）**
2. 全选内容（Ctrl+A）复制
3. 返回 `config` 文件夹页面，点击 **"Add file"** → **"Create new file"**
4. 文件名输入：`config/sources.yaml`
5. 粘贴刚才复制的内容
6. 拉到页面底部，点击 **"Commit changes"**

### 4.3 修改你想关注的内容（可选）

打开 `config/sources.yaml`，点击铅笔图标编辑，你会看到这样的结构，按需增删：

```yaml
youtube:
  - name: "频道名字（自己起，用于邮件里显示）"
    channel_id: "UCxxxxxxxxxxxxxx"    # 频道ID，见下方获取方法
```

**如何找到 YouTube 频道 ID：**
1. 打开你想关注的 YouTube 频道页面
2. 点击频道名下方的 **"分享"** → **"复制频道 ID"**
3. 或者在频道页面右键"查看网页源代码"，搜索 `channel_id`

修改完成后同样点击 **"Commit changes"** 保存。

---

## 第五部分：手动运行测试

不用等到第二天早上，先手动跑一次确认一切正常。

1. 回到仓库页面，点击顶部菜单 **"Actions"**
2. 左侧会看到 **"Daily AI Digest"**，点击它
3. 页面右侧有个 **"Run workflow"** 下拉按钮，点击它
4. 会弹出一个小窗口，直接点击绿色 **"Run workflow"** 按钮确认
5. 页面会出现一个新的运行记录，前面是黄色圆点（运行中），等待 1-5 分钟

### 5.1 查看运行结果

- 圆点变成 **绿色 ✅** = 全部成功，去邮箱查收！
- 圆点变成 **红色 ❌** = 某一步出错，点击这条记录 → 点击 **"digest"** → 展开报错的那一步查看详细日志

### 5.2 查看详细日志的方法

1. 点击刚才那条运行记录（标题类似 "Daily AI Digest #1"）
2. 点击左侧的 **"digest"**
3. 页面会展开所有步骤，点击每个步骤前的箭头可以展开查看详细文字日志
4. 找报错信息，通常在 **"运行摘要助理"** 这一步

---

## 第六部分：开启每天自动运行

只要 `daily_digest.yml` 文件上传成功，并成功运行**Run workflow**，GitHub 会自动按设定时间每天运行一次，默认是**北京时间早上 8 点**。

### 6.1 如何修改运行时间

1. 打开 `.github/workflows/daily_digest.yml` 文件，点击铅笔图标编辑
2. 找到这一行：
   ```yaml
   - cron: '0 0 * * *'
   ```
3. `cron` 时间用的是 **UTC 时区**，需要换算成北京时间（北京时间 = UTC + 8小时）：

| 想要的北京时间 | 应该填写的 cron |
|---|---|
| 07:00 | `0 23 * * *` |
| 08:00 | `0 0 * * *`（默认） |
| 09:00 | `0 1 * * *` |
| 20:00 | `0 12 * * *` |

4. 改完点击 **"Commit changes"** 保存即可生效

### 6.2 注意事项

GitHub 对长期不活跃（60天无任何操作）的仓库会自动暂停定时任务。如果发现好几天没收到邮件，去 Actions 页面点一次 **"Run workflow"** 手动触发，会自动恢复。

---

## 常见问题排查

### ❌ 邮件发送失败，报错 "Username and Password not accepted"

说明填的是登录密码而不是应用专用密码。回到 [第一部分 1.3](#13-获取邮箱发送密码) 重新生成，并在 [Secrets](#第三部分配置密钥secrets) 里更新 `EMAIL_PASSWORD`。

### ❌ Actions 页面找不到 "Daily AI Digest"

`.github/workflows/daily_digest.yml` 没有上传成功。回到仓库首页检查 `.github` 文件夹是否存在，若不存在，参考 [2.2](#22-上传项目文件) 单独把这个文件补传上去。

### ❌ YouTube 显示 "RSS 为空或无法访问"

YouTube 有反爬虫机制，属于正常现象，程序已内置了绕过策略（伪装浏览器请求头 + yt-dlp）。如果字幕经常获取失败，可以配置 Cookies 提高成功率，见 [进阶设置](#进阶设置)。

### ❌ 所有 AI 总结都失败，报 "调用异常"

检查 [Secrets](#第三部分配置密钥secrets) 里 API Key 有没有多余的空格，或者去对应控制台（[Google AI Studio](https://aistudio.google.com) / [Anthropic Console](https://console.anthropic.com)）确认额度是否用完。

### ❌ 运行成功但没收到邮件

先检查垃圾邮件文件夹。其次确认 `EMAIL_TO` 这个 Secret 是否正确填写了收件邮箱。

### ❔ 每天都想在不同时间收到摘要，怎么办

参考 [6.1](#61-如何修改运行时间) 修改 cron 时间表达式。

---

## 项目结构说明

```
ai-digest/
├── main.py                        # 程序入口，本地运行时用这个文件
├── requirements.txt                # Python 依赖包列表
├── .env.example                    # 本地运行用的密钥模板（GitHub部署不需要）
├── .gitignore                      # 声明哪些文件不上传（如真实密钥）
│
├── config/
│   ├── sources.example.yaml        # 内容源配置模板
│   └── sources.yaml                # 你实际使用的配置（需自己创建，见第四部分）
│
├── src/
│   ├── fetchers/                   # 各平台的内容抓取逻辑
│   │   ├── youtube.py              # YouTube 视频字幕抓取
│   │   ├── rss.py                  # 博客/播客/ArXiv 通用抓取
│   │   └── hackernews.py           # Hacker News 热帖抓取
│   │
│   ├── processors/
│   │   ├── summarizer.py           # 调用 AI（Gemini/Claude/GPT等）生成摘要
│   │   └── email_sender.py         # 渲染并发送邮件
│   │
│   └── utils/
│       ├── database.py             # 记录已处理内容，避免重复
│       └── logger.py               # 运行日志输出
│
├── templates/
│   └── email.html                  # 邮件的网页模板（可自行调整样式）
│
└── .github/
    └── workflows/
        └── daily_digest.yml        # GitHub 自动定时运行的配置（最关键的文件）
```

---

## 进阶设置

### 添加更多 AI Provider 作为备用

在 Secrets 里额外添加以下任意一个，程序会自动识别并加入轮换列表：

| Secret 名 | 用途 | 免费申请地址 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 极便宜备用 | [platform.deepseek.com](https://platform.deepseek.com) |
| `OPENAI_API_KEY` | GPT 备用 | [platform.openai.com](https://platform.openai.com) |
| `GROQ_API_KEY` | 免费限额备用 | [console.groq.com](https://console.groq.com) |

### 配置 YouTube Cookies 提高字幕成功率

1. 安装浏览器插件 [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. 登录 YouTube 后，点击插件图标导出 `cookies.txt`
3. 打开电脑的终端/命令行，运行：
   ```bash
   # Mac / Linux
   base64 -i cookies.txt | tr -d '\n'
   # Windows PowerShell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))
   ```
4. 复制输出的一长串字符
5. 在 GitHub Secrets 里新增 `YT_COOKIES_B64`，粘贴刚才的字符串

### 调整每次抓取的内容数量（控制 AI 调用成本）

编辑 `config/sources.yaml` 顶部：

```yaml
settings:
  max_items_per_source: 3     # 改小可以减少费用，比如改成 2
  max_content_chars: 12000    # 改小可以减少每次总结的输入长度
  days_lookback: 1            # 只看最近1天的内容
```

### 本地电脑运行（不用 GitHub Actions）

如果你想在自己电脑上先测试效果：

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制密钥模板并填写真实密钥
cp .env.example .env
# 用记事本打开 .env，填入你的密钥

# 3. 生成本地预览网页（不发邮件，用浏览器打开看效果）
python main.py --preview

# 4. 确认无误后正式运行并发送邮件
python main.py --run-now
```

---
