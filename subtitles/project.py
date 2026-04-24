#!/usr/bin/env python3
"""
视频字幕项目管理器
─────────────────────────────────────────────────────────
用法:
  python project.py new    <项目名>        创建项目目录结构
  python project.py list                   列出所有项目及状态
  python project.py status <项目名>        查看项目详情
  python project.py analyze <项目名>       提取关键帧（供 Claude 分析）
  python project.py run    <项目名>        批量生成字幕视频
  python project.py clean  <项目名>        清理分析帧图（节省空间）
  python project.py open   <项目名>        在文件管理器中打开项目文件夹

典型工作流:
  1. python project.py new    my_video
     → 将源视频放入 projects/my_video/source/
  2. python project.py analyze my_video
     → Claude 查看 analysis/ 中的帧图，将 template.json 放入项目根目录
  3. 在 projects/my_video/content/ 中添加 content_*.json
  4. python project.py run    my_video
     → 输出视频在 projects/my_video/output/
─────────────────────────────────────────────────────────
"""

import subprocess
import sys
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import datetime

# ─── 路径常量 ───────────────────────────────────────────
SCRIPTS_DIR   = Path(__file__).parent.resolve()
PROJECTS_ROOT = SCRIPTS_DIR / "projects"

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}

# ─── 默认项目配置 ───────────────────────────────────────
DEFAULT_PROJECT_CONFIG = {
    "font_path":     "",
    "cjk_font_path": "",
    "font_size":     48,
    "title_size":    0,
    "stroke_width":  5,
    "line_gap":      12,
    "preset":        "fast",
    "crf":           18,
}

# ════════════════════════════════════════════════════════
#  工具函数
# ════════════════════════════════════════════════════════

def project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def find_source_video(name: str) -> Path | None:
    src = project_dir(name) / "source"
    if not src.exists():
        return None
    for f in src.iterdir():
        if f.suffix.lower() in VIDEO_EXTS:
            return f
    return None


def load_project_config(name: str) -> dict:
    cfg_path = project_dir(name) / "project.json"
    cfg = dict(DEFAULT_PROJECT_CONFIG)
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def save_project_config(name: str, cfg: dict):
    cfg_path = project_dir(name) / "project.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _python() -> str:
    return sys.executable


def _print_header(text: str):
    print(f"\n{'─'*50}")
    print(f"  {text}")
    print(f"{'─'*50}")


# ════════════════════════════════════════════════════════
#  命令: new
# ════════════════════════════════════════════════════════

def cmd_new(name: str):
    pdir = project_dir(name)
    if pdir.exists():
        print(f"项目已存在: {pdir}")
        return

    for sub in ["source", "analysis", "content", "output"]:
        (pdir / sub).mkdir(parents=True)

    save_project_config(name, DEFAULT_PROJECT_CONFIG)

    print(f"项目已创建: {pdir}")
    print()
    print("下一步:")
    print(f"  1. 将源视频放入  →  {pdir / 'source'}/")
    print(f"  2. python project.py analyze {name}")
    print(f"  3. Claude 生成 template.json 后放入  →  {pdir}/")
    print(f"  4. 在 {pdir / 'content'}/ 中添加 content_*.json")
    print(f"  5. python project.py run {name}")


# ════════════════════════════════════════════════════════
#  命令: list
# ════════════════════════════════════════════════════════

def _project_summary(name: str) -> str:
    pdir = project_dir(name)
    video   = "Y" if find_source_video(name) else "-"
    ana     = "Y" if (pdir / "analysis" / "video_analysis.json").exists() else "-"
    tpl     = "Y" if (pdir / "template.json").exists() else "-"
    n_cont  = len(list((pdir / "content").glob("*.json"))) if (pdir / "content").exists() else 0
    n_out   = len(list((pdir / "output").glob("*.mp4")))   if (pdir / "output").exists()  else 0
    return (f"[video:{video}] [analysis:{ana}] [template:{tpl}] "
            f"[content:{n_cont}] [output:{n_out}]")


def cmd_list():
    _print_header("所有项目")
    if not PROJECTS_ROOT.exists() or not any(PROJECTS_ROOT.iterdir()):
        print("  (暂无项目，使用 python project.py new <名称> 创建)")
        return
    projects = sorted(p for p in PROJECTS_ROOT.iterdir() if p.is_dir())
    for p in projects:
        print(f"  {p.name:<28}  {_project_summary(p.name)}")
    print()


# ════════════════════════════════════════════════════════
#  命令: status
# ════════════════════════════════════════════════════════

