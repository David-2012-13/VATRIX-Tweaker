from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from optimizer import (
    apply_profile,
    get_hardware_info,
    get_system_specs,
    clean_browser_cache,
    cleanup_update_residue,
    detect_optimization_drift,
    flush_ram,
    get_battery_status,
    get_available_profiles,
    get_memory_status,
    get_optimization_state,
    get_startup_entries,
    revert_optimizations,
    run_periodic_maintenance,
    set_autostart,
    set_startup_entry_enabled,
    set_windows_service_state,
    set_windows_update_paused,
)


ROOT = Path(__file__).resolve().parent
BLUE = "#2864e8"
BLUE_HOVER = "#1e50c9"
BG = "#f4f7fb"
SURFACE = "#ffffff"
SURFACE_2 = "#f8fafc"
TEXT = "#182338"
MUTED = "#728199"
LINE = "#dbe4ee"

ACTION_LABELS_EN = {
    "power_plan": "Set power plan to Ultimate Performance",
    "hibernate": "Disable hibernation",
    "transparency": "Disable transparency",
    "shadows": "Disable shadows",
    "animations": "Disable animations and visual effects",
    "game_mode": "Enable Windows Game Mode",
    "gamebar": "Disable background video capture",
    "background": "Close unnecessary background processes",
    "background_apps": "Limit apps running in the background",
    "startup_delay": "Remove application startup delay",
    "temp_cleanup": "Clean temporary files",
    "restore_point": "Create a system restore point",
    "search_indexing": "Disable search indexing",
    "search_indexing_on": "Enable Windows Search indexing",
    "sysmain": "Disable SysMain for a faster boot",
    "menu_delay": "Remove menu display delay",
    "visual_effects": "Set Windows visual effects for performance",
    "taskbar_animations": "Disable taskbar animations",
    "window_animations": "Disable window animations",
    "updates": "Check updates and system tasks",
    "widgets": "Disable Windows Widgets",
    "notifications": "Disable notifications",
    "web_search": "Disable web results in Start search",
    "remove_bloatware": "Remove optional Windows apps (bloatware)",
    "remove_edge": "Uninstall Microsoft Edge",
    "hags": "Enable hardware-accelerated GPU scheduling",
    "telemetry": "Disable Windows telemetry",
    "prefetch": "Clean the Prefetch cache",
    "nagle": "Optimize network latency (Nagle)",
}


class OptimizerWorker(QObject):
    progress = Signal(int, int, str, str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, profile: str, selected: list[str]) -> None:
        super().__init__()
        self.profile = profile
        self.selected = selected

    def run(self) -> None:
        try:
            results = apply_profile(self.profile, self.selected, self.progress.emit)
            self.finished.emit(results)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))


class MaintenanceWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.finished.emit(run_periodic_maintenance())
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.failed.emit(str(exc))


class BackgroundTaskWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self.task = task

    def run(self) -> None:
        try:
            self.finished.emit(self.task())
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.failed.emit(str(exc))


