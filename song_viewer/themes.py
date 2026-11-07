"""Original soft high-contrast themes for low-vision reading."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    bg: str
    fg: str
    panel: str
    title_bar: str
    button: str
    button_hover: str
    border: str
    focus: str
    accent: str
    muted: str
    chord: str
    success: str
    danger: str
    selection: str
    input_bg: str
    menu_bg: str


# Soft dark backgrounds + clear but non-glaring text/chord pairs.
THEMES: dict[str, Theme] = {
    "graphite": Theme(
        id="graphite",
        name="Graphite Soft",
        bg="#2a2d32",
        fg="#e8eaed",
        panel="#22252a",
        title_bar="#1e2126",
        button="#3a3f47",
        button_hover="#4c535c",
        border="#555c66",
        focus="#7a8490",
        accent="#d6b27a",
        muted="#9aa1ab",
        chord="#e0a070",
        success="#8fbf8a",
        danger="#d98989",
        selection="#9aa1ab33",
        input_bg="#2a2d32",
        menu_bg="#2a2d32",
    ),
    "harbor": Theme(
        id="harbor",
        name="Night Harbor",
        bg="#243039",
        fg="#e6eef2",
        panel="#1c262e",
        title_bar="#182128",
        button="#33424d",
        button_hover="#425564",
        border="#5a6d7a",
        focus="#7f96a6",
        accent="#8ec8c0",
        muted="#97a8b3",
        chord="#e2b56f",
        success="#8fbf9a",
        danger="#d9899a",
        selection="#97a8b333",
        input_bg="#243039",
        menu_bg="#243039",
    ),
    "forest": Theme(
        id="forest",
        name="Forest Dusk",
        bg="#273129",
        fg="#ebe8df",
        panel="#1f2721",
        title_bar="#1a211c",
        button="#364238",
        button_hover="#48574a",
        border="#5d6d5f",
        focus="#809484",
        accent="#c5b87a",
        muted="#9aab9c",
        chord="#e09a7a",
        success="#93c08f",
        danger="#d98989",
        selection="#9aab9c33",
        input_bg="#273129",
        menu_bg="#273129",
    ),
    "ember": Theme(
        id="ember",
        name="Ember Soft",
        bg="#322824",
        fg="#f0e6dc",
        panel="#281f1c",
        title_bar="#231b18",
        button="#463632",
        button_hover="#5a4741",
        border="#726058",
        focus="#957e73",
        accent="#d9b07a",
        muted="#b09a8e",
        chord="#e0a070",
        success="#9bbf8a",
        danger="#d98989",
        selection="#b09a8e33",
        input_bg="#322824",
        menu_bg="#322824",
    ),
    "slate": Theme(
        id="slate",
        name="Slate Sky",
        bg="#2a3038",
        fg="#e9eef4",
        panel="#222830",
        title_bar="#1c2128",
        button="#3a4450",
        button_hover="#4c5866",
        border="#627080",
        focus="#8494a6",
        accent="#8eb8d9",
        muted="#9aabba",
        chord="#d9b07a",
        success="#8fbf9a",
        danger="#d9899a",
        selection="#9aabba33",
        input_bg="#2a3038",
        menu_bg="#2a3038",
    ),
    "plum": Theme(
        id="plum",
        name="Plum Quiet",
        bg="#302830",
        fg="#eee6ef",
        panel="#261f26",
        title_bar="#211a21",
        button="#433843",
        button_hover="#574a57",
        border="#6f606f",
        focus="#917f91",
        accent="#c9b07a",
        muted="#b09eb0",
        chord="#e0a080",
        success="#9bbf8a",
        danger="#d9899a",
        selection="#b09eb033",
        input_bg="#302830",
        menu_bg="#302830",
    ),
    "sandstone": Theme(
        id="sandstone",
        name="Sandstone Night",
        bg="#322e28",
        fg="#efe8dc",
        panel="#28241f",
        title_bar="#221f1a",
        button="#454038",
        button_hover="#5a544a",
        border="#726a5c",
        focus="#958b79",
        accent="#8fbfb0",
        muted="#b0a694",
        chord="#e0a878",
        success="#93c08f",
        danger="#d98989",
        selection="#b0a69433",
        input_bg="#322e28",
        menu_bg="#322e28",
    ),
    "fog": Theme(
        id="fog",
        name="Fog Lamp",
        bg="#33363b",
        fg="#eceae4",
        panel="#2a2d31",
        title_bar="#24272b",
        button="#454950",
        button_hover="#585e66",
        border="#6d737c",
        focus="#8e959f",
        accent="#d4c48a",
        muted="#a8adb4",
        chord="#8fb8d4",
        success="#8fbf9a",
        danger="#d98989",
        selection="#a8adb433",
        input_bg="#33363b",
        menu_bg="#33363b",
    ),
}

DEFAULT_THEME_ID = "graphite"

# Old Monokai ids -> closest new theme
_THEME_ALIASES = {
    "spectrum": "graphite",
    "pro": "ember",
    "classic": "forest",
    "machine": "harbor",
    "octagon": "slate",
    "ristretto": "plum",
}


def get_theme(theme_id: str) -> Theme:
    tid = _THEME_ALIASES.get(theme_id, theme_id)
    return THEMES.get(tid, THEMES[DEFAULT_THEME_ID])


def stylesheet(theme: Theme, base_font_pt: int = 14) -> str:
    """Global Qt styles for large, readable controls."""
    return f"""
    QWidget {{
        background-color: {theme.bg};
        color: {theme.fg};
        font-size: {base_font_pt}pt;
        font-family: "Segoe UI", "Arial", sans-serif;
    }}
    QMainWindow, QDialog {{
        background-color: {theme.bg};
    }}
    QMenuBar {{
        background-color: {theme.title_bar};
        color: {theme.muted};
        padding: 6px 10px;
        font-size: {base_font_pt}pt;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        margin: 0 2px;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background-color: {theme.button};
        color: {theme.fg};
    }}
    QMenu {{
        background-color: {theme.menu_bg};
        color: {theme.fg};
        border: 1px solid {theme.border};
        padding: 8px;
        font-size: {base_font_pt + 1}pt;
    }}
    QMenu::item {{
        padding: 10px 28px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {theme.button_hover};
        color: {theme.accent};
    }}
    QMenu::separator {{
        height: 1px;
        background: {theme.border};
        margin: 6px 10px;
    }}
    QPushButton {{
        background-color: {theme.button};
        color: {theme.fg};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 12px 16px;
        min-height: 32px;
        margin: 2px 0;
        font-size: {base_font_pt}pt;
    }}
    QPushButton:hover {{
        background-color: {theme.button_hover};
        color: {theme.accent};
    }}
    QPushButton:pressed {{
        background-color: {theme.focus};
    }}
    QPushButton#dangerButton {{
        border-color: {theme.danger};
        color: {theme.danger};
    }}
    QPushButton#dangerButton:hover {{
        background-color: {theme.button_hover};
        color: {theme.fg};
        border-color: {theme.danger};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit {{
        background-color: {theme.input_bg};
        color: {theme.fg};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 10px 12px;
        min-height: 30px;
        margin: 2px 0;
        selection-background-color: {theme.button_hover};
        selection-color: {theme.accent};
        font-size: {base_font_pt}pt;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {theme.menu_bg};
        color: {theme.fg};
        selection-background-color: {theme.button_hover};
        selection-color: {theme.accent};
        border: 1px solid {theme.border};
        padding: 4px;
        font-size: {base_font_pt}pt;
    }}
    QSlider::groove:horizontal {{
        height: 10px;
        background: {theme.button};
        border-radius: 5px;
        margin: 6px 0;
    }}
    QSlider::handle:horizontal {{
        background: {theme.accent};
        width: 22px;
        height: 22px;
        margin: -7px 0;
        border-radius: 11px;
    }}
    QSlider::sub-page:horizontal {{
        background: {theme.chord};
        border-radius: 5px;
    }}
    QLabel {{
        background: transparent;
        color: {theme.fg};
        font-size: {base_font_pt}pt;
    }}
    QLabel#mutedLabel {{
        color: {theme.muted};
        margin-top: 4px;
        margin-bottom: 2px;
    }}
    QLabel#sectionTitle {{
        color: {theme.accent};
        font-size: {base_font_pt}pt;
        font-weight: 600;
        margin-top: 6px;
        margin-bottom: 0px;
        padding: 0;
    }}
    QFrame#sidePanel QLabel {{
        margin: 0;
        padding: 0;
        line-height: 1.05;
    }}
    QFrame#sidePanel QLabel#mutedLabel {{
        margin-top: 0px;
        margin-bottom: 0px;
        font-size: {base_font_pt - 1}pt;
    }}
    QFrame#sidePanel QPushButton {{
        padding: 8px 12px;
        min-height: 24px;
        margin: 1px 0;
    }}
    QFrame#sidePanel QLineEdit,
    QFrame#sidePanel QSpinBox,
    QFrame#sidePanel QDoubleSpinBox,
    QFrame#sidePanel QComboBox {{
        padding: 6px 10px;
        min-height: 24px;
        margin: 0;
    }}
    QFrame#sidePanel QSlider::groove:horizontal {{
        margin: 2px 0;
    }}
    QPushButton#panelToggle {{
        padding: 6px 10px;
        min-height: 22px;
        border-radius: 6px;
    }}
    QStatusBar {{
        background-color: {theme.title_bar};
        color: {theme.muted};
        border-top: 1px solid {theme.border};
        font-size: {base_font_pt - 1}pt;
        padding: 4px;
    }}
    QScrollBar:vertical {{
        background: {theme.panel};
        width: 18px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {theme.button_hover};
        min-height: 40px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {theme.panel};
        height: 18px;
    }}
    QScrollBar::handle:horizontal {{
        background: {theme.button_hover};
        min-width: 40px;
        border-radius: 6px;
        margin: 2px;
    }}
    QListWidget {{
        background-color: {theme.panel};
        color: {theme.fg};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 8px;
        font-size: {base_font_pt + 2}pt;
        outline: none;
    }}
    QListWidget::item {{
        padding: 14px 12px;
        border-radius: 6px;
        margin: 2px 0;
    }}
    QListWidget::item:selected {{
        background-color: {theme.button};
        color: {theme.accent};
    }}
    QListWidget::item:hover {{
        background-color: {theme.button_hover};
    }}
    QTextEdit {{
        background-color: {theme.bg};
        color: {theme.fg};
        border: none;
        selection-background-color: {theme.button_hover};
        selection-color: {theme.accent};
        padding: 16px;
    }}
    QFrame#sidePanel {{
        background-color: {theme.panel};
        border-right: 1px solid {theme.border};
    }}
    QFrame#sideSection {{
        background-color: transparent;
        border: 1px solid {theme.border};
        border-radius: 10px;
        margin: 4px 0;
        padding: 4px;
    }}
    """