def cmd_status(name: str):
    pdir = project_dir(name)
    if not pdir.exists():
        print(f"项目不存在: {name}  (使用 python project.py new {name} 创建)")
        return

    _print_header(f"项目: {name}")
    print(f"  路径: {pdir}")
    print()

    # source/
    video = find_source_video(name)
    print(f"  source/    {'[有]  ' + video.name if video else '[空]  请放入源视频'}")

    # analysis/
    ana_dir = pdir / "analysis"
    frames  = list(ana_dir.glob("frame_*.png")) if ana_dir.exists() else []
    ana_json = ana_dir / "video_analysis.json"
    if frames:
        print(f"  analysis/  {len(frames)} 帧图像"
              f"{'  [有 video_analysis.json]' if ana_json.exists() else ''}")
    else:
        print(f"  analysis/  [空]  运行 analyze 命令后填充")

    # template.json
    tpl = pdir / "template.json"
    if tpl.exists():
        with open(tpl, encoding="utf-8") as f:
            t = json.load(f)
        slots = t.get("slots", [])
        types = [s.get("type", "?") for s in slots]
        print(f"  template   {len(slots)} 个槽位  {types}")
    else:
        print(f"  template   [未生成]  请让 Claude 分析后在项目根目录创建 template.json")

    # content/
    cont_dir = pdir / "content"
    cont_files = sorted(cont_dir.glob("*.json")) if cont_dir.exists() else []
    if cont_files:
        print(f"  content/   {len(cont_files)} 个 JSON:  {[f.name for f in cont_files]}")
    else:
        print(f"  content/   [空]  在此目录添加 content_*.json")

    # output/
    out_dir   = pdir / "output"
    out_files = list(out_dir.glob("*.mp4")) if out_dir.exists() else []
    if out_files:
        total_mb = sum(f.stat().st_size for f in out_files) / 1024 / 1024
        print(f"  output/    {len(out_files)} 个视频  ({total_mb:.1f} MB 合计)")
    else:
        print(f"  output/    [空]")

    # project.json
    cfg = load_project_config(name)
    font_info = cfg.get("font_path") or "(系统默认)"
    print()
    print(f"  配置: 字号={cfg['font_size']}  描边={cfg['stroke_width']}"
          f"  字体={font_info}")
    print()


# ════════════════════════════════════════════════════════
#  命令: analyze
# ════════════════════════════════════════════════════════

def cmd_analyze(name: str, frames: int = 10):
    pdir  = project_dir(name)
    video = find_source_video(name)

    if not video:
        print(f"错误: {pdir / 'source'}/ 中没有视频文件")
        print("请将源视频（.mp4/.mov 等）放入 source/ 目录")
        return

    ana_dir = pdir / "analysis"
    ana_dir.mkdir(exist_ok=True)

    print(f"分析项目: {name}")
    print(f"源视频:   {video.name}")
    print(f"输出至:   {ana_dir}/")
    print()

    subprocess.run([
        _python(),
        str(SCRIPTS_DIR / "analyze_video.py"),
        str(video),
        "--frames", str(frames),
        "--out",    str(ana_dir),
    ])

    print()
    print(f"完成！请将帧图像交给 Claude 分析，")
    print(f"Claude 输出的 template.json 放到: {pdir}/")


# ════════════════════════════════════════════════════════
#  命令: run
# ════════════════════════════════════════════════════════

def cmd_run(name: str, extra_args: list[str] | None = None):
    pdir = project_dir(name)

    video = find_source_video(name)
    if not video:
        print(f"错误: source/ 中没有视频文件")
        return

    tpl = pdir / "template.json"
    if not tpl.exists():
        print(f"错误: template.json 不存在")
        print(f"请先让 Claude 分析视频，将 template.json 放入: {pdir}/")
        return

    cont_dir   = pdir / "content"
    cont_files = sorted(cont_dir.glob("*.json")) if cont_dir.exists() else []
    if not cont_files:
        print(f"错误: content/ 中没有 JSON 文件")
        print(f"请在 {cont_dir}/ 中添加 content_*.json")
        return

    out_dir = pdir / "output"
    out_dir.mkdir(exist_ok=True)

    cfg = load_project_config(name)

    # 构建命令
    cmd = [
        _python(),
        str(SCRIPTS_DIR / "add_subtitles.py"),
        str(video),
        "--template",    str(tpl),
        "-o",            str(out_dir),
        "--font",        cfg.get("font_path",     ""),
        "--cjk-font",    cfg.get("cjk_font_path", ""),
        "--font-size",   str(cfg.get("font_size",    48)),
        "--title-size",  str(cfg.get("title_size",   0)),
        "--stroke-width",str(cfg.get("stroke_width", 5)),
        "--line-gap",    str(cfg.get("line_gap",     12)),
        "--preset",      cfg.get("preset", "fast"),
        "--crf",         str(cfg.get("crf", 18)),
    ] + [str(f) for f in cont_files] + (extra_args or [])

    print(f"运行项目: {name}")
    print(f"模板:     {tpl.name}  ({len(json.load(open(tpl,'r',encoding='utf-8')).get('slots',[]))} 槽位)")
    print(f"内容:     {len(cont_files)} 个 JSON")
    print(f"输出到:   {out_dir}/")
    print()

    subprocess.run(cmd)


