#!/usr/bin/env python3
"""
视频分析辅助脚本 - 由 Claude 调用
提取视频元数据 + 关键帧图像，Claude 据此生成 template.json

用法:
  python analyze_video.py demo.mp4
  python analyze_video.py demo.mp4 --frames 12 --out analysis/
"""

import subprocess
import json
import argparse
import sys
from pathlib import Path


def get_video_meta(video_path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe 失败:\n{r.stderr}")
    return json.loads(r.stdout)


def extract_frames(video_path: Path, timestamps: list[float], out_dir: Path) -> list[dict]:
    frames = []
    for i, t in enumerate(timestamps):
        out_png = out_dir / f"frame_{i+1:02d}_{t:.2f}s.png"
        cmd = [
            "ffmpeg", "-y", "-ss", str(t), "-i", str(video_path),
            "-frames:v", "1", "-update", "1", str(out_png),
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and out_png.exists():
            frames.append({"time_sec": t, "time_str": fmt_time(t), "path": str(out_png)})
        else:
            print(f"  警告: 无法提取 t={t:.2f}s 的帧")
    return frames


def fmt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def main():
    ap = argparse.ArgumentParser(description="提取视频关键帧，供 Claude 生成 template.json")
    ap.add_argument("video", help="视频文件路径")
    ap.add_argument("--frames", type=int, default=10, help="提取帧数 (默认: 10)")
    ap.add_argument("--out", default="", help="输出目录 (默认: <视频名>_analysis/)")
    args = ap.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"错误: 文件不存在: {video_path}")
        sys.exit(1)

    out_dir = Path(args.out) if args.out else video_path.parent / f"{video_path.stem}_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 获取元数据 ──
    print(f"分析视频: {video_path.name}")
    probe   = get_video_meta(video_path)
    fmt     = probe["format"]
    v_stream = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
    a_stream = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)

    duration  = float(fmt.get("duration", 0))
    width     = int(v_stream.get("width",  0))
    height    = int(v_stream.get("height", 0))
    fps_raw   = v_stream.get("r_frame_rate", "30/1")
    num, den  = fps_raw.split("/")
    fps       = round(int(num) / int(den), 2)

    print(f"  分辨率: {width}×{height}")
    print(f"  时长:   {duration:.2f}s  ({fmt_time(duration)})")
    print(f"  帧率:   {fps} fps")
    print(f"  音轨:   {'有' if a_stream else '无'}")

    # ── 提取均匀分布的帧 ──
    n = args.frames
    # 避免提取第 0 帧和最后一帧（可能是黑帧）
    margin   = min(0.5, duration * 0.03)
    usable   = duration - 2 * margin
    interval = usable / (n - 1) if n > 1 else usable
    timestamps = [round(margin + interval * i, 3) for i in range(n)]

    print(f"\n提取 {n} 帧到 {out_dir}/")
    frames = extract_frames(video_path, timestamps, out_dir)
    print(f"  提取成功: {len(frames)}/{n} 帧")

    # ── 保存 analysis.json ──
    analysis = {
        "video":    str(video_path),
        "width":    width,
        "height":   height,
        "duration": duration,
        "fps":      fps,
        "has_audio": a_stream is not None,
        "frames":   frames,
    }
    analysis_json = out_dir / "video_analysis.json"
    with open(analysis_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # ── 给 Claude 的提示 ──
    print(f"\n分析结果已保存至: {analysis_json}")
    print("\n" + "="*60)
    print("请 Claude 查看以下帧图像，然后生成 template.json：")
    print("="*60)
    for fr in frames:
        print(f"  [{fr['time_str']}]  {fr['path']}")
    print()
    print("Claude 应输出包含以下结构的 template.json：")
    print("""  {
    "video": "<视频文件名>",
    "config": { "font_size": 48, "stroke_width": 5, "line_gap": 10 },
    "slots": [
      {
        "id": 1,
        "type": "single",          // single | double
        "start": <秒>,
        "end":   <秒>,
        "y":     "10%",            // 字幕起始 y 位置
        "sample": {                // 示例文本（仅供参考格式）
          "title": "示例标题:",
          "lines": ["示例行1", "示例行2"]
        }
      }
    ]
  }""")


if __name__ == "__main__":
    main()
