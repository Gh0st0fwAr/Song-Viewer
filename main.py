#!/usr/bin/env python3
"""Точка входа: Song Viewer."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from song_viewer.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Song Viewer")
    app.setOrganizationName("SongViewer")

    # Крупный UI-шрифт по умолчанию (удобнее при слабом зрении)
    font = QFont("Segoe UI", 14)
    app.setFont(font)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
