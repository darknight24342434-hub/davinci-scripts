# davinci-scripts

DaVinci Resolve Studio 的命令列工具組：匯入素材、組 Timeline、排算圖、套 CDL 導演風格或 LUT、生成透明字卡並排進 V2 軌——全部在終端機做，不用進 UI 點。

## 為什麼

Resolve 有 scripting API，但每支腳本都得重複同一段樣板：找到 scripting modules、連上執行中的 Resolve、從 `Resolve` 一路走到 `ProjectManager`／`Project`／`Timeline`，還要處理「Timeline 不是從 frame 0 開始」這件事。這幾個模組把那段包一次，前面掛一個以動詞為主的 CLI。

| 模組 | 負責什麼 |
|---|---|
| `dvr_core.py` | 環境初始化、連線，以及包住專案／Timeline 存取的 `DVR` 類別。其他模組都 import 它。 |
| `dvr_cli.py` | 統一命令列入口。 |
| `dvr_media.py` | 把資料夾匯入 media pool；可選擇依檔名順序直接組成 Timeline。 |
| `dvr_render.py` | 把當前 Timeline（或全部 Timeline）以指定 preset 丟進算圖佇列。 |
| `dvr_color.py` | 對當前 Timeline 套 CDL 導演風格、LUT，或 `.drx` 調色 Still。 |
| `dvr_titles.py` | 用 Pillow 生成透明 RGBA PNG 字卡，再排到 V2 軌的正確 frame 上。 |
| `dvr_keymap.py` | 快捷鍵母版備份與跨機部署。不需要 Resolve 開著——事實上 Resolve 開著時它會拒絕部署。 |

## 環境需求

- **必須是 DaVinci Resolve _Studio_。** 免費版沒有 scripting API，除了 `dvr_keymap.py` 之外全部不能用。
- 除了 `dvr_keymap.py`，其他指令都需要 Resolve **正在執行**。
- Python 3.8 以上。
- `Pillow`，只有 `dvr_titles.py` 需要：`pip install Pillow`。其餘只用標準函式庫加 Resolve 自己的 `DaVinciResolveScript`。

`dvr_core.py` 會依平台把 `RESOLVE_SCRIPT_API` 與 `RESOLVE_SCRIPT_LIB` 設成 Blackmagic 的標準安裝位置（只在你沒設的時候）。Resolve 裝在別的地方就設這兩個環境變數，程式碼一行都不用改：

```powershell
$env:RESOLVE_SCRIPT_API = "D:\Resolve\Support\Developer\Scripting"
$env:RESOLVE_SCRIPT_LIB = "D:\Resolve\fusionscript.dll"
```

## 用法

Resolve Studio 開著、專案打開的狀態下：

```powershell
python dvr_cli.py info                        # 專案名稱、解析度、fps、Timeline 數量
python dvr_cli.py import  <資料夾>            # 匯入素材資料夾到 media pool
python dvr_cli.py timeline <資料夾>           # 匯入後依檔名順序組 Timeline
python dvr_cli.py render     <輸出資料夾>     # 排入當前 Timeline（H.264，非阻塞）
python dvr_cli.py render-all <輸出資料夾>     # 排入專案內所有 Timeline
python dvr_cli.py styles                      # 列出可用的 CDL 風格
python dvr_cli.py style   wkw                 # 對當前 Timeline 套一個
python dvr_cli.py lut     <路徑.cube>         # 對當前 Timeline 所有素材套 LUT
python dvr_cli.py drx     <路徑.drx>          # 套 .drx 調色 Still
python dvr_cli.py titles         cards.json   # 生成字卡並排進 V2
python dvr_cli.py titles-preview cards.json   # 只生成 PNG，不碰 Resolve
```

### 算圖 preset

`dvr_render.py` 把短代號對到 Resolve 的算圖 preset：`h264`（mp4，預設）、`h265`（mp4）、`prores`（mov，ProRes 422 HQ）、`dnxhd`（mxf）、`youtube`（mp4，YouTube 1080p preset）。算圖是**排進佇列，不是直接執行**——工作丟進 Resolve 的 render queue 就立刻返回。

