"""Default and stored hotkey definitions."""

from __future__ import annotations

from typing import Any

# id -> default QKeySequence string
DEFAULT_HOTKEYS: dict[str, str] = {
    "toggle_speed_scroll": "Ctrl+1",
    "toggle_timed_scroll": "Ctrl+2",
    "stop_scroll": "Escape",
    "toggle_panel": "Ctrl+Alt+P",
    "bold": "Ctrl+B",
    "italic": "Ctrl+I",
    "mark_chord": "Ctrl+Shift+C",
    "add_chord_line": "Ctrl+Shift+A",
    "detect_chords": "Ctrl+Shift+D",
    "transpose_up": "Ctrl+Up",
    "transpose_down": "Ctrl+Down",
    "increase_font": "Ctrl+=",
    "decrease_font": "Ctrl+-",
    "new_song": "Ctrl+N",
    "open_song": "Ctrl+O",
    "save_song": "Ctrl+S",
    "save_song_as": "Ctrl+Shift+S",
    "library": "Ctrl+L",
}

# Old defaults → new defaults (one-time migration for saved settings)
_LEGACY_HOTKEYS: dict[str, dict[str, str]] = {
    "toggle_speed_scroll": {
        "Ctrl+Alt+S": "Ctrl+1",
        "Alt+S": "Ctrl+1",
        "Alt+1": "Ctrl+1",
    },
    "toggle_timed_scroll": {
        "Ctrl+Alt+D": "Ctrl+2",
        "Alt+2": "Ctrl+2",
    },
    "stop_scroll": {
        "Esc": "Escape",
    },
}

HOTKEY_LABELS: dict[str, str] = {
    "toggle_speed_scroll": "Toggle speed scroll",
    "toggle_timed_scroll": "Toggle timed scroll",
    "stop_scroll": "Stop scroll",
    "toggle_panel": "Show / hide controls panel",
    "bold": "Bold",
    "italic": "Italic",
    "mark_chord": "Mark as chord",
    "add_chord_line": "Add chord line",
    "detect_chords": "Detect chords",
    "transpose_up": "Transpose +1",
    "transpose_down": "Transpose −1",
    "increase_font": "Increase font",
    "decrease_font": "Decrease font",
    "new_song": "New song",
    "open_song": "Open song",
    "save_song": "Save",
    "save_song_as": "Save as",
    "library": "Song library",
}

# Fixed (not remappable) gestures mentioned in Help
FIXED_GESTURES: list[tuple[str, str]] = [
    ("Ctrl + Mouse Wheel", "Change font size"),
    ("Ctrl + Shift + Mouse Wheel", "Change scroll speed by ±0.5%"),
    ("Ctrl + [ / Ctrl + ]", "Scroll speed −0.5% / +0.5%"),
]


def merge_hotkeys(stored: Any) -> dict[str, str]:
    result = dict(DEFAULT_HOTKEYS)
    if isinstance(stored, dict):
        for key, value in stored.items():
            if key in result and isinstance(value, str) and value.strip():
                result[key] = value.strip()
    for key, mapping in _LEGACY_HOTKEYS.items():
        current = result.get(key, "")
        if current in mapping:
            result[key] = mapping[current]
    return result
