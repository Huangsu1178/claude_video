# 批量字幕视频生成工具

对同一段基础视频，批量套用不同文案，生成 N 个带彩色字幕的视频。

---

## 目录结构

```
根目录/
├── project.py          # 项目管理器（主入口，日常只用这一个）
├── add_subtitles.py    # 渲染引擎（由 project.py 调用，无需直接运行）
├── analyze_video.py    # 视频分析（由 project.py 调用，无需直接运行）
├── _emoji_cache/       # Twemoji 彩色 emoji 图片缓存（自动管理）
├── README.md
│
└── projects/
    └── <项目名>/
        ├── project.json    # 项目配置（字体、字号、描边等）
        ├── template.json   # 时间模板（由 Claude 分析视频后生成）
        ├── source/         # 放入源视频（.mp4 / .mov 等）
        ├── analysis/       # 关键帧图片 + video_analysis.json
        ├── content/        # 批量文案 JSON（每个文件生成一个视频）
        └── output/         # 输出视频
```

---

## 完整工作流

### 第一步：创建项目

```bash
python project.py new <项目名>
```

将源视频放入 `projects/<项目名>/source/`。

---

### 第二步：分析视频（让 Claude 生成时间模板）

```bash
python project.py analyze <项目名>
```

将在 `analysis/` 中生成关键帧图片和 `video_analysis.json`。  
把帧图交给 Claude，Claude 会输出 `template.json`，将其放入项目根目录。

**template.json 结构：**

```json
{
  "video": "source.mp4",
  "config": { "font_size": 48, "stroke_width": 5, "line_gap": 12 },
  "slots": [
    {
      "id": 1,
      "type": "single",
      "start": 1.0,
      "end": 7.5,
      "y": "10%",
      "sample": {
        "title": "✅ 示例标题:",
        "lines": ["示例行一", "示例行二", "示例行三"]
      }
    },
    {
      "id": 2,
      "type": "double",
      "start": 8.0,
      "end": 10.0,
      "y": "10%",
      "sample": {
        "left":  { "title": "✅ 左列标题:", "lines": ["左侧要点"] },
        "right": { "title": "❌ 右列标题:", "lines": ["右侧要点"] }
      }
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `type` | `single`（单列居中）或 `double`（左右双列） |
| `start` / `end` | 字幕显示时间段（秒） |
| `y` | 字幕起始纵坐标，支持像素值 `200`、百分比 `"15%"`、`"center"` |
| `sample` | 示例文本，仅用于格式参考 |

---

### 第三步：准备文案 JSON

在 `projects/<项目名>/content/` 中放入一个或多个 JSON 文件，每个文件生成一个视频。

**content JSON 只需填写文本，时间/布局由模板控制：**

```json
{
  "output_name": "video_v1.mp4",
  "slots": [
    {
      "title": "✅ Results in 3 months:",
      "lines": ["Progressive overload", "High protein diet", "7-8hr sleep"]
    },
    {
      "left":  { "title": "✅ Do:", "lines": ["Train smart", "Eat well"] },
      "right": { "title": "❌ Don't:", "lines": ["Random workouts", "Skip sleep"] }
    }
  ]
}
```

- `slots` 数组按顺序对应 `template.json` 中的 `slots`
- `output_name` 可省略，默认用文件名命名输出视频
- 中文、英文、emoji 混用均支持

---

### 第四步：批量生成视频

```bash
python project.py run <项目名>
```

`content/` 中有几个 JSON 就生成几个视频，输出到 `output/`。

---

## 所有命令

```bash
python project.py new     <项目名>              # 创建项目目录结构
python project.py list                          # 列出所有项目及状态
python project.py status  <项目名>              # 查看项目详情
python project.py analyze <项目名> [--frames N] # 提取关键帧（默认10帧）
python project.py run     <项目名>              # 批量生成字幕视频
python project.py clean   <项目名> [--what frames|output|all]
                                                # 清理帧图或输出视频
python project.py open    <项目名>              # 在文件管理器中打开项目
python project.py config  <项目名>              # 查看当前项目配置
python project.py config  <项目名> <key> <val> # 修改配置项
```

---

## 项目配置

每个项目有独立的 `project.json`，通过 `config` 命令修改：

```bash
python project.py config demo_ai_motion font_size 56
python project.py config demo_ai_motion stroke_width 6
python project.py config demo_ai_motion font_path "C:/Fonts/Anton.ttf"
```

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `font_path` | 空（系统 Impact） | 主字体路径（英文/符号） |
| `cjk_font_path` | 空（系统微软雅黑） | 中文字体路径 |
| `font_size` | 48 | 正文字号（像素） |
| `title_size` | 0（同正文） | 标题字号，0 表示与正文相同 |
| `stroke_width` | 5 | 黑色描边宽度（像素） |
| `line_gap` | 12 | 行间距（像素） |
| `preset` | fast | FFmpeg 编码速度（ultrafast / fast / medium / slow） |
| `crf` | 18 | 视频质量，越小越好（18=高质，23=标准） |

---

## 字幕样式说明

- **字体**：英文默认 Impact，中文自动切换微软雅黑 Bold
- **Emoji**：使用 Twemoji 彩色图片（首次联网下载，之后离线缓存于 `_emoji_cache/`）
- **描边**：白色填充 + 黑色描边，在任何背景上清晰可读
- **布局**：
  - `single` — 文本块居中显示
  - `double` — 左列在画面 1/4 处，右列在 3/4 处

---

## 依赖

```bash
pip install Pillow pilmoji requests
```

- [FFmpeg](https://ffmpeg.org/)（需在系统 PATH 中）
- Python 3.10+
