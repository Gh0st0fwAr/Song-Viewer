"""Main window for Song Viewer."""

from __future__ import annotations

from pathlib import Path

from functools import partial

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from song_viewer.editor import SongEditor
from song_viewer.help_dialog import HelpHotkeysDialog
from song_viewer.hotkeys import HOTKEY_LABELS, merge_hotkeys
from song_viewer.hotkeys_dialog import HotkeysDialog
from song_viewer.library_dialog import LibraryDialog
from song_viewer.settings_store import (
    SONGS_DIR,
    add_recent,
    ensure_dirs,
    load_settings,
    save_settings,
)
from song_viewer.song_format import (
    document_to_song_data,
    import_plain_text,
    load_song,
    save_song,
    song_data_to_document,
)
from song_viewer.themes import DEFAULT_THEME_ID, THEMES, get_theme, stylesheet
from song_viewer.wininput import ctrl_shift_down


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.settings = load_settings()
        self.hotkeys = merge_hotkeys(self.settings.get("hotkeys"))
        self.settings["hotkeys"] = dict(self.hotkeys)
        self.current_path: Path | None = None
        self.song_title = "New Song"
        self._scroll_mode: str | None = None
        self._timed_total_steps = 0
        self._timed_step = 0
        self._timed_pixels_per_tick = 0.0
        self._scroll_accum = 0.0
        self._actions: dict[str, QAction] = {}
        self._shortcuts: dict[str, QShortcut] = {}
        self._hotkey_slots: dict[str, object] = {}
        self._hotkey_armed = True
        self._suppress_toast = True

        self.setWindowTitle("Song Viewer — New Song")
        self.resize(1280, 860)

        self.editor = SongEditor()
        self.editor.font_size_changed.connect(self._on_font_size_changed)
        self.editor.status_message.connect(self._set_status)
        self.editor.scroll_speed_nudge.connect(self._nudge_scroll_speed)
        self.editor.reflow_needed.connect(self._schedule_reflow)

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(40)
        self._scroll_timer.timeout.connect(self._on_scroll_tick)

        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._hide_value_toast)

        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.timeout.connect(self._do_reflow)

        self._build_ui()
        self._build_menus()
        self._apply_hotkeys()
        self._apply_theme(self.settings.get("theme_id", DEFAULT_THEME_ID))

        # Apply LH before font: set_editor_font emits font_size_changed → _persist,
        # which would otherwise save the spin's default 60% over a migrated 100%.
        lh = int(self.settings.get("line_height_percent", 100))
        self._set_line_height_controls(lh)
        self.editor.set_line_height_percent(lh)

        self.editor.set_editor_font(
            self.settings.get("font_family", "Consolas"),
            int(self.settings.get("font_size", 28)),
        )
        self.font_slider.blockSignals(True)
        self.font_slider.setValue(int(self.settings.get("font_size", 28)))
        self.font_spin.blockSignals(True)
        self.font_spin.setValue(int(self.settings.get("font_size", 28)))
        self.font_slider.blockSignals(False)
        self.font_spin.blockSignals(False)

        self._set_scroll_speed(float(self.settings.get("scroll_speed_percent", 30.0)))
        self.minutes_spin.setValue(int(self.settings.get("scroll_minutes", 2)))
        self.seconds_spin.setValue(int(self.settings.get("scroll_seconds", 30)))

        visible = bool(self.settings.get("panel_visible", True))
        self.side_panel.setHidden(not visible)
        self._sync_panel_toggle_label()

        geo = self.settings.get("window_geometry")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except (ValueError, TypeError):
                pass

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._suppress_toast = False
        self._schedule_reflow()
        self._set_status("Ready.")

    def _section(self, title: str) -> QLabel:
        lab = QLabel(title)
        lab.setObjectName("sectionTitle")
        return lab

    def _muted(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("mutedLabel")
        return lab

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # slim strip with panel toggle always visible
        strip = QFrame()
        strip.setObjectName("sidePanel")
        strip.setFixedWidth(44)
        strip_layout = QVBoxLayout(strip)
        strip_layout.setContentsMargins(6, 10, 6, 10)
        strip_layout.setSpacing(6)
        self.btn_panel_toggle = QPushButton("«")
        self.btn_panel_toggle.setObjectName("panelToggle")
        self.btn_panel_toggle.setToolTip("Show / hide controls")
        self.btn_panel_toggle.clicked.connect(self.toggle_panel)
        strip_layout.addWidget(self.btn_panel_toggle)
        strip_layout.addStretch(1)
        root.addWidget(strip)

        side = QFrame()
        side.setObjectName("sidePanel")
        side.setFixedWidth(320)
        self.side_panel = side
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(12, 10, 12, 10)
        side_layout.setSpacing(4)

        side_title = QLabel("Controls")
        side_title.setStyleSheet("font-size: 15pt; font-weight: bold; margin: 0; padding: 0;")
        side_layout.addWidget(side_title)

        side_layout.addWidget(self._section("Song"))
        side_layout.addWidget(self._muted("Title"))
        self.title_edit = QLineEdit(self.song_title)
        self.title_edit.textChanged.connect(self._on_title_changed)
        side_layout.addWidget(self.title_edit)

        side_layout.addWidget(self._section("Appearance"))
        side_layout.addWidget(self._muted("Font size"))
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(12, 72)
        self.font_slider.valueChanged.connect(self._on_font_slider)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(12, 72)
        self.font_spin.setFixedWidth(72)
        self.font_spin.valueChanged.connect(self._on_font_spin)
        font_row.addWidget(self.font_slider, stretch=1)
        font_row.addWidget(self.font_spin)
        side_layout.addLayout(font_row)

        side_layout.addWidget(self._muted("Line height"))
        lh_row = QHBoxLayout()
        lh_row.setSpacing(8)
        self.line_height_slider = QSlider(Qt.Horizontal)
        self.line_height_slider.setRange(60, 250)
        self.line_height_slider.valueChanged.connect(self._on_line_height_slider)
        self.line_height_spin = QSpinBox()
        self.line_height_spin.setRange(60, 250)
        self.line_height_spin.setSuffix(" %")
        self.line_height_spin.setFixedWidth(84)
        self.line_height_spin.valueChanged.connect(self._on_line_height_spin)
        lh_row.addWidget(self.line_height_slider, stretch=1)
        lh_row.addWidget(self.line_height_spin)
        side_layout.addLayout(lh_row)

        side_layout.addWidget(self._muted("Theme"))
        self.theme_combo = QComboBox()
        for tid, theme in THEMES.items():
            self.theme_combo.addItem(theme.name, tid)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        side_layout.addWidget(self.theme_combo)

        side_layout.addWidget(self._section("Scroll by speed"))
        side_layout.addWidget(self._muted("Speed %"))
        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.valueChanged.connect(self._on_speed_slider)
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 100.0)
        self.speed_spin.setSingleStep(0.5)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setSuffix(" %")
        self.speed_spin.setFixedWidth(90)
        self.speed_spin.valueChanged.connect(self._on_speed_spin)
        speed_row.addWidget(self.speed_slider, stretch=1)
        speed_row.addWidget(self.speed_spin)
        side_layout.addLayout(speed_row)

        self.btn_scroll_speed = QPushButton("▶  Scroll by speed")
        self.btn_scroll_speed.clicked.connect(self.toggle_speed_scroll)
        side_layout.addWidget(self.btn_scroll_speed)

        side_layout.addWidget(self._section("Scroll by time"))
        side_layout.addWidget(self._muted("Duration"))
        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(2)
        self.minutes_spin.setSuffix(" min")
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(30)
        self.seconds_spin.setSuffix(" sec")
        time_row.addWidget(self.minutes_spin)
        time_row.addWidget(self.seconds_spin)
        side_layout.addLayout(time_row)

        self.btn_scroll_timed = QPushButton("⏱  Scroll by time")
        self.btn_scroll_timed.clicked.connect(self.toggle_timed_scroll)
        side_layout.addWidget(self.btn_scroll_timed)

        side_layout.addWidget(self._section("Chords"))
        tr_row = QHBoxLayout()
        tr_row.setSpacing(8)
        btn_down = QPushButton("−1")
        btn_down.setFixedWidth(56)
        btn_down.clicked.connect(lambda: self.editor.transpose(-1))
        btn_up = QPushButton("+1")
        btn_up.setFixedWidth(56)
        btn_up.clicked.connect(lambda: self.editor.transpose(1))
        btn_detect = QPushButton("Detect")
        btn_detect.clicked.connect(self.editor.auto_detect_chords)
        tr_row.addWidget(btn_down)
        tr_row.addWidget(btn_up)
        tr_row.addWidget(btn_detect, stretch=1)
        side_layout.addLayout(tr_row)

        side_layout.addStretch(1)
        root.addWidget(side)

        self.editor_frame = QFrame()
        editor_layout = QVBoxLayout(self.editor_frame)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addWidget(self.editor)
        self.value_toast = QLabel(self.editor_frame)
        self.value_toast.setObjectName("valueToast")
        self.value_toast.setAlignment(Qt.AlignCenter)
        self.value_toast.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.value_toast.hide()
        root.addWidget(self.editor_frame, stretch=1)
        self.setStatusBar(QStatusBar())

    def _bind(self, key: str, slot, *, checkable: bool = False) -> QAction:
        act = QAction(HOTKEY_LABELS.get(key, key), self)
        act.triggered.connect(slot)
        if checkable:
            act.setCheckable(True)
        self._actions[key] = act
        self._hotkey_slots[key] = slot
        return act

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self._bind("new_song", self.new_song))
        file_menu.addAction(self._bind("open_song", self.open_song_dialog))

        act_import = QAction("Import from .txt…", self)
        act_import.triggered.connect(self.import_txt)
        file_menu.addAction(act_import)

        self.recent_menu = file_menu.addMenu("Open Recent")
        self._rebuild_recent_menu()
        file_menu.addAction(self._bind("library", self.open_library))
        file_menu.addSeparator()
        file_menu.addAction(self._bind("save_song", self.save_song))
        file_menu.addAction(self._bind("save_song_as", self.save_song_as))
        file_menu.addSeparator()
        act_quit = QAction("Exit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self._bind("bold", self.editor.toggle_bold))
        edit_menu.addAction(self._bind("italic", self.editor.toggle_italic))
        edit_menu.addAction(self._bind("mark_chord", self.editor.mark_selection_as_chord))
        edit_menu.addAction(
            self._bind("add_chord_line", lambda: self.editor.add_chord_line_at_cursor())
        )
        edit_menu.addAction(self._bind("detect_chords", self.editor.auto_detect_chords))
        edit_menu.addAction(self._bind("transpose_up", lambda: self.editor.transpose(1)))
        edit_menu.addAction(self._bind("transpose_down", lambda: self.editor.transpose(-1)))
        edit_menu.addSeparator()
        act_hotkeys = QAction("Hotkeys…", self)
        act_hotkeys.triggered.connect(self.open_hotkeys_dialog)
        edit_menu.addAction(act_hotkeys)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self._bind("increase_font", lambda: self._bump_font(1)))
        view_menu.addAction(self._bind("decrease_font", lambda: self._bump_font(-1)))
        view_menu.addSeparator()
        view_menu.addAction(self._bind("toggle_panel", self.toggle_panel))

        scroll_menu = self.menuBar().addMenu("Scroll")
        scroll_menu.addAction(self._bind("toggle_speed_scroll", self.toggle_speed_scroll))
        scroll_menu.addAction(self._bind("toggle_timed_scroll", self.toggle_timed_scroll))
        scroll_menu.addAction(self._bind("stop_scroll", self.stop_scroll))

        help_menu = self.menuBar().addMenu("Help")
        act_help = QAction("Keyboard Shortcuts…", self)
        act_help.triggered.connect(self.open_help_hotkeys)
        help_menu.addAction(act_help)

    def _apply_hotkeys(self) -> None:
        for sc in self._shortcuts.values():
            sc.setParent(None)
            sc.deleteLater()
        self._shortcuts.clear()
        self._hotkey_armed = True

        for key, act in self._actions.items():
            seq_text = self.hotkeys.get(key, "")
            seq = QKeySequence(seq_text)
            # Never put the shortcut on QAction — duplicates the QShortcut handler.
            act.setShortcut(QKeySequence())
            label = HOTKEY_LABELS.get(key, key)
            act.setText(f"{label}\t{seq_text}")
            act.setToolTip(f"{label} ({seq_text})")
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.setAutoRepeat(False)
            slot = self._hotkey_slots.get(key)
            if slot is not None:
                sc.activated.connect(partial(self._armed_hotkey, key, slot))
            self._shortcuts[key] = sc

        speed_seq = self.hotkeys.get("toggle_speed_scroll", "Ctrl+1")
        timed_seq = self.hotkeys.get("toggle_timed_scroll", "Ctrl+2")
        self.btn_scroll_speed.setToolTip(speed_seq)
        self.btn_scroll_timed.setToolTip(timed_seq)
        self.btn_panel_toggle.setToolTip(
            self.hotkeys.get("toggle_panel", "Ctrl+Alt+P")
        )

        # Reliable scroll-speed nudges (wheel with Alt is flaky on Windows)
        for seq, delta in (("Ctrl+[", -0.5), ("Ctrl+]", 0.5)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.setAutoRepeat(False)
            sc.activated.connect(partial(self._nudge_scroll_speed, delta))
            self._shortcuts[f"_speed_{seq}"] = sc

    def _armed_hotkey(self, key: str, slot) -> None:
        """Fire once per physical key press; re-arm on key release."""
        if not self._hotkey_armed:
            return
        self._hotkey_armed = False
        slot()

    def _schedule_reflow(self) -> None:
        self._reflow_timer.start(120)

    def _do_reflow(self) -> None:
        self.editor.reflow_chords_to_width()

    def _show_value_toast(self, label: str, value: str) -> None:
        if self._suppress_toast:
            return
        self._toast_label = label
        self._toast_value = value
        self.value_toast.setText(f"{label}: {value}")
        self.value_toast.adjustSize()
        self._position_value_toast()
        self.value_toast.show()
        self.value_toast.raise_()
        self._toast_timer.start(1400)

    def _position_value_toast(self) -> None:
        frame_w = max(self.editor_frame.width(), 1)
        toast_w = self.value_toast.sizeHint().width() + 8
        toast_h = self.value_toast.sizeHint().height()
        self.value_toast.resize(toast_w, toast_h)
        x = max(12, (frame_w - toast_w) // 2)
        self.value_toast.move(x, 18)

    def _hide_value_toast(self) -> None:
        self.value_toast.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.value_toast.isVisible():
            self._position_value_toast()

    def open_hotkeys_dialog(self) -> None:
        dlg = HotkeysDialog(self.hotkeys, self)
        if dlg.exec() and dlg.hotkeys():
            self.hotkeys = dlg.hotkeys() or self.hotkeys
            self.settings["hotkeys"] = dict(self.hotkeys)
            self._apply_hotkeys()
            self._persist()
            self._set_status("Hotkeys saved")

    def open_help_hotkeys(self) -> None:
        HelpHotkeysDialog(self.hotkeys, self).exec()

    def eventFilter(self, obj, event):  # noqa: N802
        et = event.type()
        if et == QEvent.Type.KeyRelease:
            # Re-arm only after the key is up — one physical press = one toggle.
            self._hotkey_armed = True
        if et == QEvent.Type.Wheel and isinstance(event, QWheelEvent):
            if ctrl_shift_down():
                delta = event.angleDelta().y() or event.pixelDelta().y()
                if delta != 0:
                    self._nudge_scroll_speed(0.5 if delta > 0 else -0.5)
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._schedule_reflow()

    def toggle_panel(self) -> None:
        # use isHidden(): isVisible() is False while the main window is not shown yet
        self.side_panel.setHidden(not self.side_panel.isHidden())
        self.settings["panel_visible"] = not self.side_panel.isHidden()
        self._sync_panel_toggle_label()
        self._persist()

    def _sync_panel_toggle_label(self) -> None:
        if self.side_panel.isHidden():
            self.btn_panel_toggle.setText("»")
        else:
            self.btn_panel_toggle.setText("«")

    def _apply_theme(self, theme_id: str) -> None:
        theme = get_theme(theme_id)
        self.settings["theme_id"] = theme.id
        ui_pt = int(self.settings.get("ui_font_pt", 14))
        self.setStyleSheet(
            stylesheet(theme, ui_pt)
            + f"""
            QLabel#valueToast {{
                background-color: rgba(18, 18, 22, 230);
                color: {theme.accent};
                font-size: 28pt;
                font-weight: 700;
                padding: 16px 28px;
                border: 1px solid {theme.border};
                border-radius: 12px;
            }}
            """
        )
        self.editor.set_theme_colors(theme.fg, theme.chord)
        idx = self.theme_combo.findData(theme.id)
        if idx >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)

    def _on_theme_changed(self, _index: int) -> None:
        tid = self.theme_combo.currentData()
        if tid:
            self._apply_theme(tid)
            self._persist()

    def _on_font_slider(self, value: int) -> None:
        self.font_spin.blockSignals(True)
        self.font_spin.setValue(value)
        self.font_spin.blockSignals(False)
        self.editor.set_editor_font(self.editor.font_family(), value)
        self._show_value_toast("Font size", str(value))

    def _on_font_spin(self, value: int) -> None:
        self.font_slider.blockSignals(True)
        self.font_slider.setValue(value)
        self.font_slider.blockSignals(False)
        self.editor.set_editor_font(self.editor.font_family(), value)
        self._show_value_toast("Font size", str(value))

    def _on_font_size_changed(self, size: int) -> None:
        self.font_slider.blockSignals(True)
        self.font_spin.blockSignals(True)
        self.font_slider.setValue(size)
        self.font_spin.setValue(size)
        self.font_slider.blockSignals(False)
        self.font_spin.blockSignals(False)
        self.settings["font_size"] = size
        if not self._suppress_toast:
            self._persist()
        self._show_value_toast("Font size", str(size))

    def _set_line_height_controls(self, percent: int) -> None:
        percent = max(60, min(250, int(percent)))
        self.line_height_slider.blockSignals(True)
        self.line_height_spin.blockSignals(True)
        self.line_height_slider.setValue(percent)
        self.line_height_spin.setValue(percent)
        self.line_height_slider.blockSignals(False)
        self.line_height_spin.blockSignals(False)

    def _on_line_height_slider(self, value: int) -> None:
        self.line_height_spin.blockSignals(True)
        self.line_height_spin.setValue(value)
        self.line_height_spin.blockSignals(False)
        self.editor.set_line_height_percent(value)
        self.settings["line_height_percent"] = int(value)
        if not self._suppress_toast:
            self._persist()
        self._show_value_toast("Line height", f"{value}%")

    def _on_line_height_spin(self, value: int) -> None:
        self.line_height_slider.blockSignals(True)
        self.line_height_slider.setValue(value)
        self.line_height_slider.blockSignals(False)
        self.editor.set_line_height_percent(value)
        self.settings["line_height_percent"] = int(value)
        if not self._suppress_toast:
            self._persist()
        self._show_value_toast("Line height", f"{value}%")

    def _bump_font(self, delta: int) -> None:
        self.editor.set_editor_font(self.editor.font_family(), self.editor.font_size() + delta)

    def _on_title_changed(self, text: str) -> None:
        self.song_title = text.strip() or "Untitled"
        suffix = f" — {self.current_path.name}" if self.current_path else ""
        self.setWindowTitle(f"Song Viewer — {self.song_title}{suffix}")

    def _set_scroll_speed(self, percent: float, *, announce: bool = False) -> None:
        percent = round(max(0.5, min(100.0, percent)) * 2) / 2
        self.speed_slider.blockSignals(True)
        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(percent)
        self.speed_slider.setValue(int(round(percent * 2)))
        self.speed_slider.blockSignals(False)
        self.speed_spin.blockSignals(False)
        if announce:
            self._show_value_toast("Scroll speed", f"{percent:.1f}%")

    def _nudge_scroll_speed(self, delta: float) -> None:
        self._set_scroll_speed(self.speed_spin.value() + delta, announce=True)
        self._set_status(f"Scroll speed: {self.speed_spin.value():.1f}%")

    def _on_speed_slider(self, value: int) -> None:
        percent = value / 2.0
        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(percent)
        self.speed_spin.blockSignals(False)
        self._show_value_toast("Scroll speed", f"{percent:.1f}%")

    def _on_speed_spin(self, value: float) -> None:
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(round(value * 2)))
        self.speed_slider.blockSignals(False)
        self._show_value_toast("Scroll speed", f"{value:.1f}%")

    def toggle_speed_scroll(self) -> None:
        if self._scroll_mode == "speed":
            self._stop_scroll_internal()
            return
        self._start_speed_scroll()

    def toggle_timed_scroll(self) -> None:
        if self._scroll_mode == "timed":
            self._stop_scroll_internal()
            return
        self._start_timed_scroll()

    def _start_speed_scroll(self) -> None:
        self._stop_scroll_internal(announce=False)
        bar = self.editor.verticalScrollBar()
        if bar.maximum() <= 0:
            self._set_status("Nothing to scroll — text fits in the window")
            return
        self._scroll_mode = "speed"
        self._scroll_accum = float(bar.value())
        self._scroll_timer.start()
        self.btn_scroll_speed.setText("⏸  Pause speed scroll")
        self.btn_scroll_timed.setText("⏱  Scroll by time")
        self._set_status(f"Scrolling by speed: {self.speed_spin.value():.1f}%")

    def _start_timed_scroll(self) -> None:
        self._stop_scroll_internal(announce=False)
        bar = self.editor.verticalScrollBar()
        if bar.maximum() <= 0:
            self._set_status("Nothing to scroll — text fits in the window")
            return
        duration_ms = (self.minutes_spin.value() * 60 + self.seconds_spin.value()) * 1000
        if duration_ms <= 0:
            QMessageBox.warning(self, "Time", "Set a duration greater than zero")
            return
        tick = self._scroll_timer.interval()
        steps = max(1, duration_ms // tick)
        self._timed_total_steps = steps
        self._timed_step = 0
        remaining = bar.maximum() - bar.value()
        if remaining <= 0:
            bar.setValue(bar.minimum())
            remaining = bar.maximum() - bar.minimum()
        if remaining <= 0:
            self._set_status("Nothing to scroll — text fits in the window")
            return
        self._scroll_accum = float(bar.value())
        self._timed_pixels_per_tick = remaining / steps
        self._scroll_mode = "timed"
        self._scroll_timer.start()
        self.btn_scroll_timed.setText("⏸  Pause timed scroll")
        self.btn_scroll_speed.setText("▶  Scroll by speed")
        mm = self.minutes_spin.value()
        ss = self.seconds_spin.value()
        self._set_status(f"Scrolling by time: {mm:02d}:{ss:02d}")

    def _stop_scroll_internal(self, *, announce: bool = True) -> None:
        was = self._scroll_mode
        self._scroll_timer.stop()
        self._scroll_mode = None
        self.btn_scroll_speed.setText("▶  Scroll by speed")
        self.btn_scroll_timed.setText("⏱  Scroll by time")
        if announce and was:
            self._set_status("Scroll stopped")

    def stop_scroll(self) -> None:
        self._stop_scroll_internal()

    def _on_scroll_tick(self) -> None:
        bar = self.editor.verticalScrollBar()
        if self._scroll_mode == "speed":
            pct = self.speed_spin.value() / 100.0
            # Half of the previous curve — 0.5% was still too fast for reading.
            px_per_sec = max(4.0, self.editor.viewport().height() * 0.175) * (0.15 + 2.85 * pct)
            px = px_per_sec * (self._scroll_timer.interval() / 1000.0)
            self._scroll_accum += px
            new_val = int(self._scroll_accum)
            if new_val >= bar.maximum():
                bar.setValue(bar.maximum())
                self.stop_scroll()
                self._set_status("Reached end of text")
                return
            bar.setValue(new_val)
        elif self._scroll_mode == "timed":
            self._scroll_accum += self._timed_pixels_per_tick
            self._timed_step += 1
            new_val = int(round(self._scroll_accum))
            if self._timed_step >= self._timed_total_steps or new_val >= bar.maximum():
                bar.setValue(bar.maximum())
                self.stop_scroll()
                self._set_status("Timed scroll finished")
                return
            bar.setValue(min(new_val, bar.maximum()))

    def new_song(self) -> None:
        self.stop_scroll()
        self.editor.clear()
        self.current_path = None
        self.title_edit.setText("New Song")
        self._set_scroll_speed(float(self.settings.get("scroll_speed_percent", 30.0)))
        self.minutes_spin.setValue(int(self.settings.get("scroll_minutes", 2)))
        self.seconds_spin.setValue(int(self.settings.get("scroll_seconds", 30)))
        self._suppress_toast = True
        lh = int(self.settings.get("line_height_percent", 100))
        self._set_line_height_controls(lh)
        self.editor.set_line_height_percent(lh)
        self._suppress_toast = False
        self._set_status("New song")

    def open_song_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Song",
            str(SONGS_DIR),
            "Songs (*.song.json *.json);;All files (*.*)",
        )
        if path:
            self.open_path(path)

    def import_txt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Text",
            str(SONGS_DIR),
            "Text (*.txt *.md);;All files (*.*)",
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8")
        title = Path(path).stem
        data = import_plain_text(text, title)
        self._load_song_data(data, path=None)
        self.title_edit.setText(title)
        self.editor.auto_detect_chords()
        self._set_status(f"Imported from {Path(path).name}")

    def open_path(self, path: str | Path) -> None:
        path = Path(path)
        try:
            data = load_song(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open Error", str(exc))
            return
        self._load_song_data(data, path=path)
        add_recent(self.settings, str(path))
        self._rebuild_recent_menu()
        self._persist()
        self._set_status(f"Opened: {path.name}")

    def _load_song_data(self, data: dict, path: Path | None) -> None:
        self._stop_scroll_internal(announce=False)
        self._suppress_toast = True
        theme = get_theme(self.settings.get("theme_id", DEFAULT_THEME_ID))
        font_size = int(self.settings.get("font_size", 28))
        lh = int(data.get("line_height_percent") or self.settings.get("line_height_percent", 100))
        song_data_to_document(
            data,
            self.editor.document(),
            theme.fg,
            theme.chord,
            self.editor.font_family(),
            font_size,
            line_height_percent=lh,
        )
        self.editor.set_editor_font(self.editor.font_family(), font_size)
        self.editor.set_line_height_percent(lh)
        self._set_line_height_controls(lh)
        self.current_path = path
        self.title_edit.setText(data.get("title") or "Untitled")
        if "scroll_speed_percent" in data:
            self._set_scroll_speed(float(data["scroll_speed_percent"]))
        if "scroll_minutes" in data:
            self.minutes_spin.setValue(int(data["scroll_minutes"]))
        if "scroll_seconds" in data:
            self.seconds_spin.setValue(int(data["scroll_seconds"]))
        self.editor.verticalScrollBar().setValue(0)
        self.editor.invalidate_logical()
        self._suppress_toast = False
        self._schedule_reflow()

    def save_song(self) -> None:
        if self.current_path is None:
            self.save_song_as()
            return
        self._write_to(self.current_path)

    def save_song_as(self) -> None:
        suggested = SONGS_DIR / f"{self._safe_filename(self.song_title)}.song.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Song",
            str(suggested),
            "Songs (*.song.json);;JSON (*.json)",
        )
        if not path:
            return
        if not path.endswith(".json"):
            path += ".song.json"
        self._write_to(Path(path))

    def _write_to(self, path: Path) -> None:
        # Persist unwrapped logical lines so window-width wraps don't bake into the file.
        self.editor.reflow_for_save()
        data = document_to_song_data(
            self.editor.document(),
            self.song_title,
            self.editor.font_size(),
            scroll_speed_percent=float(self.speed_spin.value()),
            scroll_minutes=int(self.minutes_spin.value()),
            scroll_seconds=int(self.seconds_spin.value()),
            line_height_percent=int(self.line_height_spin.value()),
        )
        self._schedule_reflow()
        try:
            save_song(path, data)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return
        self.current_path = path
        add_recent(self.settings, str(path))
        self._rebuild_recent_menu()
        self._persist()
        self._on_title_changed(self.song_title)
        self._set_status(f"Saved: {path.name}")

    def open_library(self) -> None:
        dlg = LibraryDialog(self)
        dlg.song_chosen.connect(self.open_path)
        dlg.song_deleted.connect(self._on_song_deleted)
        dlg.exec()

    def _on_song_deleted(self, path: str) -> None:
        recent = list(self.settings.get("recent") or [])
        path_norm = str(Path(path).resolve())
        self.settings["recent"] = [
            p for p in recent if str(Path(p).resolve()) != path_norm
        ]
        self._rebuild_recent_menu()
        self._persist()
        if self.current_path and str(self.current_path.resolve()) == path_norm:
            self.current_path = None
            self._on_title_changed(self.song_title)
        self._set_status(f"Deleted: {Path(path).name}")

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = list(self.settings.get("recent") or [])
        if not recent:
            act = QAction("(empty)", self)
            act.setEnabled(False)
            self.recent_menu.addAction(act)
            return
        for path in recent:
            p = Path(path)
            label = p.stem.replace(".song", "")
            act = QAction(f"{label}  —  {p.name}", self)
            act.triggered.connect(lambda checked=False, pp=path: self.open_path(pp))
            if not p.exists():
                act.setEnabled(False)
                act.setText(f"{label} (missing)")
            self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clear = QAction("Clear List", self)
        clear.triggered.connect(self._clear_recent)
        self.recent_menu.addAction(clear)

    def _clear_recent(self) -> None:
        self.settings["recent"] = []
        self._rebuild_recent_menu()
        self._persist()

    @staticmethod
    def _safe_filename(name: str) -> str:
        bad = '<>:"/\\|?*'
        cleaned = "".join("_" if c in bad else c for c in name).strip() or "song"
        return cleaned[:80]

    def _set_status(self, text: str) -> None:
        self.statusBar().showMessage(text, 8000)

    def _persist(self) -> None:
        self.settings["font_size"] = self.editor.font_size()
        self.settings["font_family"] = self.editor.font_family()
        self.settings["line_height_percent"] = int(self.line_height_spin.value())
        self.settings["scroll_speed_percent"] = float(self.speed_spin.value())
        self.settings["scroll_minutes"] = int(self.minutes_spin.value())
        self.settings["scroll_seconds"] = int(self.seconds_spin.value())
        self.settings["panel_visible"] = not self.side_panel.isHidden()
        self.settings["hotkeys"] = dict(self.hotkeys)
        self.settings["window_geometry"] = bytes(self.saveGeometry()).hex()
        save_settings(self.settings)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_scroll()
        self._persist()
        super().closeEvent(event)
