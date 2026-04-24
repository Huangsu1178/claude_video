# 🎬 video-use 部署完成总结

## ✅ 已完成的部署步骤

1. **Python 依赖安装** - 所有必需的包已成功安装：
   - ✅ requests
   - ✅ librosa
   - ✅ matplotlib
   - ✅ pillow
   - ✅ numpy

2. **ffmpeg 安装** - 已通过 winget 安装 FFmpeg 8.1
   - 状态：已安装，需要重启终端生效

3. **配置文件创建** - `.env` 文件已创建

4. **Helper 脚本验证** - 所有 6 个 helper 脚本都存在：
   - ✅ transcribe.py
   - ✅ transcribe_batch.py
   - ✅ pack_transcripts.py
   - ✅ timeline_view.py
   - ✅ render.py
   - ✅ grade.py

## ⚠️ 需要您手动完成的步骤

### 1. 重启终端（必须）
关闭当前的 PowerShell 窗口，然后重新打开一个新的终端窗口。
这样可以让系统识别新安装的 ffmpeg。

### 2. 配置 ElevenLabs API Key（必须）
编辑项目根目录的 `.env` 文件：
```
ELEVENLABS_API_KEY=your_actual_api_key_here
```

获取 API Key：
- 访问 https://elevenlabs.io/
- 注册或登录账户
- 在账户设置中获取 API Key

### 3. （可选）安装 yt-dlp
如果您需要下载在线视频：
```powershell
winget install yt-dlp
```

### 4. （可选）配置 Claude Code Skills
如果要在 Claude Code 中使用此技能：
```powershell
# 以管理员身份运行 PowerShell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\video-use" -Target "d:\code\video-use-main"
```

## 🚀 验证安装

重启终端后，运行验证脚本：
```powershell
cd d:\code\video-use-main
python verify_installation.py
```

如果所有检查都通过，您会看到：
```
🎉 所有依赖检查通过！项目已就绪。
```

## 📖 快速开始

### 方法一：使用 Claude Code（推荐）
```powershell
cd path\to\your\video\folder
claude
# 在 Claude 会话中输入：edit these into a launch video
```

### 方法二：手动使用 Helper 脚本
```powershell
# 1. 转录视频（批量，4个并行worker）
python d:\code\video-use-main\helpers\transcribe_batch.py path\to\videos

# 2. 打包转录文本
python d:\code\video-use-main\helpers\pack_transcripts.py --edit-dir path\to\videos\edit

# 3. 创建 EDL 文件（手动或使用 LLM）

# 4. 渲染视频
python d:\code\video-use-main\helpers\render.py path\to\edit\edl.json -o path\to\edit\final.mp4
```

## 📚 文档

- [README.md](./README.md) - 项目概述和使用说明
- [SKILL.md](./SKILL.md) - 完整的编辑规则和工艺指南
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 详细部署指南
- [verify_installation.py](./verify_installation.py) - 安装验证脚本

## 🆘 常见问题

**Q: ffmpeg 仍然找不到？**
A: 确保已重启终端。如果还是不行，手动添加 PATH：
```powershell
$env:PATH += ";C:\Program Files\FFmpeg\bin"
```

**Q: 如何测试转录功能？**
A: 准备一个短视频文件，运行：
```powershell
python helpers\transcribe.py path\to\video.mp4
```

**Q: 可以使用其他 TTS 服务吗？**
A: 当前版本使用 ElevenLabs Scribe。如需其他服务，需要修改 transcribe.py。

---

**部署日期**: 2026-04-22
**项目版本**: 0.1.0
**Python 版本**: 3.14.4
**FFmpeg 版本**: 8.1 (已安装，待重启终端)