class AnimatedPageHost(QFrame):
    """Hosts pages and performs a smooth slide/fade transition between them."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current: QWidget | None = None
        self.animation: QParallelAnimationGroup | None = None
        self.setStyleSheet("background: transparent;")

    def show_page(self, page: QWidget) -> None:
        # A second click can arrive while the previous slide/fade is running.
        # Stop that animation and remove every stale page before creating the
        # next one, otherwise the old pages remain stacked underneath it.
        if self.animation is not None:
            self.animation.stop()
            self.animation.deleteLater()
            self.animation = None
        if self.current is not None:
            self.current.setGraphicsEffect(None)
            self.current.setGeometry(self.rect())
        for child in self.findChildren(QWidget, "", Qt.FindChildOption.FindDirectChildrenOnly):
            if child is not self.current:
                child.hide()
                child.setParent(None)
                child.deleteLater()

        old = self.current
        page.setParent(self)
        page.setGeometry(self.rect().translated(self.width(), 0))
        page.show()
        self.current = page

        new_effect = QGraphicsOpacityEffect(page)
        new_effect.setOpacity(0.0)
        page.setGraphicsEffect(new_effect)
        new_pos = QPropertyAnimation(page, b"pos", self)
        new_pos.setStartValue(QPoint(self.width(), 0))
        new_pos.setEndValue(QPoint(0, 0))
        new_pos.setDuration(280)
        new_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade = QPropertyAnimation(new_effect, b"opacity", self)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setDuration(240)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(new_pos)
        group.addAnimation(fade)
        if old is not None:
            old_pos = QPropertyAnimation(old, b"pos", self)
            old_pos.setStartValue(QPoint(0, 0))
            old_pos.setEndValue(QPoint(-self.width() // 5, 0))
            old_pos.setDuration(280)
            old_pos.setEasingCurve(QEasingCurve.Type.InCubic)
            old_effect = old.graphicsEffect()
            if old_effect is None:
                old_effect = QGraphicsOpacityEffect(old)
                old.setGraphicsEffect(old_effect)
            old_fade = QPropertyAnimation(old_effect, b"opacity", self)
            old_fade.setStartValue(1.0)
            old_fade.setEndValue(0.0)
            old_fade.setDuration(220)
            group.addAnimation(old_pos)
            group.addAnimation(old_fade)

        def finish() -> None:
            if old is not None:
                old.hide()
                old.deleteLater()
            page.setGraphicsEffect(None)
            if self.animation is group:
                self.animation = None

        group.finished.connect(finish)
        self.animation = group
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if self.current is not None and (self.animation is None or self.animation.state() != QPropertyAnimation.State.Running):
            self.current.setGeometry(self.rect())


class StartupDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Startup Programs")
        self.resize(720, 500)
        self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        title = QLabel("Startup Programs")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QLabel("Aplicațiile care pornesc împreună cu Windows")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        listing = QVBoxLayout(content)
        for entry in get_startup_entries():
            row = QFrame()
            row.setObjectName("card")
            row_layout = QHBoxLayout(row)
            text = QVBoxLayout()
            name = QLabel(entry["name"])
            name.setObjectName("cardTitle")
            location = QLabel(entry["location"])
            location.setObjectName("muted")
            text.addWidget(name)
            text.addWidget(location)
            switch = QCheckBox()
            switch.setChecked(bool(entry["enabled"]))
            switch.stateChanged.connect(lambda state, item=entry, control=switch: self.on_startup_toggled(state, item, control))
            row_layout.addLayout(text, 1)
            row_layout.addWidget(switch)
            listing.addWidget(row)
        listing.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.status_label = QLabel()
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

    def on_startup_toggled(self, state: int, entry: dict, control: QCheckBox) -> None:
        requested = bool(state)
        previous = bool(entry.get("enabled"))
        result = set_startup_entry_enabled(entry, requested)
        failed = "failed" in result.lower() or "eșuat" in result.lower() or "doar pe" in result.lower()
        if failed:
            control.blockSignals(True)
            control.setChecked(previous)
            control.blockSignals(False)
        else:
            entry["enabled"] = requested
        self.status_label.setText(result)


class WinTweaker(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Win Tweaker")
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.settings = QSettings("WinTweaker", "WinTweaker")
        self.profile_data = get_available_profiles()
        saved_profile = str(self.settings.value("profile", "custom"))
        self.profile = saved_profile if saved_profile in self.profile_data else "custom"
        self.lang = str(self.settings.value("language", "RO"))
        if self.lang not in {"RO", "EN"}:
            self.lang = "RO"
        self.dark_mode = str(self.settings.value("dark_mode", "false")).lower() == "true"
        self.current_page = "Home"
        self.running = False
        self._maintenance_running = False
        self._background_task_running = False
        self._pending_update_state: bool | None = None
        self._pending_service: tuple[QCheckBox, bool] | None = None
        self._home_specs_cache: tuple[dict, dict] | None = None
        self._home_detailed_cache: tuple[dict, dict] | None = None
        self._home_specs_pending = False
        self._stylesheet_cache: str | None = None
        self.background_mode = str(self.settings.value("background_mode", "true")).lower() == "true"
        self.tray_available = False
        self._loading_settings = True
        self.worker_thread: QThread | None = None
        self.worker: OptimizerWorker | None = None
        self.action_checks: dict[str, QCheckBox] = {}
        self.action_handlers: dict[str, str] = {}
        self.validation_states: dict[str, str] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        self.nav_data = {
            "Home": ("⌂", "Acasă", "Home"),
            "Optimization": ("⚡", "Optimizare", "Optimization"),
            "Apps": ("▣", "Aplicații", "Apps"),
            "Services": ("◉", "Servicii", "Services"),
        }
        self.setStyleSheet(self.stylesheet())
        self.show_welcome()
        self._allow_close = False
        self.setup_tray()
        self.setup_maintenance()
        self.setup_monitoring()
        # Preload detailed system specs and battery wear in the background so
        # pressing "Deschide aplicația" shows them instantly, without blocking.
        self.run_background_task(
            get_hardware_info,
            self._home_specs_loaded,
        )

    def stylesheet(self) -> str:
        style = f"""
        QWidget {{ font-family: 'Segoe UI'; color: {TEXT}; font-size: 10pt; }}
        QMainWindow {{ background: {BG}; }}
        QFrame#sidebar, QFrame#card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px; }}
        QFrame#sidebar {{ border: none; border-radius: 16px; }}
        QLabel#brand {{ font-size: 13pt; font-weight: 700; }}
        QLabel#eyebrow {{ color: {BLUE}; font-size: 9pt; font-weight: 700; }}
        QLabel#pageTitle {{ font-size: 20pt; font-weight: 700; }}
        QLabel#cardTitle {{ font-weight: 700; }}
        QLabel#muted {{ color: {MUTED}; }}
        QPushButton {{ border: none; border-radius: 8px; padding: 9px 12px; background: transparent; text-align: left; }}
        QPushButton:hover {{ background: #eaf2ff; color: {BLUE}; }}
        QPushButton#navButton {{ color: #52647c; font-size: 10pt; padding: 11px 12px; }}
        QPushButton#navButton[selected="true"] {{ background: #eaf2ff; color: {BLUE}; font-weight: 700; }}
        QPushButton#primary {{ background: {BLUE}; color: #000000; font-weight: 700; }}
        QPushButton#primary:hover {{ background: {BLUE_HOVER}; color: #000000; }}
        QPushButton#soft {{ background: {BLUE}; color: #000000; font-weight: 700; border: none; }}
        QPushButton#soft:hover {{ background: {BLUE_HOVER}; color: #000000; }}
        QPushButton#welcomePill, QPushButton#welcomePillSelected {{ border-radius: 18px; padding: 8px 18px; font-weight: 700; color: #000000; background: #dce8fd; }}
        QPushButton#welcomePillSelected {{ background: {BLUE}; color: #000000; }}
        QPushButton#welcomePill:hover {{ background: #c3d8fb; color: #000000; }}
        QPushButton#welcomeProfile {{ border-radius: 8px; padding: 8px 13px; font-size: 8pt; font-weight: 700; color: #000000; background: {BLUE}; }}
        QPushButton#welcomeStart {{ border-radius: 14px; background: {BLUE}; color: #000000; font-weight: 700; padding: 12px; }}
        QPushButton#welcomeStart:hover {{ background: {BLUE_HOVER}; color: #000000; }}
        QCheckBox {{ spacing: 10px; padding: 8px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid #b7c5d7; border-radius: 5px; background: white; }}
        QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE}; }}
        QProgressBar {{ border: none; border-radius: 5px; background: #e7edf4; height: 10px; text-align: center; }}
        QProgressBar::chunk {{ border-radius: 5px; background: {BLUE}; }}
        QLabel {{ background: transparent; }}
        QCheckBox {{ background: transparent; color: {TEXT}; }}
        QScrollArea, QScrollArea > QWidget > QWidget {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: #b7c5d7; border-radius: 5px; min-height: 24px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QListWidget {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {LINE}; border-radius: 8px; padding: 4px; }}
        QListWidget::item {{ padding: 8px; border-radius: 5px; }}
        QListWidget::item:selected {{ background: #dce9ff; color: {TEXT}; }}
        QToolButton {{ border: none; color: {MUTED}; font-size: 18pt; }}
        """
        if self.dark_mode:
            style += """
            QMainWindow, QWidget { background: #111827; color: #edf4ff; }
            QFrame#sidebar, QFrame#card { background: #182331; border-color: #304159; }
            QLabel, QLabel#muted, QLabel#eyebrow, QLabel#pageTitle, QLabel#cardTitle { color: #ffffff; }
            QPushButton#navButton { color: #bfcee0; }
            QPushButton:hover { background: #243a5e; color: #ffffff; }
            QPushButton#navButton[selected="true"] { background: #243a5e; color: #8fb5ff; }
            QPushButton#soft { background: #2864e8; color: #ffffff; }
            QPushButton#soft:hover { background: #1e50c9; color: #ffffff; }
            QScrollArea, QScrollArea > QWidget > QWidget { background: #111827; }
            QListWidget { background: #111827; color: #ffffff; border-color: #304159; }
            QListWidget::item:selected { background: #243a5e; color: #ffffff; }
            QLabel, QCheckBox { background: transparent; color: #ffffff; }
            QCheckBox::indicator { background: #182331; border-color: #60708a; }
            QScrollBar::handle:vertical { background: #60708a; }
            QProgressBar { background: #26354a; }
            """
        return style

    def build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)
        self.sidebar = QFrame(objectName="sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 14)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(2)
        logo = QLabel()
        logo.setFixedSize(38, 38)
        pixmap = QPixmap(str(ROOT / "WinTweaker-logo.png"))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_row.addWidget(logo)
        self.sidebar_logo = logo
        self.brand_label = QLabel("WIN\nTWEAKER", objectName="brand")
        brand_row.addWidget(self.brand_label)
        sidebar_layout.addLayout(brand_row)
        self.sidebar_caption = QLabel("WORKSPACE", objectName="muted")
        self.sidebar_caption.setStyleSheet("font-size: 8pt; font-weight: 700; margin-top: 20px;")
        sidebar_layout.addWidget(self.sidebar_caption)
        for page, (icon, ro, en) in self.nav_data.items():
            button = QPushButton(self.tr(ro, en), objectName="navButton")
            button.setIcon(self.nav_icon(page))
            button.setIconSize(QSize(20, 20))
            button.setProperty("page", page)
            button.clicked.connect(lambda _checked=False, name=page: self.show_page(name))
            self.nav_buttons[page] = button
            sidebar_layout.addWidget(button)
        sidebar_layout.addStretch()
        self.sidebar_footer = QLabel("WinTweaker 1.2\nrizeadavid90@gmail.com", objectName="muted")
        sidebar_layout.addWidget(self.sidebar_footer)
        root.addWidget(self.sidebar)

        content = QVBoxLayout()
        content.setSpacing(10)
        content.setContentsMargins(16, 12, 16, 4)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb = QLabel("Home", objectName="pageTitle")
        self.breadcrumb.setStyleSheet("font-size: 15pt;")
        top_layout.addWidget(self.breadcrumb)
        top_layout.addWidget(QLabel("Rizea David  •  Windows 11", objectName="muted"))
        top_layout.addStretch()
        language = QPushButton("RO / EN", objectName="soft")
        language.clicked.connect(self.toggle_language)
        top_layout.addWidget(language)
        self.apply_button = QPushButton(self.tr("Aplică optimizările", "Apply optimizations"), objectName="primary")
        self.style_primary(self.apply_button)
        self.apply_button.clicked.connect(self.run_selected)
        self.apply_button.setVisible(False)
        top_layout.addWidget(self.apply_button)
        self.drift_label = QLabel(objectName="muted")
        self.drift_label.setVisible(False)
        top_layout.addWidget(self.drift_label)
        content.addLayout(top_layout)
        self.page_host = AnimatedPageHost()
        content.addWidget(self.page_host, 1)
        root.addLayout(content, 1)

    def show_welcome(self) -> None:
        """Render the V2-style welcome screen before opening the workspace."""
        central = QWidget()
        central.setStyleSheet("background: #111827;" if self.dark_mode else "background: #e5efff;")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedSize(700, 470)
        card.setStyleSheet(
            "background: #182331; border: none; border-radius: 0px;"
            if self.dark_mode
            else "background: #ffffff; border: none; border-radius: 0px;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(46, 28, 46, 42)
        card_layout.setSpacing(0)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addStretch()
        dark = QPushButton("Light" if self.dark_mode else "Dark")
        self.theme_button = dark
        dark.setObjectName("welcomePill")
        self.style_welcome_pill(dark, selected=False)
        dark.clicked.connect(self.toggle_welcome_theme)
        ro = QPushButton("RO")
        ro.setObjectName("welcomePillSelected" if self.lang == "RO" else "welcomePill")
        self.style_welcome_pill(ro, selected=self.lang == "RO")
        ro.clicked.connect(lambda: self.set_language("RO"))
        uk = QPushButton("UK")
        uk.setObjectName("welcomePillSelected" if self.lang == "EN" else "welcomePill")
        self.style_welcome_pill(uk, selected=self.lang == "EN")
        uk.clicked.connect(lambda: self.set_language("EN"))
        controls.addWidget(dark); controls.addWidget(ro); controls.addWidget(uk)
        card_layout.addLayout(controls)

        eyebrow = QLabel("OPTIMIZARE WINDOWS")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eyebrow.setStyleSheet(
            f"color: {'#ffffff' if self.dark_mode else BLUE}; font-size: 9pt; font-weight: 700; background: transparent;"
        )
        card_layout.addWidget(eyebrow)
        title = QLabel("Win Tweaker")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {'#ffffff' if self.dark_mode else '#071c42'}; font-size: 38pt; font-weight: 700; background: transparent;"
        )
        card_layout.addWidget(title)
        author = QLabel("Rizea David")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author.setStyleSheet(
            f"color: {'#ffffff' if self.dark_mode else '#6480ad'}; font-size: 10pt; background: transparent;"
        )
        card_layout.addWidget(author)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background: {BLUE}; border: none;")
        card_layout.addSpacing(25); card_layout.addWidget(line); card_layout.addSpacing(20)

        description = QLabel(self.tr("Alege profilul potrivit și adaptează Windows pentru calculatorul tău.", "Choose the right profile and adapt Windows for your computer."))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet(
            f"color: {'#ffffff' if self.dark_mode else '#1e579f'}; font-size: 12pt; "
            f"background: {'#223044' if self.dark_mode else '#f2f6fd'}; padding: 6px;"
        )
        card_layout.addWidget(description)
        card_layout.addSpacing(18)

        profiles = QHBoxLayout(); profiles.setSpacing(4); profiles.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile_names = (("low_end", "PC MODEST"), ("gaming", "JOCURI"), ("office", "BIROU"), ("custom", "PERSONALIZAT"))
        for key, label in profile_names:
            button = QPushButton(label)
            button.setObjectName("welcomeProfile")
            self.style_welcome_profile(button)
            button.clicked.connect(lambda _checked=False, value=key: self.choose_welcome_profile(value))
            profiles.addWidget(button)
        card_layout.addLayout(profiles)
        card_layout.addSpacing(24)

        start = QPushButton(self.tr("Deschide aplicația", "Open application"))
        start.setObjectName("welcomeStart")
        start.setFixedHeight(54)
        start.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.style_primary(start, radius=14, font_size="11pt")
        start.clicked.connect(self.show_app)
        card_layout.addWidget(start)
        outer.addWidget(card)
        self.setCentralWidget(central)

    def show_app(self) -> None:
        if self._stylesheet_cache is None:
            self._stylesheet_cache = self.stylesheet()
        self.setStyleSheet(self._stylesheet_cache)
        self.build_ui()
        self.show_page("Home", animate=False)
        self.showNormal()

    def set_language(self, language: str) -> None:
        self.lang = language
        self.settings.setValue("language", self.lang)
        self.show_welcome()

    def choose_welcome_profile(self, profile: str) -> None:
        self.profile = profile
        self.settings.setValue("profile", self.profile)

    def toggle_welcome_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.settings.setValue("dark_mode", self.dark_mode)
        self.setStyleSheet(self.stylesheet())
        self.show_welcome()

    def save_preferences(self) -> None:
        """Persist the current profile and selected optimization actions."""
        self.settings.setValue("profile", self.profile)
        selected = [name for name, check in self.action_checks.items() if check.isChecked()]
        self.settings.setValue(f"selected/{self.profile}", ",".join(selected))
        self.settings.sync()

    def nav_icon(self, page: str) -> QIcon:
        if page == "Settings":
            settings_icon = QIcon.fromTheme("preferences-system")
            if not settings_icon.isNull():
                return settings_icon
        icons = {
            "Home": QStyle.StandardPixmap.SP_DirHomeIcon,
            "Optimization": QStyle.StandardPixmap.SP_MediaPlay,
            "Apps": QStyle.StandardPixmap.SP_ComputerIcon,
            "Services": QStyle.StandardPixmap.SP_BrowserReload,
            "Settings": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        }
        return QApplication.style().standardIcon(icons[page])

    def tr(self, ro: str, en: str) -> str:
        return en if self.lang == "EN" else ro

    @staticmethod
    def style_primary(button: QPushButton, radius: int = 8, font_size: str = "10pt") -> None:
        button.setStyleSheet(
            f"QPushButton {{ background-color: {BLUE}; color: #000000; "
            f"border: 1px solid {BLUE_HOVER}; border-radius: {radius}px; "
            f"font-size: {font_size}; font-weight: 700; padding: 9px 12px; text-align: center; }} "
            f"QPushButton:hover {{ background-color: {BLUE_HOVER}; color: #000000; }} "
            f"QPushButton:pressed {{ background-color: #17409f; color: #000000; }}"
        )

    def style_welcome_pill(self, button: QPushButton, selected: bool) -> None:
        background = BLUE if selected else ("#223044" if self.dark_mode else "#dce8fd")
        foreground = "#ffffff" if selected or self.dark_mode else "#000000"
        border = BLUE_HOVER if selected else ("#3b4d68" if self.dark_mode else "#8fb0e8")
        hover_background = BLUE_HOVER if selected else ("#30486b" if self.dark_mode else "#c3d8fb")
        hover_foreground = "#ffffff" if selected or self.dark_mode else "#000000"
        button.setStyleSheet(
            f"QPushButton {{ background-color: {background}; color: {foreground}; "
            f"border: 1px solid {border}; border-radius: 18px; padding: 8px 18px; font-weight: 700; }} "
            f"QPushButton:hover {{ background-color: {hover_background}; color: {hover_foreground}; }}"
        )

    def style_welcome_profile(self, button: QPushButton) -> None:
        button.setStyleSheet(
            f"QPushButton {{ background-color: {BLUE}; color: #000000; "
            f"border: 1px solid {BLUE_HOVER}; border-radius: 8px; padding: 8px 13px; "
            "font-size: 8pt; font-weight: 700; } "
            f"QPushButton:hover {{ background-color: {BLUE_HOVER}; border-color: {BLUE_HOVER}; color: #000000; }}"
        )

    def toggle_language(self) -> None:
        self.lang = "EN" if self.lang == "RO" else "RO"
        self.settings.setValue("language", self.lang)
        for page, button in self.nav_buttons.items():
            _icon, ro, en = self.nav_data[page]
            button.setText("" if self.sidebar.width() < 120 else self.tr(ro, en))
        if hasattr(self, "apply_button"):
            self.apply_button.setText(self.tr("Aplică optimizările", "Apply optimizations"))
        self.show_page(self.current_page, animate=False)

    def toggle_background_mode(self, enabled: bool) -> None:
        self.background_mode = bool(enabled)
        self.settings.setValue("background_mode", self.background_mode)
        self.settings.sync()
        if hasattr(self, "background_switch") and self.background_switch.isChecked() != self.background_mode:
            self.background_switch.blockSignals(True)
            self.background_switch.setChecked(self.background_mode)
            self.background_switch.blockSignals(False)
        if enabled and not self.tray_available:
            self.settings.setValue("background_mode", False)
            self.settings.sync()
            self.background_mode = False
            self.statusBar().showMessage(
                self.tr(
                    "Zona de notificări nu este disponibilă. Rularea în fundal nu poate fi activată.",
                    "The system tray is unavailable. Background mode cannot be enabled.",
                ),
                6000,
            )
            if hasattr(self, "background_switch"):
                self.background_switch.blockSignals(True)
                self.background_switch.setChecked(False)
                self.background_switch.blockSignals(False)
            return
        self.statusBar().showMessage(
            self.tr(
                "Rularea în fundal este activată." if enabled else "Rularea în fundal este dezactivată.",
                "Background mode enabled." if enabled else "Background mode disabled.",
            ),
            4000,
        )

    def show_page(self, page: str, animate: bool = True) -> None:
        self.current_page = page
        for name, button in self.nav_buttons.items():
            button.setProperty("selected", name == page)
            button.style().unpolish(button)
            button.style().polish(button)
        titles = {name: self.tr(ro, en) for name, (_icon, ro, en) in self.nav_data.items()}
        self.breadcrumb.setText(titles[page])
        builders = {
            "Home": self.page_home,
            "Optimization": self.page_optimization,
            "Apps": self.page_apps,
            "Services": self.page_services,
        }
        self._building_page = True
        new_page = builders[page]()
        self._building_page = False
        if animate:
            self.page_host.show_page(new_page)
        else:
            if self.page_host.current is not None:
                self.page_host.current.deleteLater()
            self.page_host.current = new_page
            new_page.setParent(self.page_host)
            new_page.setGeometry(self.page_host.rect())
            new_page.show()

    def card(self) -> QFrame:
        return QFrame(objectName="card")

    def page_shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(QLabel(title, objectName="pageTitle"))
        description = QLabel(subtitle, objectName="muted")
        description.setWordWrap(True)
        layout.addWidget(description)
        return page, layout

    def page_home(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Bun venit înapoi", "Welcome back"), self.tr("Monitorizează și îmbunătățește performanța PC-ului tău.", "Monitor and improve your PC performance."))
        hero = self.card(); hero_layout = QVBoxLayout(hero)
        hero_layout.addWidget(QLabel("OPTIMIZATION LAB", objectName="eyebrow"))
        hero_layout.addWidget(QLabel(self.tr("Sistemul tău este pregătit pentru optimizare.", "Your system is ready for optimization."), objectName="cardTitle"))
        hero_layout.addWidget(QLabel(self.tr("Profil recomandat: PC cu resurse reduse • Windows 11", "Recommended profile: Low-end PC • Windows 11"), objectName="muted"))
        open_button = QPushButton(self.tr("Deschide optimizarea", "Open optimization"), objectName="primary")
        open_button.setIcon(self.nav_icon("Optimization"))
        self.style_primary(open_button)
        open_button.setFixedWidth(190)
        open_button.clicked.connect(lambda: self.show_page("Optimization"))
        hero_layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hero)

        specs = self.card(); specs_layout = QVBoxLayout(specs)
        specs_layout.addWidget(QLabel(self.tr("SPECIFICAȚII SISTEM", "SYSTEM SPECIFICATIONS"), objectName="cardTitle"))
        if self._home_detailed_cache is None and not self._home_specs_pending:
            self._home_specs_pending = True
            self.run_background_task(
                get_hardware_info,
                self._home_specs_loaded,
            )
            self._home_detailed_cache = ({}, {"available": False, "message": self.tr("Se colectează informațiile de sistem...", "Collecting system information...")})
        detailed, battery = self._home_detailed_cache
        memory_status = get_memory_status()
        total_ram = memory_status.get("total", 0) / 1024 ** 3
        cpu = detailed.get("cpu") or {}
        os_info = detailed.get("os") or {}
        board = detailed.get("board") or {}
        bios_info = detailed.get("bios") or {}
        system_info = detailed.get("system") or {}
        cpu_name = cpu.get("Name") or platform.processor() or platform.machine()
        windows_caption = os_info.get("Caption") or f"Windows {platform.win32_ver()[0] or platform.release()}"
        build_number = os_info.get("BuildNumber") or platform.version()
        specs_data = (
            (self.tr("Procesor", "Processor"), f"{cpu_name} — {cpu.get('NumberOfCores', '?')} nuclee / {cpu.get('NumberOfLogicalProcessors', os.cpu_count() or '?')} fire"),
            (self.tr("Frecvență", "Clock"), f"{(cpu.get('CurrentClockSpeed') or 0) / 1000:.2f} GHz (max {(cpu.get('MaxClockSpeed') or 0) / 1000:.2f} GHz)"),
            (self.tr("RAM", "RAM"), f"{total_ram:.1f} GB — {len(detailed.get('memory') or [])} module"),
            (self.tr("Windows", "Windows"), f"{windows_caption} (build {build_number})"),
            (self.tr("Arhitectură", "Architecture"), os_info.get("OSArchitecture") or platform.machine()),
            (self.tr("Placă de bază", "Motherboard"), f"{board.get('Manufacturer', '?')} {board.get('Product', '')}".strip()),
            (self.tr("BIOS", "BIOS"), f"{bios_info.get('Manufacturer', '?')} {bios_info.get('SMBIOSBIOSVersion', '')}".strip()),
            (self.tr("Sistem", "System"), f"{system_info.get('Manufacturer', '?')} {system_info.get('Model', '')}".strip()),
            (self.tr("Ultimul boot", "Last boot"), str(os_info.get("LastBootUpTime") or "n/a")),
            (self.tr("Instalat la", "Installed on"), str(os_info.get("InstallDate") or "n/a")),
        )
        grid = QGridLayout(); grid.setHorizontalSpacing(24); grid.setVerticalSpacing(10)
        for index, (label, value) in enumerate(specs_data):
            row = index // 2; column = (index % 2) * 2
            grid.addWidget(QLabel(label, objectName="muted"), row, column)
            value_label = QLabel(value, objectName="cardTitle"); value_label.setWordWrap(True)
            grid.addWidget(value_label, row, column + 1)
        specs_layout.addLayout(grid)

        gpu_list = detailed.get("gpu") or []
        if gpu_list:
            specs_layout.addSpacing(14)
            specs_layout.addWidget(QLabel(self.tr("PLACĂ GRAFICĂ", "GRAPHICS"), objectName="cardTitle"))
            gpu_grid = QGridLayout(); gpu_grid.setHorizontalSpacing(24); gpu_grid.setVerticalSpacing(6)
            for index, gpu in enumerate(gpu_list):
                width = gpu.get("CurrentHorizontalResolution"); height = gpu.get("CurrentVerticalResolution")
                res_text = f"{width}x{height}" if width and height else "n/a"
                gpu_grid.addWidget(QLabel(str(gpu.get("Name") or "n/a"), objectName="cardTitle"), index, 0)
                gpu_grid.addWidget(QLabel(self.tr("Driver", "Driver"), objectName="muted"), index, 1)
                gpu_grid.addWidget(QLabel(str(gpu.get("DriverVersion") or "n/a"), objectName="cardTitle"), index, 2)
                gpu_grid.addWidget(QLabel(self.tr("Rezoluție", "Resolution"), objectName="muted"), index, 3)
                gpu_grid.addWidget(QLabel(res_text, objectName="cardTitle"), index, 4)
            specs_layout.addLayout(gpu_grid)

        memory_modules = detailed.get("memory") or []
        if memory_modules:
            specs_layout.addSpacing(14)
            specs_layout.addWidget(QLabel(self.tr("MEMORIE RAM", "RAM MEMORY"), objectName="cardTitle"))
            ram_grid = QGridLayout(); ram_grid.setHorizontalSpacing(24); ram_grid.setVerticalSpacing(6)
            for index, module in enumerate(memory_modules):
                capacity = (module.get("Capacity") or 0) / 1024 ** 3
                speed = module.get("ConfiguredClockSpeed") or module.get("Speed") or "n/a"
                ram_grid.addWidget(QLabel(f"#{index + 1}", objectName="muted"), index, 0)
                ram_grid.addWidget(QLabel(f"{capacity:.0f} GB @ {speed} MHz — {module.get('Manufacturer') or 'n/a'}", objectName="cardTitle"), index, 1)
            specs_layout.addLayout(ram_grid)

        disks = detailed.get("disks") or []
        if disks:
            specs_layout.addSpacing(14)
            specs_layout.addWidget(QLabel(self.tr("STOCARE", "STORAGE"), objectName="cardTitle"))
            disk_grid = QGridLayout(); disk_grid.setHorizontalSpacing(24); disk_grid.setVerticalSpacing(6)
            for index, disk in enumerate(disks):
                size = (disk.get("Size") or 0) / 1024 ** 3
                disk_grid.addWidget(QLabel(str(disk.get("Model") or "n/a"), objectName="cardTitle"), index, 0)
                disk_grid.addWidget(QLabel(f"{size:.0f} GB ({disk.get('InterfaceType') or 'n/a'})", objectName="muted"), index, 1)
            specs_layout.addLayout(disk_grid)

        network = detailed.get("network") or []
        if network:
            specs_layout.addSpacing(14)
            specs_layout.addWidget(QLabel(self.tr("REȚEA", "NETWORK"), objectName="cardTitle"))
            net_grid = QGridLayout(); net_grid.setHorizontalSpacing(24); net_grid.setVerticalSpacing(6)
            for index, adapter in enumerate(network):
                speed = (adapter.get("Speed") or 0) / 1_000_000_000
                net_grid.addWidget(QLabel(str(adapter.get("Name") or "n/a"), objectName="cardTitle"), index, 0)
                net_grid.addWidget(QLabel(f"{speed:.1f} Gbps" if speed else "n/a", objectName="muted"), index, 1)
            specs_layout.addLayout(net_grid)

        layout.addWidget(specs)
        layout.addWidget(self._build_battery_card(battery))
        layout.addStretch()
        self.refresh_memory()
        return page

    def _home_specs_loaded(self, payload: object) -> None:
        """Receive the detailed specs collected on a background thread."""
        detailed, battery = payload
        self._home_detailed_cache = (detailed or {}, battery or {"available": False})
        self._home_specs_pending = False
        if self.current_page == "Home" and hasattr(self, "page_host"):
            self.show_page("Home", animate=False)

    def _build_battery_card(self, battery: dict) -> QFrame:
        """Build the detailed battery wear card shown on the Home page."""
        card = self.card(); card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel(self.tr("BATERIE — UZURĂ DETALIATĂ", "BATTERY — DETAILED WEAR"), objectName="cardTitle"))
        if not battery.get("available"):
            message = battery.get("message") or self.tr("Nu a fost detectată nicio baterie pe acest sistem.", "No battery was detected on this system.")
            note = QLabel(message, objectName="muted"); note.setWordWrap(True)
            card_layout.addWidget(note)
            return card
        b = battery.get("battery") or {}
        static = battery.get("static") or {}
        full_info = battery.get("full") or {}
        rate = battery.get("rate") or {}
        design = static.get("DesignedCapacity") or b.get("DesignCapacity") or 0
        full = full_info.get("FullChargedCapacity") or 0
        charge_pct = b.get("EstimatedChargeRemaining") or 0
        voltage = (b.get("DesignVoltage") or 0) / 1000.0
        runtime = b.get("EstimatedRunTime") or 0
        runtime_text = self.tr("n/a (conectat la priză)", "n/a (plugged in)") if runtime >= 71582788 else self.tr(f"{runtime} minute", f"{runtime} minutes")
        status_map = {
            1: self.tr("Descărcare", "Discharging"),
            2: self.tr("La priză / încărcare", "On AC / charging"),
            3: self.tr("Rezervă critică", "Critical reserve"),
            4: self.tr("Parțial descărcată", "Partially discharged"),
            5: self.tr("Rezervă", "Reserve"),
            10: self.tr("Ținută în rezervă", "On standby"),
            11: self.tr("Iniciată", "Initialized"),
        }
        status_text = status_map.get(b.get("BatteryStatus"), str(b.get("BatteryStatus") or "n/a"))
        wear_pct = max(0, 100 - (full / design * 100)) if design and full else None
        if wear_pct is None:
            wear_text = "n/a"
        elif wear_pct < 10:
            wear_text = f"{wear_pct:.1f}% — " + self.tr("stare excelentă", "excellent condition")
        elif wear_pct < 25:
            wear_text = f"{wear_pct:.1f}% — " + self.tr("stare bună", "good condition")
        else:
            wear_text = f"{wear_pct:.1f}% — " + self.tr("uzură avansată, capacitatea reală este redusă", "significant wear, real capacity is reduced")
        rows = (
            (self.tr("Model", "Model"), str(b.get("Name") or "n/a")),
            (self.tr("ID dispozitiv", "Device ID"), str(b.get("DeviceID") or "n/a")),
            (self.tr("Capacitate proiectată", "Design capacity"), f"{design} mWh" if design else "n/a"),
            (self.tr("Capacitate la încărcare completă", "Full-charge capacity"), f"{full} mWh" if full else "n/a"),
            (self.tr("Uzură", "Wear"), wear_text),
            (self.tr("Nivel încărcare actual", "Current charge"), f"{charge_pct}%"),
            (self.tr("Tensiune proiectată", "Design voltage"), f"{voltage:.2f} V" if voltage else "n/a"),
            (self.tr("Timp estimat rămas", "Estimated runtime"), runtime_text),
            (self.tr("Stare", "Status"), status_text),
            (self.tr("Se încarcă acum", "Charging now"), self.tr("Da", "Yes") if rate.get("Charging") else self.tr("Nu", "No")),
            (self.tr("Se descarcă acum", "Discharging now"), self.tr("Da", "Yes") if rate.get("Discharging") else self.tr("Nu", "No")),
            (self.tr("Conectat la priză", "Plugged in"), self.tr("Da", "Yes") if rate.get("PowerOnline") else self.tr("Nu", "No")),
            (self.tr("Rată de încărcare", "Charge rate"), f"{rate.get('ChargeRate') or 0} mW"),
            (self.tr("Rată de descărcare", "Discharge rate"), f"{rate.get('DischargeRate') or 0} mW"),
        )
        grid = QGridLayout(); grid.setHorizontalSpacing(24); grid.setVerticalSpacing(6)
        for index, (label, value) in enumerate(rows):
            row = index // 2; column = (index % 2) * 2
            grid.addWidget(QLabel(label, objectName="muted"), row, column)
            grid.addWidget(QLabel(value, objectName="cardTitle"), row, column + 1)
        card_layout.addLayout(grid)
        if wear_pct is not None:
            wear_bar = QProgressBar(); wear_bar.setRange(0, 100); wear_bar.setValue(round(wear_pct)); wear_bar.setTextVisible(True)
            wear_bar.setFormat(self.tr("Uzură bateriei: %p%", "Battery wear: %p%"))
            card_layout.addSpacing(12)
            card_layout.addWidget(wear_bar)
            if wear_pct >= 25:
                advice = self.tr(
                    "Recomandare: capacitatea reală a scăzut sub 75%. Ai în vedere înlocuirea bateriei, evită descărcarea completă și nu lăsa laptopul la priză permanent la 100%.",
                    "Recommendation: real capacity dropped below 75%. Consider replacing the battery, avoid full discharges and don't keep the laptop plugged at 100% permanently.",
                )
            elif wear_pct >= 10:
                advice = self.tr(
                    "Recomandare: uzură moderată. Evită temperaturile mari și descărcările profunde pentru a încetini degradarea.",
                    "Recommendation: moderate wear. Avoid high temperatures and deep discharges to slow degradation.",
                )
            else:
                advice = self.tr(
                    "Recomandare: bateria este în stare foarte bună. Menține nivelul de încărcare între 20% și 80% când e posibil.",
                    "Recommendation: battery is in excellent condition. Keep charge between 20% and 80% when possible.",
                )
            advice_label = QLabel(advice, objectName="muted"); advice_label.setWordWrap(True)
            card_layout.addSpacing(8)
            card_layout.addWidget(advice_label)
        return card

    def page_optimization(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Optimizare", "Optimization"), self.tr("Alege un profil și activează doar setările de care ai nevoie.", "Choose a profile and enable only the settings you need."))
        columns = QHBoxLayout()
        profiles = self.card(); profile_layout = QVBoxLayout(profiles)
        profile_layout.addWidget(QLabel(self.tr("PROFIL DE PERFORMANȚĂ", "PERFORMANCE PROFILE"), objectName="cardTitle"))
        names = {"low_end": ("PC cu resurse reduse", "Low-end PC"), "gaming": ("PC pentru jocuri", "Gaming PC"), "office": ("PC de birou", "Office PC"), "custom": ("Personalizat", "Custom")}
        for key in self.profile_data:
            button = QPushButton(self.tr(*names[key]), objectName="soft")
            button.clicked.connect(lambda _checked=False, value=key: self.select_profile(value)); profile_layout.addWidget(button)
        apply_button = QPushButton(self.tr("Aplică selecția", "Apply selection"), objectName="primary")
        apply_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.style_primary(apply_button)
        apply_button.clicked.connect(self.run_selected); profile_layout.addStretch(); profile_layout.addWidget(apply_button)
        revert_button = QPushButton(self.tr("Revert optimizations", "Revert optimizations"), objectName="soft")
        revert_button.clicked.connect(self.confirm_revert)
        profile_layout.addWidget(revert_button)
        columns.addWidget(profiles, 1)

        actions = self.card(); actions_layout = QVBoxLayout(actions)
        actions_layout.addWidget(QLabel(self.tr("SETĂRI DISPONIBILE", "AVAILABLE SETTINGS"), objectName="cardTitle"))
        self.selected_label = QLabel(objectName="muted"); actions_layout.addWidget(self.selected_label)
        self.validation_label = QLabel(objectName="muted")
        self.validation_label.setWordWrap(True)
        actions_layout.addWidget(self.validation_label)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.action_container = QWidget(); self.action_layout = QVBoxLayout(self.action_container); self.action_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.action_container); actions_layout.addWidget(scroll, 1); columns.addWidget(actions, 2)
        layout.addLayout(columns, 1); self.select_profile(self.profile)
        return page

    def select_profile(self, name: str) -> None:
        self.profile = name
        self.settings.setValue("profile", self.profile)
        if not hasattr(self, "action_layout"):
            return
        while self.action_layout.count():
            item = self.action_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.action_checks.clear()
        self.action_handlers.clear()
        self.validation_states.clear()
        actions = self.profile_data[name]["actions"]
        visible = actions[:15] + [action for action in actions if action["id"] in {"telemetry", "prefetch", "nagle"}]
        saved_value = self.settings.value(f"selected/{name}", None)
        saved_ids = {item for item in str(saved_value).split(",") if item}
        has_saved = saved_value is not None and name == "custom"
        self._loading_settings = True
        for index, action in enumerate(visible):
            if self.lang == "EN":
                action = {**action, "label": ACTION_LABELS_EN.get(action["id"], action["label"])}
            check = QCheckBox(action["label"]); check.setChecked(name != "custom"); check.stateChanged.connect(self.update_selected)
            self.action_checks[action["id"]] = check; self.action_layout.addWidget(check)
            self.action_handlers[action["id"]] = action["handler"]
            check.stateChanged.connect(self.mark_settings_changed)
            check.setChecked(
                action["id"] in saved_ids
                if has_saved
                else name != "custom"
            )
        self.action_layout.addStretch(); self.update_selected()
        self._loading_settings = False
        self.validate_selected_actions()
        if not getattr(self, "_building_page", False) and hasattr(self, "apply_button"):
            self.apply_button.setVisible(True)

    def mark_settings_changed(self, _state: int = 0) -> None:
        if not self._loading_settings and hasattr(self, "apply_button"):
            self.apply_button.setVisible(True)
        self.update_selected()
        if not self._loading_settings:
            self.validate_selected_actions()

    def update_selected(self) -> None:
        if hasattr(self, "selected_label"):
            self.save_preferences()
            count = sum(check.isChecked() for check in self.action_checks.values())
            self.selected_label.setText(self.tr(f"{count} setări selectate", f"{count} settings selected"))

    def validate_selected_actions(self) -> None:
        if not hasattr(self, "validation_label"):
            return
        self.validation_states = {
            action_id: get_optimization_state(action_id, self.action_handlers.get(action_id))
            for action_id, check in self.action_checks.items()
            if check.isChecked()
        }
        already = sum(state == "already_applied" for state in self.validation_states.values())
        pending = sum(state == "can_apply" for state in self.validation_states.values())
        unknown = sum(state == "unknown" for state in self.validation_states.values())
        if not self.validation_states:
            self.validation_label.clear()
            return
        self.validation_label.setText(
            self.tr(
                f"Stare verificată: {already} deja active, {pending} pregătite pentru aplicare, {unknown} vor fi verificate la aplicare.",
                f"Checked now: {already} already active, {pending} ready to apply, {unknown} checked when applying.",
            )
        )

    def start_menu_entries(self) -> list[Path]:
        roots = []
        program_data = os.environ.get("PROGRAMDATA")
        app_data = os.environ.get("APPDATA")
        if program_data:
            roots.append(Path(program_data) / r"Microsoft\Windows\Start Menu\Programs")
        if app_data:
            roots.append(Path(app_data) / r"Microsoft\Windows\Start Menu\Programs")
        entries: list[Path] = []
        allowed = {".lnk", ".url", ".exe", ".bat", ".cmd"}
        for root in roots:
            if root.exists():
                entries.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in allowed)
        return sorted(set(entries), key=lambda path: path.stem.lower())

    def page_apps(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Aplicații", "Apps"), self.tr("Aplicații și scurtături din Meniul Start.", "Apps and shortcuts from the Start Menu."))
        card = self.card(); card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel(self.tr("APLICAȚII INSTALATE", "INSTALLED APPS"), objectName="cardTitle"))
        entries = QListWidget(); entries.setAlternatingRowColors(True); entries.setMinimumHeight(360)
        paths = self.start_menu_entries()
        if not paths:
            entries.addItem(self.tr("Nu au fost găsite scurtături în Meniul Start.", "No Start Menu shortcuts were found."))
        for path in paths:
            item = QListWidgetItem(f"{path.stem}  —  {path.parent}")
            item.setToolTip(str(path))
            entries.addItem(item)
        card_layout.addWidget(entries, 1)
        button = QPushButton(self.tr("Programe Startup", "Startup programs"), objectName="primary")
        button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.style_primary(button); button.clicked.connect(self.open_startup)
        cleanup = QPushButton(self.tr("Curăță reziduuri Windows Update", "Clean Windows Update residue"), objectName="soft")
        cleanup.clicked.connect(self.confirm_update_cleanup)
        activation = QPushButton(self.tr("Deschide Activatorul Massgravel", "Open Massgravel Activator"), objectName="soft")
        activation.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://massgrave.dev/")))
        utility_row = QHBoxLayout()
        utility_row.setSpacing(8)
        utility_row.addWidget(button, 1)
        utility_row.addWidget(cleanup, 1)
        utility_row.addWidget(activation, 1)
        card_layout.addLayout(utility_row)
        browser_row = QHBoxLayout()
        for browser, label in (("chrome", "Chrome"), ("edge", "Edge"), ("firefox", "Firefox")):
            cache_button = QPushButton(self.tr(f"Curăță {label}", f"Clean {label}"), objectName="soft")
            cache_button.clicked.connect(lambda _checked=False, name=browser: self.confirm_browser_cleanup(name))
            browser_row.addWidget(cache_button)
        card_layout.addLayout(browser_row)
        card_layout.addSpacing(12)
        startup = QCheckBox(self.tr("Pornește WinTweaker odată cu Windows", "Run WinTweaker at startup"))
        startup.setChecked(str(self.settings.value("autostart", "false")).lower() == "true")
        startup.toggled.connect(self.toggle_autostart)
        card_layout.addWidget(startup, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(card, 1); return page

    def page_services(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Servicii", "Services"), self.tr("Ajustări rapide pentru servicii și funcții Windows.", "Quick controls for Windows services and features."))
        card = self.card(); card_layout = QVBoxLayout(card)
        services = (
            ("Telemetry", "DiagTrack", "Reduce colectarea datelor de diagnostic.", "Reduce diagnostic data collection.", False),
            ("SysMain / Superfetch", "SysMain", "Gestionează preîncărcarea și performanța în fundal.", "Manages preloading and background performance.", True),
            ("Windows Search", "WSearch", "Controlează indexarea pentru căutări rapide.", "Controls indexing for faster file searches.", True),
            ("Fax", "Fax", "Serviciu vechi, de obicei inutil pe PC-urile moderne.", "Legacy fax service, usually unnecessary on modern PCs.", False),
            ("Print Spooler", "Spooler", "Necesar pentru imprimante; dezactivează-l doar dacă nu este folosit.", "Required for printers; disable only if unused.", True),
            ("Connected User Experiences", "CDPUserSvc", "Diagnosticare Windows și experiențe conectate.", "Windows diagnostics and connected experiences.", False),
            ("Delivery Optimization", "DoSvc", "Partajează descărcările de actualizări cu alte dispozitive.", "Shares update downloads with other devices.", True),
            ("Bluetooth Support", "bthserv", "Necesar pentru dispozitive Bluetooth.", "Required for Bluetooth devices.", True),
            ("Remote Registry", "RemoteRegistry", "Serviciu pentru acces la registry de la distanță.", "Remote registry access service.", False),
        )
        for title, service_name, description_ro, description_en, enabled in services:
            row = QHBoxLayout(); text = QVBoxLayout()
            text.addWidget(QLabel(title, objectName="cardTitle"))
            text.addWidget(QLabel(self.tr(description_ro, description_en), objectName="muted"))
            saved = self.settings.value(f"service/{service_name}", None)
            current = str(saved).lower() == "true" if saved is not None else enabled
            switch = QCheckBox(); switch.setChecked(current)
            switch.toggled.connect(lambda checked, name=service_name, control=switch: self.confirm_service_toggle(name, checked, control))
            row.addLayout(text, 1); row.addWidget(switch); card_layout.addLayout(row)
        self.update_switch = QCheckBox(self.tr("Pauzează Windows Update (necesită administrator)", "Pause Windows Update (requires administrator)"))
        self.update_switch.toggled.connect(self.confirm_windows_update_toggle)
        card_layout.addWidget(self.update_switch)
        layout.addWidget(card); layout.addStretch(); return page

    def page_settings(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Setări", "Settings"), self.tr("Personalizează modul în care funcționează Win Tweaker.", "Customize how Win Tweaker works."))
        card = self.card(); card_layout = QHBoxLayout(card); text = QVBoxLayout()
        text.addWidget(QLabel("Light Mode", objectName="cardTitle")); text.addWidget(QLabel("Folosește aspectul luminos Windows 11.", objectName="muted"))
        card_layout.addLayout(text, 1); card_layout.addWidget(QCheckBox()); layout.addWidget(card)
        background_card = self.card(); background_layout = QHBoxLayout(background_card); background_text = QVBoxLayout()
        background_text.addWidget(QLabel(self.tr("Rulare în fundal", "Background mode"), objectName="cardTitle"))
        background_text.addWidget(QLabel(self.tr("Păstrează WinTweaker activ în zona de notificări când închizi fereastra.", "Keep WinTweaker running in the tray when you close the window."), objectName="muted"))
        self.background_switch = QCheckBox()
        self.background_switch.setChecked(self.background_mode)
        self.background_switch.toggled.connect(self.toggle_background_mode)
        background_layout.addLayout(background_text, 1); background_layout.addWidget(self.background_switch)
        layout.addWidget(background_card); layout.addStretch(); return page

    def refresh_memory(self) -> None:
        if not hasattr(self, "memory_progress"):
            return
        status = get_memory_status(); total = status.get("total", 0); used = status.get("used", 0)
        ratio = used / total if total else 0
        self.memory_progress.setValue(round(max(0, min(1, ratio)) * 100))
        self.memory_label.setText(self.tr(f"RAM folosită: {used / 1024 ** 3:.1f} GB din {total / 1024 ** 3:.1f} GB", f"RAM used: {used / 1024 ** 3:.1f} GB of {total / 1024 ** 3:.1f} GB"))

    def clean_ram(self) -> None:
        QMessageBox.information(self, self.tr("Curățare RAM", "RAM cleanup"), flush_ram()); self.refresh_memory()

    def run_selected(self) -> None:
        if self.running:
            return
        selected = [name for name, check in self.action_checks.items() if check.isChecked()]
        if not selected:
            QMessageBox.information(self, "Win Tweaker", self.tr("Selectează cel puțin o setare.", "Select at least one setting.")); return
        self.current_run_selected = selected
        self.running = True; self.worker_thread = QThread(self); self.worker = OptimizerWorker(self.profile, selected); self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run); self.worker.progress.connect(self.on_progress); self.worker.finished.connect(self.on_finished); self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.worker_thread.quit); self.worker.failed.connect(self.worker_thread.quit); self.worker_thread.finished.connect(self.worker.deleteLater); self.worker_thread.finished.connect(self.thread_finished)
        self.worker_thread.start()

    def on_progress(self, done: int, total: int, action: str, result: str) -> None:
        self.statusBar().showMessage(f"{done}/{total}  {action}: {result}")

    def on_finished(self, _results: list[str]) -> None:
        self.settings.setValue(f"applied/{self.profile}", ",".join(getattr(self, "current_run_selected", [])))
        self.settings.sync()
        if hasattr(self, "apply_button"):
            self.apply_button.setVisible(False)
        self.statusBar().showMessage(self.tr("Optimizarea s-a terminat.", "Optimization finished."), 6000)
        QMessageBox.information(self, "Win Tweaker", self.tr("Optimizarea s-a terminat cu succes.", "Optimization finished successfully."))

    def on_failed(self, error: str) -> None:
        QMessageBox.critical(self, "Win Tweaker", error)

    def thread_finished(self) -> None:
        self.running = False; self.worker = None; self.worker_thread = None

    def open_startup(self) -> None:
        StartupDialog(self).exec()

    def toggle_autostart(self, enabled: bool) -> None:
        result = set_autostart(enabled)
        self.settings.setValue("autostart", enabled)
        self.settings.sync()
        self.statusBar().showMessage(result, 5000)

    def run_background_task(self, task: Callable[[], object], on_finished: Callable[[object], None]) -> bool:
        if self.running or self._maintenance_running or self._background_task_running:
            self.statusBar().showMessage(
                self.tr("O altă operație rulează deja în fundal.", "Another background operation is already running."),
                5000,
            )
            return False
        self._background_task_running = True
        self._background_task_thread = QThread(self)
        self._background_task_worker = BackgroundTaskWorker(task)
        self._background_task_worker.moveToThread(self._background_task_thread)
        self._background_task_thread.started.connect(self._background_task_worker.run)
        self._background_task_worker.finished.connect(on_finished)
        self._background_task_worker.failed.connect(self._background_task_failed)
        self._background_task_worker.finished.connect(self._background_task_thread.quit)
        self._background_task_worker.failed.connect(self._background_task_thread.quit)
        self._background_task_thread.finished.connect(self._background_task_worker.deleteLater)
        self._background_task_thread.finished.connect(self._background_task_thread_finished)
        self._background_task_thread.start()
        return True

    def _background_task_failed(self, error: str) -> None:
        self.statusBar().showMessage(
            self.tr(f"Operația a eșuat: {error}", f"Operation failed: {error}"),
            10000,
        )
        if self._pending_update_state is not None and hasattr(self, "update_switch"):
            self.update_switch.blockSignals(True)
            self.update_switch.setChecked(not self._pending_update_state)
            self.update_switch.blockSignals(False)
            self._pending_update_state = None
        if self._pending_service is not None:
            control, previous = self._pending_service
            control.blockSignals(True)
            control.setChecked(previous)
            control.blockSignals(False)
            control.setEnabled(True)
            self._pending_service = None

    def _background_task_thread_finished(self) -> None:
        self._background_task_running = False
        self._background_task_worker = None
        self._background_task_thread = None

    def confirm_service_toggle(self, service_name: str, enabled: bool, control: QCheckBox) -> None:
        if not enabled:
            answer = QMessageBox.warning(
                self,
                self.tr("Dezactivează serviciul", "Disable service"),
                self.tr(
                    f"Vrei să oprești serviciul {service_name}? Unele funcții Windows pot să nu mai funcționeze.",
                    f"Disable {service_name}? Some Windows features may stop working.",
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                control.blockSignals(True)
                control.setChecked(True)
                control.blockSignals(False)
                return
        previous = not enabled
        self._pending_service = (control, previous)
        control.setEnabled(False)
        started = self.run_background_task(
            lambda: set_windows_service_state(service_name, enabled),
            lambda result: self._service_toggle_finished(service_name, enabled, control, result),
        )
        if not started:
            control.setEnabled(True)
            self._pending_service = None

    def _service_toggle_finished(self, service_name: str, enabled: bool, control: QCheckBox, result: object) -> None:
        message = str(result)
        failed = "failed" in message.lower() or "eșuat" in message.lower()
        if not failed:
            self.settings.setValue(f"service/{service_name}", enabled)
            self.settings.sync()
            self._pending_service = None
        else:
            control.blockSignals(True)
            control.setChecked(not enabled)
            control.blockSignals(False)
            self._pending_service = None
        self.statusBar().showMessage(message, 10000)
        control.setEnabled(True)

    def confirm_update_cleanup(self) -> None:
        preview = cleanup_update_residue(preview=True)
        answer = QMessageBox.question(
            self,
            self.tr("Curățare Windows Update", "Windows Update cleanup"),
            f"{preview}\n\n" + self.tr(
                "Continui cu DISM și ștergerea Windows.old? Operația poate necesita drepturi de administrator.",
                "Continue with DISM and Windows.old deletion? This may require administrator rights.",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage(
                self.tr("Curățarea rulează în fundal...", "Cleanup is running in the background..."),
                5000,
            )
            self.run_background_task(
                lambda: cleanup_update_residue(preview=False),
                lambda result: self.statusBar().showMessage(str(result), 10000),
            )

    def confirm_browser_cleanup(self, browser: str) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Curățare cache", "Cache cleanup"),
            self.tr(
                f"Închide {browser.title()} și șterge cache-ul și cookie-urile locale?",
                f"Close {browser.title()} and delete local cache and cookies?",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage(
                self.tr("Curățarea cache-ului rulează în fundal...", "Cache cleanup is running in the background..."),
                5000,
            )
            self.run_background_task(
                lambda: clean_browser_cache(browser, include_cookies=True),
                lambda result: self.statusBar().showMessage(str(result), 7000),
            )

    def confirm_windows_update_toggle(self, paused: bool) -> None:
        if paused:
            answer = QMessageBox.warning(
                self,
                self.tr("Pauză Windows Update", "Pause Windows Update"),
                self.tr(
                    "Oprirea actualizărilor poate lăsa sistemul neprotejat. Continui?",
                    "Pausing updates can leave the system unprotected. Continue?",
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.update_switch.blockSignals(True); self.update_switch.setChecked(False); self.update_switch.blockSignals(False)
                return
        self._pending_update_state = paused
        self.statusBar().showMessage(
            self.tr("Se modifică Windows Update în fundal...", "Updating Windows Update in the background..."),
            5000,
        )
        self.run_background_task(
            lambda: set_windows_update_paused(paused),
            lambda result: self._background_update_finished(result),
        )

    def _background_update_finished(self, result: object) -> None:
        self._pending_update_state = None
        self.statusBar().showMessage(str(result), 10000)

    def confirm_revert(self) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Revert optimizations", "Revert optimizations"),
            self.tr(
                "Restaurează backup-ul de registry creat înaintea optimizării?",
                "Restore the registry backup created before optimization?",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage(
                self.tr("Restaurarea rulează în fundal...", "Revert is running in the background..."),
                5000,
            )
            self.run_background_task(
                revert_optimizations,
                lambda result: self.statusBar().showMessage(str(result), 10000),
            )

    def setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(QIcon(str(ROOT / "WinTweaker-logo.png")), self)
        self.tray_icon.setToolTip("Win Tweaker")
        menu = QMenu(self)
        show_action = QAction(self.tr("Deschide WinTweaker", "Open WinTweaker"), self)
        show_action.triggered.connect(self.show_from_tray)
        menu.addAction(show_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        if self.tray_available:
            self.tray_icon.activated.connect(self._tray_activated)
            self.tray_icon.show()
        elif self.background_mode:
            self.background_mode = False
            self.settings.setValue("background_mode", False)
            self.settings.sync()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_from_tray()

    def setup_maintenance(self) -> None:
        self.maintenance_timer = QTimer(self)
        self.maintenance_timer.setInterval(48 * 60 * 60 * 1000)
        self.maintenance_timer.timeout.connect(self.run_maintenance)
        self.maintenance_timer.start()
        last_run = float(self.settings.value("maintenance/last_run", 0) or 0)
        if time.time() - last_run >= 48 * 60 * 60:
            QTimer.singleShot(10000, self.run_maintenance)

    def setup_monitoring(self) -> None:
        self.monitor_timer = QTimer(self)
        self.monitor_timer.setInterval(60 * 1000)
        self.monitor_timer.timeout.connect(self.monitor_optimizations)
        self.monitor_timer.start()

    def monitor_optimizations(self) -> None:
        applied = self.settings.value(f"applied/{self.profile}", "")
        selected_ids = [item for item in str(applied).split(",") if item]
        drift = detect_optimization_drift(selected_ids)
        if drift and drift != getattr(self, "_last_drift", []):
            self._last_drift = drift
            if hasattr(self, "drift_label"):
                self.drift_label.setText(self.tr("⚠ Setare modificată", "⚠ Setting changed"))
                self.drift_label.setVisible(True)
            if hasattr(self, "apply_button"):
                self.apply_button.setVisible(True)
            if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "Win Tweaker",
                    self.tr("Windows a modificat o optimizare. Apasă Aplică pentru reaplicare.", "Windows changed an optimization. Press Apply to reapply it."),
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000,
                )
        elif not drift:
            self._last_drift = []
            if hasattr(self, "drift_label"):
                self.drift_label.setVisible(False)

    def run_maintenance(self) -> None:
        if self._maintenance_running or self.running:
            return
        self._maintenance_running = True
        self._maintenance_thread = QThread(self)
        self._maintenance_worker = MaintenanceWorker()
        self._maintenance_worker.moveToThread(self._maintenance_thread)
        self._maintenance_thread.started.connect(self._maintenance_worker.run)
        self._maintenance_worker.finished.connect(self._maintenance_finished)
        self._maintenance_worker.failed.connect(self._maintenance_failed)
        self._maintenance_worker.finished.connect(self._maintenance_thread.quit)
        self._maintenance_worker.failed.connect(self._maintenance_thread.quit)
        self._maintenance_thread.finished.connect(self._maintenance_worker.deleteLater)
        self._maintenance_thread.finished.connect(self._maintenance_thread_finished)
        self._maintenance_thread.start()

    def _maintenance_finished(self, result: str) -> None:
        self.settings.setValue("maintenance/last_run", time.time())
        self.settings.sync()
        self.statusBar().showMessage(result, 6000)

    def _maintenance_failed(self, error: str) -> None:
        self.statusBar().showMessage(
            self.tr(f"Întreținerea a eșuat: {error}", f"Maintenance failed: {error}"),
            10000,
        )

    def _maintenance_thread_finished(self) -> None:
        self._maintenance_running = False
        self._maintenance_worker = None
        self._maintenance_thread = None

    def show_from_tray(self) -> None:
        self.show()
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def exit_from_tray(self) -> None:
        if self._maintenance_running or self._background_task_running:
            self.tray_icon.showMessage(
                "Win Tweaker",
                self.tr(
                    "O operație rulează încă în fundal. Încearcă din nou după finalizare.",
                    "A background operation is still running. Try again after it finishes.",
                ),
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
            return
        self._allow_close = True
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        self.close()

    def closeEvent(self, event: Any) -> None:
        if self._maintenance_running or self._background_task_running:
            event.ignore()
            return
        if self._allow_close or not self.background_mode or not self.tray_available:
            event.accept()
            return
        self.hide()
        self.tray_icon.showMessage(
            "Win Tweaker",
            self.tr("Aplicația rulează în zona de notificări.", "The app is running in the system tray."),
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )
        event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Win Tweaker")
    app.setQuitOnLastWindowClosed(False)
    window = WinTweaker(); window.showNormal(); sys.exit(app.exec())
