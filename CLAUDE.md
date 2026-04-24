# Video Production Workflow

This directory contains two complementary tools for video editing and subtitle production. Claude uses both together.

## Tool Map

| Tool | Location | Purpose |
|------|----------|---------|
| `video-use` skill | `~/.claude/skills/video-use` (symlinked) | AI-driven editing: cuts, grades, SRT speech subtitles, animations |
| `subtitles/` | `./subtitles/` | Batch text-card overlays: same base video → N output variants |

---

## When to use which tool

**Use `video-use` when:**
- Raw footage needs to be cut, trimmed, or multi-take assembled
- Speech-based SRT captions needed (synced to spoken words)
- Color grading or animation overlays are required
- Output: `edit/final.mp4` with optional burned-in captions

**Use `subtitles/` when:**
- A base video already exists and you need to batch-generate variants with different text cards
- Overlay content is custom text (titles, bullet points, do/don't comparisons, callouts)
- CJK (Chinese/Japanese/Korean) or emoji text is required
- Output: multiple MP4 files, one per content JSON

**Combined workflow:** video-use first → then subtitles batch.

---

## subtitles/ Tool Reference

All scripts live in `./subtitles/`. Use absolute paths when calling from elsewhere.

### Project manager (main entry point)
```bash
cd subtitles
python project.py new    <name>           # create project skeleton
python project.py analyze <name>          # extract keyframes for template generation
python project.py run    <name>           # batch render all content JSONs
python project.py list                    # show all projects and status
python project.py status  <name>          # detail view
python project.py config  <name> [k] [v] # read/write per-project config
python project.py clean   <name>          # remove temp frames
python project.py open    <name>          # open in file explorer
```

### Direct script usage
```bash
python subtitles/analyze_video.py <video> [--frames N] [--out dir]
python subtitles/add_subtitles.py <video> [--template t.json] content_*.json -o output/
```

### Template JSON (time skeleton, Claude generates this after analyzing frames)
```json
{
  "video": "source.mp4",
  "config": { "font_size": 48, "stroke_width": 5, "line_gap": 12 },
  "slots": [
    {
      "id": 1, "type": "single",
      "start": 1.0, "end": 7.5, "y": "10%",
      "sample": { "title": "Example:", "lines": ["Line 1", "Line 2"] }
    },
    {
      "id": 2, "type": "double",
      "start": 8.0, "end": 10.0, "y": "10%",
      "sample": {
        "left":  { "title": "✅ Do:",    "lines": ["Good"] },
        "right": { "title": "❌ Don't:", "lines": ["Bad"]  }
      }
    }
  ]
}
```

### Content JSON (text only, timing comes from template)
```json
{
  "output_name": "video_v1.mp4",
  "slots": [
    { "title": "✅ Results in 3 months:", "lines": ["Progressive overload", "High protein diet"] },
    {
      "left":  { "title": "✅ Do:",    "lines": ["Train smart"] },
      "right": { "title": "❌ Don't:", "lines": ["Random workouts"] }
    }
  ]
}
```

### Per-project config keys
| Key | Default | Notes |
|-----|---------|-------|
| `font_path` | `""` | Main font (.ttf/.otf). Falls back to Impact on Win |
| `cjk_font_path` | `""` | CJK font. Falls back to 微软雅黑 on Win, PingFang on Mac |
| `font_size` | 48 | Body text size (px) |
| `title_size` | 0 | Title size; 0 = same as font_size |
| `stroke_width` | 5 | Outline width (px) |
| `line_gap` | 12 | Line spacing (px) |
| `preset` | `fast` | FFmpeg encode speed |
| `crf` | 18 | Video quality (18=high, 23=standard) |

---

## Combined workflow steps

1. **Edit footage** with video-use → get `<videos_dir>/edit/final.mp4`
2. **Create subtitle project**: `python subtitles/project.py new <name>`
3. **Place base video** in `subtitles/projects/<name>/source/` (copy or symlink `final.mp4`)
4. **Analyze**: `python subtitles/project.py analyze <name>` — Claude reads frames, generates `template.json`
5. **Write content JSONs** in `subtitles/projects/<name>/content/` (one per variant)
6. **Batch render**: `python subtitles/project.py run <name>` → outputs in `subtitles/projects/<name>/output/`

---

## video-use helpers reference

Helpers live in `~/.claude/skills/video-use/helpers/` (or `D:/Videos/claude_video/video-use-main/helpers/`).

```bash
python helpers/transcribe.py <video>           # single transcription (ElevenLabs Scribe)
python helpers/transcribe_batch.py <dir>       # 4-worker parallel transcription
python helpers/pack_transcripts.py --edit-dir <dir>  # pack to takes_packed.md
python helpers/timeline_view.py <video> <start> <end>  # filmstrip+waveform PNG
python helpers/render.py <edl.json> -o <out>   # EDL → final.mp4
python helpers/grade.py <in> -o <out>          # color grade
```

EDL format: see `~/.claude/skills/video-use/SKILL.md` § EDL format.

---

## Notes

- video-use requires `ELEVENLABS_API_KEY` in `D:/Videos/claude_video/video-use-main/.env`
- subtitles requires `ffmpeg` on PATH and `pip install Pillow pilmoji requests`
- All video-use session outputs go to `<videos_dir>/edit/` — never inside the skill directory
- Emoji in subtitles: first use downloads from Twemoji CDN, then cached in `subtitles/_emoji_cache/`