# ════════════════════════════════════════════════════════
#  命令: clean
# ════════════════════════════════════════════════════════

def cmd_clean(name: str, what: str):
    pdir = project_dir(name)

    removed = 0
    freed   = 0

    if what in ("frames", "all"):
        ana_dir = pdir / "analysis"
        for f in list(ana_dir.glob("frame_*.png")):
            freed   += f.stat().st_size
            f.unlink()
            removed += 1
        print(f"删除分析帧图: {removed} 个  ({freed/1024/1024:.1f} MB)")

    if what in ("output", "all"):
        out_dir = pdir / "output"
        videos  = list(out_dir.glob("*.mp4"))
        for v in videos:
            freed   += v.stat().st_size
            v.unlink()
            removed += 1
        print(f"删除输出视频: {len(videos)} 个  ({freed/1024/1024:.1f} MB)")

    if what == "all":
        print(f"共释放: {freed/1024/1024:.1f} MB")


# ════════════════════════════════════════════════════════
#  命令: open
# ════════════════════════════════════════════════════════

def cmd_open(name: str):
    pdir = project_dir(name)
    if not pdir.exists():
        print(f"项目不存在: {name}")
        return
    if sys.platform == "win32":
        os.startfile(str(pdir))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(pdir)])
    else:
        subprocess.run(["xdg-open", str(pdir)])


# ════════════════════════════════════════════════════════
#  命令: config
# ════════════════════════════════════════════════════════

def cmd_config(name: str, key: str | None, value: str | None):
    """查看或修改项目配置。"""
    pdir = project_dir(name)
    if not pdir.exists():
        print(f"项目不存在: {name}")
        return

    cfg = load_project_config(name)

    if key is None:
        # 打印全部配置
        _print_header(f"项目配置: {name}")
        for k, v in cfg.items():
            print(f"  {k:<20} = {v}")
        print()
        print(f"修改: python project.py config {name} <key> <value>")
        return

    if key not in DEFAULT_PROJECT_CONFIG:
        print(f"未知配置项: {key}")
        print(f"可用项: {list(DEFAULT_PROJECT_CONFIG.keys())}")
        return

    # 类型转换
    default_val = DEFAULT_PROJECT_CONFIG[key]
    if isinstance(default_val, int):
        value = int(value)

    cfg[key] = value
    save_project_config(name, cfg)
    print(f"已更新: {key} = {value}")


# ════════════════════════════════════════════════════════
#  CLI 入口
# ════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        prog="project.py",
        description="视频字幕项目管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", metavar="<命令>")
    sub.required = True

    # ── new ──
    p = sub.add_parser("new", help="创建新项目")
    p.add_argument("name", help="项目名称（英文/数字/下划线）")

    # ── list ──
    sub.add_parser("list", help="列出所有项目")

    # ── status ──
    p = sub.add_parser("status", help="查看项目详情")
    p.add_argument("name", help="项目名称")

    # ── analyze ──
    p = sub.add_parser("analyze", help="分析源视频，提取关键帧")
    p.add_argument("name", help="项目名称")
    p.add_argument("--frames", type=int, default=10, help="提取帧数（默认: 10）")

    # ── run ──
    p = sub.add_parser("run", help="批量生成字幕视频")
    p.add_argument("name", help="项目名称")

    # ── clean ──
    p = sub.add_parser("clean", help="清理临时/过程文件")
    p.add_argument("name", help="项目名称")
    p.add_argument("--what", choices=["frames", "output", "all"],
                   default="frames",
                   help="清理内容: frames=分析帧图 / output=输出视频 / all=全部（默认: frames）")

    # ── open ──
    p = sub.add_parser("open", help="在文件管理器中打开项目目录")
    p.add_argument("name", help="项目名称")

    # ── config ──
    p = sub.add_parser("config", help="查看/修改项目配置（字体、字号等）")
    p.add_argument("name",  help="项目名称")
    p.add_argument("key",   nargs="?", default=None,
                   help=f"配置项名称，可选: {list(DEFAULT_PROJECT_CONFIG.keys())}")
    p.add_argument("value", nargs="?", default=None, help="新值")

    args = ap.parse_args()

    if   args.cmd == "new":     cmd_new(args.name)
    elif args.cmd == "list":    cmd_list()
    elif args.cmd == "status":  cmd_status(args.name)
    elif args.cmd == "analyze": cmd_analyze(args.name, args.frames)
    elif args.cmd == "run":     cmd_run(args.name)
    elif args.cmd == "clean":   cmd_clean(args.name, args.what)
    elif args.cmd == "open":    cmd_open(args.name)
    elif args.cmd == "config":  cmd_config(args.name, args.key, args.value)


if __name__ == "__main__":
    main()
