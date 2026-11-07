"""Формат файла песни (.song.json) — текст с разметкой и аккордами."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtGui import (
    QColor,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)

# Пользовательское свойство формата символа: пометка «это аккорд»
CHORD_PROPERTY = 0x1001


def make_chord_format(base: QTextCharFormat, chord_color: str) -> QTextCharFormat:
    fmt = QTextCharFormat(base)
    fmt.setForeground(QColor(chord_color))
    fmt.setFontWeight(QFont.Bold)
    fmt.setProperty(CHORD_PROPERTY, True)
    return fmt


def is_chord_format(fmt: QTextCharFormat) -> bool:
    return bool(fmt.property(CHORD_PROPERTY))


def document_to_song_data(
    document: QTextDocument,
    title: str,
    font_size: int,
    *,
    scroll_speed_percent: float = 30.0,
    scroll_minutes: int = 2,
    scroll_seconds: int = 30,
    line_height_percent: int = 100,
) -> dict[str, Any]:
    paragraphs: list[dict[str, Any]] = []
    block = document.begin()
    while block.isValid():
        runs: list[dict[str, Any]] = []
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                text = fragment.text().replace("\u2029", "\n").replace("\u2028", "\n")
                fmt = fragment.charFormat()
                if text:
                    chord = is_chord_format(fmt)
                    runs.append(
                        {
                            "text": text,
                            "chord": chord,
                            "bold": fmt.fontWeight() >= int(QFont.Bold),
                            "italic": bool(fmt.fontItalic()),
                        }
                    )
            it += 1
        paragraphs.append({"runs": runs})
        block = block.next()

    return {
        "version": 1,
        "title": title,
        "font_size": font_size,
        "line_height_percent": int(line_height_percent),
        "scroll_speed_percent": float(scroll_speed_percent),
        "scroll_minutes": int(scroll_minutes),
        "scroll_seconds": int(scroll_seconds),
        "paragraphs": paragraphs,
    }


def make_block_format(line_height_percent: int = 100) -> QTextBlockFormat:
    block_fmt = QTextBlockFormat()
    block_fmt.setTopMargin(0)
    block_fmt.setBottomMargin(0)
    block_fmt.setLineHeight(
        float(line_height_percent),
        QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
    )
    return block_fmt


def song_data_to_document(
    data: dict[str, Any],
    document: QTextDocument,
    text_color: str,
    chord_color: str,
    font_family: str,
    font_size: int,
    line_height_percent: int = 100,
) -> None:
    document.clear()
    cursor = QTextCursor(document)
    paragraphs = data.get("paragraphs") or []

    default_fmt = QTextCharFormat()
    default_fmt.setForeground(QColor(text_color))
    default_fmt.setFontFamily(font_family)
    default_fmt.setFontPointSize(font_size)

    lh = int(data.get("line_height_percent") or line_height_percent)
    block_fmt = make_block_format(lh)

    for i, para in enumerate(paragraphs):
        if i > 0:
            cursor.insertBlock(block_fmt)
        else:
            cursor.setBlockFormat(block_fmt)

        for run in para.get("runs") or []:
            text = run.get("text") or ""
            if not text:
                continue
            fmt = QTextCharFormat(default_fmt)
            if run.get("italic"):
                fmt.setFontItalic(True)
            if run.get("bold"):
                fmt.setFontWeight(QFont.Bold)
            if run.get("chord"):
                fmt = make_chord_format(fmt, chord_color)
                fmt.setFontPointSize(font_size)
                fmt.setFontFamily(font_family)
                if run.get("italic"):
                    fmt.setFontItalic(True)
            cursor.insertText(text, fmt)


def save_song(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_song(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid song file")
    if "paragraphs" not in data and "text" in data:
        lines = str(data["text"]).splitlines()
        data["paragraphs"] = [
            {"runs": [{"text": line, "chord": False, "bold": False, "italic": False}]}
            for line in lines
        ]
    if "paragraphs" not in data:
        raise ValueError("Song file has no lyrics")
    if "title" not in data:
        data["title"] = path.stem.replace(".song", "")
    return data


def import_plain_text(text: str, title: str = "Untitled") -> dict[str, Any]:
    from song_viewer.chords import sanitize_pasted_text

    lines = sanitize_pasted_text(text).split("\n")
    return {
        "version": 1,
        "title": title,
        "font_size": 28,
        "paragraphs": [
            {"runs": [{"text": line, "chord": False, "bold": False, "italic": False}]}
            for line in lines
        ],
    }
