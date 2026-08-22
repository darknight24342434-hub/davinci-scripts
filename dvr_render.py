"""
dvr_render.py — 批次輸出腳本
用法：python dvr_render.py <輸出資料夾> [選項]
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(__file__))
from dvr_core import DVR

# ── 常用 Preset 快查表 ────────────────────────────────────────────────────────
PRESETS = {
    "h264":    ("mp4",  "H264",       "H.264 Master"),
    "h265":    ("mp4",  "H265",       "H.265 Master"),
    "prores":  ("mov",  "ProRes422HQ","ProRes Master"),
    "dnxhd":  ("mxf",  "DNxHD",      "DNxHD Master"),
    "youtube": ("mp4",  "H264",       "YouTube 1080p"),
}


def render_current_timeline(output_dir: str, preset_key: str = "h264",
                             custom_name: str = None):
    dvr = DVR()
    info = dvr.info()
    print(f"[專案] {info['name']}  {info['width']}x{info['height']} @ {info['fps']}fps")

    tl = dvr.timeline
    if tl is None:
        print("[錯誤] 沒有作用中的 Timeline")
        return False

    tl_name = tl.GetName()
    fmt, codec, preset_name = PRESETS.get(preset_key, PRESETS["h264"])

    os.makedirs(output_dir, exist_ok=True)

    if custom_name:
        dvr.project.SetRenderSettings({"CustomName": custom_name})

    job_id = dvr.add_render_job(tl, output_dir, preset=preset_name, fmt=fmt, codec=codec)
    print(f"[加入] Timeline '{tl_name}'  →  {output_dir}  [{preset_key.upper()}]  job={job_id}")

    ok = dvr.render_all_jobs(wait=True)
    if ok:
        print(f"[完成] 輸出完成")
    else:
        print(f"[錯誤] 輸出失敗")
    return ok


def render_all_timelines(output_dir: str, preset_key: str = "h264"):
    dvr = DVR()
    info = dvr.info()
    print(f"[專案] {info['name']}  共 {info['timeline_count']} 條 Timeline")

    fmt, codec, preset_name = PRESETS.get(preset_key, PRESETS["h264"])
    os.makedirs(output_dir, exist_ok=True)

    timelines = dvr.get_all_timelines()
    for tl in timelines:
        job_id = dvr.add_render_job(tl, output_dir, preset=preset_name, fmt=fmt, codec=codec)
        print(f"  加入：{tl.GetName()}  job={job_id}")

    print(f"[輸出] 開始批次輸出...")
    dvr.goto("deliver")
    ok = dvr.project.StartRendering()
    if ok:
        while dvr.project.IsRenderingInProgress():
            time.sleep(2)
        dvr.project.DeleteAllRenderJobs()
        print(f"[完成] 全部 {len(timelines)} 條 Timeline 輸出完成")
    else:
        print("[錯誤] 無法啟動輸出")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DaVinci Resolve 批次輸出")
    parser.add_argument("output_dir", help="輸出資料夾路徑")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="h264",
                        help="輸出格式 (預設: h264)")
    parser.add_argument("--all", action="store_true",
                        help="輸出所有 Timeline（預設只輸出當前）")
    parser.add_argument("--name", help="自訂輸出檔名", default=None)
    args = parser.parse_args()

    if args.all:
        render_all_timelines(args.output_dir, args.preset)
    else:
        render_current_timeline(args.output_dir, args.preset, custom_name=args.name)
