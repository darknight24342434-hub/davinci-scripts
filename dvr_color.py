"""
dvr_color.py — 調色、LUT、CDL 導演風格套用
用法：python dvr_color.py --style wkw
      python dvr_color.py --lut <LUT路徑>
      python dvr_color.py --drx <DRX路徑>
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from dvr_core import DVR

# ── 導演風格 CDL 預設 ──────────────────────────────────────────────────────────
DIRECTOR_STYLES = {
    "wkw": {
        "_name": "王家衛（Wong Kar-wai）夜色",
        "NodeIndex":   "1",
        "Slope":       "1.12 1.02 0.88",   # 暖紅金高光，壓藍
        "Offset":      "0.005 0.02 0.05",  # 青綠霧感陰影
        "Power":       "0.95 0.97 1.02",   # 暖中間調
        "Saturation":  "1.30",
    },
    "fincher": {
        "_name": "大衛芬奇（Fincher）冷調商業",
        "NodeIndex":   "1",
        "Slope":       "0.95 0.98 1.05",   # 冷藍色調
        "Offset":      "-0.01 0.00 0.02",  # 壓陰影
        "Power":       "1.02 1.00 0.96",
        "Saturation":  "0.85",             # 去飽和
    },
    "koreeda": {
        "_name": "是枝裕和（Koreeda）人文自然",
        "NodeIndex":   "1",
        "Slope":       "1.00 1.02 0.98",
        "Offset":      "0.01 0.01 0.005",  # 輕微暖陰影
        "Power":       "0.98 0.99 1.00",
        "Saturation":  "1.10",
    },
    "jia": {
        "_name": "賈樟柯（Jia Zhangke）社會寫實",
        "NodeIndex":   "1",
        "Slope":       "0.90 0.92 0.95",   # 壓低整體亮度
        "Offset":      "0.02 0.02 0.02",   # 略抬陰影
        "Power":       "1.00 1.00 0.98",
        "Saturation":  "0.75",             # 低飽和寫實感
    },
    "neutral": {
        "_name": "中性（不套任何風格）",
        "NodeIndex":   "1",
        "Slope":       "1.00 1.00 1.00",
        "Offset":      "0.00 0.00 0.00",
        "Power":       "1.00 1.00 1.00",
        "Saturation":  "1.00",
    },
}


def apply_style(style_key: str, track: int = 1):
    """套用預設導演風格 CDL 到當前 Timeline V1 所有鏡頭。"""
    if style_key not in DIRECTOR_STYLES:
        print(f"[錯誤] 未知風格：{style_key}")
        print(f"可用風格：{', '.join(k for k in DIRECTOR_STYLES if not k.startswith('_'))}")
        return

    dvr = DVR()
    tl = dvr.timeline
    if tl is None:
        print("[錯誤] 沒有作用中的 Timeline")
        return

    style = DIRECTOR_STYLES[style_key]
    cdl = {k: v for k, v in style.items() if not k.startswith("_")}
    print(f"[調色] 套用風格：{style['_name']}")
    dvr.apply_cdl(tl, cdl, track=track)
    print(f"[完成] CDL 已套用至 V{track} 所有鏡頭")


def list_styles():
    print("可用導演風格：")
    for k, v in DIRECTOR_STYLES.items():
        print(f"  {k:12s}  {v['_name']}")


def apply_lut_to_current(lut_path: str, node_index: int = 1):
    dvr = DVR()
    tl = dvr.timeline
    if tl is None:
        print("[錯誤] 沒有作用中的 Timeline")
        return

    print(f"[調色] 套用 LUT：{lut_path}  → Node {node_index}")
    ok = dvr.apply_lut(tl, lut_path, node_index)
    print(f"[{'完成' if ok else '警告'}] LUT 套用{'成功' if ok else '部分失敗（檢查 node 索引）'}")


def apply_drx_to_current(drx_path: str, grade_mode: int = 0):
    """
    grade_mode:
      0 = 無調色曲線（只套結構）
      1 = 套用所有調色
      2 = 套用調色但保留輸入調色
    """
    dvr = DVR()
    tl = dvr.timeline
    if tl is None:
        print("[錯誤] 沒有作用中的 Timeline")
        return

    print(f"[調色] 套用 DRX Still：{drx_path}  mode={grade_mode}")
    ok = dvr.apply_drx(tl, drx_path, grade_mode)
    print(f"[{'完成' if ok else '錯誤'}] DRX 套用{'成功' if ok else '失敗'}")


def list_luts(dvr: DVR = None):
    """列出 Resolve 已知的 LUT 清單（透過 GetLUTList）"""
    if dvr is None:
        dvr = DVR()
    luts = dvr.project.GetLUTList() if hasattr(dvr.project, "GetLUTList") else []
    if not luts:
        print("[提示] 無法取得 LUT 清單，請在 Resolve → 色彩管理 → LUT 資料夾 手動確認")
        return
    for name, path in luts.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DaVinci Resolve 調色工具")
    parser.add_argument("--style", help="導演風格 CDL (wkw/fincher/koreeda/jia/neutral)", default=None)
    parser.add_argument("--lut", help="LUT 檔案路徑 (.cube / .3dl)", default=None)
    parser.add_argument("--drx", help="DRX Still 檔案路徑", default=None)
    parser.add_argument("--node", type=int, default=1, help="套用 LUT 的 node 索引（1-based）")
    parser.add_argument("--mode", type=int, default=0, help="DRX grade mode (0/1/2)")
    parser.add_argument("--list-styles", action="store_true", help="列出所有導演風格")
    parser.add_argument("--list-luts", action="store_true", help="列出可用 LUT")
    args = parser.parse_args()

    if args.list_styles:
        list_styles()
    if args.list_luts:
        list_luts()
    if args.style:
        apply_style(args.style)
    if args.lut:
        apply_lut_to_current(args.lut, node_index=args.node)
    if args.drx:
        apply_drx_to_current(args.drx, grade_mode=args.mode)
    if not any([args.style, args.lut, args.drx, args.list_styles, args.list_luts]):
        parser.print_help()
