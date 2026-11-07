"""Редактор текста песни с аккордами и контекстным меню."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QTextCharFormat,
    QTextCursor,
    QWheelEvent,
)
from PySide6.QtWidgets import QMenu, QTextEdit

from song_viewer.chord_reflow import pack_state, reflow_line_pairs, state_is_chord
from song_viewer.chords import (
    find_chords_in_text,
    is_plausible_chord,
    looks_like_chord_line,
    sanitize_pasted_text,
    strip_invisibles,
    transpose_chord,
)
from song_viewer.song_format import CHORD_PROPERTY, is_chord_format, make_block_format, make_chord_format
from song_viewer.wininput import ctrl_down, ctrl_shift_down


class SongEditor(QTextEdit):
    font_size_changed = Signal(int)
    status_message = Signal(str)
    scroll_speed_nudge = Signal(float)  # +0.5 / -0.5 from Ctrl+Shift+Wheel
    reflow_needed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_family = "Consolas"
        self._font_size = 28
        self._line_height_percent = 100
        self._text_color = "#f7f1ff"
        self._chord_color = "#fd9353"
        self._context_pos: QTextCursor | None = None
        self._reflow_lock = False
        # Logical (unwrapped) chord/lyric lines — source of truth for paired wrap
        self._logical_lines: list[tuple[str, bool]] | None = None
        self.setAcceptRichText(True)
        # Soft-wrap breaks chord/lyric columns — hard-reflow pairs to window width instead.
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setTabChangesFocus(False)
        self.setUndoRedoEnabled(True)
        self._apply_default_font()
        self.document().contentsChange.connect(self._on_contents_change)

    def set_theme_colors(self, text_color: str, chord_color: str) -> None:
        self._text_color = text_color
        self._chord_color = chord_color
        self.setStyleSheet(
            f"QTextEdit {{ background: transparent; color: {text_color}; border: none; }}"
        )
        self._recolor_document()

    def set_editor_font(self, family: str, size: int) -> None:
        self._font_family = family
        self._font_size = max(10, min(96, size))
        self._apply_default_font()
        self._rescale_document_fonts()
        self.font_size_changed.emit(self._font_size)
        self.reflow_needed.emit()

    def font_size(self) -> int:
        return self._font_size

    def font_family(self) -> str:
        return self._font_family

    def line_height_percent(self) -> int:
        return self._line_height_percent

    def set_line_height_percent(self, percent: int) -> None:
        self._line_height_percent = max(60, min(250, int(percent)))
        block_fmt = make_block_format(self._line_height_percent)
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        while block.isValid():
            cursor.setPosition(block.position())
            cursor.mergeBlockFormat(block_fmt)
            block = block.next()
        cursor.endEditBlock()
        self.setCurrentCharFormat(self._base_format())
        cur = self.textCursor()
        cur.mergeBlockFormat(block_fmt)
        self.setTextCursor(cur)

    def chars_per_line(self) -> int:
        # Do NOT use self.fontMetrics(): global QWidget stylesheet forces UI
        # font (e.g. 14pt Segoe UI) onto the editor widget, while lyrics render
        # at self._font_size via char formats — that made cols far too large
        # and hard-wrap never kicked in.
        font = QFont(self._font_family, self._font_size)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        fm = QFontMetrics(font)
        cw = max(
            1,
            fm.horizontalAdvance("M"),
            fm.horizontalAdvance("Ж"),
            fm.horizontalAdvance("W"),
        )
        width = self.viewport().width()
        if width < 40:
            width = max(self.width(), 400)
        # Stylesheet padding (16px) + scrollbar gutter + 1-char safety so the
        # last glyph (often a bold chord) is not clipped / forcing hscroll.
        return max(8, (width - 48) // cw - 1)

    def _line_is_chord(self, text: str, block) -> bool:
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and is_chord_format(frag.charFormat()) and frag.text().strip():
                return True
            it += 1
        return looks_like_chord_line(text)

    def extract_line_meta(self) -> list[tuple[str, bool, int]]:
        rows: list[tuple[str, bool, int]] = []
        block = self.document().begin()
        while block.isValid():
            text = block.text()
            state = int(block.userState())
            guessed = self._line_is_chord(text, block)
            rows.append((text, state_is_chord(state, guessed), state))
            block = block.next()
        return rows

    def _on_contents_change(self, position: int, chars_removed: int, chars_added: int) -> None:
        if self._reflow_lock:
            return
        # User typed/pasted — drop stale reflow marks on touched blocks so
        # chord detection falls back to format / looks_like_chord_line.
        if chars_added or chars_removed:
            block = self.document().findBlock(position)
            last = self.document().findBlock(max(position, position + chars_added - 1))
            while block.isValid():
                block.setUserState(-1)
                if block == last:
                    break
                block = block.next()
        self._logical_lines = None
        self.reflow_needed.emit()

    def invalidate_logical(self) -> None:
        self._logical_lines = None

    def capture_logical_lines(self) -> list[tuple[str, bool]]:
        """Unwrap display lines into logical chord/lyric source lines."""
        meta = self.extract_line_meta()
        # reflow_line_pairs unwraps WRAP_CONT then wraps; take only unwrap via cols huge
        huge = 10_000
        reflowed = reflow_line_pairs(meta, huge)
        return [(t, c) for t, c, _s in reflowed]

    def reflow_for_save(self) -> None:
        """Expand to logical (unwrapped) lines before serializing a song file."""
        if self._logical_lines is None:
            self._logical_lines = self.capture_logical_lines()
        self._apply_reflowed(
            [
                (t, c, pack_state(is_chord=c, wrap_cont=False))
                for t, c in (self._logical_lines or [])
            ]
        )

    def reflow_chords_to_width(self) -> None:
        """Hard-wrap chord+lyric pairs so chords stay above the matching words."""
        if self._reflow_lock:
            return
        cols = self.chars_per_line()
        if self._logical_lines is None:
            self._logical_lines = self.capture_logical_lines()
        if not self._logical_lines:
            return

        source = [
            (t, c, pack_state(is_chord=c, wrap_cont=False))
            for t, c in self._logical_lines
        ]
        reflowed = reflow_line_pairs(source, cols)

        current = self.extract_line_meta()
        if len(reflowed) == len(current) and all(
            a[0] == b[0] and a[1] == b[1] and a[2] == b[2]
            for a, b in zip(current, reflowed)
        ):
            return

        self._apply_reflowed(reflowed)

    def _apply_reflowed(self, reflowed: list[tuple[str, bool, int]]) -> None:
        scroll = self.verticalScrollBar().value()
        self._reflow_lock = True
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.removeSelectedText()

        block_fmt = make_block_format(self._line_height_percent)
        for i, (text, is_chord, state) in enumerate(reflowed):
            if i > 0:
                cursor.insertBlock(block_fmt)
            else:
                cursor.setBlockFormat(block_fmt)
            cursor.block().setUserState(state)
            if is_chord:
                self._insert_chord_line(cursor, text)
            else:
                cursor.insertText(text, self._base_format())
        cursor.endEditBlock()
        self._reflow_lock = False
        self.verticalScrollBar().setValue(scroll)

    def _insert_chord_line(self, cursor: QTextCursor, text: str) -> None:
        if not text:
            cursor.insertText("", self._base_format())
            return
        pos = 0
        for start, end, _name in find_chords_in_text(text):
            if start > pos:
                cursor.insertText(text[pos:start], self._base_format())
            cursor.insertText(text[start:end], self._chord_format())
            pos = end
        if pos < len(text):
            cursor.insertText(text[pos:], self._base_format())

    def _apply_default_font(self) -> None:
        font = QFont(self._font_family, self._font_size)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self.document().setDefaultFont(font)

    def _base_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self._text_color))
        fmt.setFontFamily(self._font_family)
        fmt.setFontPointSize(self._font_size)
        return fmt

    def _chord_format(self) -> QTextCharFormat:
        return make_chord_format(self._base_format(), self._chord_color)

    def _rescale_document_fonts(self) -> None:
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    cursor.setPosition(frag.position())
                    cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                    fmt = QTextCharFormat(frag.charFormat())
                    fmt.setFontPointSize(self._font_size)
                    fmt.setFontFamily(self._font_family)
                    cursor.mergeCharFormat(fmt)
                it += 1
            block = block.next()
        cursor.endEditBlock()

    def _recolor_document(self) -> None:
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    cursor.setPosition(frag.position())
                    cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                    fmt = QTextCharFormat(frag.charFormat())
                    if is_chord_format(fmt):
                        fmt.setForeground(QColor(self._chord_color))
                        fmt.setProperty(CHORD_PROPERTY, True)
                    else:
                        fmt.setForeground(QColor(self._text_color))
                    cursor.mergeCharFormat(fmt)
                it += 1
            block = block.next()
        cursor.endEditBlock()

    # --- форматирование ---

    def toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        weight = QFont.Normal
        cur = self.textCursor()
        if cur.charFormat().fontWeight() < int(QFont.Bold):
            weight = QFont.Bold
        fmt.setFontWeight(weight)
        self.mergeCurrentCharFormat(fmt)

    def toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.textCursor().charFormat().fontItalic())
        self.mergeCurrentCharFormat(fmt)

    def set_normal_style(self) -> None:
        cur = self.textCursor()
        if not cur.hasSelection():
            return
        fmt = self._base_format()
        fmt.setFontWeight(QFont.Normal)
        fmt.setFontItalic(False)
        fmt.setProperty(CHORD_PROPERTY, False)
        cur.mergeCharFormat(fmt)

    # --- аккорды ---

    def mark_selection_as_chord(self) -> None:
        cur = self.textCursor()
        if not cur.hasSelection():
            self.status_message.emit("Select chord text first")
            return
        text = cur.selectedText().replace("\u2029", " ").strip()
        if text and not is_plausible_chord(text) and " " not in text:
            pass
        fmt = self._chord_format()
        cur.mergeCharFormat(fmt)
        self.status_message.emit(f"Marked as chord: {text or '…'}")

    def unmark_selection_chord(self) -> None:
        cur = self.textCursor()
        if not cur.hasSelection():
            self.status_message.emit("Select a chord first")
            return
        fmt = self._base_format()
        fmt.setFontWeight(QFont.Normal)
        fmt.setProperty(CHORD_PROPERTY, False)
        cur.mergeCharFormat(fmt)

    def add_chord_line_at_cursor(self, at: QTextCursor | None = None) -> None:
        """Insert a line above the current one and place the caret at the click column."""
        cur = QTextCursor(at) if at is not None else QTextCursor(self.textCursor())
        block = cur.block()
        col = max(0, cur.position() - block.position())
        insert_at = block.position()
        cur.setPosition(insert_at)
        cur.insertText((" " * col) + "\n", self._chord_format())
        cur.setPosition(insert_at + col)
        cur.setCharFormat(self._chord_format())
        self.setTextCursor(cur)
        self.setFocus()
        self.status_message.emit("Chord line added — type the chord")

    def auto_detect_chords(self) -> int:
        """Mark chords in the whole document. Returns how many were found."""
        count = 0
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        while block.isValid():
            text = block.text()
            # Drop BOM/ZWSP that often sit only on the first pasted line
            if text != strip_invisibles(text):
                cleaned = strip_invisibles(text)
                pos = block.position()
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(text), QTextCursor.KeepAnchor)
                cursor.insertText(cleaned, self._base_format())
                block = cursor.block()
                text = block.text()

            matches = find_chords_in_text(text)
            chord_line = looks_like_chord_line(text)
            for start, end, name in matches:
                # Single-letter C/D/E/F/G/A/B only on real chord lines
                # (otherwise every capital letter in lyrics would light up).
                if not chord_line and len(name) <= 1:
                    continue
                abs_start = block.position() + start
                abs_end = block.position() + end
                cursor.setPosition(abs_start)
                cursor.setPosition(abs_end, QTextCursor.KeepAnchor)
                selected = cursor.selectedText()
                if (
                    is_chord_format(cursor.charFormat())
                    and selected == name
                ):
                    continue
                # Replace Cyrillic lookalikes (Вm → Bm) with Latin chord text
                cursor.insertText(name, self._chord_format())
                count += 1
            block = block.next()
        cursor.endEditBlock()
        self.invalidate_logical()
        self.reflow_needed.emit()
        self.status_message.emit(f"Chords found: {count}")
        return count

    def transpose(self, semitones: int) -> int:
        if semitones == 0:
            return 0
        changed = 0
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        # идём с конца блоков/фрагментов, чтобы позиции не съезжали
        blocks = []
        while block.isValid():
            blocks.append(block)
            block = block.next()
        for block in reversed(blocks):
            # собираем chord-фрагменты блока
            frags = []
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and is_chord_format(frag.charFormat()):
                    frags.append((frag.position(), frag.length(), frag.text()))
                it += 1
            for pos, length, text in reversed(frags):
                # текст фрагмента может содержать несколько аккордов через пробелы
                new_parts = []
                idx = 0
                for m_start, m_end, name in find_chords_in_text(text):
                    new_parts.append(text[idx:m_start])
                    new_parts.append(transpose_chord(name, semitones))
                    idx = m_end
                    changed += 1
                new_parts.append(text[idx:])
                new_text = "".join(new_parts)
                if new_text == text:
                    # целиком один аккорд без regex match — пробуем напрямую
                    if is_plausible_chord(text.strip()):
                        new_text = transpose_chord(text.strip(), semitones)
                        # сохраняем пробелы вокруг
                        if text != text.strip():
                            leading = len(text) - len(text.lstrip())
                            trailing = len(text) - len(text.rstrip())
                            new_text = (" " * leading) + new_text + (" " * trailing)
                        if new_text != text:
                            changed += 1
                    else:
                        continue
                cursor.setPosition(pos)
                cursor.setPosition(pos + length, QTextCursor.KeepAnchor)
                fmt = self._chord_format()
                cursor.insertText(new_text, fmt)
        cursor.endEditBlock()
        self.status_message.emit(f"Transposed: {changed}")
        return changed

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() or event.pixelDelta().y()
        # Ctrl+Shift+Wheel — scroll speed (Alt is unreliable on Windows)
        if ctrl_shift_down():
            if delta != 0:
                self.scroll_speed_nudge.emit(0.5 if delta > 0 else -0.5)
            event.accept()
            return
        if ctrl_down():
            if delta != 0:
                step = 1 if delta > 0 else -1
                self.set_editor_font(self._font_family, self._font_size + step)
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.reflow_needed.emit()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._context_pos = self.cursorForPosition(event.pos())
        menu = QMenu(self)
        act_add = menu.addAction("Add Chord")
        act_mark = menu.addAction("Mark as Chord")
        act_unmark = menu.addAction("Unmark Chord")
        menu.addSeparator()
        act_detect = menu.addAction("Detect Chords")
        menu.addSeparator()
        act_bold = menu.addAction("Bold")
        act_italic = menu.addAction("Italic")
        act_normal = menu.addAction("Normal Style")
        chosen = menu.exec(event.globalPos())
        if chosen is act_add:
            self.add_chord_line_at_cursor(self._context_pos)
        elif chosen is act_mark:
            if not self.textCursor().hasSelection() and self._context_pos:
                c = QTextCursor(self._context_pos)
                c.select(QTextCursor.WordUnderCursor)
                self.setTextCursor(c)
            self.mark_selection_as_chord()
        elif chosen is act_unmark:
            if not self.textCursor().hasSelection() and self._context_pos:
                c = QTextCursor(self._context_pos)
                c.select(QTextCursor.WordUnderCursor)
                self.setTextCursor(c)
            self.unmark_selection_chord()
        elif chosen is act_detect:
            self.auto_detect_chords()
        elif chosen is act_bold:
            self.toggle_bold()
        elif chosen is act_italic:
            self.toggle_italic()
        elif chosen is act_normal:
            self.set_normal_style()

    def insertFromMimeData(self, source) -> None:  # noqa: N802
        """Prefer plain text paste so chord spacing is preserved."""
        if source.hasText():
            text = sanitize_pasted_text(source.text())
            cursor = self.textCursor()
            # Clear leftover reflow state on the target block (often the
            # first empty block still marked as non-chord from startup reflow).
            cursor.block().setUserState(-1)
            cursor.insertText(text, self._base_format())
            self.invalidate_logical()
            self.auto_detect_chords()
        else:
            super().insertFromMimeData(source)
