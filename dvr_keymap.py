"""
dvr_keymap.py — DaVinci Resolve 快捷鍵「母版備份 / 一鍵部署」工具

背景：
  Resolve 的快捷鍵存在 keyboard.preset.xml，內容是二進位封包(PresetListBA)，
  無法用純文字逐條編輯。所以「定義快捷鍵」必須在 UI 做一次(Keyboard
  Customization → Save As 存成具名 preset)。之後本工具負責把它存成母版、
  一鍵還原/部署到任何機器，永不用再手動設。

★ 鐵則：deploy/restore 一定要在 Resolve「關閉」時做。
  Resolve 開著時設定在記憶體，關閉會把檔覆寫回去 → 你寫的會被蓋掉。
  本工具偵測到 Resolve 執行中會「拒絕部署」。

用法：
  python dvr_keymap.py backup  <母版名>     # 把目前快捷鍵存成母版
  python dvr_keymap.py deploy  <母版名>     # 把母版部署回 Resolve(需關閉)
  python dvr_keymap.py list                 # 列出所有母版
  python dvr_keymap.py status               # 顯示現況(檔案時間 / Resolve 是否開著)
  選項 --with-config  連 config.user.xml 一起處理(整份偏好，較重，預設只處理快捷鍵)
"""

import os
import sys
import shutil
import argparse
import subprocess

# ── 路徑 ──────────────────────────────────────────────────────────────────────
PREF_DIR = os.path.join(
    os.environ["APPDATA"], "Blackmagic Design", "DaVinci Resolve", "Preferences"
)
KEYBOARD_FILE = os.path.join(PREF_DIR, "keyboard.preset.xml")
CONFIG_FILE = os.path.join(PREF_DIR, "config.user.xml")

MASTERS_DIR = os.path.join(os.path.dirname(__file__), "keymaps")


# ── Resolve 執行偵測 ──────────────────────────────────────────────────────────
def is_resolve_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/NH"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return "Resolve.exe" in out
    except Exception:
        # 偵測失敗時保守當作「開著」，避免誤覆寫
        return True


def _files(with_config: bool) -> list:
    files = [KEYBOARD_FILE]
    if with_config:
        files.append(CONFIG_FILE)
    return files


# ── 指令 ──────────────────────────────────────────────────────────────────────
def cmd_status():
    print(f"[Preferences] {PREF_DIR}")
    for f in (KEYBOARD_FILE, CONFIG_FILE):
        if os.path.exists(f):
            import datetime
            mt = datetime.datetime.fromtimestamp(os.path.getmtime(f))
            print(f"  {os.path.basename(f):22s} {mt:%Y-%m-%d %H:%M:%S}")
        else:
            print(f"  {os.path.basename(f):22s} (不存在)")
    print(f"[Resolve] {'執行中 ⚠️ 部署前請先關閉' if is_resolve_running() else '未執行 ✓ 可部署'}")
    print(f"[母版庫] {MASTERS_DIR}")
    cmd_list(quiet=True)


def cmd_list(quiet=False):
    if not os.path.isdir(MASTERS_DIR):
        if not quiet:
            print("[母版] 尚無任何母版")
        return
    masters = [d for d in os.listdir(MASTERS_DIR)
               if os.path.isdir(os.path.join(MASTERS_DIR, d))]
    if not masters:
        print("[母版] 尚無任何母版")
        return
    print("[母版] 可用清單：")
    for m in sorted(masters):
        files = os.listdir(os.path.join(MASTERS_DIR, m))
        print(f"  - {m}  ({', '.join(files)})")


def cmd_backup(name: str, with_config: bool = False):
    if is_resolve_running():
        print("[提醒] Resolve 執行中。請先在 UI 用 Keyboard Customization → Save As")
        print("       存好你的具名 preset(這步會把快捷鍵寫進檔案)，再來備份。")
        print("       若你已存過且確定檔案是最新，可繼續，但建議關閉 Resolve 後再備份最保險。")

    dst = os.path.join(MASTERS_DIR, name)
    os.makedirs(dst, exist_ok=True)
    copied = []
    for f in _files(with_config):
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
            copied.append(os.path.basename(f))
        else:
            print(f"[警告] 找不到 {f}")
    print(f"[備份] 母版 '{name}' 已存：{', '.join(copied)}")
    print(f"       位置：{dst}")


def cmd_deploy(name: str, with_config: bool = False):
    src = os.path.join(MASTERS_DIR, name)
    if not os.path.isdir(src):
        print(f"[錯誤] 找不到母版：{name}")
        cmd_list()
        return

    if is_resolve_running():
        print("[拒絕] Resolve 正在執行 —— 現在部署會在 Resolve 關閉時被覆寫掉。")
        print("       請先完全關閉 Resolve，再執行一次 deploy。")
        return

    # 部署前先自動備份現況(安全：不覆寫沒備份過的東西)
    import datetime
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safety = os.path.join(PREF_DIR, f"keyboard_shortcut_backup_{stamp}")
    os.makedirs(safety, exist_ok=True)
    for f in _files(with_config):
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(safety, os.path.basename(f)))
    print(f"[安全備份] 現況已備份到：{safety}")

    # 部署母版
    deployed = []
    for fname in os.listdir(src):
        if not with_config and fname == "config.user.xml":
            continue
        shutil.copy2(os.path.join(src, fname), os.path.join(PREF_DIR, fname))
        deployed.append(fname)
    print(f"[部署] 母版 '{name}' 已套用：{', '.join(deployed)}")
    print("       開啟 Resolve 後，若快捷鍵沒生效，到 Keyboard Customization")
    print("       右上下拉選單把你的 preset 選為作用中即可。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DaVinci Resolve 快捷鍵母版工具")
    parser.add_argument("command", choices=["backup", "deploy", "list", "status"])
    parser.add_argument("name", nargs="?", help="母版名稱(backup/deploy 需要)")
    parser.add_argument("--with-config", action="store_true",
                        help="連 config.user.xml 整份偏好一起處理")
    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "list":
        cmd_list()
    elif args.command in ("backup", "deploy"):
        if not args.name:
            print(f"[錯誤] '{args.command}' 需要母版名稱")
            sys.exit(1)
        (cmd_backup if args.command == "backup" else cmd_deploy)(args.name, args.with_config)
