"""Help: current hotkeys and fixed gestures."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from song_viewer.hotkeys import FIXED_GESTURES, HOTKEY_LABELS


class HelpHotkeysDialog(QDialog):
    def __init__(self, hotkeys: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(620, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Current shortcuts (customize via Edit → Hotkeys…)"))

        rows = [(HOTKEY_LABELS.get(k, k), v) for k, v in hotkeys.items()]
        rows.extend(FIXED_GESTURES)

        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        for i, (action, shortcut) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(action))
            table.setItem(i, 1, QTableWidgetItem(shortcut))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)
