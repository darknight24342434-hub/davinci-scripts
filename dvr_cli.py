"""
dvr_cli.py — DaVinci Resolve 統一命令列入口
用法：python dvr_cli.py <命令> [參數]

命令清單：
  info                    顯示當前專案資訊
  import <路徑>           匯入素材資料夾
  timeline <路徑>         匯入素材並建立 Timeline
  render <輸出路徑>       輸出當前 Timeline (預設 H.264，非阻塞)
  render-all <輸出路徑>   輸出所有 Timeline
  style <風格名稱>        套用導演風格 CDL（wkw/fincher/koreeda/jia）
  lut <LUT路徑>           對當前 Timeline 所有素材套用 LUT
  drx <DRX路徑>           套用 DRX 調色 Still
  titles <cards.json>     生成字卡 PNG 並排入 V2 軌
  titles-preview <json>   只生成字卡 PNG，不排入 Resolve
  styles                  列出所有可用導演風格
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from dvr_core import DVR


def cmd_info():
    dvr = DVR()
    info = dvr.info()
    print(f"專案名稱：{info['name']}")
    print(f"解析度　：{info['width']}x{info['height']}  @{info['fps']}fps")
    print(f"Timeline：{info['timeline_count']} 條")
    tl = dvr.timeline
    if tl:
        print(f"當前 TL ：{tl.GetName()}")


def cmd_import(folder):
    from dvr_media import import_folder
    clips = import_folder(folder)
    print(f"匯入完成：{len(clips)} 個素材")


def cmd_timeline(folder):
    from dvr_media import import_and_make_timeline
    import_and_make_timeline(folder)


def cmd_render(output_dir, preset="h264"):
    from dvr_render import render_current_timeline
    render_current_timeline(output_dir, preset)


def cmd_render_all(output_dir, preset="h264"):
    from dvr_render import render_all_timelines
    render_all_timelines(output_dir, preset)


def cmd_style(style_key):
    from dvr_color import apply_style
    apply_style(style_key)


def cmd_styles():
    from dvr_color import list_styles
    list_styles()


def cmd_lut(lut_path, node=1):
    from dvr_color import apply_lut_to_current
    apply_lut_to_current(lut_path, int(node))


def cmd_drx(drx_path, mode=0):
    from dvr_color import apply_drx_to_current
    apply_drx_to_current(drx_path, int(mode))


def cmd_titles(json_path, fps=30.0):
    from dvr_titles import load_cards_from_json, generate_cards, place_cards_in_resolve
    cards = load_cards_from_json(json_path)
    results = generate_cards(cards)
    place_cards_in_resolve(results, fps=float(fps))


def cmd_titles_preview(json_path):
    from dvr_titles import load_cards_from_json, generate_cards
    cards = load_cards_from_json(json_path)
    generate_cards(cards)


COMMANDS = {
    "info":            (cmd_info,           0, "顯示當前專案資訊"),
    "import":          (cmd_import,         1, "匯入素材資料夾"),
    "timeline":        (cmd_timeline,       1, "匯入並建立 Timeline"),
    "render":          (cmd_render,         1, "輸出當前 Timeline（非阻塞）"),
    "render-all":      (cmd_render_all,     1, "輸出所有 Timeline"),
    "style":           (cmd_style,          1, "套用導演風格 CDL"),
    "styles":          (cmd_styles,         0, "列出所有導演風格"),
    "lut":             (cmd_lut,            1, "對當前 TL 套用 LUT"),
    "drx":             (cmd_drx,            1, "套用 DRX 調色 Still"),
    "titles":          (cmd_titles,         1, "生成字卡並排入 V2"),
    "titles-preview":  (cmd_titles_preview, 1, "只生成字卡 PNG"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    extra_args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"[錯誤] 未知命令：{cmd}")
        print("可用命令：" + ", ".join(COMMANDS.keys()))
        sys.exit(1)

    fn, min_args, desc = COMMANDS[cmd]

    if len(extra_args) < min_args:
        print(f"[錯誤] '{cmd}' 需要 {min_args} 個參數")
        sys.exit(1)

    try:
        fn(*extra_args)
    except RuntimeError as e:
        print(f"[失敗] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
