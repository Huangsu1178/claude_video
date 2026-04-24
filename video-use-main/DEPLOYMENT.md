# video-use 部署指南

## 部署状态

### ✅ 已完成
1. Python依赖安装 (`pip install -e .`)
2. ffmpeg 安装 (通过 winget)
3. .env 配置文件创建

### ⚠️ 需要手动完成

#### 1. 重启终端以使用 ffmpeg
ffmpeg 已通过 winget 安装，但需要**重启 PowerShell 终端**才能生效。

重启后验证：
```powershell
ffmpeg -version
ffprobe -version
```

#### 2. 配置 ElevenLabs API Key
编辑 `.env` 文件，填入您的 ElevenLabs API Key：
```
ELEVENLABS_API_KEY=your_api_key_here
```

获取 API Key: https://elevenlabs.io/

#### 3. (可选) 安装 yt-dlp
用于下载在线视频源：
```powershell
winget install yt-dlp
```

#### 4. (可选) 配置 Claude Code Skills 符号链接
如果要与 Claude Code 配合使用：
```powershell
# 在 PowerShell 中（需要管理员权限）
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\video-use" -Target "d:\code\video-use-main"
```

## 验证安装

重启终端后，运行以下命令验证所有依赖：

```powershell
# 检查 Python 包
python -c "import librosa; import matplotlib; import pillow; import numpy; print('✅ Python 依赖正常')"

# 检查 ffmpeg
ffmpeg -version
ffprobe -version

# 检查 helper 脚本
python helpers/transcribe.py --help
python helpers/render.py --help
python helpers/timeline_view.py --help
```

## 快速开始

1. 准备视频素材文件夹
2. 进入视频文件夹：`cd path\to\your\videos`
3. 启动 Claude Code：`claude`
4. 在会话中输入：`edit these into a launch video`

或者手动使用 helper 脚本：
```powershell
# 转录视频
python d:\code\video-use-main\helpers\transcribe_batch.py path\to\videos

# 打包转录文本
python d:\code\video-use-main\helpers\pack_transcripts.py --edit-dir path\to\videos\edit

# 渲染视频
python d:\code\video-use-main\helpers\render.py path\to\edit\edl.json -o path\to\edit\final.mp4
```

## 故障排除

### ffmpeg 未找到
- 重启 PowerShell 终端
- 如果仍然无法找到，手动添加到 PATH：
  ```powershell
  $env:PATH += ";C:\Program Files\FFmpeg\bin"
  ```

### ElevenLabs API 错误
- 检查 `.env` 文件中的 API Key 是否正确
- 确保网络连接正常

### Python 导入错误
- 重新安装依赖：`pip install -e . --force-reinstall`
