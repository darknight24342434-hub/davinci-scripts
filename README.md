# davinci-scripts

A small command-line toolkit for DaVinci Resolve Studio: import footage, build a timeline, queue renders, apply a CDL grade or a LUT, generate transparent title cards and drop them onto V2 — all from a terminal rather than the UI.

## What it does / why

Resolve exposes a scripting API, but every script that uses it has to repeat the same boilerplate: locate the scripting modules, connect to a running Resolve, walk from `Resolve` to `ProjectManager` to `Project` to `Timeline`, and deal with the fact that a timeline does not start at frame 0. These modules wrap that once, and put a single verb-based CLI in front of it.

It is aimed at the repetitive middle of an edit — the parts that are identical every time and slow to click through.

| Module | Responsibility |
| --- | --- |
| `dvr_core.py` | Environment setup, connection, and a `DVR` helper class wrapping project/timeline access. Everything else imports this. |
| `dvr_cli.py` | The unified command-line entry point. |
| `dvr_media.py` | Import a folder into the media pool; optionally build a timeline from it in filename order. |
| `dvr_render.py` | Queue the current timeline, or every timeline, into the render queue with a preset. |
| `dvr_color.py` | Apply a CDL "director look", a LUT, or a `.drx` still to the current timeline. |
| `dvr_titles.py` | Render transparent RGBA PNG title cards with Pillow, then place them on video track 2 at the right frames. |
| `dvr_keymap.py` | Back up and redeploy Resolve keyboard-shortcut presets between machines. Does not need Resolve running — in fact it refuses to deploy while Resolve is open. |

## Requirements

- **DaVinci Resolve _Studio_.** The free edition does not ship the scripting API, so nothing here works on it except `dvr_keymap.py`.
- Resolve must be **running** for every command except `dvr_keymap.py`.
- Python 3.8 or newer.
- `Pillow`, but only for `dvr_titles.py`: `pip install Pillow`. Everything else is standard library plus Resolve's own `DaVinciResolveScript` module.

`dvr_core.py` sets `RESOLVE_SCRIPT_API` and `RESOLVE_SCRIPT_LIB` to Blackmagic's standard install locations for your platform if they are not already set. If Resolve lives somewhere else, export those two variables and no code needs editing:

```powershell
$env:RESOLVE_SCRIPT_API = "D:\Resolve\Support\Developer\Scripting"
$env:RESOLVE_SCRIPT_LIB = "D:\Resolve\fusionscript.dll"
```

## Install

```
git clone <repo-url>
cd davinci-scripts
pip install Pillow          # only needed for title cards
python dvr_cli.py --help
```

## Usage

With Resolve Studio open on the project you want to act on:

```
python dvr_cli.py info                        # project name, resolution, fps, timeline count
python dvr_cli.py import  <folder>            # import a folder of footage into the media pool
python dvr_cli.py timeline <folder>           # import, then build a timeline in filename order
python dvr_cli.py render     <output-dir>     # queue the current timeline (H.264, non-blocking)
python dvr_cli.py render-all <output-dir>     # queue every timeline in the project
python dvr_cli.py styles                      # list the available CDL looks
python dvr_cli.py style   wkw                 # apply one to the current timeline
python dvr_cli.py lut     <path-to.cube>      # apply a LUT to every clip on the current timeline
python dvr_cli.py drx     <path-to.drx>       # apply a .drx grade still
python dvr_cli.py titles         cards.json   # render title cards and place them on V2
python dvr_cli.py titles-preview cards.json   # render the PNGs only, do not touch Resolve
```

### Render presets

`dvr_render.py` maps a short key onto a Resolve render preset: `h264` (mp4, default), `h265` (mp4), `prores` (mov, ProRes 422 HQ), `dnxhd` (mxf) and `youtube` (mp4, the YouTube 1080p preset). Renders are **queued, not executed** — the job lands in Resolve's render queue and returns immediately.

### CDL looks

`dvr_color.py` ships five CDL presets — `wkw`, `fincher`, `koreeda`, `jia` and `neutral` — each a Slope/Offset/Power/Saturation quadruple applied to node 1. `python dvr_cli.py styles` prints them with descriptions.

