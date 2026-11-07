"""Song library dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from song_viewer.settings_store import list_library_songs


class LibraryDialog(QDialog):
    song_chosen = Signal(str)
    song_deleted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Song Library")
        self.resize(720, 560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("All saved songs")
        title.setStyleSheet("font-size: 20pt; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("Double-click to open. You can search by title.")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.list, stretch=1)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(self._delete_selected)
        buttons.addWidget(btn_delete)
        buttons.addStretch(1)
        btn_open = QPushButton("Open")
        btn_open.clicked.connect(self._open_selected)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        buttons.addWidget(btn_open)
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

        self._paths: list[Path] = []
        self.reload()

    def reload(self) -> None:
        self._paths = list_library_songs()
        self._filter(self.search.text())

    def _filter(self, query: str = "") -> None:
        self.list.clear()
        q = (query or "").strip().lower()
        for path in self._paths:
            title = path.stem.replace(".song", "")
            if q and q not in title.lower() and q not in path.name.lower():
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, str(path))
            item.setToolTip(str(path))
            self.list.addItem(item)

    def _open_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.song_chosen.emit(path)
            self.accept()

    def _open_selected(self) -> None:
        item = self.list.currentItem()
        if item:
            self._open_item(item)

    def _delete_selected(self) -> None:
        item = self.list.currentItem()
        if not item:
            QMessageBox.information(self, "Delete", "Select a song first.")
            return
        path_str = item.data(Qt.UserRole)
        title = item.text()
        answer = QMessageBox.question(
            self,
            "Delete Song",
            f'Delete "{title}"?\n\nThis removes the file from disk.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        path = Path(path_str)
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            QMessageBox.critical(self, "Delete Error", str(exc))
            return
        self.song_deleted.emit(path_str)
        self.reload()
