"""
dvr_core.py — DaVinci Resolve Studio 核心連線與 Helper
使用方式：from dvr_core import DVR
"""

import os
import sys
import time

# ── 環境初始化 ────────────────────────────────────────────────────────────────
# Blackmagic 的標準安裝位置，依平台而異。若你的 Resolve 裝在別處，設環境變數
# RESOLVE_SCRIPT_API 與 RESOLVE_SCRIPT_LIB 覆寫即可，本檔不需要改。
_DEFAULT_API = {
    "win32": r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
    "darwin": "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
}.get(sys.platform, "/opt/resolve/Developer/Scripting")

_DEFAULT_LIB = {
    "win32": r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll",
    "darwin": "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
}.get(sys.platform, "/opt/resolve/libs/Fusion/fusionscript.so")

os.environ.setdefault("RESOLVE_SCRIPT_API", _DEFAULT_API)
os.environ.setdefault("RESOLVE_SCRIPT_LIB", _DEFAULT_LIB)

SCRIPTING_API = os.environ["RESOLVE_SCRIPT_API"]
SCRIPTING_LIB = os.environ["RESOLVE_SCRIPT_LIB"]

modules_path = os.path.join(SCRIPTING_API, "Modules")
if modules_path not in sys.path:
    sys.path.append(modules_path)


# ── 連線 ──────────────────────────────────────────────────────────────────────
def get_resolve():
    """取得 Resolve 物件，Resolve 必須已開啟。"""
    try:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if resolve is None:
            raise RuntimeError("Resolve 回傳 None，請確認 Resolve Studio 已開啟")
        return resolve
    except ImportError:
        raise RuntimeError(
            "無法匯入 DaVinciResolveScript。\n"
            f"請確認 Modules 路徑：{modules_path}\n"
            "並確認 Resolve Studio 已開啟（非 Free 版）"
        )


