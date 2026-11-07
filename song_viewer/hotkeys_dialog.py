"""Dialog to customize application hotkeys."""

from __future__ import annotations

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from song_viewer.hotkeys import DEFAULT_HOTKEYS, HOTKEY_LABELS


class HotkeysDialog(QDialog):
    def __init__(self, hotkeys: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hotkeys")
        self.resize(560, 640)
        self.setModal(True)

        self._editors: dict[str, QKeySequenceEdit] = {}
        self._result: dict[str, str] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(QLabel("Click a field and press the new shortcut."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setSpacing(10)
        form.setContentsMargins(8, 8, 8, 8)

        for key in DEFAULT_HOTKEYS:
            editor = QKeySequenceEdit(QKeySequence(hotkeys.get(key, DEFAULT_HOTKEYS[key])))
            self._editors[key] = editor
            form.addRow(HOTKEY_LABELS.get(key, key), editor)

        scroll.setWidget(form_host)
        root.addWidget(scroll, stretch=1)

        row = QHBoxLayout()
        btn_reset = QPushButton("Reset defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        row.addWidget(btn_reset)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        root.addLayout(row)

    def _reset_defaults(self) -> None:
        for key, editor in self._editors.items():
            editor.setKeySequence(QKeySequence(DEFAULT_HOTKEYS[key]))

    def _accept(self) -> None:
        result: dict[str, str] = {}
        used: dict[str, str] = {}
        for key, editor in self._editors.items():
            seq = editor.keySequence()
            text = seq.toString(QKeySequence.PortableText)
            if not text:
                QMessageBox.warning(
                    self,
                    "Hotkeys",
                    f'"{HOTKEY_LABELS.get(key, key)}" cannot be empty.',
                )
                return
            if text in used:
                QMessageBox.warning(
                    self,
                    "Hotkeys",
                    f'Conflict: "{text}" is used by both\n'
                    f'• {HOTKEY_LABELS.get(used[text], used[text])}\n'
                    f'• {HOTKEY_LABELS.get(key, key)}',
                )
                return
            used[text] = key
            result[key] = text
        self._result = result
        self.accept()

    def hotkeys(self) -> dict[str, str] | None:
        return self._result