### CDL 導演風格

`dvr_color.py` 內建五組 CDL：`wkw`、`fincher`、`koreeda`、`jia`、`neutral`，各是一組套在 node 1 的 Slope／Offset／Power／Saturation。`python dvr_cli.py styles` 會列出說明。

### 字卡

字卡用 JSON 陣列定義：

```json
[
  { "slug": "card_open", "text": "開場字卡", "pos_sec": 2.0, "dur_sec": 3.0, "position": "center" },
  { "slug": "card_end",  "text": "結尾字卡", "pos_sec": 55.0, "dur_sec": 4.0, "position": "lower" }
]
```

`position` 是 `center`、`lower` 或 `upper`。先產範例並只預覽 PNG、不碰 Resolve：

```powershell
python dvr_titles.py --example --preview --out .\cards
```

PNG 預設輸出到腳本旁邊的 `_title_cards\`，用 `--out` 或環境變數 `DVR_TITLE_CARDS_DIR` 覆寫。字型從一份跨平台 fallback 清單挑，設 `DVR_TITLE_FONT` 可指定特定字型檔。

**字卡檔名千萬別用連號（`t1`／`t2`／`t3`）。** Resolve 會把數字連號的檔名當成圖片序列，合成單一媒體。用語意命名。也因為同一個理由，每張 PNG 是逐一 ImportMedia，不是一次傳清單。

### 快捷鍵母版

Resolve 的快捷鍵存在 `keyboard.preset.xml`，內容是二進位封包，沒辦法當文字逐條編輯——所以你在 UI 裡設定一次（Keyboard Customization → Save As），之後由這支工具在機器之間搬。

```powershell
python dvr_keymap.py status                   # 偏好檔位置、Resolve 是否開著
python dvr_keymap.py backup  <母版名>         # 把目前快捷鍵存成母版
python dvr_keymap.py list                     # 列出所有母版
python dvr_keymap.py deploy  <母版名>         # 部署母版（Resolve 必須關閉）
```

加 `--with-config` 連整份偏好 `config.user.xml` 一起處理。

**部署一定要在 Resolve 關閉時做。** Resolve 開著時設定在記憶體，關閉會把檔覆寫回去，你部署的會被蓋掉。工具偵測到 Resolve 執行中會拒絕；連偵測本身失敗時也保守當作「開著」，寧可不動。部署前它還會先把你現況的檔案快照到 Resolve 自己的 Preferences 底下一個帶時間戳的資料夾。

母版存在腳本旁的 `keymaps\`。那個資料夾已被 gitignore——存下來的 preset 是你的個人設定，不是要公開的東西。

## 已知限制

- **只支援 Studio，而且 Resolve 要先開著。** 工具不會幫你啟動 Resolve；`get_resolve()` 拿不到物件就直接丟錯。
- **Timeline 不是從 frame 0 開始。** 30 fps 的 Resolve Timeline 從 frame 108000（01:00:00:00）起算。`dvr_titles.py` 已經處理，但你若自己拿這些模組寫排列邏輯，記得照做。
- **`--fps` 是你傳進去的，不是讀回來的。** 字卡排列相信你給的 fps；跟實際 Timeline 不一致時，每張卡都會安靜地位移。
- **CDL 風格是近似值，不是官方調色。** 用導演名字只是那一類調性的簡稱，是起點、要逐鏡再調，與該導演本人無關、也未經其背書。
- **算圖只是排進佇列。** 沒有任何機制回頭確認工作是否成功，`render-all` 也不會跟佇列中既有工作去重。
- **套 LUT 是走過當前 Timeline 上每一個素材**，用固定 node index，沒有逐鏡選擇，也沒有 Resolve 以外的復原。
- **`dvr_keymap.py` 只能在 Windows 跑。** 它讀 `%APPDATA%`，用 `tasklist` 偵測 Resolve。
- **沒有測試。** 真正重要的部分沒有 Resolve Studio 就跑不起來；只有字卡生成能獨立執行。

## 授權

MIT，見 [LICENSE](LICENSE)。

English version: [README.md](README.md)