class DVR:
    """DaVinci Resolve 操作主類別。每次 script 建立一個即可。"""

    def __init__(self):
        self.resolve = get_resolve()
        self.pm = self.resolve.GetProjectManager()
        self._project = None
        self._timeline = None

    # ── 專案 ──────────────────────────────────────────────────────────────────
    @property
    def project(self):
        if self._project is None:
            self._project = self.pm.GetCurrentProject()
            if self._project is None:
                raise RuntimeError("沒有開啟中的專案，請先在 Resolve 開啟或建立專案")
        return self._project

    def open_project(self, name: str):
        p = self.pm.LoadProject(name)
        if not p:
            raise RuntimeError(f"找不到專案：{name}")
        self._project = p
        self._timeline = None
        return p

    def create_project(self, name: str, fps: str = "24", w: int = 1920, h: int = 1080):
        p = self.pm.CreateProject(name)
        if not p:
            raise RuntimeError(f"無法建立專案：{name}（名稱已存在？）")
        p.SetSetting("timelineFrameRate", fps)
        p.SetSetting("timelineResolutionWidth", str(w))
        p.SetSetting("timelineResolutionHeight", str(h))
        self._project = p
        self._timeline = None
        self.pm.SaveProject()
        return p

    def save(self):
        self.pm.SaveProject()

    # ── 頁面切換 ──────────────────────────────────────────────────────────────
    def goto(self, page: str):
        """page: 'media' | 'cut' | 'edit' | 'fusion' | 'color' | 'fairlight' | 'deliver'"""
        valid = {"media", "cut", "edit", "fusion", "color", "fairlight", "deliver"}
        if page not in valid:
            raise ValueError(f"無效頁面 '{page}'，可用：{valid}")
        self.resolve.OpenPage(page)

    # ── Media Pool ────────────────────────────────────────────────────────────
    @property
    def media_pool(self):
        return self.project.GetMediaPool()

    @property
    def media_storage(self):
        return self.resolve.GetMediaStorage()

    def import_clips(self, path: str) -> list:
        """匯入單一資料夾的所有媒體，回傳 clip 物件清單。"""
        return self.media_storage.AddItemListToMediaPool(path)

    def import_files(self, file_paths: list) -> list:
        """匯入指定檔案清單。"""
        return self.media_pool.ImportMedia(file_paths)

    def create_bin(self, name: str, parent=None):
        """在 Media Pool 建立子資料夾（bin）。"""
        mp = self.media_pool
        if parent:
            mp.SetCurrentFolder(parent)
        return mp.AddSubFolder(mp.GetCurrentFolder(), name)

    # ── Timeline ──────────────────────────────────────────────────────────────
    @property
    def timeline(self):
        if self._timeline is None:
            self._timeline = self.project.GetCurrentTimeline()
        return self._timeline

    def create_timeline(self, name: str = "Timeline 1") -> object:
        tl = self.media_pool.CreateEmptyTimeline(name)
        if not tl:
            raise RuntimeError(f"無法建立 Timeline：{name}")
        self._timeline = tl
        return tl

    def get_timeline(self, index: int = 1) -> object:
        return self.project.GetTimelineByIndex(index)

    def set_timeline(self, tl) -> None:
        self.project.SetCurrentTimeline(tl)
        self._timeline = tl

    def append_clips(self, clips: list) -> bool:
        return self.media_pool.AppendToTimeline(clips)

    def append_clips_with_inout(self, clip_infos: list) -> bool:
        """
        精確入出點排列。clip_infos 格式：
        [{"mediaPoolItem": item, "startFrame": int, "endFrame": int,
          "trackIndex": 1, "recordFrame": int, "mediaType": 1}]

        ★ recordFrame 請用 tl.GetStartFrame() + 秒*fps
          （Timeline 預設起始 = 108000，即 01:00:00:00 @ 30fps）
        """
        return self.media_pool.AppendToTimeline(clip_infos)

    def timeline_start_frame(self, tl=None) -> int:
        """回傳 timeline 起始 frame（通常 108000）。排字卡/音樂時必用。"""
        t = tl or self.timeline
        return int(t.GetStartFrame())

    def get_all_timelines(self) -> list:
        count = int(self.project.GetTimelineCount())
        return [self.project.GetTimelineByIndex(i + 1) for i in range(count)]

    # ── 專案資訊 ──────────────────────────────────────────────────────────────
    def info(self) -> dict:
        p = self.project
        return {
            "name": p.GetName(),
            "fps": p.GetSetting("timelineFrameRate"),
            "width": p.GetSetting("timelineResolutionWidth"),
            "height": p.GetSetting("timelineResolutionHeight"),
            "timeline_count": int(p.GetTimelineCount()),
        }

    # ── Render ────────────────────────────────────────────────────────────────
    def add_render_job(self, timeline, output_dir: str,
                       preset: str = "H.264 Master",
                       fmt: str = "mp4", codec: str = "H264") -> str:
        self.project.SetCurrentTimeline(timeline)
        self.project.LoadRenderPreset(preset)
        self.project.SetCurrentRenderFormatAndCodec(fmt, codec)
        self.project.SetRenderSettings({
            "SelectAllFrames": 1,
            "TargetDir": output_dir,
        })
        job_id = self.project.AddRenderJob()
        return job_id

    def render_all_jobs(self, wait: bool = False) -> bool:
        """
        啟動渲染。預設非阻塞（wait=False）。
        ★ 在 Resolve Console 內執行時 wait 必須為 False，
          否則 while sleep 會卡死 UI。
          完成判斷請輪詢輸出資料夾是否出現目標檔案。
        外部 py 腳本（命令列執行）可用 wait=True。
        """
        self.goto("deliver")
        ok = self.project.StartRendering()
        if ok and wait:
            while self.project.IsRenderingInProgress():
                time.sleep(2)
            self.project.DeleteAllRenderJobs()
        return ok

    def wait_render_done(self, output_dir: str, expected_name: str,
                         timeout: int = 300) -> bool:
        """輪詢輸出資料夾，直到目標檔案出現（取代 Console 內的 sleep loop）。"""
        import glob as _glob
        target = os.path.join(output_dir, expected_name)
        for _ in range(timeout):
            time.sleep(1)
            matches = _glob.glob(target)
            if matches:
                return True
        return False

    # ── 調色 ──────────────────────────────────────────────────────────────────
    def apply_lut(self, timeline, lut_path: str, node_index: int = 1) -> bool:
        track_count = int(timeline.GetTrackCount("video"))
        ok = True
        for i in range(1, track_count + 1):
            for clip in timeline.GetItemListInTrack("video", i):
                if not clip.SetLUT(node_index, lut_path):
                    ok = False
        return ok

    def apply_cdl(self, timeline, cdl: dict, track: int = 1) -> None:
        """
        對 timeline 指定軌道（預設 V1）的每顆鏡頭套用 ASC CDL。
        cdl 格式範例：
          {"NodeIndex":"1",
           "Slope":"1.12 1.02 0.88",
           "Offset":"0.005 0.02 0.05",
           "Power":"0.95 0.97 1.02",
           "Saturation":"1.30"}
        ★ NodeIndex 從 v16.2 起 1-based（不是 0）。
        """
        for item in timeline.GetItemListInTrack("video", track):
            item.SetCDL(cdl)

    def apply_drx(self, timeline, drx_path: str, grade_mode: int = 0) -> bool:
        track_count = int(timeline.GetTrackCount("video"))
        ok = True
        for i in range(1, track_count + 1):
            clips = timeline.GetItemListInTrack("video", i)
            if not timeline.ApplyGradeFromDRX(drx_path, grade_mode, clips):
                ok = False
        return ok
