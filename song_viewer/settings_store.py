"""Сохранение настроек и списка недавних файлов."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
SONGS_DIR = APP_DIR / "songs"
SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "theme_id": "graphite",
    "font_size": 28,
    "font_family": "Consolas",
    "line_height_percent": 100,
    "scroll_speed_percent": 30.0,
    "scroll_minutes": 2,
    "scroll_seconds": 30,
    "panel_visible": True,
    "window_geometry": None,
    "recent": [],
    "ui_font_pt": 14,
    "hotkeys": {},
    "lh_reset_v5": False,
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SONGS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    # One-time factory reset of line-height to 100% (old builds stuck at 60).
    if not merged.get("lh_reset_v5"):
        merged["line_height_percent"] = 100
        merged["lh_reset_v5"] = True
        try:
            save_settings(merged)
        except OSError:
            pass
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    ensure_dirs()
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_recent(settings: dict[str, Any], path: str, limit: int = 12) -> None:
    recent: list[str] = list(settings.get("recent") or [])
    path = str(Path(path).resolve())
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    settings["recent"] = recent[:limit]


def list_library_songs() -> list[Path]:
    ensure_dirs()
    files = list(SONGS_DIR.glob("*.song.json")) + list(SONGS_DIR.glob("*.json"))
    # уникальные пути
    seen: set[Path] = set()
    result: list[Path] = []
    for f in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        resolved = f.resolve()
        if resolved in seen:
            continue
        # пропускаем settings и прочее
        if f.name == "settings.json":
            continue
        seen.add(resolved)
        result.append(f)
    return result
