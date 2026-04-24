#!/usr/bin/env python3
"""
批量字幕添加脚本 v2
─────────────────────────────────────────────────────────────────
工作流程（推荐）：
  1. 首次分析: python analyze_video.py demo.mp4
             → Claude 查看关键帧 → 生成 template.json（含时间节点）
  2. 批量生成: python add_subtitles.py demo.mp4 --template template.json content_*.json -o output/

content JSON 只需提供文本，时间/布局由模板控制：
  {
    "output_name": "video_v1.mp4",    ← 可选
    "slots": [
      { "title": "✅ My title:", "lines": ["Line 1", "Line 2"] },
      { "left":  { "title": "✅ Do:", "lines": ["A"] },
        "right": { "title": "❌ Don't:", "lines": ["B"] } }
    ]
  }

兼容模式（无需模板，每个 JSON 含完整时间信息）：
  python add_subtitles.py demo.mp4 full_config_*.json -o output/
─────────────────────────────────────────────────────────────────
"""

import json
import subprocess
import argparse
import sys
import os
import glob
import tempfile
import shutil
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("错误: 需要安装 Pillow: pip install Pillow")
    sys.exit(1)

try:
    from pilmoji import Pilmoji
    from pilmoji.source import BaseSource
except ImportError:
    print("错误: 需要安装 pilmoji: pip install pilmoji")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None

# ─── 本地缓存 Twemoji 图片源 ─────────────────────────────
# 首次使用时从 CDN 下载，之后从本地读取，完全离线可用

_EMOJI_CACHE = Path(__file__).parent / "_emoji_cache"
_TWEMOJI_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{}.png"

# pilmoji 调用 source() 创建实例，共享 session 放在模块级
_shared_session = requests.Session() if requests else None


class CachedTwemojiSource(BaseSource):
    """下载并本地缓存 Twemoji PNG；缓存命中后完全离线工作。
    注意: pilmoji 传入的是类而非实例，因此每次渲染都会 __init__，
         用模块级 _shared_session 复用连接。
    """

    def __init__(self):
        _EMOJI_CACHE.mkdir(exist_ok=True)

    @staticmethod
    def _to_hex(emoji: str) -> str:
        points = [f"{ord(c):x}" for c in emoji if ord(c) != 0xFE0F]
        return "-".join(points)

    def get_emoji(self, emoji: str, /):
        from io import BytesIO
        hex_name   = self._to_hex(emoji)
        cache_path = _EMOJI_CACHE / f"{hex_name}.png"

        if cache_path.exists():
            return BytesIO(cache_path.read_bytes())

        if _shared_session is None:
            return None

        try:
            resp = _shared_session.get(_TWEMOJI_URL.format(hex_name), timeout=8)
            if resp.status_code == 200:
                cache_path.write_bytes(resp.content)
                return BytesIO(resp.content)
        except Exception:
            pass
        return None

    def get_discord_emoji(self, id: int, /):
        return None


# ════════════════════════════════════════════
#  视频工具
# ════════════════════════════════════════════

