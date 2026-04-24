# Claude Video Production Workflow

对话式视频剪辑 + 批量字幕生成，全程由 Claude Code 驱动。

---

## 目录

- [工作流概览](#工作流概览)
- [部署：macOS](#部署macos)
- [部署：Windows](#部署windows)
- [工作流 A — 视频剪辑（video-use）](#工作流-a--视频剪辑video-use)
- [工作流 B — 批量字幕（subtitles）](#工作流-b--批量字幕subtitles)
- [工作流 C — 联合流程（剪辑 + 批量字幕）](#工作流-c--联合流程剪辑--批量字幕)
- [配置参考](#配置参考)
- [常见问题](#常见问题)

---

## 工作流概览

```
原始素材
   │
   ▼
[video-use skill]           ← Claude 对话式剪辑：多镜头筛选、调色、音频淡入淡出
   │                           语音字幕（SRT）、动画叠加
   ▼
edit/final.mp4
   │
   ▼
[subtitles 工具]            ← 同一个基底视频 × N 套文案 → N 个输出视频
   │                           支持中英文混排、彩色 Emoji、单列/双列布局
   ▼
output/video_v1.mp4  …  video_vN.mp4
```

| 工具 | 路径 | 用途 |
|------|------|------|
| `video-use` skill | `~/.claude/skills/video-use` | AI 剪辑 + 语音字幕 + 调色 + 动画 |
| `subtitles/` | `./subtitles/` | 批量文字卡片叠加，生成多版本视频 |

---

## 部署：macOS

### 1. 安装系统依赖

```bash
# Homebrew（若未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install ffmpeg
brew install yt-dlp          # 可选，用于下载在线视频
```

### 2. 克隆仓库并安装 Python 依赖

```bash
# 克隆到本地（或直接使用已有目录）
cd ~/Videos   # 根据实际情况修改

# video-use 依赖
cd video-use-main
pip install -e .

# subtitles 依赖
pip install Pillow pilmoji requests
```

### 3. 创建 video-use skill 符号链接

```bash
mkdir -p ~/.claude/skills

# 将 video-use-main 目录链接为 Claude 可识别的 skill
ln -s "$(pwd)/video-use-main" ~/.claude/skills/video-use
# 或者使用绝对路径
ln -s "/Users/<你的用户名>/Videos/video-use-main" ~/.claude/skills/video-use
```

验证：
```bash
ls -la ~/.claude/skills/
# 应显示: video-use -> /Users/.../video-use-main
```

### 4. 配置 ElevenLabs API Key

`video-use` 使用 ElevenLabs Scribe 做语音转录（字幕）。

```bash
cd video-use-main
cp .env.example .env
nano .env
# 填入: ELEVENLABS_API_KEY=sk_...
```

在 [ElevenLabs 官网](https://elevenlabs.io/) 注册并获取 API Key（有免费额度）。

### 5. 验证安装

```bash
# 检查 ffmpeg
ffmpeg -version
ffprobe -version

# 检查 Python 依赖
python -c "import librosa, matplotlib, PIL, numpy; print('video-use deps OK')"
python -c "import PIL, pilmoji, requests; print('subtitles deps OK')"

# 检查 helper 脚本
python video-use-main/helpers/transcribe.py --help
python subtitles/project.py list
```

---

## 部署：Windows

### 1. 安装 Python（3.10+）

下载安装 [Python for Windows](https://www.python.org/downloads/windows/)，安装时勾选 **Add to PATH**。

### 2. 安装 ffmpeg

**推荐方式：winget（Windows 11 内置包管理器）**

```powershell
winget install Gyan.FFmpeg
# 安装完成后重启 PowerShell 或命令提示符，使 PATH 生效
ffmpeg -version    # 验证
```

**备选：Chocolatey**

```powershell
# 先安装 Chocolatey（管理员 PowerShell）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

choco install ffmpeg -y
```

**备选：Scoop**

```powershell
# 先安装 Scoop
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

scoop install ffmpeg
```

### 3. 安装 Python 依赖

```powershell
# 进入 video-use-main 目录
cd D:\Videos\claude_video\video-use-main
pip install -e .

# subtitles 依赖
pip install Pillow pilmoji requests
```

### 4. 创建 video-use skill 符号链接

**PowerShell（需要管理员权限）：**

```powershell
# 确保目标目录存在
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"

# 创建符号链接（管理员 PowerShell）
New-Item -ItemType SymbolicLink `
  -Path "$env:USERPROFILE\.claude\skills\video-use" `
  -Target "D:\Videos\claude_video\video-use-main"
```

> **提示：** 若没有管理员权限，可启用开发者模式（Settings → Developer Mode）后再运行。

验证：
```powershell
Get-Item "$env:USERPROFILE\.claude\skills\video-use"
# 应显示 LinkType: SymbolicLink
```

**如果系统不支持符号链接，使用 Junction（目录联接，无需管理员）：**

```powershell
cmd /c mklink /J "%USERPROFILE%\.claude\skills\video-use" "D:\Videos\claude_video\video-use-main"
```

### 5. 配置 ElevenLabs API Key

```powershell
cd D:\Videos\claude_video\video-use-main
copy .env.example .env
notepad .env
# 填入: ELEVENLABS_API_KEY=sk_...
```

### 6. 验证安装

```powershell
# ffmpeg
ffmpeg -version
ffprobe -version

# Python 依赖
python -c "import librosa, matplotlib, PIL, numpy; print('video-use deps OK')"
python -c "import PIL, pilmoji, requests; print('subtitles deps OK')"

# Helper 脚本
python D:\Videos\claude_video\video-use-main\helpers\transcribe.py --help
python D:\Videos\claude_video\subtitles\project.py list
```

---

## 工作流 A — 视频剪辑（video-use）

适用场景：有多段原始素材（多镜次、多段录制），需要 AI 辅助剪辑成一条完整视频，可选：调色、动画叠加、语音字幕。

### 步骤

**1. 进入视频目录，启动 Claude**

```bash
cd /path/to/your/raw/footage
claude
```

**2. 在 Claude 会话中描述任务**

```
将这些素材剪辑成一条 60 秒的产品介绍视频，暖色调，加上英文字幕
```

Claude 会：
- 运行 `transcribe_batch.py` 转录所有素材（缓存，不会重复转录）
- 打包为 `takes_packed.md`（片段级时间戳文本，供 LLM 阅读）
- 用 `timeline_view.py` 在关键决策点查看画面帧
- 向你提出编辑策略（4–8 句），**等待你确认**
- 生成 `edl.json` → 按段提取 + concat → 叠加动画 → 最后烧制字幕
- 自评（检查每个剪辑点）→ 通过后给你看预览

**3. 输出结构**

```
<footage_dir>/
└── edit/
    ├── project.md           ← 会话记忆（跨次会话持续）
    ├── takes_packed.md      ← 转录文本
    ├── edl.json             ← 剪辑决策
    ├── transcripts/         ← 缓存的原始转录 JSON
    ├── master.srt           ← 输出时间轴字幕
    ├── preview.mp4
    └── final.mp4            ← 最终输出
```

### 常用指令示例

```
帮我剪出最精华的 90 秒，去掉所有 "um" 和口误
加上暖色调和白色大字体英文字幕
帮我给 0:30-0:45 做一个技术图表动画叠加
导出 1080x1920 竖屏版本
```

---

## 工作流 B — 批量字幕（subtitles）

适用场景：已有一段基底视频（比如无字幕的短视频素材），需要批量生成多套文案版本，用于 A/B 测试、多语言或多平台分发。

### 步骤

**1. 创建项目**

```bash
cd subtitles
python project.py new my_video
# 输出: projects/my_video/{source, analysis, content, output}/
```

**2. 放入源视频**

将基底视频复制到 `projects/my_video/source/`（支持 .mp4 .mov .avi .mkv .webm）。

**3. 分析视频（提取关键帧）**

```bash
python project.py analyze my_video
# 在 analysis/ 中生成 10 张关键帧 PNG + video_analysis.json
```

**4. 让 Claude 生成 template.json**

在 Claude Code 会话中：
```
读取 subtitles/projects/my_video/analysis/ 中的帧图像和 video_analysis.json，
分析视频内容节奏，为我生成 template.json（字幕出现时间节点和布局），
放入 subtitles/projects/my_video/ 目录。
```

Claude 会查看帧图、推断字幕时机，输出类似：

```json
{
  "config": { "font_size": 48, "stroke_width": 5 },
  "slots": [
    { "id": 1, "type": "single", "start": 1.2, "end": 6.8, "y": "10%",
      "sample": { "title": "✅ 核心结论:", "lines": ["第一点", "第二点"] } },
    { "id": 2, "type": "double", "start": 7.5, "end": 12.0, "y": "10%",
      "sample": {
        "left":  { "title": "✅ 做:", "lines": ["正确做法"] },
        "right": { "title": "❌ 不做:", "lines": ["错误做法"] }
      } }
  ]
}
```

**5. 编写文案 JSON**

在 `projects/my_video/content/` 中创建多个 JSON 文件，每个生成一个视频：

`content_v1.json`
```json
{
  "output_name": "video_en_v1.mp4",
  "slots": [
    { "title": "✅ Results in 3 months:", "lines": ["Progressive overload", "High protein diet", "7-8hr sleep"] },
    {
      "left":  { "title": "✅ Do:",    "lines": ["Train smart", "Track progress"] },
      "right": { "title": "❌ Don't:", "lines": ["Random workouts", "Skip recovery"] }
    }
  ]
}
```

`content_v2.json`
```json
{
  "output_name": "video_zh_v1.mp4",
  "slots": [
    { "title": "✅ 3个月结果:", "lines": ["渐进超负荷训练", "高蛋白饮食", "7-8小时睡眠"] },
    {
      "left":  { "title": "✅ 做:", "lines": ["系统训练", "记录进度"] },
      "right": { "title": "❌ 别:", "lines": ["随机乱练", "忽视恢复"] }
    }
  ]
}
```

**6. 批量生成**

```bash
python project.py run my_video
# content/ 中有几个 JSON 就输出几个视频 → output/
```

**查看状态**

```bash
python project.py status my_video
```
```
──────────────────────────────────────────────────
  项目: my_video
──────────────────────────────────────────────────
  source/    [有]  source.mp4
  analysis/  10 帧图像  [有 video_analysis.json]
  template   2 个槽位  ['single', 'double']
  content/   2 个 JSON:  ['content_v1.json', 'content_v2.json']
  output/    2 个视频  (28.4 MB 合计)
```

---

## 工作流 C — 联合流程（剪辑 + 批量字幕）

```
1. cd /path/to/raw/footage && claude
   → 剪辑成 edit/final.mp4（含语音字幕）

2. cd subtitles
   python project.py new campaign_jan
   cp /path/to/raw/footage/edit/final.mp4 projects/campaign_jan/source/

3. python project.py analyze campaign_jan
   → Claude 生成 template.json（文字卡片时间节点）

4. 准备 content/ 文案 JSON（N 套）

5. python project.py run campaign_jan
   → output/ 中 N 个完整视频（已含语音字幕 + 文字卡片）
```

---

## 配置参考

### video-use .env

| 变量 | 说明 |
|------|------|
| `ELEVENLABS_API_KEY` | ElevenLabs API Key，用于语音转录（Scribe） |

### subtitles 项目配置

通过 `python project.py config <name> [key] [value]` 修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `font_path` | 空 | 主字体路径（英文/符号），留空自动选 Impact（Win）/Arial Bold（Mac） |
| `cjk_font_path` | 空 | 中文字体，留空自动选 微软雅黑（Win）/ PingFang（Mac） |
| `font_size` | 48 | 正文字号（像素） |
| `title_size` | 0 | 标题字号，0 = 同正文 |
| `stroke_width` | 5 | 描边宽度（像素）|
| `line_gap` | 12 | 行间距（像素） |
| `preset` | `fast` | FFmpeg 编码速度：ultrafast / fast / medium / slow |
| `crf` | 18 | 视频质量：18=高质，23=标准 |

**示例：**
```bash
python project.py config my_video font_size 56
python project.py config my_video stroke_width 6
python project.py config my_video font_path "C:/Fonts/Anton.ttf"
python project.py config my_video cjk_font_path "/System/Library/Fonts/PingFang.ttc"
```

### subtitles 字幕样式

- **字体回退链：** 自定义路径 → 系统默认（Impact / 微软雅黑）→ 内置 default
- **Emoji：** 使用 Twemoji 彩色图片（首次使用时从 CDN 下载并缓存至 `_emoji_cache/`，之后完全离线）
- **布局类型：**
  - `single` — 文字块居中
  - `double` — 左列在画面 1/4 处，右列在 3/4 处

---

## 常见问题

### ffmpeg: command not found

**macOS：** `brew install ffmpeg`

**Windows：** `winget install Gyan.FFmpeg` 后**重启终端**（PowerShell / CMD）再试。

若仍找不到，手动加 PATH：
```powershell
$env:PATH += ";C:\Program Files\FFmpeg\bin"   # 临时
# 永久: 系统属性 → 环境变量 → Path → 新增
```

### ElevenLabs 转录报错

1. 检查 `.env` 中 `ELEVENLABS_API_KEY` 是否填写正确
2. 检查网络连接
3. 免费额度用完时，到 [elevenlabs.io](https://elevenlabs.io) 查看用量

### Pillow / pilmoji 导入报错

```bash
pip install --upgrade Pillow pilmoji requests
```

### Windows 创建符号链接失败（权限错误）

选项一：以管理员身份运行 PowerShell，再执行 `New-Item -ItemType SymbolicLink`。

选项二：启用开发者模式 → Settings → Privacy & security → For developers → Developer Mode（开）。

选项三：使用 Junction（目录联接，不需要管理员）：
```powershell
cmd /c mklink /J "%USERPROFILE%\.claude\skills\video-use" "D:\Videos\claude_video\video-use-main"
```

### macOS：PingFang 字体路径

```bash
# 查找 PingFang
ls /System/Library/Fonts/ | grep -i ping
# 通常是: PingFang.ttc
# 完整路径: /System/Library/Fonts/PingFang.ttc
```

配置：
```bash
python project.py config <name> cjk_font_path "/System/Library/Fonts/PingFang.ttc"
```

### 字幕 Emoji 不显示彩色

首次使用时需要网络连接以下载 Twemoji 图片缓存到 `_emoji_cache/`。下载后即可离线使用。  
若网络受限，可手动将 72×72 的 Twemoji PNG（以 Unicode code point 命名，如 `2705.png`）放入 `_emoji_cache/`。

### video-use 转录很慢

转录结果缓存在 `<videos_dir>/edit/transcripts/<name>.json`，同一个素材只转录一次。  
若要强制重新转录，删除对应缓存文件即可。

---

## 目录结构

```
D:\Videos\claude_video\          ← 本仓库根目录
├── CLAUDE.md                     ← Claude 工具使用说明
├── README.md                     ← 本文件
│
├── video-use-main/               ← video-use 核心（已 symlink 至 ~/.claude/skills/video-use）
│   ├── SKILL.md                  ← Claude 读取的技能规则
│   ├── helpers/                  ← transcribe / render / grade / timeline_view
│   ├── skills/manim-video/       ← Manim 动画子技能
│   ├── .env                      ← ELEVENLABS_API_KEY
│   └── pyproject.toml
│
└── subtitles/                    ← 批量字幕工具
    ├── project.py                ← 项目管理主入口
    ├── add_subtitles.py          ← 渲染引擎
    ├── analyze_video.py          ← 关键帧提取
    ├── _emoji_cache/             ← Twemoji 本地缓存
    └── projects/                 ← 用户项目数据
        └── <project_name>/
            ├── source/           ← 放入源视频
            ├── analysis/         ← 关键帧 + video_analysis.json
            ├── content/          ← 文案 JSON（N 个）
            ├── output/           ← 输出视频（N 个）
            ├── template.json     ← Claude 生成的时间模板
            └── project.json      ← 字体/字号等配置
```

---

## 快速上手（TL;DR）

```bash
# --- 剪辑 ---
cd /path/to/raw/footage
claude
# > 帮我剪成 60 秒精华，暖色调，英文字幕

# --- 批量字幕 ---
cd D:/Videos/claude_video/subtitles
python project.py new demo
# 把视频放入 projects/demo/source/
python project.py analyze demo
# 让 Claude 生成 template.json
# 写若干 content_*.json 到 projects/demo/content/
python project.py run demo
# → projects/demo/output/ 中是你的视频
```
