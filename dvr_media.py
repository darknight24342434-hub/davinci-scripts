"""
dvr_media.py — Media Pool 匯入與整理腳本
用法：python dvr_media.py <素材資料夾路徑> [--bin <bin名稱>]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from dvr_core import DVR


def import_folder(folder_path: str, bin_name: str = None, sort_by_name: bool = True):
    dvr = DVR()
    print(f"[專案] {dvr.info()['name']}")

    # 可選：建立 bin
    target_bin = None
    if bin_name:
        target_bin = dvr.create_bin(bin_name)
        print(f"[Bin] 已建立：{bin_name}")

    # 匯入
    print(f"[匯入] {folder_path}")
    clips = dvr.import_clips(folder_path)
    if not clips:
        print("[警告] 沒有匯入任何素材，請確認路徑與格式")
        return []

    print(f"[完成] 匯入 {len(clips)} 個素材")

    if sort_by_name:
        clips = sorted(clips, key=lambda c: c.GetClipProperty("File Name"))

    return clips


def import_and_make_timeline(folder_path: str, timeline_name: str = "Timeline 1",
                              fps: str = "24", bin_name: str = None):
    dvr = DVR()
    clips = import_folder(folder_path, bin_name=bin_name)
    if not clips:
        return

    tl = dvr.create_timeline(timeline_name)
    dvr.append_clips(clips)
    dvr.save()

    print(f"[Timeline] '{timeline_name}' 已建立，含 {len(clips)} 個素材")
    return tl


def list_media_pool(dvr: DVR = None):
    if dvr is None:
        dvr = DVR()

    def walk_folder(folder, indent=0):
        prefix = "  " * indent
        print(f"{prefix}[{folder.GetName()}]")
        for clip in folder.GetClipList():
            name = clip.GetClipProperty("File Name")
            dur = clip.GetClipProperty("Duration")
            print(f"{prefix}  {name}  ({dur})")
        for sub in folder.GetSubFolderList():
            walk_folder(sub, indent + 1)

    mp = dvr.media_pool
    walk_folder(mp.GetRootFolder())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Media Pool 匯入工具")
    parser.add_argument("folder", help="素材資料夾路徑")
    parser.add_argument("--bin", help="建立並匯入到指定 Bin 名稱", default=None)
    parser.add_argument("--timeline", help="自動建立 Timeline 名稱", default=None)
    parser.add_argument("--list", action="store_true", help="列出 Media Pool 內容")
    args = parser.parse_args()

    if args.list:
        list_media_pool()
    elif args.timeline:
        import_and_make_timeline(args.folder, args.timeline, bin_name=args.bin)
    else:
        import_folder(args.folder, bin_name=args.bin)