def get_video_info(video_path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe 失败:\n{r.stderr}")
    s = json.loads(r.stdout)["streams"][0]
    return {"width": int(s["width"]), "height": int(s["height"])}


def has_audio(video_path: Path) -> bool:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "a:0", str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False
    return bool(json.loads(r.stdout).get("streams"))


# ════════════════════════════════════════════
#  字体加载
# ════════════════════════════════════════════

def _try_font(path: str, size: int):
    try:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return None


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    f = _try_font(font_path, size)
    if f:
        return f
    for candidate in [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]:
        f = _try_font(candidate, size)
        if f:
            return f
    return ImageFont.load_default()


def load_cjk_font(cjk_font_path: str, size: int):
    """加载支持中文/日文/韩文的字体，用于含 CJK 字符的行。"""
    f = _try_font(cjk_font_path, size)
    if f:
        return f
    for candidate in [
        "C:/Windows/Fonts/msyhbd.ttc",   # 微软雅黑 Bold
        "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",   # 黑体
        "C:/Windows/Fonts/simsun.ttc",   # 宋体
    ]:
        f = _try_font(candidate, size)
        if f:
            return f
    return None


_CJK_RANGES = (
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Extension A
    (0x20000, 0x2A6DF), # CJK Extension B
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth Forms
    (0x2E80, 0x2EFF),   # CJK Radicals Supplement
)

def _has_cjk(text: str) -> bool:
    return any(any(lo <= ord(c) <= hi for lo, hi in _CJK_RANGES) for c in text)


# ════════════════════════════════════════════
#  文本渲染
# ════════════════════════════════════════════

def time_to_seconds(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    parts = str(t).split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(t)


def draw_line(img: Image.Image, text: str, cx: int, y: int,
              font, cfg: dict, cjk_font=None) -> int:
    """用 pilmoji 渲染一行文字（彩色 emoji 本地缓存 + 描边 + CJK 字体切换）。"""
    f = cjk_font if (_has_cjk(text) and cjk_font) else font
    with Pilmoji(img, source=CachedTwemojiSource) as p:
        tw, th = p.getsize(text, font=f)
        x = cx - tw // 2
        p.text(
            (x, y), text, font=f,
            fill=tuple(cfg.get("font_color",   [255, 255, 255])),
            stroke_width=cfg.get("stroke_width", 5),
            stroke_fill=tuple(cfg.get("stroke_color", [0, 0, 0])),
        )
    return th


def draw_block(img: Image.Image, title: str, lines: list,
               cx: int, y: int, main_font, title_font, cfg: dict,
               cjk_font=None, cjk_title_font=None):
    gap = cfg.get("line_gap", 10)
    cur = y
    if title:
        h   = draw_line(img, title, cx, cur, title_font, cfg, cjk_title_font or cjk_font)
        cur += h + gap
    for line in lines:
        h   = draw_line(img, line, cx, cur, main_font, cfg, cjk_font)
        cur += h + gap


def render_overlay(subtitle: dict, W: int, H: int, cfg: dict) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    font_size  = cfg.get("font_size",    48)
    title_size = cfg.get("title_size",   font_size)
    font_path  = cfg.get("font_path",    "")
    cjk_path   = cfg.get("cjk_font_path", "")

    main_font  = load_font(font_path, font_size)
    title_font = load_font(font_path, title_size)
    cjk_font   = load_cjk_font(cjk_path, font_size)
    cjk_t_font = load_cjk_font(cjk_path, title_size)

    raw_y = subtitle.get("y", "10%")
    if isinstance(raw_y, str) and raw_y.endswith("%"):
        y = int(H * float(raw_y[:-1]) / 100)
    elif raw_y == "center":
        y = H // 4
    else:
        y = int(raw_y)

    sub_type = subtitle.get("type", "single")

    if sub_type == "single":
        draw_block(img, subtitle.get("title", ""), subtitle.get("lines", []),
                   W // 2, y, main_font, title_font, cfg, cjk_font, cjk_t_font)

    elif sub_type == "double":
        left  = subtitle.get("left",  {})
        right = subtitle.get("right", {})
        draw_block(img, left.get("title",  ""), left.get("lines",  []),
                   W // 4, y, main_font, title_font, cfg, cjk_font, cjk_t_font)
        draw_block(img, right.get("title", ""), right.get("lines", []),
                   3 * W // 4, y, main_font, title_font, cfg, cjk_font, cjk_t_font)

    return img


# ════════════════════════════════════════════
#  模板 × 内容 合并
# ════════════════════════════════════════════

def merge_slot(template_slot: dict, content_slot: dict | None) -> dict:
    """
    将模板 slot（含时间/布局）与内容 slot（含文本）合并。
    若 content_slot 为 None，则使用模板中的 sample 文本作为占位。
    """
    slot_type = template_slot["type"]
    merged = {
        "type":  slot_type,
        "start": template_slot["start"],
        "end":   template_slot["end"],
        "y":     template_slot.get("y", "10%"),
    }

    # 无内容时使用 sample
    src = content_slot if content_slot is not None else template_slot.get("sample", {})

    if slot_type == "single":
        merged["title"] = src.get("title", "")
        merged["lines"] = src.get("lines", [])

    elif slot_type == "double":
        left_src  = src.get("left",  {})
        right_src = src.get("right", {})
        merged["left"]  = {"title": left_src.get("title",  ""), "lines": left_src.get("lines",  [])}
        merged["right"] = {"title": right_src.get("title", ""), "lines": right_src.get("lines", [])}

    return merged


def build_subtitles_from_template(template: dict, content: dict) -> list[dict]:
    """
    用模板的 slots（时间框架）+ content 的 slots（文本）合并成最终字幕列表。
    """
    t_slots = template.get("slots", [])
    c_slots = content.get("slots", [])

    if len(c_slots) != len(t_slots):
        print(f"  警告: 模板有 {len(t_slots)} 个槽，内容有 {len(c_slots)} 个槽", end="")
        if len(c_slots) < len(t_slots):
            print(f"，不足部分将使用模板示例文本")
        else:
            print(f"，多余部分将被忽略")

    result = []
    for i, t_slot in enumerate(t_slots):
        c_slot = c_slots[i] if i < len(c_slots) else None
        result.append(merge_slot(t_slot, c_slot))
    return result


# ════════════════════════════════════════════
#  FFmpeg 合成
# ════════════════════════════════════════════

def run_ffmpeg(input_video: Path, overlays: list[dict],
               output_path: Path, cfg: dict, with_audio: bool) -> bool:
    cmd = ["ffmpeg", "-y", "-i", str(input_video)]
    for ov in overlays:
        cmd += ["-i", str(ov["path"])]

    parts, prev = [], "0:v"
    for i, ov in enumerate(overlays):
        label = f"v{i}" if i < len(overlays) - 1 else "vout"
        s, e  = ov["start"], ov["end"]
        parts.append(f"[{prev}][{i+1}:v]overlay=0:0:enable='between(t,{s},{e})'[{label}]")
        prev  = label

    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]"]
    if with_audio:
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += ["-c:v", "libx264",
            "-preset", cfg.get("preset", "fast"),
            "-crf",    str(cfg.get("crf",    18)),
            str(output_path)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    FFmpeg 错误:\n{r.stderr[-1200:]}")
        return False
    return True


# ════════════════════════════════════════════
#  单文件处理
# ════════════════════════════════════════════

def process_one(
    content_json: Path,
    input_video:  Path,
    output_dir:   Path,
    global_cfg:   dict,
    video_info:   dict,
    with_audio:   bool,
    template:     dict | None,
) -> bool:
    with open(content_json, encoding="utf-8") as f:
        data = json.load(f)

    # JSON 内 config 字段可局部覆盖全局参数
    cfg = {**global_cfg, **data.get("config", {})}

    # ── 确定字幕列表 ──
    if template is not None:
        # 模板模式：从模板取时间，从 content 取文本
        subtitles = build_subtitles_from_template(template, data)
    else:
        # 兼容模式：content JSON 含完整 subtitles 字段
        subtitles = data.get("subtitles", [])

    if not subtitles:
        print(f"  跳过 {content_json.name}: 无字幕数据")
        return False

    output_name = data.get("output_name") or (content_json.stem + "_out.mp4")
    output_path = output_dir / output_name
    W, H = video_info["width"], video_info["height"]

    tmpdir = Path(tempfile.mkdtemp(prefix="sub_"))
    try:
        overlays = []
        for i, sub in enumerate(subtitles):
            img = render_overlay(sub, W, H, cfg)
            png = tmpdir / f"ov_{i:04d}.png"
            img.save(str(png))
            overlays.append({
                "path":  png,
                "start": time_to_seconds(sub["start"]),
                "end":   time_to_seconds(sub["end"]),
            })

        mode_tag = "[模板模式]" if template else "[独立模式]"
        print(f"  {mode_tag} {content_json.name} -> {output_path.name}  ({len(subtitles)} 段)")
        ok = run_ffmpeg(input_video, overlays, output_path, cfg, with_audio)
        if ok:
            mb = output_path.stat().st_size / 1024 / 1024
            print(f"    完成 ({mb:.1f} MB)")
        return ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="批量为视频添加字幕（支持模板模式 + 独立模式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
─── 模板模式（推荐）───────────────────────────────────────────
  content JSON 只需提供文本槽 slots，时间/布局来自 template.json：
  {
    "output_name": "v1.mp4",
    "slots": [
      { "title": "✅ My title:", "lines": ["Line A", "Line B"] },
      { "left":  { "title": "✅ Do:",    "lines": ["Good"] },
        "right": { "title": "❌ Don't:", "lines": ["Bad"]  } }
    ]
  }

─── 独立模式（兼容旧格式）────────────────────────────────────
  每个 JSON 包含完整 subtitles 字段（含 type/start/end/y/title/lines）
""",
    )
    ap.add_argument("input_video", help="基础视频路径")
    ap.add_argument("json_files",  nargs="+", help="content JSON 文件（支持 *.json）")
    ap.add_argument("--template",  default="", help="模板 JSON 路径（由 Claude 生成）")
    ap.add_argument("-o", "--output-dir", default="output", help="输出目录（默认: output）")
    ap.add_argument("--font",        default="",           help="主字体路径，用于英文/符号 (.ttf/.otf)")
    ap.add_argument("--cjk-font",    default="",           help="CJK字体路径，用于中日韩文字（默认自动选微软雅黑/黑体）")
    ap.add_argument("--font-size",   type=int, default=48, help="正文字号（默认: 48）")
    ap.add_argument("--title-size",  type=int, default=0,  help="标题字号（默认: 同正文）")
    ap.add_argument("--stroke-width",type=int, default=5,  help="描边宽度（默认: 5）")
    ap.add_argument("--font-color",  default="255,255,255",help="字色 R,G,B（默认: 白）")
    ap.add_argument("--stroke-color",default="0,0,0",      help="描边色 R,G,B（默认: 黑）")
    ap.add_argument("--line-gap",    type=int, default=10, help="行间距像素（默认: 10）")
    ap.add_argument("--preset",      default="fast",       help="FFmpeg 预设（默认: fast）")
    ap.add_argument("--crf",         type=int, default=18, help="视频质量 CRF（默认: 18）")
    args = ap.parse_args()

    # ── 输入验证 ──
    input_video = Path(args.input_video)
    if not input_video.exists():
        print(f"错误: 视频文件不存在: {input_video}")
        sys.exit(1)

    template = None
    if args.template:
        tp = Path(args.template)
        if not tp.exists():
            print(f"错误: 模板文件不存在: {tp}")
            sys.exit(1)
        with open(tp, encoding="utf-8") as f:
            template = json.load(f)
        print(f"模板: {tp.name}  ({len(template.get('slots', []))} 个槽位)")

    # ── 视频信息 ──
    try:
        video_info = get_video_info(input_video)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)
    with_audio = has_audio(input_video)
    print(f"视频: {input_video.name}  {video_info['width']}x{video_info['height']}  {'[有音轨]' if with_audio else '[无音轨]'}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def parse_rgb(s):
        return [int(x.strip()) for x in s.split(",")]

    global_cfg = {
        "font_path":     args.font,
        "cjk_font_path": args.cjk_font,
        "font_size":     args.font_size,
        "title_size":    args.title_size or args.font_size,
        "stroke_width":  args.stroke_width,
        "font_color":    parse_rgb(args.font_color),
        "stroke_color":  parse_rgb(args.stroke_color),
        "line_gap":      args.line_gap,
        "preset":        args.preset,
        "crf":           args.crf,
    }
    if template and "config" in template:
        global_cfg.update(template["config"])

    # ── 展开 JSON 文件列表 ──
    json_paths: list[Path] = []
    for pattern in args.json_files:
        matched = sorted(glob.glob(pattern))
        if matched:
            json_paths.extend(Path(p) for p in matched)
        else:
            p = Path(pattern)
            if p.exists():
                json_paths.append(p)
            else:
                print(f"警告: 未找到文件: {pattern}")

    if not json_paths:
        print("错误: 未找到任何 JSON 文件")
        sys.exit(1)

    print(f"共 {len(json_paths)} 个 content JSON -> 输出到 {output_dir}/\n")

    ok_n = fail_n = 0
    for jp in json_paths:
        try:
            ok = process_one(jp, input_video, output_dir, global_cfg,
                             video_info, with_audio, template)
        except Exception as e:
            print(f"  异常: {jp.name}: {e}")
            ok = False
        if ok:
            ok_n += 1
        else:
            fail_n += 1

    print(f"\n{'='*45}")
    print(f"完成: 成功 {ok_n} 个，失败 {fail_n} 个")


if __name__ == "__main__":
    main()
