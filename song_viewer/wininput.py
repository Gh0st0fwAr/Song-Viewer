"""Reliable modifier state helpers (Windows GetAsyncKeyState)."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10


def _async_down(vk: int) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:  # noqa: BLE001
        return False


def ctrl_down() -> bool:
    if _async_down(VK_CONTROL):
        return True
    return bool(QApplication.queryKeyboardModifiers() & Qt.ControlModifier)


def alt_down() -> bool:
    if _async_down(VK_MENU):
        return True
    return bool(QApplication.queryKeyboardModifiers() & Qt.AltModifier)


def shift_down() -> bool:
    if _async_down(VK_SHIFT):
        return True
    return bool(QApplication.queryKeyboardModifiers() & Qt.ShiftModifier)


def ctrl_shift_down() -> bool:
    """Preferred for wheel gestures — Alt is often stolen by Windows."""
    return ctrl_down() and shift_down()
