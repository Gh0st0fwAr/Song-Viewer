# Song Viewer

**Song Viewer** is a large-print lyrics & chords reader for **low-vision guitarists**.  
It keeps chords aligned over the words while you enlarge the font or narrow the window, and can auto-scroll so you do not have to touch the mouse mid-song.

Repository: [Gh0st0fwAr/Song-Viewer](https://github.com/Gh0st0fwAr/Song-Viewer)

---

## Who it is for

- Guitarists and singers who need **very large text**
- Players who use a **screen magnifier** or a small / portrait window
- Anyone who wants a calm, high-contrast chord sheet without fighting a browser tab

## What you get

- **Readable first** — big fonts, clear themes, large controls
- **Chords stay useful when text wraps** — chord lines reflow with the lyrics so marks stay over the right words
- **Hands-free practice** — auto-scroll by speed or by total time
- **Your library** — save songs, reopen recent files, browse a local song list
- **Fast tweaks while playing** — font size and scroll speed from the keyboard / mouse wheel

## Features

- Monospace chord + lyric editor with paired wrap on resize / font change
- Bold / italic, chord color, transpose ±1
- Paste plain chord sheets → auto-detect chords (Detect button / shortcut)
- Manual chord tools: add chord line, mark / unmark selection (context menu or hotkeys)
- Auto-scroll by **speed (%)** or by **duration** (minutes + seconds)
- Remappable hotkeys + Help shortcut list
- Collapsible control panel
- Themes for low-glare reading (Night Harbor, Graphite Soft, Forest Dusk, and more)
- Songs stored as `.song.json` under `songs/`; settings in `data/settings.json`

---

## Run from source

1. Install **Python 3.11+**
2. `pip install -r requirements.txt`
3. Double-click **`run.bat`**, or run `py -3 main.py`

## Windows build (prebuilt)

Download the latest Windows package from **Releases**:

**https://github.com/Gh0st0fwAr/Song-Viewer/releases**

1. Grab the release asset (e.g. `SV.zip`)
2. Unpack it
3. Run **`SongViewer.exe`**

---

## Interface guide

### Layout

- **Left — Controls:** title, font size, line height, theme, scroll settings, transpose, Detect
- **Right — Editor:** lyrics and chords (large text)
- **Menu bar:** File, Edit, View, Scroll, Help  
  Use **View → Show/Hide controls** (default `Ctrl+Alt+P`) if you need a wider reading area.

### Paste a song

1. Copy a chord sheet from anywhere (plain text works best)
2. Click in the editor and paste (`Ctrl+V`)
3. Chords on their own lines (e.g. `Em              C`) are detected automatically  
4. If something was missed, press **Detect** (or `Ctrl+Shift+D`)

Typical layout the app expects:

```text
Em              C
Lyrics under the chords here
               G
Next lyric line
```

### Mark chords by hand

- **Right-click → Add Chord** — inserts a chord line above the current line  
- Select text → **Mark as Chord** (`Ctrl+Shift+C`) or **Unmark Chord**  
- **Detect** rescans the whole song  
- **-1 / +1** (or `Ctrl+↑` / `Ctrl+↓`) transpose marked chords

### Font size

- Slider / spin box in **Appearance**, or **`Ctrl` + mouse wheel** over the editor  
- Size is remembered in settings

### Line height

- **Line height** slider (percent) — more spacing between lines for easier tracking

### Auto-scroll

**By speed**

1. Set **Speed %** (small values = slow crawl; good for reading)
2. Press **Scroll by speed** (or `Ctrl+1`)  
3. Nudge speed while playing: **`Ctrl+Shift` + mouse wheel**, or **`Ctrl+[`** / **`Ctrl+]`** (±0.5%)

**By time**

1. Set **minutes** and **seconds** for the rest of the song
2. Press **Scroll by time** (or `Ctrl+2`) — the view reaches the bottom in that duration

**Stop:** `Escape` (or the pause label on the same button)

Scroll speed and timed duration can be stored **per song** when you save.

### Save and library

| Action | How |
|--------|-----|
| Save | `Ctrl+S` / File → Save |
| Save As | `Ctrl+Shift+S` |
| Open | `Ctrl+O` |
| Open Recent | File → Open Recent |
| Library | `Ctrl+L` — list songs in `songs/`, open or delete |

New and edited songs default to the `songs/` folder as `*.song.json`.

### Themes & hotkeys

- Pick a theme under **Appearance → Theme**
- **Edit → Hotkeys…** — change shortcuts  
- **Help → Keyboard Shortcuts…** — current map + fixed gestures

### Useful shortcuts

| Keys | Action |
|------|--------|
| `Ctrl+S` / `Ctrl+O` / `Ctrl+L` | Save / Open / Library |
| `Ctrl+1` / `Ctrl+2` | Speed scroll / timed scroll |
| `Escape` | Stop scroll |
| `Ctrl+Alt+P` | Show / hide controls |
| `Ctrl` + wheel | Font size |
| `Ctrl+Shift` + wheel | Scroll speed ±0.5% |
| `Ctrl+[` / `Ctrl+]` | Scroll speed ±0.5% |
| `Ctrl+B` / `Ctrl+I` | Bold / Italic |
| `Ctrl+Shift+C` / `A` / `D` | Mark chord / Add chord line / Detect |
| `Ctrl+↑` / `Ctrl+↓` | Transpose |

---

## Project layout

```text
main.py          entry point
run.bat          Windows launcher
song_viewer/     application package
songs/           saved songs
data/            settings (created at runtime)
```

Prebuilt Windows binaries are published on the [Releases](https://github.com/Gh0st0fwAr/Song-Viewer/releases) page (not stored in this repository).


## License

Use and modify for personal practice as you like. Themes in this project are original (not Monokai-licensed).