### Title cards

Cards are defined in a JSON list:

```json
[
  { "slug": "card_open", "text": "Opening title", "pos_sec": 2.0, "dur_sec": 3.0, "position": "center" },
  { "slug": "card_end",  "text": "End card",      "pos_sec": 55.0, "dur_sec": 4.0, "position": "lower" }
]
```

`position` is `center`, `lower` or `upper`. Generate a starter file and preview the PNGs without touching Resolve:

```
python dvr_titles.py --example --preview --out ./cards
```

PNGs default to a `_title_cards/` folder next to the scripts; override with `--out` or the `DVR_TITLE_CARDS_DIR` environment variable. The font is picked from a per-platform fallback list; set `DVR_TITLE_FONT` to a specific font file to override it.

**Do not name your cards `t1`, `t2`, `t3`.** Resolve treats numerically sequential filenames as an image sequence and imports them as a single media item. Use semantic slugs. Each PNG is imported individually for the same reason.

### Keyboard presets

Resolve stores shortcuts in `keyboard.preset.xml` as a binary blob, so they cannot be edited as text — you define them once in the UI (Keyboard Customization → Save As), then this tool moves that preset between machines.

```
python dvr_keymap.py status                   # where the preference files are, and whether Resolve is running
python dvr_keymap.py backup  <master-name>    # save the current shortcuts as a named master
python dvr_keymap.py list                     # list saved masters
python dvr_keymap.py deploy  <master-name>    # restore a master (Resolve must be CLOSED)
```

Add `--with-config` to include `config.user.xml`, the full preferences file.

**Deploy only while Resolve is closed.** While it runs, Resolve holds preferences in memory and writes them back on exit, overwriting whatever you deployed. The tool detects a running Resolve and refuses; if the detection itself fails it assumes Resolve is running, so it errs toward not clobbering anything. Before deploying it also snapshots your current files into a timestamped folder inside Resolve's own Preferences directory.

Masters are stored in `keymaps/` next to the scripts. That folder is gitignored — a saved preset is your personal configuration, not something to publish.

## Output

- `import` / `timeline` print how many clips were added.
- `render` / `render-all` add jobs to Resolve's render queue and print the job identifiers. Nothing is encoded until you start the queue.
- `titles` writes one RGBA PNG per card (transparent background, 1920×1080 by default, with a soft drop shadow) and then places each on video track 2 at `timeline_start_frame + pos_sec × fps`.
- `dvr_keymap.py backup` writes into `keymaps/<master-name>/`.

## Limitations

- **Studio only, and Resolve must already be open.** There is no launch-Resolve step; `get_resolve()` raises if the API returns nothing.
- **The console output and the source comments are in Traditional Chinese.** The CLI verbs and JSON keys are English; the help text, error messages and inline commentary are not.
- **Timelines do not start at frame 0.** A 30 fps Resolve timeline starts at frame 108000 (01:00:00:00). `dvr_titles.py` accounts for this, but if you write your own placement code against these modules, do the same.
- **`--fps` is passed in, not read back.** Title-card placement trusts the fps you give it; a mismatch with the actual timeline silently shifts every card.
- **The CDL looks are approximations, not official grades.** They are named after directors as shorthand for a family of looks; they are starting points to be adjusted per shot, and carry no endorsement by or connection to those film-makers.
- **Renders are queued only.** Nothing checks whether a job later succeeded, and `render-all` does not deduplicate against jobs already in the queue.
- **LUT application walks every clip on the current timeline** at a fixed node index. There is no per-clip selection and no undo beyond Resolve's own.
- **`dvr_keymap.py` is Windows-only.** It reads `%APPDATA%` and detects a running Resolve with `tasklist`.
- **No tests.** The parts that matter cannot be exercised without a Resolve Studio install; only the title-card generation runs standalone.

## License

MIT. See [LICENSE](LICENSE).

A Traditional Chinese version of this document is in [README.zh-TW.md](README.zh-TW.md).
