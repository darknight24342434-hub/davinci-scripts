"""
dvr_titles.py — 字卡生成與排列（PIL 透明 PNG → V2 軌）

踩坑記錄（必讀）：
  ★ 檔名千萬別用連號（t1/t2/t3），會被當圖片序列合成 1 個媒體。
    改用 card_open / card_smoke / card_end 等語意命名。
  ★ recordFrame = tl.GetStartFrame() + 秒*fps
    （Timeline 起始 = 108000 / 01:00:00:00 @ 30fps，不是 0）
  ★ 每張 PNG 逐一 ImportMedia，不要一次傳清單給 ImportMedia，
    否則連號問題照樣觸發。

用法：
  python dvr_titles.py cards.json   # 從 JSON 定義批次生成並排入 Resolve
  python dvr_titles.py --preview    # 只預覽產出 PNG，不連 Resolve
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))

# ── 預設字型（PIL / Pillow 必須已安裝） ────────────────────────────────────────
# 設環境變數 DVR_TITLE_FONT 可指定字型檔，優先於這張清單。
DEFAULT_FONT_PATHS = [
    p for p in [
        os.environ.get("DVR_TITLE_FONT"),
        r"C:\Windows\Fonts\msjh.ttc",                    # Windows：微軟正黑體
        r"C:\Windows\Fonts\mingliu.ttc",                 # Windows：細明體
        r"C:\Windows\Fonts\arial.ttf",                   # Windows：最後 fallback
        "/System/Library/Fonts/PingFang.ttc",              # macOS：蘋方
        "/System/Library/Fonts/Supplemental/Arial.ttf",    # macOS：fallback
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux：Noto CJK
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",         # Linux：fallback
    ] if p
]

# 產出的字卡 PNG 放哪裡。設環境變數 DVR_TITLE_CARDS_DIR 可覆寫。
DEFAULT_OUTPUT_DIR = os.environ.get(
    "DVR_TITLE_CARDS_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "_title_cards"),
)

# ── 字卡定義範例（也可從 JSON 讀入） ──────────────────────────────────────────
EXAMPLE_CARDS = [
    # (slug,        text,             pos_sec, dur_sec, position)
    ("card_open",   "Opening title",   2.0,     3.0,    "center"),
    ("card_middle", "第二張字卡",       8.0,     4.0,    "lower"),
    ("card_end",    "End card",       55.0,    4.0,    "center"),
]


def find_font(size: int = 72):
    try:
        from PIL import ImageFont
    except ImportError:
        raise RuntimeError("請先安裝 Pillow：pip install Pillow")

    for path in DEFAULT_FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_title_card(text: str, output_path: str, position: str = "center",
                    width: int = 1920, height: int = 1080,
                    font_size: int = 72, color: tuple = (255, 255, 255, 255)):
    """
    生成透明背景 RGBA PNG 字卡。
    position: 'center' | 'lower' | 'upper'
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise RuntimeError("請先安裝 Pillow：pip install Pillow")

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = find_font(font_size)

    # 計算文字位置
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (width - tw) // 2

    if position == "lower":
        y = int(height * 0.72) - th // 2
    elif position == "upper":
        y = int(height * 0.18) - th // 2
    else:
        y = (height - th) // 2

    # 文字陰影（提升可讀性）
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=color)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_cards(cards: list, output_dir: str = DEFAULT_OUTPUT_DIR) -> list:
    """生成所有字卡 PNG，回傳 (slug, png_path, pos_sec, dur_sec) 清單。"""
    results = []
    for entry in cards:
        slug, text, pos_sec, dur_sec, position = entry
        png_path = os.path.join(output_dir, f"{slug}.png")
        make_title_card(text, png_path, position=position)
        print(f"  [字卡] {slug}.png  '{text}'  @{pos_sec}s  {dur_sec}s  {position}")
        results.append((slug, png_path, pos_sec, dur_sec))
    return results


def place_cards_in_resolve(card_results: list, fps: float = 30.0):
    """
    把生成的 PNG 字卡排入 Resolve 當前 Timeline V2 軌道。
    每張逐一 ImportMedia（避免被當圖片序列）。
    """
    from dvr_core import DVR
    dvr = DVR()
    tl = dvr.timeline
    if tl is None:
        print("[錯誤] 沒有作用中的 Timeline")
        return

    mp = dvr.media_pool
    start_frame = dvr.timeline_start_frame(tl)
    print(f"[Timeline] 起始 frame = {start_frame}（{start_frame/fps/3600:.0f}h offset）")

    # 確保 V2 軌存在
    video_track_count = int(tl.GetTrackCount("video"))
    if video_track_count < 2:
        tl.AddTrack("video")
        print("[軌道] 已新增 V2 字卡軌")

    for slug, png_path, pos_sec, dur_sec in card_results:
        # ★ 逐一匯入，不批量
        items = mp.ImportMedia([png_path])
        if not items:
            print(f"  [警告] 匯入失敗：{png_path}")
            continue
        item = items[0]

        record_frame = start_frame + int(round(pos_sec * fps))
        end_frame = int(round(dur_sec * fps)) - 1

        clip_info = {
            "mediaPoolItem": item,
            "startFrame": 0,
            "endFrame": end_frame,
            "trackIndex": 2,
            "recordFrame": record_frame,
            "mediaType": 1,
        }
        mp.AppendToTimeline([clip_info])
        print(f"  [排入] {slug}  @frame {record_frame}  dur={end_frame+1}f")


def load_cards_from_json(json_path: str) -> list:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return [(c["slug"], c["text"], c["pos_sec"], c["dur_sec"], c.get("position", "center"))
            for c in data]


def write_example_json(path: str = "cards_example.json"):
    data = [{"slug": slug, "text": text, "pos_sec": pos,
              "dur_sec": dur, "position": pos_type}
            for slug, text, pos, dur, pos_type in EXAMPLE_CARDS]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[範例] JSON 已寫出：{path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DaVinci Resolve 字卡生成工具")
    parser.add_argument("cards_json", nargs="?", help="字卡定義 JSON 檔案路徑")
    parser.add_argument("--preview", action="store_true", help="只生成 PNG，不排入 Resolve")
    parser.add_argument("--fps", type=float, default=30.0, help="Timeline FPS（預設 30）")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_DIR, help="PNG 輸出資料夾")
    parser.add_argument("--example", action="store_true", help="輸出範例 JSON 並用範例資料")
    args = parser.parse_args()

    if args.example:
        write_example_json()
        cards = EXAMPLE_CARDS
    elif args.cards_json:
        cards = load_cards_from_json(args.cards_json)
    else:
        print("[提示] 用 --example 生成範例，或傳入 JSON 檔案路徑")
        parser.print_help()
        sys.exit(0)

    print(f"[字卡] 生成 {len(cards)} 張...")
    results = generate_cards(cards, output_dir=args.out)

    if not args.preview:
        print(f"[Resolve] 排入 Timeline...")
        place_cards_in_resolve(results, fps=args.fps)
        print("[完成] 字卡已排入 V2 軌")
    else:
        print(f"[預覽] PNG 存於：{args.out}")
