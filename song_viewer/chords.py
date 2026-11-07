"""Распознавание и транспозиция аккордов."""

from __future__ import annotations

import re

# Корень + качество + опциональный бас (Am, F#, Cmaj7, G/B, Asus4, Bbdim ...)
CHORD_RE = re.compile(
    r"(?<![A-Za-z0-9#b])"
    r"([A-G])([#b]?)"
    r"(maj|min|dim|aug|sus|add|m|M)?"
    r"([0-9]{0,2})"
    r"(sus[24]?|add[0-9]{1,2}|maj[0-9]{0,2}|min[0-9]{0,2}|dim[0-9]{0,2}|aug)?"
    r"(/([A-G])([#b]?))?"
    r"(?![A-Za-z0-9#b])"
)

# Invisible / paste junk that often lands on the first clipboard line only.
_INVISIBLE_RE = re.compile(r"[\ufeff\u200b\u200c\u200d\u2060\u00ad]")

# Cyrillic letters that look like Latin chord roots/quality (wrong keyboard / OCR).
_CYR_LOOKALIKE = str.maketrans({
    "А": "A",
    "В": "B",
    "Е": "E",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "Х": "X",
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "т": "t",
    "х": "x",
    "м": "m",
})

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}
SHARP_TO_FLAT = {v: k for k, v in FLAT_TO_SHARP.items()}


def normalize_root(root: str, accidental: str) -> str:
    note = root + accidental
    if note in FLAT_TO_SHARP:
        return FLAT_TO_SHARP[note]
    if note in NOTES_SHARP:
        return note
    # редкий случай: B# / E# и т.п. — оставляем как есть через индекс
    return note


def note_index(note: str) -> int | None:
    n = FLAT_TO_SHARP.get(note, note)
    try:
        return NOTES_SHARP.index(n)
    except ValueError:
        return None


def transpose_note(root: str, accidental: str, semitones: int, prefer_flats: bool = False) -> str:
    note = normalize_root(root, accidental)
    idx = note_index(note)
    if idx is None:
        return root + accidental
    new_idx = (idx + semitones) % 12
    if prefer_flats:
        return NOTES_FLAT[new_idx]
    return NOTES_SHARP[new_idx]


def transpose_chord(chord: str, semitones: int, prefer_flats: bool = False) -> str:
    """Транспонирует одну запись аккорда. Если не похоже на аккорд — возвращает как есть."""
    m = CHORD_RE.fullmatch(chord.strip())
    if not m:
        return chord

    root, acc, qual, num, extra, _slash, bass_root, bass_acc = m.groups()
    new_root = transpose_note(root, acc or "", semitones, prefer_flats)

    parts = [new_root]
    if qual:
        parts.append(qual)
    if num:
        parts.append(num)
    if extra:
        parts.append(extra)
    if bass_root:
        new_bass = transpose_note(bass_root, bass_acc or "", semitones, prefer_flats)
        parts.append("/")
        parts.append(new_bass)
    return "".join(parts)


def strip_invisibles(text: str) -> str:
    return _INVISIBLE_RE.sub("", text)


def sanitize_pasted_text(text: str) -> str:
    """Normalize clipboard text before insert (BOM/ZWSP/NBSP/CRLF)."""
    text = strip_invisibles(text)
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2002", " ")
        .replace("\u2003", " ")
        .replace("\u2009", " ")
        .replace("\t", " ")
    )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def _latinize_lookalikes(text: str) -> str:
    return text.translate(_CYR_LOOKALIKE)


def find_chords_in_text(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, chord) matches. Positions refer to ``text`` as given."""
    # Lookalike map is 1:1 so indices stay valid on the original string.
    probe = _latinize_lookalikes(text)
    return [(m.start(), m.end(), m.group(0)) for m in CHORD_RE.finditer(probe)]


def looks_like_chord_line(text: str) -> bool:
    """Строка в основном из аккордов и пробелов (типичная chord-line)."""
    cleaned = strip_invisibles(text).strip()
    if not cleaned:
        return False
    probe = _latinize_lookalikes(cleaned)
    leftover = CHORD_RE.sub("", probe)
    leftover = re.sub(r"[\s|./\-–—]+", "", leftover)
    if leftover:
        return False
    return bool(CHORD_RE.search(probe))


def is_plausible_chord(text: str) -> bool:
    probe = _latinize_lookalikes(strip_invisibles(text).strip())
    return bool(CHORD_RE.fullmatch(probe))
