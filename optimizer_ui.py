from __future__ import annotations

import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPointF,
    Property,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRectF,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Slot,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QDesktopServices,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
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
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
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
    get_service_info,
    is_startup_app_running,
    launch_startup_app,
    close_startup_app,
    open_windows_uninstaller_panel,
)
from installed_apps import (
    InstalledApplication,
    get_installed_applications,
    launch_uninstaller,
)
from temp_cleanup import estimate_temp_cleanup, format_byte_size, purge_temp_files
from system_scan import capture_system_snapshot
from dashboard_theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_LIGHT,
    ACCENT_BLUE_HOVER,
    ACCENT_CYAN,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    AnimatedToggleSwitch,
    BG_DARK,
    CARD_BG,
    DASHBOARD_QSS,
    GlassCard,
    GlowingPulseButton,
    LivePulseMonitor,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    create_nav_vector_pixmap,
    draw_nav_vector_icon,
    get_dashboard_qss,
)
from winget_catalog import (
    WINGET_CATALOG,
    WINGET_CATEGORIES,
    check_installed_packages,
    install_winget_package,
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

SERVICES_CATALOG = [
    (
        "Telemetry & Diagnostic",
        "DiagTrack",
        "◈",
        "Colectează și transmite date de telemetrie și diagnostic către Microsoft.",
        "Collects and sends Windows telemetry and diagnostic data to Microsoft.",
    ),
    (
        "SysMain / Superfetch",
        "SysMain",
        "⚡",
        "Gestionează preîncărcarea aplicațiilor în RAM; dezactivarea eliberează disc și memorie.",
        "Preloads apps into RAM; disabling frees memory and disk usage.",
    ),
    (
        "Windows Search Indexer",
        "WSearch",
        "⌕",
        "Controlează indexarea de fișiere în fundal pentru căutări rapide.",
        "Controls background file indexing for instant search.",
    ),
    (
        "Print Spooler",
        "Spooler",
        "▣",
        "Necesar pentru imprimante fizice sau imprimare în fișiere PDF.",
        "Required for physical printers or PDF printing.",
    ),
    (
        "Delivery Optimization",
        "DoSvc",
        "▷",
        "Partajează descărcările de actualizări Windows P2P cu alte calculatoare.",
        "Shares P2P Windows update downloads with other computers.",
    ),
    (
        "Bluetooth Support",
        "bthserv",
        "✦",
        "Necesar pentru descoperirea și conectarea dispozitivelor Bluetooth.",
        "Required for Bluetooth devices discovery and connection.",
    ),
    (
        "Remote Registry",
        "RemoteRegistry",
        "⛊",
        "Permite modificarea regitrilor de la distanță (recomandat Oprit).",
        "Allows remote registry modification (recommended Disabled).",
    ),
    (
        "Windows Error Reporting",
        "WerSvc",
        "◉",
        "Colectează și trimite rapoarte de erori și blocări către Microsoft.",
        "Collects and sends crash and error reports to Microsoft.",
    ),
    (
        "Downloaded Maps Manager",
        "MapsBroker",
        "⎗",
        "Gestionează hărțile descărcate în fundal pentru utilizare offline.",
        "Manages downloaded offline maps in the background.",
    ),
]


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
            try:
                self.finished.emit(results)
            except RuntimeError:
                pass
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            try:
                self.failed.emit(str(exc))
            except RuntimeError:
                pass


class MaintenanceWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            res = run_periodic_maintenance()
            try:
                self.finished.emit(res)
            except RuntimeError:
                pass
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            try:
                self.failed.emit(str(exc))
            except RuntimeError:
                pass


class BackgroundTaskWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable[[], object]) -> None:
        super().__init__()
        self.task = task

    def run(self) -> None:
        try:
            res = self.task()
            try:
                self.finished.emit(res)
            except RuntimeError:
                pass
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            try:
                self.failed.emit(str(exc))
            except RuntimeError:
                pass


class BackgroundTaskDispatcher(QObject):
    def __init__(
        self,
        on_finished: Callable[[object], None],
        on_failed: Callable[[str], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._on_finished = on_finished
        self._on_failed = on_failed

    @Slot(object)
    def deliver_finished(self, result: object) -> None:
        self._on_finished(result)

    @Slot(str)
    def deliver_failed(self, error: str) -> None:
        self._on_failed(error)


class WingetWorker(QObject):
    progress = Signal(str, str)
    finished = Signal(str, bool, str)
    batch_finished = Signal(int, int)

    def __init__(self, packages: list[dict]) -> None:
        super().__init__()
        self.packages = packages

    def run(self) -> None:
        installed = 0
        total = len(self.packages)
        for pkg in self.packages:
            pkg_id = pkg["id"]
            pkg_name = pkg["name"]
            pkg_source = pkg.get("source")
            try:
                self.progress.emit(pkg_id, f"Se pregătește {pkg_name}...")
                success, msg = install_winget_package(
                    pkg_id,
                    lambda line, p=pkg_id: self.progress.emit(p, line),
                    source=pkg_source,
                )
                if success:
                    installed += 1
                self.finished.emit(pkg_id, success, msg)
            except Exception as exc:
                self.finished.emit(pkg_id, False, str(exc))

        self.batch_finished.emit(installed, total)


class ThemeTransitionOverlay(QWidget):
    """Covers the window with a snapshot of the old theme and fades out smoothly."""

    def __init__(self, parent: QWidget, old_pixmap: QPixmap, duration: int = 180) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pixmap = old_pixmap
        self.setGeometry(parent.rect())
        self.show()
        self.raise_()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(duration)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)


class SmoothScrollArea(QScrollArea):
    """QScrollArea with butter-smooth animated wheel scrolling."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._target_value = 0
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._anim.setDuration(210)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def wheelEvent(self, event: Any) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return

        steps = -delta / 120.0
        step_distance = 110
        current_val = self.verticalScrollBar().value()

        if self._anim.state() == QPropertyAnimation.State.Running:
            base_val = self._target_value
        else:
            base_val = current_val

        min_val = self.verticalScrollBar().minimum()
        max_val = self.verticalScrollBar().maximum()
        self._target_value = int(max(min_val, min(max_val, base_val + steps * step_distance)))

        self._anim.stop()
        self._anim.setStartValue(current_val)
        self._anim.setEndValue(self._target_value)
        self._anim.start()
        event.accept()


class AnimatedPageHost(QFrame):
    """Hosts pages using QStackedLayout: guarantees EXACTLY ONE page is visible at any time."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.setStackingMode(QStackedLayout.StackingMode.StackOne)
        self.current: QWidget | None = None
        self._transition_animation: QParallelAnimationGroup | None = None
        self._transition_page: QWidget | None = None
        self._transition_opacity_effect: QGraphicsOpacityEffect | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def show_page(self, page: QWidget, direction: int = 1, animate: bool = True) -> None:
        previous = self.current
        self._clear_page_transition()

        if self.stack.indexOf(page) == -1:
            self.stack.addWidget(page)

        # Force every other page in the host to hide immediately so they can NEVER overlap
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if w is not page:
                w.hide()

        self.stack.setCurrentWidget(page)
        self.current = page
        page.setGeometry(self.rect())
        page.show()
        page.raise_()
        if animate and previous is not None and previous is not page and self.isVisible():
            end_geometry = self.rect()
            start_geometry = end_geometry.adjusted(18, 18, -18, -18).translated(
                0, 12 * (1 if direction >= 0 else -1)
            )
            page.setGeometry(start_geometry)

            opacity_effect = QGraphicsOpacityEffect(page)
            opacity_effect.setOpacity(0.0)
            page.setGraphicsEffect(opacity_effect)

            animation = QParallelAnimationGroup(self)
            geometry_animation = QPropertyAnimation(page, b"geometry", animation)
            geometry_animation.setDuration(220)
            geometry_animation.setStartValue(start_geometry)
            geometry_animation.setEndValue(end_geometry)
            geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            opacity_animation = QPropertyAnimation(
                opacity_effect, b"opacity", animation
            )
            opacity_animation.setDuration(175)
            opacity_animation.setStartValue(0.0)
            opacity_animation.setEndValue(1.0)
            opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.finished.connect(lambda: self._finish_page_transition(page, animation))
            self._transition_page = page
            self._transition_animation = animation
            self._transition_opacity_effect = opacity_effect
            animation.start()

    def _clear_page_transition(self) -> None:
        animation = self._transition_animation
        page = self._transition_page
        opacity_effect = self._transition_opacity_effect
        self._transition_animation = None
        self._transition_page = None
        self._transition_opacity_effect = None
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        if page is not None:
            page.setGeometry(self.rect())
            page.setGraphicsEffect(None)

    def _finish_page_transition(
        self, page: QWidget, animation: QParallelAnimationGroup
    ) -> None:
        if self._transition_animation is not animation:
            return
        self._transition_animation = None
        self._transition_page = None
        opacity_effect = self._transition_opacity_effect
        self._transition_opacity_effect = None
        page.setGeometry(self.rect())
        page.setGraphicsEffect(None)
        animation.deleteLater()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if self.current is not None:
            self.current.setGeometry(self.rect())


class IntroLogoWidget(QWidget):
    """
    High-end animated cyber emblem for the startup intro screen:
    - Orbiting particle rings with glowing heads
    - Sweeping conical radar aura
    - Breathing core glow
    - Smooth 40 FPS antialiased vector rendering
    """
    def __init__(self, is_dark: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.is_dark = is_dark
        self.setFixedSize(260, 260)
        self._angle1 = 0.0
        self._angle2 = 180.0
        self._pulse_phase = 0.0

        self.update_pixmap()

        self._timer = QTimer(self)
        self._timer.setInterval(25)  # ~40 FPS butter smooth
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def update_pixmap(self) -> None:
        name = "VATRIXTweaker-logo-white.png" if self.is_dark else "VATRIXTweaker-logo-black.png"
        self.pixmap = QPixmap(str(ROOT / name))

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update_pixmap()
        self.update()

    def _on_tick(self) -> None:
        self._angle1 = (self._angle1 + 3.0) % 360.0
        self._angle2 = (self._angle2 - 2.0) % 360.0
        self._pulse_phase = (self._pulse_phase + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        pulse = (math.sin(self._pulse_phase) + 1.0) / 2.0  # 0.0 to 1.0

        if self.is_dark:
            # 1. Ambient breathing backdrop glow
            glow_r = 100.0 + 18.0 * pulse
            glow = QRadialGradient(QPointF(cx, cy), glow_r)
            glow_alpha = int(25 + 30 * pulse)
            glow.setColorAt(0.0, QColor(56, 189, 248, glow_alpha))
            glow.setColorAt(0.5, QColor(30, 41, 59, int(glow_alpha * 0.4)))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

            # 2. Sweeping radar beam / conical sweep
            radar = QConicalGradient(QPointF(cx, cy), -self._angle1)
            radar.setColorAt(0.0, QColor(56, 189, 248, int(45 + 35 * pulse)))
            radar.setColorAt(0.25, QColor(56, 189, 248, 0))
            radar.setColorAt(1.0, QColor(56, 189, 248, 0))
            painter.setBrush(QBrush(radar))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), 95, 95)

            # 3. Outer orbiting cyber ring 1 (clockwise)
            r1 = 105.0
            arc_pen = QPen(QColor(56, 189, 248, 140), 1.8)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx - r1, cy - r1, r1 * 2, r1 * 2), int(self._angle1 * 16), int(130 * 16))

            # Orbiting bright particle dot on Ring 1
            rad1 = math.radians(self._angle1 + 130)
            px1 = cx + r1 * math.cos(rad1)
            py1 = cy - r1 * math.sin(rad1)
            dot1_grad = QRadialGradient(QPointF(px1, py1), 7)
            dot1_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
            dot1_grad.setColorAt(0.5, QColor(56, 189, 248, 180))
            dot1_grad.setColorAt(1.0, QColor(56, 189, 248, 0))
            painter.setBrush(QBrush(dot1_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px1, py1), 6, 6)

            # 4. Inner counter-rotating cyber ring 2 (counter-clockwise)
            r2 = 88.0
            r2_pen = QPen(QColor(148, 163, 184, 110), 1.4)
            r2_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(r2_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2), int(self._angle2 * 16), int(90 * 16))

            # Orbiting dot on Ring 2
            rad2 = math.radians(self._angle2 + 90)
            px2 = cx + r2 * math.cos(rad2)
            py2 = cy - r2 * math.sin(rad2)
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px2, py2), 2.5, 2.5)

        else:
            # LIGHT MODE: Clean modern pure black cyber orbit rings
            glow_r = 100.0 + 15.0 * pulse
            glow = QRadialGradient(QPointF(cx, cy), glow_r)
            glow.setColorAt(0.0, QColor(0, 0, 0, 20))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

            r1 = 105.0
            arc_pen = QPen(QColor(0, 0, 0, 220), 2.0)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx - r1, cy - r1, r1 * 2, r1 * 2), int(self._angle1 * 16), int(130 * 16))

            rad1 = math.radians(self._angle1 + 130)
            px1 = cx + r1 * math.cos(rad1)
            py1 = cy - r1 * math.sin(rad1)
            painter.setBrush(QBrush(QColor(0, 0, 0, 255)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px1, py1), 4, 4)

            r2 = 88.0
            r2_pen = QPen(QColor(0, 0, 0, 160), 1.5)
            r2_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(r2_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2), int(self._angle2 * 16), int(90 * 16))

            rad2 = math.radians(self._angle2 + 90)
            px2 = cx + r2 * math.cos(rad2)
            py2 = cy - r2 * math.sin(rad2)
            painter.setBrush(QBrush(QColor(0, 0, 0, 220)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px2, py2), 2.5, 2.5)

        # Draw center Logo
        logo_size = 130.0
        target = QRectF(cx - logo_size / 2.0, cy - logo_size / 2.0, logo_size, logo_size)
        if not self.pixmap.isNull():
            painter.drawPixmap(target.toRect(), self.pixmap)


class TitleBarButton(QPushButton):
    """
    Modern glassmorphic capsule title bar button (Minimize, Maximize/Restore, Close).
    Renders an elegant rounded capsule container with precision vector icons.
    """
    def __init__(self, btn_type: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.btn_type = btn_type  # "min", "max", "close"
        self.setFixedSize(32, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._hovered = False
        self._pressed = False
        self._is_maximized = False

    def set_maximized(self, state: bool) -> None:
        if self._is_maximized != state:
            self._is_maximized = state
            self.update()

    def enterEvent(self, event: Any) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        win = self.window()
        is_dark = getattr(win, "dark_mode", True) if win else True

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 6.5

        # 1. Capsule container background & border
        if self.btn_type == "close":
            if self._pressed:
                painter.setBrush(QBrush(QColor("#be123c")))
                painter.setPen(QPen(QColor(255, 255, 255, 80), 1.0))
                icon_col = QColor("#ffffff")
            elif self._hovered:
                painter.setBrush(QBrush(QColor("#e11d48")))
                painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
                icon_col = QColor("#ffffff")
            else:
                bg = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 16)
                border = QColor(255, 255, 255, 26) if is_dark else QColor(0, 0, 0, 28)
                painter.setBrush(QBrush(bg))
                painter.setPen(QPen(border, 1.0))
                icon_col = QColor("#cbd5e1") if is_dark else QColor("#334155")
        else:
            if self._pressed:
                bg = QColor(255, 255, 255, 30) if is_dark else QColor(0, 0, 0, 32)
                border = QColor(255, 255, 255, 60) if is_dark else QColor(0, 0, 0, 50)
                painter.setBrush(QBrush(bg))
                painter.setPen(QPen(border, 1.0))
                icon_col = QColor("#ffffff") if is_dark else QColor("#0f172a")
            elif self._hovered:
                bg = QColor(255, 255, 255, 22) if is_dark else QColor(0, 0, 0, 24)
                border = QColor(255, 255, 255, 50) if is_dark else QColor(0, 0, 0, 40)
                painter.setBrush(QBrush(bg))
                painter.setPen(QPen(border, 1.0))
                icon_col = QColor("#ffffff") if is_dark else QColor("#0f172a")
            else:
                bg = QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 16)
                border = QColor(255, 255, 255, 26) if is_dark else QColor(0, 0, 0, 28)
                painter.setBrush(QBrush(bg))
                painter.setPen(QPen(border, 1.0))
                icon_col = QColor("#cbd5e1") if is_dark else QColor("#334155")

        painter.drawRoundedRect(rect, radius, radius)

        # 2. Precision vector glyphs inside the capsule
        if self.btn_type == "min":
            # Solid rounded pill bar (10px wide, 2.0px stroke)
            pen = QPen(icon_col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(cx - 5.0, cy), QPointF(cx + 5.0, cy))

        elif self.btn_type == "max":
            pen = QPen(icon_col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self._is_maximized:
                # Restore: two overlapping window frames
                painter.drawRoundedRect(QRectF(cx - 2.5, cy - 5.2, 7.5, 7.5), 1.5, 1.5)
                # Front frame with fill mask
                mask_bg = (
                    QColor("#e11d48") if (self._hovered and self.btn_type == "close")
                    else (QColor(255, 255, 255, 22) if self._hovered and is_dark
                          else (QColor(0, 0, 0, 24) if self._hovered and not is_dark
                                else (QColor(255, 255, 255, 14) if is_dark else QColor(0, 0, 0, 16))))
                )
                painter.fillRect(QRectF(cx - 5.0, cy - 2.5, 7.5, 7.5), mask_bg)
                painter.drawRoundedRect(QRectF(cx - 5.0, cy - 2.5, 7.5, 7.5), 1.5, 1.5)
            else:
                # Maximize: single rounded window frame (10x10)
                painter.drawRoundedRect(QRectF(cx - 5.0, cy - 5.0, 10.0, 10.0), 2.0, 2.0)

        elif self.btn_type == "close":
            # Bold rounded cross (8.4 x 8.4 px, stroke 1.9px)
            pen = QPen(icon_col, 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            d = 4.2
            painter.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
            painter.drawLine(QPointF(cx + d, cy - d), QPointF(cx - d, cy + d))


class CustomTitleBar(QWidget):
    """Integrated frameless title bar matching the VATRIXTweaker dark theme."""

    def __init__(self, parent: QMainWindow) -> None:
        super().__init__(parent)
        self.win = parent
        self.setFixedHeight(36)
        self.setObjectName("customTitleBar")
        self.update_theme(getattr(self.win, "dark_mode", True))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(8)

        # Brand icon
        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(18, 18)
        logo_name = "VATRIXTweaker-logo-white.png" if getattr(self.win, "dark_mode", True) else "VATRIXTweaker-logo-black.png"
        pix = QPixmap(str(ROOT / logo_name))
        if not pix.isNull():
            self.logo_lbl.setPixmap(pix.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.logo_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Brand title
        self.title_lbl = QLabel("VATRIXTweaker", objectName="customTitleText")
        layout.addWidget(self.title_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()

        # Window control buttons group (modern floating glass capsules)
        ctrl_box = QHBoxLayout()
        ctrl_box.setContentsMargins(0, 0, 12, 0)
        ctrl_box.setSpacing(6)

        self.btn_min = TitleBarButton("min", self)
        self.btn_min.setToolTip(self.win.tr("Minimizare", "Minimize"))
        self.btn_min.clicked.connect(self.win.minimize_animated)
        ctrl_box.addWidget(self.btn_min, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_max = TitleBarButton("max", self)
        self.btn_max.setToolTip(self.win.tr("Maximizare / Restaurare", "Maximize / Restore"))
        self.btn_max.clicked.connect(self.toggle_max)
        ctrl_box.addWidget(self.btn_max, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_close = TitleBarButton("close", self)
        self.btn_close.setToolTip(self.win.tr("Închide", "Close"))
        self.btn_close.clicked.connect(self.win.close)
        ctrl_box.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(ctrl_box)

    def update_theme(self, is_dark: bool) -> None:
        bg = "#0d0f12" if is_dark else "#cbcfd6"
        border_col = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.10)"
        text_col = "#e2e8f0" if is_dark else "#0f172a"
        self.setStyleSheet(f"""
            QWidget#customTitleBar {{
                background: {bg};
                border-bottom: 1px solid {border_col};
            }}
            QLabel#customTitleText {{
                color: {text_col};
                font-size: 9.5pt;
                font-weight: 600;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
            }}
        """)
        if hasattr(self, "logo_lbl"):
            logo_name = "VATRIXTweaker-logo-white.png" if is_dark else "VATRIXTweaker-logo-black.png"
            pix = QPixmap(str(ROOT / logo_name))
            if not pix.isNull():
                self.logo_lbl.setPixmap(pix.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        if hasattr(self, "btn_min"):
            self.btn_min.update()
        if hasattr(self, "btn_max"):
            self.btn_max.update()
        if hasattr(self, "btn_close"):
            self.btn_close.update()

    def toggle_max(self) -> None:
        self.win.toggle_window_maximized()

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: Any) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            if self.win.isMaximized():
                self.win.showNormal()
                self.btn_max.set_maximized(False)
            self.win.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_max()
            event.accept()


class SidebarNavButton(QPushButton):
    """
    Sleek modern sidebar button that paints sharp antialiased vector icons
    for Home, Optimization, Apps, and Services, dynamically adapting to
    idle, hover, and active states in both Dark and Light themes.
    """
    def __init__(self, page_id: str, tooltip: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarNavBtn")
        self.page_id = page_id
        self.setFixedSize(60, 52)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover_progress = 0.0
        self._selection_progress = 0.0
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(160)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._selection_animation = QPropertyAnimation(self, b"selectionProgress", self)
        self._selection_animation.setDuration(210)
        self._selection_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def get_selection_progress(self) -> float:
        return self._selection_progress

    def set_selection_progress(self, value: float) -> None:
        self._selection_progress = max(0.0, min(1.0, float(value)))
        self.update()

    selectionProgress = Property(float, get_selection_progress, set_selection_progress)

    def set_selected_state(self, selected: bool, animate: bool = True) -> None:
        self.setProperty("selected", selected)
        self.setProperty("active", selected)
        self._selection_animation.stop()
        if not animate:
            self.set_selection_progress(float(selected))
            return
        self._selection_animation.setStartValue(self._selection_progress)
        self._selection_animation.setEndValue(float(selected))
        self._selection_animation.start()

    def enterEvent(self, event: Any) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        active_progress = self._selection_progress
        hover_progress = self._hover_progress
        win = self.window()
        is_dark = getattr(win, "dark_mode", True) if win else True

        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)

        if active_progress > 0.001:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            if is_dark:
                start_color = QColor("#1e2229")
                end_color = QColor("#121418")
                pen_color = QColor(255, 255, 255, int(40 * active_progress))
            else:
                start_color = QColor("#0f172a")
                end_color = QColor("#1e293b")
                pen_color = QColor(0, 0, 0, int(40 * active_progress))
            start_color.setAlpha(int(255 * active_progress))
            end_color.setAlpha(int(255 * active_progress))
            grad.setColorAt(0, start_color)
            grad.setColorAt(1, end_color)
            painter.setPen(QPen(pen_color, 1))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 13, 13)
            indicator_height = 22 * active_progress
            indicator_y = (self.height() - indicator_height) / 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(56, 189, 248, int(255 * active_progress)))
            painter.drawRoundedRect(QRectF(1, indicator_y, 3, indicator_height), 1.5, 1.5)
        elif hover_progress > 0.001:
            border_alpha = int((100 if is_dark else 120) * hover_progress)
            hover_alpha = int((18 if is_dark else 15) * hover_progress)
            painter.setPen(QPen(QColor(148, 163, 184, border_alpha), 1))
            hover_bg = QColor(255, 255, 255, hover_alpha) if is_dark else QColor(0, 0, 0, hover_alpha)
            painter.setBrush(QBrush(hover_bg))
            painter.drawRoundedRect(rect, 13, 13)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        icon_size = 28.0 * (1.0 + 0.12 * active_progress + 0.035 * hover_progress)
        ix = (self.width() - icon_size) / 2.0
        iy = (self.height() - icon_size) / 2.0
        idle_color = QColor("#94a3b8" if is_dark else "#475569")
        selected_color = QColor("#ffffff" if is_dark else "#0f172a")
        color = QColor(
            round(idle_color.red() + (selected_color.red() - idle_color.red()) * max(active_progress, hover_progress)),
            round(idle_color.green() + (selected_color.green() - idle_color.green()) * max(active_progress, hover_progress)),
            round(idle_color.blue() + (selected_color.blue() - idle_color.blue()) * max(active_progress, hover_progress)),
        )
        draw_nav_vector_icon(painter, self.page_id, ix, iy, icon_size, color.name())


class StartupDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Startup Programs — VATRIXTweaker")
        self.setWindowIcon(QIcon(str(ROOT / "VATRIXTweaker.ico")))
        self.resize(760, 540)
        self.setMinimumSize(640, 420)
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        # Header bar
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title = QLabel(self._t("Programe Startup", "Startup Programs"), objectName="pageHeaderTitle")
        subtitle = QLabel(
            self._t("Aplicațiile și serviciile care pornesc automat odată cu Windows.", "Applications and services that launch automatically with Windows."),
            objectName="pageHeaderSubtitle"
        )
        subtitle.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_row.addLayout(header_text, 1)

        self.count_badge = QLabel(objectName="actionPillBtn")
        header_row.addWidget(self.count_badge, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_row)

        # Scroll Area for entries
        self.scroll = SmoothScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.listing = QVBoxLayout(self.content_widget)
        self.listing.setContentsMargins(2, 2, 8, 2)
        self.listing.setSpacing(8)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll, 1)

        # Bottom Bar: Status Label on left, Close button on right
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(2, 4, 2, 0)
        bottom_bar.setSpacing(10)

        self.status_label = QLabel(objectName="cardStatusTag")
        bottom_bar.addWidget(self.status_label, 1)

        refresh_btn = QPushButton("⟲ " + self._t("Reîmprospătează", "Refresh"), objectName="softCardBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.populate_entries)
        bottom_bar.addWidget(refresh_btn)

        close_btn = QPushButton(self._t("Închide", "Close"), objectName="actionPillBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom_bar.addWidget(close_btn)

        layout.addLayout(bottom_bar)

        self.populate_entries()

    def _t(self, ro: str, en: str) -> str:
        lang = getattr(self.main_window, "lang", "RO")
        return en if lang == "EN" else ro

    def populate_entries(self) -> None:
        # Clear existing
        while self.listing.count():
            item = self.listing.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = get_startup_entries()
        total = len(entries)
        enabled_count = sum(1 for e in entries if e.get("enabled"))
        self.count_badge.setText(
            self._t(f"{enabled_count} active / {total} total", f"{enabled_count} active / {total} total")
        )

        is_dark = getattr(self.main_window, "dark_mode", True)
        badge_bg = "rgba(59, 130, 246, 0.12)" if is_dark else "rgba(37, 99, 235, 0.08)"
        badge_color = "#00d2ff" if is_dark else "#1685e8"
        badge_border = "rgba(59, 130, 246, 0.25)" if is_dark else "rgba(37, 99, 235, 0.20)"

        if not entries:
            empty_frame = QFrame(objectName="taskItemRow")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(24, 28, 24, 28)
            empty_layout.setSpacing(8)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            e_icon = QLabel("✓")
            e_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_icon.setStyleSheet(f"font-size: 26pt; color: #10b981; font-weight: bold;")
            empty_layout.addWidget(e_icon)

            e_title = QLabel(self._t("Nicio aplicație la pornire", "No startup programs"), objectName="taskTitle")
            e_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(e_title)

            e_desc = QLabel(
                self._t("Sistemul tău este complet curat! Nicio aplicație nu încetinește secvența de pornire Windows.", "Your system is clean! No applications slow down Windows startup."),
                objectName="taskDesc"
            )
            e_desc.setWordWrap(True)
            e_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(e_desc)

            self.listing.addWidget(empty_frame)
            self.listing.addStretch()
            return

        for entry in entries:
            row = QFrame(objectName="taskItemRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 10, 14, 10)
            row_layout.setSpacing(12)

            # Left app badge icon
            badge = QLabel("▷")
            badge.setStyleSheet(f"font-size: 11pt; color: {badge_color}; background: {badge_bg}; border-radius: 8px; padding: 4px 8px; border: 1px solid {badge_border}; font-weight: bold;")
            row_layout.addWidget(badge)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_lbl = QLabel(entry["name"], objectName="taskTitle")
            desc_lbl = QLabel(f"{entry['location']} • {entry['command']}", objectName="taskDesc")
            desc_lbl.setWordWrap(True)
            text_col.addWidget(name_lbl)
            text_col.addWidget(desc_lbl)
            row_layout.addLayout(text_col, 1)

            # Animated toggle switch
            switch = AnimatedToggleSwitch(row, checked=bool(entry["enabled"]))
            switch.toggled.connect(lambda checked, item=entry, control=switch: self.on_startup_toggled(checked, item, control))
            row_layout.addWidget(switch, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.listing.addWidget(row)

        self.listing.addStretch()

    def on_startup_toggled(self, checked: bool, entry: dict, control: AnimatedToggleSwitch) -> None:
        previous = bool(entry.get("enabled"))
        result = set_startup_entry_enabled(entry, checked)
        failed = "eroare" in result.lower() or "failed" in result.lower() or "eșuat" in result.lower()
        if failed:
            control.blockSignals(True)
            control.setChecked(previous)
            control.blockSignals(False)
            self.status_label.setStyleSheet("color: #ef4444; font-weight: 600;")
        else:
            entry["enabled"] = checked
            self.status_label.setStyleSheet("color: #10b981; font-weight: 600;")
            # Live update badge counter
            entries = get_startup_entries()
            total = len(entries)
            en = sum(1 for e in entries if e.get("enabled"))
            self.count_badge.setText(self._t(f"{en} active / {total} total", f"{en} active / {total} total"))
            # Update main window Home card if available
            if hasattr(self.main_window, "startup_card") and self.main_window.startup_card:
                self.main_window.startup_card.update_data(
                    big_stat=f"{en} / {total}",
                    stat_sub=self._t("Aplicații active la pornire", "Active autorun apps"),
                )

        self.status_label.setText(result)


class WinTweaker(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VATRIXTweaker")
        self.setWindowIcon(QIcon(str(ROOT / "VATRIXTweaker.ico")))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.settings = QSettings("VATRIXTweaker", "VATRIXTweaker")
        self.profile_data = get_available_profiles()
        saved_profile = str(self.settings.value("profile", "custom"))
        self.profile = saved_profile if saved_profile in self.profile_data else "custom"
        self.lang = str(self.settings.value("language", "RO"))
        if self.lang not in {"RO", "EN"}:
            self.lang = "RO"
        self.dark_mode = True
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
        self.background_mode = False
        self.tray_available = False
        self._loading_settings = True
        self.worker_thread: QThread | None = None
        self.worker: OptimizerWorker | None = None
        self.action_checks: dict[str, QCheckBox] = {}
        self.action_handlers: dict[str, str] = {}
        self.validation_states: dict[str, str] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        self.nav_data = {
            "Home": ("Home", "Acasă", "Home"),
            "Optimization": ("Optimization", "Optimizare", "Optimization"),
            "Winget": ("Winget", "WinGet", "WinGet"),
            "Startup": ("Startup", "Startup", "Startup"),
            "Apps": ("Apps", "Utilitare", "Tools"),
            "Services": ("Services", "Servicii", "Services"),
        }
        self.winget_installing_ids: set[str] = set()
        self.winget_installed_ids: set[str] = set()
        self.winget_selected_ids: set[str] = set()
        self.winget_active_filter: str = "all"
        self.winget_search_query: str = ""
        self._winget_worker_thread: Optional[QThread] = None
        self._winget_worker: Optional[WingetWorker] = None
        self._active_winget_workers: list[tuple[QThread, WingetWorker]] = []
        self._winget_installed_checked: bool = False
        self._page_cache: dict[str, QWidget] = {}
        self.service_status_labels: dict[str, QLabel] = {}
        self.service_switches: dict[str, AnimatedToggleSwitch] = {}
        self.services_summary_badge: Optional[QLabel] = None
        self.wu_status_lbl: Optional[QLabel] = None
        self.wu_switch: Optional[AnimatedToggleSwitch] = None
        self.installed_programs_list: list[dict] = []
        self.installed_apps_widget: Optional[QListWidget] = None
        self.installed_apps_search: Optional[QLineEdit] = None
        self.installed_apps_count_lbl: Optional[QLabel] = None
        self.uninstall_btn: Optional[QPushButton] = None
        self.scan_running = False
        self._junk_size_bytes = 0
        self.setStyleSheet(self.stylesheet())
        self.show_welcome()
        self._allow_close = False
        self.setup_tray()
        self.setup_maintenance()
        self.setup_monitoring()
        self.setup_live_updates()
        # Permanently eliminate running on Windows startup
        try:
            set_autostart(False)
            self.settings.setValue("autostart", False)
        except Exception:
            pass
        # Preload detailed system specs and battery wear in the background so
        # pressing "Deschide aplicația" shows them instantly, without blocking.
        self.run_background_task(
            get_hardware_info,
            self._home_specs_loaded,
            silent=True,
        )
        # Preload installed winget packages in background via dedicated thread
        self.start_winget_installed_check()

    def _preload_pages(self) -> None:
        """Prebuild pages in background after startup so every section switch is 0ms instant."""
        for p in ("Optimization", "Winget", "Startup", "Apps", "Services"):
            if p not in self._page_cache:
                try:
                    builders = {
                        "Optimization": self.page_optimization,
                        "Winget": self.page_winget,
                        "Startup": self.page_startup,
                        "Apps": self.page_apps,
                        "Services": self.page_services,
                    }
                    self._building_page = True
                    target = builders[p]()
                    self._building_page = False
                    self._page_cache[p] = target
                    target.hide()
                except Exception:
                    pass

    def stylesheet(self) -> str:
        return get_dashboard_qss(self.dark_mode)

    def build_ui(self) -> None:
        central = QWidget(objectName="centralRoot")
        central_vbox = QVBoxLayout(central)
        central_vbox.setContentsMargins(0, 0, 0, 0)
        central_vbox.setSpacing(0)

        # Integrated custom title bar at the very top
        self.custom_title_bar = CustomTitleBar(self)
        central_vbox.addWidget(self.custom_title_bar)

        dashboard_body = QWidget()
        root = QHBoxLayout(dashboard_body)
        root.setContentsMargins(14, 10, 14, 14)
        root.setSpacing(14)

        # Narrow CleanMyMac-style sidebar (icon-driven, rounded glass frame)
        self.sidebar = QFrame(objectName="cleanSidebar")
        self.sidebar.setFixedWidth(86)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(12)

        # App Logo Icon in sidebar - larger and crisp (VATRIXTweaker VT monogram)
        logo = QLabel()
        logo.setFixedSize(56, 56)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_logo = logo
        self.update_sidebar_logo()
        sidebar_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addSpacing(18)

        # Sidebar navigation buttons (large, clear, precision vector icons with rich tooltips)
        for page, (_icon, ro, en) in self.nav_data.items():
            button = SidebarNavButton(page, f"{self.tr(ro, en)} ({page})", self)
            button.setProperty("page", page)
            button.clicked.connect(lambda _checked=False, name=page: self.show_page(name))
            self.nav_buttons[page] = button
            sidebar_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addStretch()

        # Bottom sidebar controls: Language button
        sidebar_ctrl_layout = QVBoxLayout()
        sidebar_ctrl_layout.setSpacing(6)
        sidebar_ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lang_btn = QPushButton(self.lang, objectName="headerBtn")
        lang_btn.setFixedSize(50, 32)
        lang_btn.setToolTip(self.tr("Comută limba (RO / EN)", "Toggle language (RO / EN)"))
        lang_btn.clicked.connect(self.toggle_language)
        self.lang_sidebar_btn = lang_btn
        sidebar_ctrl_layout.addWidget(lang_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addLayout(sidebar_ctrl_layout)

        root.addWidget(self.sidebar)

        # Main content area
        content = QVBoxLayout()
        content.setSpacing(10)
        content.setContentsMargins(6, 4, 6, 4)

        # Top header bar
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(6, 2, 6, 2)
        top_layout.setSpacing(12)

        self.breadcrumb = QLabel("Acasă", objectName="pageHeaderTitle")
        self.breadcrumb.setMinimumWidth(220)
        top_layout.addWidget(self.breadcrumb)

        top_layout.addStretch()

        # Quick action: Flush RAM button in header
        quick_ram_btn = QPushButton("⚡ " + self.tr("Curăță RAM", "Flush RAM"), objectName="headerBtn")
        quick_ram_btn.clicked.connect(self.clean_ram)
        top_layout.addWidget(quick_ram_btn)

        # Quick action: System Restore button
        restore_btn = QPushButton("◈ " + self.tr("Restore Point", "Restore Point"), objectName="headerBtn")
        restore_btn.clicked.connect(self.create_quick_restore_point)
        top_layout.addWidget(restore_btn)

        self.apply_button = QPushButton(self.tr("Aplică optimizările", "Apply optimizations"), objectName="actionPillBtn")
        self.apply_button.clicked.connect(self.run_selected)
        self.apply_button.setVisible(False)
        top_layout.addWidget(self.apply_button)

        self.drift_label = QLabel(objectName="cardStatusTagWarning")
        self.drift_label.setVisible(False)
        top_layout.addWidget(self.drift_label)

        content.addLayout(top_layout)

        # Page host with smooth slide/fade transitions
        self.page_host = AnimatedPageHost()
        content.addWidget(self.page_host, 1)
        root.addLayout(content, 1)

        central_vbox.addWidget(dashboard_body, 1)
        self.setCentralWidget(central)

    def show_welcome(self) -> None:
        """Render the clean Octane Optimizer-style intro screen with integrated custom titlebar."""
        bg_css = "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #16181d, stop:0.5 #0d0f12, stop:1 #07080a);"

        central = QWidget()
        central.setStyleSheet(bg_css)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 24)
        outer.setSpacing(0)

        # Integrated custom titlebar at the very top
        self.custom_title_bar = CustomTitleBar(self)
        outer.addWidget(self.custom_title_bar)

        # Top Control Row: Language buttons
        top_row = QHBoxLayout()
        top_row.setContentsMargins(28, 14, 28, 0)
        top_row.addStretch()

        ro = QPushButton("RO")
        ro.setObjectName("welcomePillSelected" if self.lang == "RO" else "welcomePill")
        self.style_welcome_pill(ro, selected=self.lang == "RO")
        ro.clicked.connect(lambda: self.set_language("RO"))

        uk = QPushButton("EN")
        uk.setObjectName("welcomePillSelected" if self.lang == "EN" else "welcomePill")
        self.style_welcome_pill(uk, selected=self.lang == "EN")
        uk.clicked.connect(lambda: self.set_language("EN"))

        top_row.addWidget(ro)
        top_row.addWidget(uk)
        outer.addLayout(top_row)

        outer.addStretch(1)

        # Center Intro Content
        center_box = QVBoxLayout()
        center_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_box.setSpacing(14)

        self.intro_logo = IntroLogoWidget(is_dark=self.dark_mode, parent=central)
        center_box.addWidget(self.intro_logo, alignment=Qt.AlignmentFlag.AlignCenter)

        title_color = "#ffffff" if self.dark_mode else "#000000"
        title = QLabel("VATRIXTweaker")
        title.setStyleSheet(f"color: {title_color}; font-size: 28pt; font-weight: 800; letter-spacing: 2px; border: none; background: transparent;")
        center_box.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        slogan_color = "#94a3b8" if self.dark_mode else "#000000"
        sub = QLabel("SMART CLEAN  •  DEEP TUNE")
        sub.setStyleSheet(f"color: {slogan_color}; font-size: 9.5pt; font-weight: 800; letter-spacing: 3px; border: none; background: transparent;")
        center_box.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        outer.addLayout(center_box)
        outer.addStretch(1)

        self.setCentralWidget(central)

        # Smooth auto-transition timer (~2.2 seconds) into main dashboard
        if hasattr(self, "_intro_advance_timer") and self._intro_advance_timer:
            self._intro_advance_timer.stop()
            self._intro_advance_timer.deleteLater()
            self._intro_advance_timer = None
        self._intro_advance_timer = QTimer(self)
        self._intro_advance_timer.setSingleShot(True)
        self._intro_advance_timer.timeout.connect(self._finish_intro)
        self._intro_advance_timer.start(2200)

    def _finish_intro(self) -> None:
        if hasattr(self, "_intro_advance_timer") and self._intro_advance_timer:
            self._intro_advance_timer.stop()
            self._intro_advance_timer.deleteLater()
            self._intro_advance_timer = None
        self.show_app()

    def show_app(self) -> None:
        if hasattr(self, "_intro_advance_timer") and self._intro_advance_timer:
            self._intro_advance_timer.stop()
            self._intro_advance_timer.deleteLater()
            self._intro_advance_timer = None
        self._stylesheet_cache = self.stylesheet()
        self.setStyleSheet(self._stylesheet_cache)
        QApplication.instance().setStyleSheet(self._stylesheet_cache)
        old_central = self.centralWidget()
        if old_central is not None:
            old_central.hide()
            try:
                from shiboken6 import delete as shiboken_delete
                shiboken_delete(old_central)
            except Exception:
                old_central.deleteLater()
        self.build_ui()
        self.show_page("Home", animate=False)

    def tr(self, ro: str, en: str) -> str:
        return en if self.lang == "EN" else ro

    @staticmethod
    def style_primary(button: QPushButton, radius: int = 10, font_size: str = "9.5pt") -> None:
        button.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1217, stop:1 #1c2027); "
            f"color: #ffffff; border: 1px solid rgba(255,255,255,0.18); border-radius: {radius}px; "
            f"font-size: {font_size}; font-weight: 700; padding: 8px 14px; text-align: center; }} "
            f"QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e2430, stop:1 #2d3546); border-color: rgba(255,255,255,0.35); }} "
            f"QPushButton:pressed {{ background: #090a0d; }}"
        )

    def set_language(self, language: str) -> None:
        self.lang = language
        self.settings.setValue("language", self.lang)
        self.show_welcome()

    def choose_welcome_profile(self, profile: str) -> None:
        self.profile = profile
        self.settings.setValue("profile", self.profile)
        if hasattr(self, "welcome_profile_buttons"):
            for key, btn in self.welcome_profile_buttons.items():
                self.style_welcome_profile(btn, active=(key == profile))

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

    def style_welcome_pill(self, button: QPushButton, selected: bool) -> None:
        if selected:
            button.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1217, stop:1 #1c2027); "
                "color: #ffffff; border: 1px solid rgba(255,255,255,0.30); border-radius: 12px; padding: 5px 12px; font-weight: 700; font-size: 8.5pt; }"
            )
        else:
            bg = "rgba(255, 255, 255, 0.06)" if self.dark_mode else "#cbd2dc"
            fg = "#e2e8f0" if self.dark_mode else "#0f172a"
            border = "rgba(255, 255, 255, 0.10)" if self.dark_mode else "#94a3b8"
            hover_bg = "rgba(255, 255, 255, 0.12)" if self.dark_mode else "#0f172a"
            hover_fg = "#ffffff"
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 12px; padding: 5px 12px; font-weight: 600; font-size: 8.5pt; }} "
                f"QPushButton:hover {{ background: {hover_bg}; color: {hover_fg}; }}"
            )

    def style_welcome_profile(self, button: QPushButton, active: bool = False) -> None:
        if active:
            button.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1217, stop:1 #1c2027); "
                "color: #ffffff; border: 1px solid rgba(255,255,255,0.35); border-radius: 10px; padding: 10px 14px; "
                "font-size: 8.5pt; font-weight: 800; }"
            )
        else:
            bg = "rgba(255, 255, 255, 0.05)" if self.dark_mode else "#cbd2dc"
            fg = "#e2e8f0" if self.dark_mode else "#0f172a"
            border = "rgba(255, 255, 255, 0.08)" if self.dark_mode else "#94a3b8"
            hover_bg = "rgba(255, 255, 255, 0.10)" if self.dark_mode else "#0f172a"
            hover_fg = "#ffffff"
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 10px; padding: 10px 14px; "
                "font-size: 8.5pt; font-weight: 700; } "
                f"QPushButton:hover {{ background: {hover_bg}; border-color: #94a3b8; color: {hover_fg}; }}"
            )

    def toggle_theme(self) -> None:
        try:
            old_pixmap = self.grab()
            overlay = ThemeTransitionOverlay(self, old_pixmap, duration=260)
        except Exception:
            overlay = None

        self.dark_mode = not self.dark_mode
        self.settings.setValue("dark_mode", self.dark_mode)
        self._stylesheet_cache = self.stylesheet()
        self.setStyleSheet(self._stylesheet_cache)
        QApplication.instance().setStyleSheet(self._stylesheet_cache)

        theme_text = "🌙 Dark" if self.dark_mode else "☀️ Light"
        if hasattr(self, "theme_header_btn") and self.theme_header_btn:
            try:
                self.theme_header_btn.setText(theme_text)
            except RuntimeError:
                pass
        if hasattr(self, "theme_sidebar_btn") and self.theme_sidebar_btn:
            try:
                self.theme_sidebar_btn.setText("🌙" if self.dark_mode else "☀️")
            except RuntimeError:
                pass
        if hasattr(self, "theme_welcome_btn") and self.theme_welcome_btn:
            try:
                self.theme_welcome_btn.setText(theme_text)
                self.style_welcome_pill(self.theme_welcome_btn, selected=False)
            except RuntimeError:
                pass

        if hasattr(self, "custom_title_bar") and self.custom_title_bar:
            try:
                self.custom_title_bar.update_theme(self.dark_mode)
            except Exception:
                pass

        if hasattr(self, "page_host") and self.page_host:
            for p in self._page_cache.values():
                try:
                    p.deleteLater()
                except Exception:
                    pass
            self._page_cache.clear()
            self.page_host.current = None
            for button in self.nav_buttons.values():
                button.update()
            self.update_sidebar_logo()
            self.show_page(self.current_page, animate=False)
        else:
            self.show_welcome()

        if overlay is not None:
            overlay.raise_()

    def update_sidebar_logo(self) -> None:
        if hasattr(self, "sidebar_logo") and self.sidebar_logo:
            logo_name = "VATRIXTweaker-logo-white.png" if self.dark_mode else "VATRIXTweaker-logo-black.png"
            pixmap = QPixmap(str(ROOT / logo_name))
            if not pixmap.isNull():
                self.sidebar_logo.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_welcome_logo(self) -> None:
        if hasattr(self, "welcome_logo") and self.welcome_logo:
            logo_name = "VATRIXTweaker-logo-white.png" if self.dark_mode else "VATRIXTweaker-logo-black.png"
            pixmap = QPixmap(str(ROOT / logo_name))
            if not pixmap.isNull():
                self.welcome_logo.setPixmap(pixmap.scaled(124, 124, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def toggle_language(self) -> None:
        self.lang = "EN" if self.lang == "RO" else "RO"
        self.settings.setValue("language", self.lang)
        if hasattr(self, "lang_sidebar_btn"):
            self.lang_sidebar_btn.setText(self.lang)
        for page, button in self.nav_buttons.items():
            _icon, ro, en = self.nav_data[page]
            button.setToolTip(f"{self.tr(ro, en)} ({page})")
            button.update()
        if hasattr(self, "apply_button"):
            self.apply_button.setText(self.tr("Aplică optimizările", "Apply optimizations"))
        if hasattr(self, "page_host") and self.page_host:
            for p in self._page_cache.values():
                try:
                    p.deleteLater()
                except Exception:
                    pass
            self._page_cache.clear()
            self.page_host.current = None
        self.show_page(self.current_page, animate=False)

    def create_quick_restore_point(self) -> None:
        from optimizer import create_restore_point
        self.statusBar().showMessage(
            self.tr("Se creează punctul de restaurare...", "Creating restore point..."),
            5000,
        )
        self.run_background_task(
            lambda: create_restore_point(self.profile),
            lambda res: self.statusBar().showMessage(
                self.tr("Punct de restaurare: ", "Restore point: ") + str(res),
                8000,
            ),
        )

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
        page_order = {"Home": 0, "Optimization": 1, "Winget": 2, "Startup": 3, "Apps": 4, "Services": 5}
        old_idx = page_order.get(self.current_page, 0)
        new_idx = page_order.get(page, 0)
        direction = 1 if new_idx >= old_idx else -1

        self.current_page = page
        for name, button in self.nav_buttons.items():
            is_active = (name == page)
            button.set_selected_state(is_active, animate=animate)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        titles = {name: self.tr(ro, en) for name, (_icon, ro, en) in self.nav_data.items()}
        self.breadcrumb.setText(titles.get(page, page))
        self.breadcrumb.updateGeometry()

        target_page = self._page_cache.get(page)
        if target_page is None:
            builders = {
                "Home": self.page_home,
                "Optimization": self.page_optimization,
                "Winget": self.page_winget,
                "Startup": self.page_startup,
                "Apps": self.page_apps,
                "Services": self.page_services,
            }
            self._building_page = True
            target_page = builders[page]()
            self._building_page = False
            self._page_cache[page] = target_page

        if page == "Startup" and hasattr(self, "_refresh_startup_entries"):
            self._refresh_startup_entries()
        if page == "Services" and hasattr(self, "refresh_services_page"):
            self.refresh_services_page()

        self.page_host.show_page(target_page, direction=direction, animate=animate)

    def card(self) -> QFrame:
        return QFrame(objectName="glassCard")

    def page_shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 0, 4, 8)
        layout.setSpacing(8)
        description = QLabel(subtitle, objectName="pageHeaderSubtitle")
        description.setWordWrap(True)
        layout.addWidget(description)
        return page, layout

    def page_home(self) -> QWidget:
        """
        CleanMyMac-inspired dashboard page:
        1. Top Hero Card: Smart Care / System Status with real-time health indicator,
           detected bottlenecks/recommendations, and the prominent pulsing Scan/Stop button.
        2. 2x2 Glassmorphism Interactive Grid:
           - Junk Files (cleanup estimate, 1-click clean)
           - Startup Programs (number of autorun apps, open startup manager)
           - RAM Memory (real-time usage %, 1-click optimize)
           - WinGet & Apps (installed software inventory)
        3. Collapsible detailed hardware specs and battery wear diagnostics.
        """
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 12)
        layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. HERO CARD: SMART CARE / SYSTEM STATUS
        # -------------------------------------------------------------
        hero = QFrame(objectName="heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(6)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        smart_care_tag = QLabel(self.tr("SMART CARE • STARE SISTEM", "SMART CARE • SYSTEM STATUS"))
        smart_care_tag.setObjectName("cardCategory")
        smart_care_tag.setStyleSheet(f"color: {'#38bdf8' if self.dark_mode else '#000000'}; font-weight: 800; letter-spacing: 1.5px;")
        tag_row.addWidget(smart_care_tag)
        tag_row.addStretch()
        hero_left.addLayout(tag_row)

        self.hero_status_title = QLabel(
            self.tr("Sistemul tău este monitorizat și optimizat în timp real.", "Your system is monitored and optimized in real time."),
            objectName="heroTitle",
        )
        self.hero_status_title.setWordWrap(True)
        hero_left.addWidget(self.hero_status_title)

        # Real-time summary subtitle
        memory_status = get_memory_status()
        total_ram = (memory_status.get("total") or 0) / (1024 ** 3)
        used_ram = (memory_status.get("used") or 0) / (1024 ** 3)
        ram_pct = int((used_ram / total_ram * 100)) if total_ram else 0

        self.hero_status_sub = QLabel(
            self.tr(
                f"RAM: {used_ram:.1f}/{total_ram:.1f} GB ({ram_pct}%) • Monitorizare activă • Profil: {self.profile.upper()}",
                f"RAM: {used_ram:.1f}/{total_ram:.1f} GB ({ram_pct}%) • Active monitoring • Profile: {self.profile.upper()}",
            ),
            objectName="heroSub",
        )
        hero_left.addWidget(self.hero_status_sub)

        # Action pills below hero text
        pills_row = QHBoxLayout()
        pills_row.setSpacing(8)

        optimize_btn = QPushButton("✦ " + self.tr("Deschide Optimizarea", "Open Optimization"), objectName="actionPillBtn")
        optimize_btn.clicked.connect(lambda: self.show_page("Optimization"))
        pills_row.addWidget(optimize_btn)

        maintenance_btn = QPushButton("⟲ " + self.tr("Rulează Întreținerea", "Run Maintenance"), objectName="softCardBtn")
        maintenance_btn.clicked.connect(self.run_maintenance)
        pills_row.addWidget(maintenance_btn)

        pills_row.addStretch()
        hero_left.addLayout(pills_row)

        hero_layout.addLayout(hero_left, 1)

        # Right side of Hero: Automated live telemetry pulse radar (no manual scan button)
        hero_right = QVBoxLayout()
        hero_right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_pulse = LivePulseMonitor(hero, diameter=64)
        self.live_pulse.set_dark_mode(self.dark_mode)
        hero_right.addWidget(self.live_pulse)

        hero_layout.addLayout(hero_right)
        layout.addWidget(hero)

        # -------------------------------------------------------------
        # 2. 2x2 GLASSMORPHIC INTERACTIVE DASHBOARD GRID
        # -------------------------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        # Card 1: Junk Files / Temporary Cleanup
        self.junk_card = GlassCard(
            title=self.tr("Fișiere Temporare", "Junk Files"),
            category=self.tr("Curățare", "Cleanup"),
            big_stat=self.tr("Calcul...", "Scanning..."),
            stat_sub=self.tr("Junk Files • Cache • Temp", "Junk Files • Cache • Temp"),
            status_tag=self.tr("● Pregătit pentru curățare", "● Ready to clean"),
            accent_color=ACCENT_BLUE_LIGHT,
            icon_symbol="◈",
            action_hint=self.tr("Curăță ➔", "Clean ➔"),
        )
        self.junk_card.set_dark_mode(self.dark_mode)
        self.junk_card.clicked.connect(self.trigger_junk_cleanup)
        grid.addWidget(self.junk_card, 0, 0)

        # Card 2: RAM Optimization
        ram_stat_str = f"{ram_pct}%"
        ram_sub_str = self.tr(f"{used_ram:.1f} GB folosiți din {total_ram:.1f} GB", f"{used_ram:.1f} GB used of {total_ram:.1f} GB")
        ram_tag = self.tr("● Stare normală", "● Optimal") if ram_pct < 80 else self.tr("● Încărcare mare", "● High load")
        self.ram_card = GlassCard(
            title=self.tr("Optimizare RAM", "RAM Optimization"),
            category=self.tr("Performanță", "Performance"),
            big_stat=ram_stat_str,
            stat_sub=ram_sub_str,
            status_tag=ram_tag,
            accent_color=ACCENT_CYAN,
            icon_symbol="⚡",
            action_hint=self.tr("Optimizează ➔", "Optimize ➔"),
        )
        self.ram_card.set_dark_mode(self.dark_mode)
        self.ram_card.clicked.connect(self.clean_ram)
        grid.addWidget(self.ram_card, 0, 1)

        # Card 3: Startup Management
        try:
            startup_items = get_startup_entries()
            startup_count = len(startup_items)
            startup_enabled = sum(1 for e in startup_items if e.get("enabled"))
        except Exception:
            startup_count = 0
            startup_enabled = 0
        startup_stat = f"{startup_enabled} / {startup_count}"
        startup_sub = self.tr("Aplicații active la pornire", "Active autorun apps")
        self.startup_card = GlassCard(
            title=self.tr("Programe Startup", "Startup Programs"),
            category=self.tr("Boot", "Boot"),
            big_stat=startup_stat,
            stat_sub=startup_sub,
            status_tag=self.tr("● Gestionează autorun", "● Manage autorun"),
            accent_color=ACCENT_BLUE,
            icon_symbol="▷",
            action_hint=self.tr("Deschide ➔", "Open ➔"),
        )
        self.startup_card.set_dark_mode(self.dark_mode)
        self.startup_card.clicked.connect(self.open_startup)
        grid.addWidget(self.startup_card, 1, 0)

        # Card 4: WinGet Software Hub
        self.apps_card = GlassCard(
            title=self.tr("Aplicații WinGet", "WinGet Apps"),
            category=self.tr("Software", "Software"),
            big_stat="79+",
            stat_sub=self.tr("Browsere • Jocuri • Dev • Utilitare", "Browsers • Gaming • Dev • Tools"),
            status_tag=self.tr("● 7 categorii esențiale", "● 7 essential categories"),
            accent_color=ACCENT_GREEN,
            icon_symbol="vector:Winget",
            action_hint=self.tr("Explorează ➔", "Explore ➔"),
        )
        self.apps_card.set_dark_mode(self.dark_mode)
        self.apps_card.clicked.connect(lambda: self.show_page("Winget"))
        grid.addWidget(self.apps_card, 1, 1)

        layout.addLayout(grid)

        # Trigger background estimate of temp files to populate junk card
        self.estimate_temp_files_dashboard()

        # -------------------------------------------------------------
        # 3. SYSTEM SPECIFICATIONS & HARDWARE DETAILS CARD
        # -------------------------------------------------------------
        specs = QFrame(objectName="glassCard")
        specs_layout = QVBoxLayout(specs)
        specs_layout.setContentsMargins(18, 16, 18, 16)
        specs_layout.setSpacing(10)

        specs_header = QHBoxLayout()
        specs_title = QLabel(self.tr("SPECIFICAȚII HARDWARE & SISTEM", "SYSTEM SPECIFICATIONS & HARDWARE"))
        specs_title.setObjectName("cardTitle")
        specs_header.addWidget(specs_title)
        specs_header.addStretch()
        specs_layout.addLayout(specs_header)

        if self._home_detailed_cache is None and not self._home_specs_pending:
            self._home_specs_pending = True
            self.run_background_task(
                get_hardware_info,
                self._home_specs_loaded,
                silent=True,
            )
            self._home_detailed_cache = ({}, {"available": False, "message": self.tr("Se colectează informațiile de sistem...", "Collecting system information...")})

        detailed, battery = self._home_detailed_cache
        cpu = detailed.get("cpu") or {}
        os_info = detailed.get("os") or {}
        board = detailed.get("board") or {}
        bios_info = detailed.get("bios") or {}
        system_info = detailed.get("system") or {}
        cpu_name = cpu.get("Name") or platform.processor() or platform.machine()
        windows_caption = os_info.get("Caption") or f"Windows {platform.win32_ver()[0] or platform.release()}"
        build_number = os_info.get("BuildNumber") or platform.version()

        specs_data = (
            ("cpu", self.tr("Procesor", "Processor"), f"{cpu_name} — {cpu.get('NumberOfCores', '?')} nuclee / {cpu.get('NumberOfLogicalProcessors', os.cpu_count() or '?')} fire"),
            ("clock", self.tr("Frecvență", "Clock"), f"{(cpu.get('CurrentClockSpeed') or 0) / 1000:.2f} GHz (max {(cpu.get('MaxClockSpeed') or 0) / 1000:.2f} GHz)"),
            ("ram", self.tr("RAM", "RAM"), f"{total_ram:.1f} GB — {len(detailed.get('memory') or [])} module"),
            ("windows", self.tr("Windows", "Windows"), f"{windows_caption} (build {build_number})"),
            ("arch", self.tr("Arhitectură", "Architecture"), str(os_info.get("OSArchitecture") or platform.machine())),
            ("board", self.tr("Placă de bază", "Motherboard"), f"{board.get('Manufacturer', '?')} {board.get('Product', '')}".strip()),
            ("bios", self.tr("BIOS", "BIOS"), f"{bios_info.get('Manufacturer', '?')} {bios_info.get('SMBIOSBIOSVersion', '')}".strip()),
            ("system", self.tr("Sistem", "System"), f"{system_info.get('Manufacturer', '?')} {system_info.get('Model', '')}".strip()),
            ("boot", self.tr("Ultimul boot", "Last boot"), str(os_info.get("LastBootUpTime") or "n/a")),
            ("install", self.tr("Instalat la", "Installed on"), str(os_info.get("InstallDate") or "n/a")),
        )
        spec_grid = QGridLayout()
        spec_grid.setHorizontalSpacing(24)
        spec_grid.setVerticalSpacing(8)
        self._specs_val_labels = {}
        for index, (key, label, value) in enumerate(specs_data):
            row = index // 2
            col = (index % 2) * 2
            spec_grid.addWidget(QLabel(label, objectName="mutedLabel"), row, col)
            val_lbl = QLabel(value, objectName="specValue")
            val_lbl.setWordWrap(True)
            self._specs_val_labels[key] = val_lbl
            spec_grid.addWidget(val_lbl, row, col + 1)
        specs_layout.addLayout(spec_grid)

        # GPU info if present
        gpu_list = detailed.get("gpu") or []
        if gpu_list:
            specs_layout.addSpacing(8)
            gpu_title = QLabel(self.tr("PLACĂ GRAFICĂ", "GRAPHICS"))
            gpu_title.setObjectName("cardCategory")
            specs_layout.addWidget(gpu_title)
            gpu_grid = QGridLayout()
            gpu_grid.setHorizontalSpacing(20)
            gpu_grid.setVerticalSpacing(4)
            for index, gpu in enumerate(gpu_list):
                w = gpu.get("CurrentHorizontalResolution")
                h = gpu.get("CurrentVerticalResolution")
                res = f"{w}x{h}" if w and h else "n/a"
                gpu_grid.addWidget(QLabel(str(gpu.get("Name") or "n/a"), objectName="specValue"), index, 0)
                gpu_grid.addWidget(QLabel(f"Driver: {gpu.get('DriverVersion') or 'n/a'}", objectName="mutedLabel"), index, 1)
                gpu_grid.addWidget(QLabel(f"Rezoluție: {res}", objectName="specValue"), index, 2)
            specs_layout.addLayout(gpu_grid)

        layout.addWidget(specs)

        # Detailed Battery Wear card
        layout.addWidget(self._build_battery_card(battery))

        scroll.setWidget(container)
        return scroll

    def estimate_temp_files_dashboard(self) -> None:
        """Estimate temporary files in the background without freezing the UI or tearing down widgets."""
        if self._background_task_running:
            return

        def task():
            return estimate_temp_cleanup()

        def on_done(estimate):
            try:
                if getattr(self, "current_page", "") != "Home":
                    return
                if hasattr(self, "junk_card") and self.junk_card and estimate:
                    self._junk_size_bytes = estimate.bytes_total
                    formatted = format_byte_size(estimate.bytes_total)
                    self.junk_card.update_data(
                        big_stat=formatted,
                        stat_sub=self.tr(f"{estimate.file_count} fișiere temporare", f"{estimate.file_count} temporary files"),
                        status_tag=self.tr("● Curățare recomandată", "● Cleanup recommended") if estimate.bytes_total > 500 * 1024 * 1024 else self.tr("● Curat", "● Clean"),
                    )
            except Exception:
                pass

        self.run_background_task(task, on_done, silent=True)

    def trigger_junk_cleanup(self) -> None:
        """Execute Junk / Temp file cleanup directly without popup dialogs."""
        formatted = format_byte_size(self._junk_size_bytes) if self._junk_size_bytes else self.tr("fișierele temporare", "temporary files")
        self.statusBar().showMessage(self.tr(f"Curățarea fișierelor temporare ({formatted}) este în curs...", f"Cleaning temporary files ({formatted}) in progress..."), 5000)
        if hasattr(self, "junk_card"):
            self.junk_card.update_data(
                big_stat=self.tr("Curățare...", "Cleaning..."),
                status_tag=self.tr("● În curs de curățare...", "● Cleaning in progress..."),
            )

        def on_cleanup_done(res):
            if not res:
                return
            deleted_cnt = getattr(res, "deleted_files", 0)
            deleted_bytes = getattr(res, "deleted_bytes", 0)
            self._junk_size_bytes = 0
            if hasattr(self, "junk_card"):
                self.junk_card.update_data(
                    big_stat="0 B",
                    stat_sub=self.tr(f"{deleted_cnt} fișiere eliminate", f"{deleted_cnt} files removed"),
                    status_tag=self.tr("● Curățat cu succes", "● Cleaned successfully"),
                )
            self.statusBar().showMessage(
                self.tr(
                    f"Curățare finalizată: {deleted_cnt} fișiere șterse ({format_byte_size(deleted_bytes)} eliberați).",
                    f"Cleanup complete: {deleted_cnt} files deleted ({format_byte_size(deleted_bytes)} freed).",
                ),
                8000,
            )
            QTimer.singleShot(1000, self.estimate_temp_files_dashboard)

        self.run_background_task(purge_temp_files, on_cleanup_done)

    def _home_specs_loaded(self, payload: object) -> None:
        """Receive the detailed specs collected on a background thread without tearing down the page."""
        try:
            detailed, battery = payload
            self._home_detailed_cache = (detailed or {}, battery or {"available": False})
            self._home_specs_pending = False
            if getattr(self, "current_page", "") == "Home":
                self._update_home_specs_in_place()
        except Exception:
            pass

    def _update_home_specs_in_place(self) -> None:
        if not hasattr(self, "_specs_val_labels") or not self._specs_val_labels:
            return
        detailed, battery = getattr(self, "_home_detailed_cache", ({}, {}))
        if not detailed:
            return
        try:
            cpu = detailed.get("cpu") or {}
            os_info = detailed.get("os") or {}
            board = detailed.get("board") or {}
            bios_info = detailed.get("bios") or {}
            system_info = detailed.get("system") or {}
            cpu_name = cpu.get("Name") or platform.processor() or platform.machine()
            windows_caption = os_info.get("Caption") or f"Windows {platform.win32_ver()[0] or platform.release()}"
            build_number = os_info.get("BuildNumber") or platform.version()

            fresh = {
                "cpu": f"{cpu_name} — {cpu.get('NumberOfCores', '?')} nuclee / {cpu.get('NumberOfLogicalProcessors', os.cpu_count() or '?')} fire",
                "clock": f"{(cpu.get('CurrentClockSpeed') or 0) / 1000:.2f} GHz (max {(cpu.get('MaxClockSpeed') or 0) / 1000:.2f} GHz)",
                "windows": f"{windows_caption} (build {build_number})",
                "arch": str(os_info.get("OSArchitecture") or platform.machine()),
                "board": f"{board.get('Manufacturer', '?')} {board.get('Product', '')}".strip(),
                "bios": f"{bios_info.get('Manufacturer', '?')} {bios_info.get('SMBIOSBIOSVersion', '')}".strip(),
                "system": f"{system_info.get('Manufacturer', '?')} {system_info.get('Model', '')}".strip(),
                "boot": str(os_info.get("LastBootUpTime") or "n/a"),
                "install": str(os_info.get("InstallDate") or "n/a"),
            }
            for k, val in fresh.items():
                lbl = self._specs_val_labels.get(k)
                if lbl:
                    try:
                        lbl.setText(val)
                    except RuntimeError:
                        pass
        except Exception:
            pass

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
            grid.addWidget(QLabel(label, objectName="mutedLabel"), row, column)
            grid.addWidget(QLabel(value, objectName="specValue"), row, column + 1)
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
        icons = {"low_end": "▸", "gaming": "▲", "office": "▣", "custom": "✦"}
        self.opt_profile_buttons = {}
        for key in self.profile_data:
            btn_text = f"{icons.get(key, '✦')}  {self.tr(*names[key])}"
            button = QPushButton(btn_text, objectName="profileBtn")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=key: self.select_profile(value))
            profile_layout.addWidget(button)
            self.opt_profile_buttons[key] = button
        apply_button = QPushButton("✦  " + self.tr("Aplică selecția", "Apply selection"), objectName="primary")
        self.style_primary(apply_button)
        apply_button.clicked.connect(self.run_selected)
        profile_layout.addStretch()
        profile_layout.addWidget(apply_button)
        self.opt_apply_button = apply_button
        revert_button = QPushButton("⟲  " + self.tr("Restaurează setările", "Revert optimizations"), objectName="softCardBtn")
        revert_button.clicked.connect(self.confirm_revert)
        profile_layout.addWidget(revert_button)
        columns.addWidget(profiles, 1)

        actions = self.card(); actions_layout = QVBoxLayout(actions)
        actions_layout.addWidget(QLabel(self.tr("SETĂRI DISPONIBILE", "AVAILABLE SETTINGS"), objectName="cardTitle"))
        self.selected_label = QLabel(objectName="muted"); actions_layout.addWidget(self.selected_label)
        self.validation_label = QLabel(objectName="muted")
        self.validation_label.setWordWrap(True)
        actions_layout.addWidget(self.validation_label)
        scroll = SmoothScrollArea(); scroll.setWidgetResizable(True)
        self.action_container = QWidget(objectName="actionContainer"); self.action_layout = QVBoxLayout(self.action_container); self.action_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.action_container); actions_layout.addWidget(scroll, 1); columns.addWidget(actions, 2)
        layout.addLayout(columns, 1); self.select_profile(self.profile)
        return page

    def select_profile(self, name: str) -> None:
        self.profile = name
        self.settings.setValue("profile", self.profile)
        if hasattr(self, "opt_profile_buttons"):
            for key, btn in self.opt_profile_buttons.items():
                btn.setProperty("selected", key == name)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
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
            self.selected_label.setText(
                self.tr(
                    f"{count} setări selectate — apasă «Aplică selecția» pentru activare",
                    f"{count} settings selected — click «Apply selection» to activate"
                )
            )

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

    def page_winget(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 10)
        layout.setSpacing(12)

        # 1. Header Hero Panel for Winget Hub
        hero = QFrame(objectName="heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(16)

        left_hero = QVBoxLayout()
        left_hero.setSpacing(4)
        tag = QLabel(self.tr("WINDOWS PACKAGE MANAGER • WINGET SOFTWARE HUB", "WINDOWS PACKAGE MANAGER • WINGET SOFTWARE HUB"))
        tag.setObjectName("cardCategory")
        tag.setStyleSheet(f"color: {'#38bdf8' if self.dark_mode else '#000000'}; font-weight: 800; letter-spacing: 1.5px;")
        left_hero.addWidget(tag)

        h_title = QLabel(self.tr("Instalează Programe Esențiale (79 Disponibile)", "Install Essential Software (79 Available)"), objectName="heroTitle")
        left_hero.addWidget(h_title)

        h_sub = QLabel(
            self.tr(
                "Descarcă și instalează rapid browsere, jocuri, medii de programare și utilitare printr-un singur click, fără reclame sau pași inutili.",
                "Download and install browsers, gaming clients, IDEs and utilities in one click without ads or bloated installers."
            ),
            objectName="heroSub"
        )
        h_sub.setWordWrap(True)
        left_hero.addWidget(h_sub)
        hero_layout.addLayout(left_hero, 1)

        # Right side of Hero: Batch Action Button & Status Counter
        right_hero = QVBoxLayout()
        right_hero.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_hero.setSpacing(6)

        total_p = len(WINGET_CATALOG)
        inst_cnt = len(self.winget_installed_ids)
        self.winget_count_badge = QLabel(
            self.tr(f"{inst_cnt} instalate / {total_p} total", f"{inst_cnt} installed / {total_p} total"),
            objectName="actionPillBtn"
        )
        right_hero.addWidget(self.winget_count_badge, alignment=Qt.AlignmentFlag.AlignRight)

        cnt_sel = len(self.winget_selected_ids)
        self.batch_install_btn = QPushButton("✦ " + self.tr(f"Instalează selecția ({cnt_sel})", f"Install selected ({cnt_sel})"), objectName="actionPillBtn")
        self.batch_install_btn.setMinimumHeight(38)
        self.batch_install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_install_btn.clicked.connect(self.run_batch_winget_install)
        right_hero.addWidget(self.batch_install_btn)

        batch_ctrls = QHBoxLayout()
        batch_ctrls.setSpacing(6)
        sel_all_btn = QPushButton(self.tr("Selectează tot", "Select all"), objectName="softCardBtn")
        sel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_all_btn.clicked.connect(self.winget_select_all)
        desel_all_btn = QPushButton(self.tr("Deselectează", "Deselect"), objectName="softCardBtn")
        desel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        desel_all_btn.clicked.connect(self.winget_deselect_all)
        batch_ctrls.addWidget(sel_all_btn)
        batch_ctrls.addWidget(desel_all_btn)
        right_hero.addLayout(batch_ctrls)

        hero_layout.addLayout(right_hero)
        layout.addWidget(hero)

        # 2. Search & Category Filters Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(10)

        self.winget_search_input = QLineEdit()
        self.winget_search_input.setPlaceholderText("🔍  " + self.tr("Caută aplicație (ex: Chrome, Steam, Discord, VS Code, VLC...)", "Search app (e.g. Chrome, Steam, Discord, VS Code, VLC...)"))
        self.winget_search_input.setText(self.winget_search_query)
        self.winget_search_input.textChanged.connect(self.on_winget_search_changed)
        self.winget_search_input.setMinimumHeight(38)
        ctrl_bar.addWidget(self.winget_search_input, 1)

        # Tools link button
        tools_link_btn = QPushButton("🛠️ " + self.tr("Utilitare && Startup", "Tools && Startup"), objectName="headerBtn")
        tools_link_btn.setMinimumHeight(38)
        tools_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tools_link_btn.clicked.connect(lambda: self.show_page("Apps"))
        ctrl_bar.addWidget(tools_link_btn)

        layout.addLayout(ctrl_bar)

        # Category Filter Pills Scroll Area / Row
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(38)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_widget = QWidget()
        cat_layout = QHBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(6)

        self.category_buttons: dict[str, QPushButton] = {}
        for cat_id, ro_title, en_title in WINGET_CATEGORIES:
            btn_title = self.tr(ro_title, en_title).replace("&", "&&")
            cat_btn = QPushButton(btn_title, objectName="catPillBtn")
            cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cat_btn.setFixedHeight(32)
            is_active = (cat_id == self.winget_active_filter)
            cat_btn.setProperty("active", "true" if is_active else "false")
            cat_btn.clicked.connect(lambda _checked=False, c=cat_id: self.filter_winget_category(c))
            self.category_buttons[cat_id] = cat_btn
            cat_layout.addWidget(cat_btn)

        cat_layout.addStretch()
        cat_scroll.setWidget(cat_widget)
        layout.addWidget(cat_scroll)

        # 3. Main Applications Grid in SmoothScrollArea
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 10, 16)
        content_layout.setSpacing(0)

        self.winget_grid_widget = QWidget()
        self.winget_grid = QGridLayout(self.winget_grid_widget)
        self.winget_grid.setContentsMargins(0, 0, 0, 0)
        self.winget_grid.setHorizontalSpacing(12)
        self.winget_grid.setVerticalSpacing(10)

        content_layout.addWidget(self.winget_grid_widget)
        content_layout.addStretch(1)

        # Populate the catalog after the page is shown so navigation is not blocked.
        self.winget_item_cards = []
        self.winget_loading_label = QLabel(
            self.tr("Se încarcă aplicațiile...", "Loading applications...")
        )
        self.winget_loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.winget_loading_label.setMinimumHeight(100)
        content_layout.addWidget(self.winget_loading_label)
        self.winget_content_layout = content_layout
        self._winget_cards_next_index = 0
        self._winget_page_generation = getattr(self, "_winget_page_generation", 0) + 1
        page_generation = self._winget_page_generation

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        if not self.winget_installed_ids and not getattr(self, "_winget_detect_running", False):
            self.start_winget_installed_check()

        QTimer.singleShot(16, lambda generation=page_generation: self._populate_winget_cards(generation))
        return page

    def _populate_winget_cards(self, generation: int) -> None:
        if generation != self._winget_page_generation:
            return

        if self.winget_loading_label is not None:
            self.winget_content_layout.removeWidget(self.winget_loading_label)
            self.winget_loading_label.deleteLater()
            self.winget_loading_label = None

        end_index = min(self._winget_cards_next_index + 12, len(WINGET_CATALOG))
        for index in range(self._winget_cards_next_index, end_index):
            pkg = WINGET_CATALOG[index]
            card = QFrame(objectName="taskItemRow")
            card.setFixedHeight(68)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(12)

            # Checkbox for batch selection
            chk = QCheckBox()
            chk.setFixedSize(22, 22)
            chk.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chk.setChecked(pkg["id"] in self.winget_selected_ids)
            chk.stateChanged.connect(lambda state, p=pkg["id"]: self.on_winget_pkg_checked(p, bool(state)))
            card_layout.addWidget(chk, alignment=Qt.AlignmentFlag.AlignVCenter)

            # Category icon badge
            cat_symbol = pkg["category_title"].split()[0]
            badge = QLabel(cat_symbol, objectName="cardBadge")
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

            # Info column: Name, Description
            info_col = QVBoxLayout()
            info_col.setSpacing(2)

            name_lbl = QLabel(pkg["name"], objectName="taskTitle")
            info_col.addWidget(name_lbl)

            desc_text = self.tr(pkg["desc"], pkg.get("desc_en", pkg["desc"]))
            desc_lbl = QLabel(desc_text, objectName="taskDesc")
            desc_lbl.setWordWrap(True)
            info_col.addWidget(desc_lbl)

            card.setToolTip(f"{pkg['name']} (ID: {pkg['id']})")
            card_layout.addLayout(info_col, 1)

            # Action install button
            inst_btn = QPushButton("⬇ " + self.tr("Instalează", "Install"), objectName="softCardBtn")
            inst_btn.setFixedSize(104, 32)
            inst_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if pkg["id"] in self.winget_installing_ids:
                inst_btn.setText("⏳ " + self.tr("În curs...", "Installing..."))
                inst_btn.setEnabled(False)
            elif pkg["id"] in self.winget_installed_ids:
                inst_btn.setText("✓ " + self.tr("Instalat", "Installed"))
                inst_btn.setEnabled(False)
                inst_btn.setStyleSheet("color: #10b981; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.35); background: rgba(16, 185, 129, 0.10); border-radius: 9px;")
                chk.setChecked(False)
                chk.setEnabled(False)
            else:
                inst_btn.clicked.connect(lambda _checked=False, p=pkg: self.install_single_winget_package(p))

            card_layout.addWidget(inst_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
            self.winget_grid.addWidget(card, index // 2, index % 2)
            self.winget_item_cards.append((pkg, card, chk, inst_btn))

        self._winget_cards_next_index = end_index
        self.relayout_winget_grid()

        if end_index < len(WINGET_CATALOG):
            QTimer.singleShot(16, lambda: self._populate_winget_cards(generation))

    def style_category_pill(self, button: QPushButton, active: bool = False) -> None:
        if active:
            button.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1217, stop:1 #1c2027); "
                "color: #ffffff; border: 1px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 4px 14px; font-weight: 700; font-size: 8.5pt; }"
            )
        else:
            is_dark = self.dark_mode
            bg = "rgba(255, 255, 255, 0.06)" if is_dark else "#cbd2dc"
            fg = "#cbd5e1" if is_dark else "#0f172a"
            border = "rgba(255, 255, 255, 0.10)" if is_dark else "#94a3b8"
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 12px; padding: 4px 14px; font-weight: 600; font-size: 8.5pt; }} "
                "QPushButton:hover { background: rgba(255, 255, 255, 0.12) if is_dark else '#0f172a'; color: '#ffffff'; border-color: '#94a3b8'; }"
            )

    def filter_winget_category(self, cat_id: str) -> None:
        self.winget_active_filter = cat_id
        if hasattr(self, "category_buttons"):
            for cid, btn in self.category_buttons.items():
                is_act = (cid == cat_id)
                btn.setProperty("active", "true" if is_act else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        self.relayout_winget_grid()

    def on_winget_search_changed(self, text: str) -> None:
        self.winget_search_query = text
        if text.strip() and self.winget_active_filter != "all":
            self.winget_active_filter = "all"
            if hasattr(self, "category_buttons"):
                for cid, btn in self.category_buttons.items():
                    is_act = (cid == "all")
                    btn.setProperty("active", "true" if is_act else "false")
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
        self.relayout_winget_grid()

    def relayout_winget_grid(self) -> None:
        if not hasattr(self, "winget_item_cards") or not hasattr(self, "winget_grid"):
            return

        query = self.winget_search_query.lower().strip()
        cat_filter = self.winget_active_filter

        self.winget_grid_widget.setUpdatesEnabled(False)

        # Remove cards from current grid positions without deleting layout
        for pkg, card, _chk, _btn in self.winget_item_cards:
            self.winget_grid.removeWidget(card)

        visible_index = 0
        for pkg, card, _chk, _btn in self.winget_item_cards:
            matches_cat = (cat_filter == "all" or pkg["category"] == cat_filter)
            matches_search = (
                not query
                or query in pkg["name"].lower()
                or query in pkg["id"].lower()
                or query in pkg["desc"].lower()
                or query in pkg.get("desc_en", "").lower()
            )

            is_visible = bool(matches_cat and matches_search)
            card.setVisible(is_visible)
            if is_visible:
                row = visible_index // 2
                col = visible_index % 2
                self.winget_grid.addWidget(card, row, col)
                visible_index += 1

        self.winget_grid_widget.setUpdatesEnabled(True)

    def on_winget_pkg_checked(self, pkg_id: str, checked: bool) -> None:
        if checked:
            self.winget_selected_ids.add(pkg_id)
        else:
            self.winget_selected_ids.discard(pkg_id)
        self.update_batch_btn_text()

    def winget_select_all(self) -> None:
        for pkg, card, chk, _btn in getattr(self, "winget_item_cards", []):
            if card.isVisible() and pkg["id"] not in self.winget_installed_ids:
                chk.setChecked(True)
                self.winget_selected_ids.add(pkg["id"])
        self.update_batch_btn_text()

    def winget_deselect_all(self) -> None:
        for _pkg, _card, chk, _btn in getattr(self, "winget_item_cards", []):
            chk.setChecked(False)
        self.winget_selected_ids.clear()
        self.update_batch_btn_text()

    def update_batch_btn_text(self) -> None:
        if hasattr(self, "batch_install_btn") and self.batch_install_btn:
            cnt = len(self.winget_selected_ids)
            self.batch_install_btn.setText("✦ " + self.tr(f"Instalează selecția ({cnt})", f"Install selected ({cnt})"))

    def install_single_winget_package(self, pkg: dict) -> None:
        pkg_id = pkg["id"]
        if pkg_id in self.winget_installing_ids:
            return

        if pkg_id in self.winget_installed_ids:
            self.statusBar().showMessage(self.tr(f"{pkg['name']} este deja instalat.", f"{pkg['name']} is already installed."), 4000)
            return

        self.winget_installing_ids.add(pkg_id)
        self._update_winget_card_btn(pkg_id)
        self.statusBar().showMessage(self.tr(f"Se instalează {pkg['name']} prin WinGet...", f"Installing {pkg['name']} via WinGet..."), 5000)

        thread = QThread(self)
        worker = WingetWorker([pkg])
        worker.moveToThread(thread)
        self._active_winget_workers.append((thread, worker))

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_winget_progress)
        worker.finished.connect(self._on_winget_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        def cleanup_thread(t=thread, w=worker):
            try:
                if (t, w) in self._active_winget_workers:
                    self._active_winget_workers.remove((t, w))
            except Exception:
                pass
            t.deleteLater()

        thread.finished.connect(cleanup_thread)
        thread.start()

    def run_batch_winget_install(self) -> None:
        if not self.winget_selected_ids:
            self.statusBar().showMessage(
                self.tr("Selectează cel puțin o aplicație din listă pentru instalare.", "Select at least one application from the list to install."),
                5000,
            )
            return

        selected_pkgs = [p for p in WINGET_CATALOG if p["id"] in self.winget_selected_ids and p["id"] not in self.winget_installing_ids and p["id"] not in self.winget_installed_ids]
        if not selected_pkgs:
            self.statusBar().showMessage(
                self.tr("Toate aplicațiile selectate sunt deja instalate.", "All selected applications are already installed."),
                5000,
            )
            return

        cnt = len(selected_pkgs)
        for p in selected_pkgs:
            self.winget_installing_ids.add(p["id"])
            self._update_winget_card_btn(p["id"])

        self.statusBar().showMessage(self.tr(f"Instalarea a {cnt} aplicații a început în fundal...", f"Installation of {cnt} apps started in the background..."), 6000)

        thread = QThread(self)
        worker = WingetWorker(selected_pkgs)
        worker.moveToThread(thread)
        self._active_winget_workers.append((thread, worker))

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_winget_progress)
        worker.finished.connect(self._on_winget_finished)
        worker.batch_finished.connect(self._on_winget_batch_finished)
        worker.batch_finished.connect(thread.quit)
        worker.batch_finished.connect(worker.deleteLater)

        def cleanup_batch(t=thread, w=worker):
            try:
                if (t, w) in self._active_winget_workers:
                    self._active_winget_workers.remove((t, w))
            except Exception:
                pass
            t.deleteLater()

        thread.finished.connect(cleanup_batch)
        thread.start()

    @Slot(str, str)
    def _on_winget_progress(self, pkg_id: str, line: str) -> None:
        self.statusBar().showMessage(f"WinGet [{pkg_id}]: {line}", 4000)
        progress_text = None
        lower_line = line.lower()
        if "%" in line:
            for part in line.split():
                if "%" in part:
                    progress_text = f"⏳ {part}"
                    break
        elif "download" in lower_line or "descarcă" in lower_line:
            progress_text = "⏳ Descărcare..."
        elif "install" in lower_line or "instalare" in lower_line:
            progress_text = "⏳ Instalare..."

        if progress_text:
            for pkg, _card, _chk, btn in getattr(self, "winget_item_cards", []):
                if pkg["id"] == pkg_id:
                    btn.setText(progress_text)
                    break

    @Slot(str, bool, str)
    def _on_winget_finished(self, pkg_id: str, success: bool, msg: str) -> None:
        self.winget_installing_ids.discard(pkg_id)
        if success:
            self.winget_installed_ids.add(pkg_id)
            self.winget_selected_ids.discard(pkg_id)
            self.update_batch_btn_text()

        self._update_winget_card_btn(pkg_id, success, msg)
        if hasattr(self, "winget_count_badge") and self.winget_count_badge:
            cnt = len(self.winget_installed_ids)
            total = len(WINGET_CATALOG)
            self.winget_count_badge.setText(
                self.tr(f"{cnt} instalate / {total} total", f"{cnt} installed / {total} total")
            )
        if hasattr(self, "apps_card") and self.apps_card:
            self.apps_card.update_data(big_stat=f"{len(self.winget_installed_ids)}+")
        prefix = "✓ " if success else "⚠ "
        self.statusBar().showMessage(f"{prefix}WinGet [{pkg_id}]: {msg}", 7000)

    @Slot(int, int)
    def _on_winget_batch_finished(self, installed: int, total: int) -> None:
        self.statusBar().showMessage(
            self.tr(f"Instalare finalizată: {installed} din {total} aplicații instalate cu succes.", f"Installation finished: {installed} of {total} apps installed successfully."),
            8000
        )

    def start_winget_installed_check(self) -> None:
        """Check installed packages without blocking the UI or touching it from a worker."""
        if getattr(self, "_winget_detect_running", False):
            return
        self._winget_detect_running = True

        started = self.run_background_task(
            lambda: check_installed_packages([p["id"] for p in WINGET_CATALOG]),
            self._on_winget_installed_detected,
            silent=True,
            on_failed=self._winget_installed_detection_failed,
        )
        if not started:
            self._winget_detect_running = False

    @Slot(str)
    def _winget_installed_detection_failed(self, _error: str) -> None:
        self._winget_detect_running = False

    @Slot(object)
    def _on_winget_installed_detected(self, installed_set: object) -> None:
        self._winget_detect_running = False
        if isinstance(installed_set, set):
            self.winget_installed_ids.update(installed_set)
            for pid in installed_set:
                self._update_winget_card_btn(pid)
            if hasattr(self, "winget_count_badge") and self.winget_count_badge:
                cnt = len(self.winget_installed_ids)
                total = len(WINGET_CATALOG)
                self.winget_count_badge.setText(
                    self.tr(f"{cnt} instalate / {total} total", f"{cnt} installed / {total} total")
                )
            if hasattr(self, "apps_card") and self.apps_card:
                self.apps_card.update_data(big_stat=f"{len(self.winget_installed_ids)}+")

    def _update_winget_card_btn(self, pkg_id: str, success: Optional[bool] = None, msg: str = "") -> None:
        for pkg, _card, chk, btn in getattr(self, "winget_item_cards", []):
            if pkg["id"] == pkg_id:
                if pkg_id in self.winget_installing_ids:
                    btn.setText("⏳ " + self.tr("În curs...", "Installing..."))
                    btn.setEnabled(False)
                    btn.setStyleSheet("")
                elif pkg_id in self.winget_installed_ids or success is True:
                    btn.setText("✓ " + self.tr("Instalat", "Installed"))
                    btn.setEnabled(False)
                    btn.setStyleSheet("color: #10b981; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.35); background: rgba(16, 185, 129, 0.10); border-radius: 9px;")
                    chk.setChecked(False)
                    chk.setEnabled(False)
                elif success is False:
                    btn.setText("⚠ " + self.tr("Reîncearcă", "Retry"))
                    btn.setEnabled(True)
                    btn.setStyleSheet("color: #ef4444; font-weight: 700; border: 1px solid rgba(239, 68, 68, 0.35);")
                    chk.setEnabled(True)
                else:
                    btn.setText("⬇ " + self.tr("Instalează", "Install"))
                    btn.setEnabled(True)
                    btn.setStyleSheet("")
                    chk.setEnabled(True)
                break

    def page_startup(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 10)
        layout.setSpacing(12)

        # Header Hero Card for Startup Management
        hero = QFrame(objectName="heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(16)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        cat_tag = QLabel(self.tr("VITEZĂ BOOT • GESTIUNE STARTUP", "BOOT SPEED • STARTUP MANAGEMENT"))
        cat_tag.setObjectName("cardCategory")
        cat_tag.setStyleSheet(f"color: {'#38bdf8' if self.dark_mode else '#000000'}; font-weight: 800; letter-spacing: 1.5px;")
        header_text.addWidget(cat_tag)

        title = QLabel(self.tr("Programe de Pornire (Startup)", "Startup Programs"), objectName="heroTitle")
        subtitle = QLabel(
            self.tr("Aplicațiile și serviciile care pornesc automat odată cu Windows. Dezactivează aplicațiile inutile pentru un boot mult mai rapid.",
                    "Applications and services that launch automatically with Windows. Disable unused apps for faster boot."),
            objectName="heroSub"
        )
        subtitle.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        hero_layout.addLayout(header_text, 1)

        # Right side: Count badge and Refresh
        right_hero = QVBoxLayout()
        right_hero.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_hero.setSpacing(8)

        self.startup_count_badge = QLabel(objectName="actionPillBtn")
        right_hero.addWidget(self.startup_count_badge)

        refresh_btn = QPushButton("⟲ " + self.tr("Reîmprospătează", "Refresh"), objectName="softCardBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._refresh_startup_entries)
        right_hero.addWidget(refresh_btn)

        hero_layout.addLayout(right_hero)
        layout.addWidget(hero)

        # Smooth Scroll Area with taskItemRow cards
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_widget = QWidget()
        self._startup_listing = QVBoxLayout(content_widget)
        self._startup_listing.setContentsMargins(2, 2, 8, 12)
        self._startup_listing.setSpacing(8)
        self._startup_loading_label = QLabel(
            self.tr("Se încarcă aplicațiile...", "Loading startup applications...")
        )
        self._startup_loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._startup_loading_label.setMinimumHeight(100)
        self._startup_listing.addWidget(self._startup_loading_label)
        self._startup_page_generation = getattr(self, "_startup_page_generation", 0) + 1

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        return page

    def _refresh_startup_entries(self) -> None:
        if not hasattr(self, "_startup_listing") or self._startup_listing is None:
            return
        if getattr(self, "_startup_refresh_running", False):
            return

        self._startup_refresh_running = True
        generation = self._startup_page_generation

        def fetch_entries() -> list[dict]:
            raw_entries = get_startup_entries()
            seen = set()
            entries = []
            for entry in raw_entries:
                key = (entry.get("name", "").lower(), entry.get("command", "").lower())
                if key not in seen:
                    seen.add(key)
                    entries.append(entry)
            return entries

        def on_done(result: object) -> None:
            self._startup_refresh_running = False
            if generation != self._startup_page_generation:
                QTimer.singleShot(0, self._refresh_startup_entries)
                return
            if not isinstance(result, list):
                return
            self._render_startup_entries(result)

        def on_failed(_error: str) -> None:
            self._startup_refresh_running = False
            if generation != self._startup_page_generation:
                QTimer.singleShot(0, self._refresh_startup_entries)
                return
            if self._startup_loading_label is not None:
                self._startup_loading_label.setText(
                    self.tr("Nu s-au putut încărca aplicațiile Startup.", "Startup applications could not be loaded.")
                )

        if not self.run_background_task(fetch_entries, on_done, silent=True, on_failed=on_failed):
            self._startup_refresh_running = False

    def _render_startup_entries(self, entries: list[dict]) -> None:
        while self._startup_listing.count():
            item = self._startup_listing.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

        self._startup_loading_label = None
        self._startup_entries = entries
        self._startup_status_labels: dict[str, QLabel] = {}
        total = len(entries)
        enabled_count = sum(1 for e in entries if e.get("enabled"))

        if hasattr(self, "startup_count_badge") and self.startup_count_badge:
            self.startup_count_badge.setText(
                self.tr(f"{enabled_count} active / {total} total", f"{enabled_count} active / {total} total")
            )

        is_dark = self.dark_mode
        badge_bg = "rgba(59, 130, 246, 0.12)" if is_dark else "rgba(37, 99, 235, 0.08)"
        badge_color = "#00d2ff" if is_dark else "#1685e8"
        badge_border = "rgba(59, 130, 246, 0.25)" if is_dark else "rgba(37, 99, 235, 0.20)"

        if not entries:
            empty_lbl = QLabel(self.tr("Nicio aplicație nu este configurată pentru pornire automată.", "No applications are set to run at startup."), objectName="taskDesc")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._startup_listing.addWidget(empty_lbl)
        else:
            for entry in entries:
                row = QFrame(objectName="taskItemRow")
                row.setFixedHeight(72)
                row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(14, 10, 14, 10)
                row_layout.setSpacing(12)

                badge = QLabel("▷", objectName="cardBadge")
                badge.setFixedSize(36, 36)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(f"font-size: 13pt; color: {badge_color}; background: {badge_bg}; border-radius: 8px; border: 1px solid {badge_border}; font-weight: bold;")
                row_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

                text_col = QVBoxLayout()
                text_col.setSpacing(2)

                top_line = QHBoxLayout()
                top_line.setSpacing(8)
                name_lbl = QLabel(entry["name"], objectName="taskTitle")
                top_line.addWidget(name_lbl)

                status_lbl = QLabel()
                status_lbl.setText(self.tr("Se verifică...", "Checking..."))
                status_lbl.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")
                self._startup_status_labels[entry["id"]] = status_lbl
                top_line.addWidget(status_lbl)
                top_line.addStretch()
                text_col.addLayout(top_line)

                desc_lbl = QLabel(f"{entry['location']} • {entry['command']}", objectName="taskDesc")
                desc_lbl.setWordWrap(True)
                text_col.addWidget(desc_lbl)
                row_layout.addLayout(text_col, 1)

                # Action buttons: Open (Deschide) and Close (Inchide)
                action_box = QHBoxLayout()
                action_box.setSpacing(6)

                btn_open = QPushButton("▷ " + self.tr("Deschide", "Open"), objectName="softCardBtn")
                btn_open.setToolTip(self.tr("Pornește această aplicație acum", "Launch this application now"))
                btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_open.clicked.connect(lambda _c=False, cmd=entry["command"]: self.launch_app_action(cmd))
                action_box.addWidget(btn_open)

                btn_kill = QPushButton("✕ " + self.tr("Închide", "Close"), objectName="softCardBtn")
                btn_kill.setToolTip(self.tr("Oprește procesul care rulează în fundal", "Kill running background process"))
                btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_kill.clicked.connect(lambda _c=False, cmd=entry["command"]: self.close_app_action(cmd))
                action_box.addWidget(btn_kill)

                row_layout.addLayout(action_box)

                # Switch for automatic Windows startup
                switch = AnimatedToggleSwitch(row, checked=bool(entry["enabled"]))
                switch.setToolTip(self.tr("Pornire automată cu Windows", "Auto-start with Windows"))
                switch.toggled.connect(lambda checked, item=entry, control=switch: self.on_startup_toggled_page(checked, item, control))
                row_layout.addWidget(switch, alignment=Qt.AlignmentFlag.AlignVCenter)

                self._startup_listing.addWidget(row)

        self._startup_listing.addStretch()
        self._refresh_startup_process_states(entries, self._startup_page_generation)

    def _refresh_startup_process_states(self, entries: list[dict], page_generation: int) -> None:
        self._startup_status_generation = getattr(self, "_startup_status_generation", 0) + 1
        status_generation = self._startup_status_generation

        def fetch_states() -> dict[str, bool]:
            return {
                entry["id"]: is_startup_app_running(entry.get("command", ""))
                for entry in entries
            }

        def on_done(result: object) -> None:
            if (
                page_generation != self._startup_page_generation
                or status_generation != self._startup_status_generation
                or not isinstance(result, dict)
            ):
                return
            for entry_id, is_running in result.items():
                label = self._startup_status_labels.get(entry_id)
                if label is None:
                    continue
                if is_running:
                    label.setText("● " + self.tr("Rulează acum", "Running now"))
                    label.setStyleSheet("font-size: 8pt; color: #10b981; font-weight: 700;")
                else:
                    label.setText("○ " + self.tr("Nu rulează", "Not running"))
                    label.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")

        def on_failed(_error: str) -> None:
            if page_generation != self._startup_page_generation:
                return
            for label in self._startup_status_labels.values():
                label.setText(self.tr("Stare indisponibilă", "Status unavailable"))
                label.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")

        self.run_background_task(fetch_states, on_done, silent=True, on_failed=on_failed)

    def launch_app_action(self, command: str) -> None:
        msg = launch_startup_app(command)
        self.statusBar().showMessage(msg, 5000)
        QTimer.singleShot(1500, self._refresh_startup_entries)

    def close_app_action(self, command: str) -> None:
        msg = close_startup_app(command)
        self.statusBar().showMessage(msg, 5000)
        QTimer.singleShot(1000, self._refresh_startup_entries)

    def on_startup_toggled_page(self, checked: bool, entry: dict, control: AnimatedToggleSwitch) -> None:
        previous = bool(entry.get("enabled"))
        result = set_startup_entry_enabled(entry, checked)
        failed = "eroare" in result.lower() or "failed" in result.lower() or "eșuat" in result.lower()
        if failed:
            control.blockSignals(True)
            control.setChecked(previous)
            control.blockSignals(False)
            self.statusBar().showMessage(self.tr(f"Eroare: {result}", f"Error: {result}"), 5000)
        else:
            entry["enabled"] = checked
            self.statusBar().showMessage(self.tr(f"{entry['name']}: {result}", f"{entry['name']}: {result}"), 4000)
            entries = getattr(self, "_startup_entries", [])
            total = len(entries)
            en = sum(1 for e in entries if e.get("enabled"))
            if hasattr(self, "startup_count_badge") and self.startup_count_badge:
                self.startup_count_badge.setText(self.tr(f"{en} active / {total} total", f"{en} active / {total} total"))
            if hasattr(self, "startup_card") and self.startup_card:
                self.startup_card.update_data(
                    big_stat=f"{en} / {total}",
                    stat_sub=self.tr("Aplicații active la pornire", "Active autorun apps"),
                )

    def page_apps(self) -> QWidget:
        page, layout = self.page_shell(
            self.tr("Utilitare & Dezinstalare Programe", "Utilities & App Uninstaller"),
            self.tr("Gestionează programele instalate, dezinstalează aplicații, curăță cache-ul și reziduurile de sistem.",
                    "Manage installed programs, uninstall apps, clean browser cache and system residue.")
        )
        card = self.card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        # Header row: Title + Search bar + Count badge
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        sec_title = QLabel(self.tr("APLICAȚII INSTALATE & DEZINSTALARE", "INSTALLED APPS & UNINSTALL"))
        sec_title.setObjectName("cardTitle")
        header_row.addWidget(sec_title)

        header_row.addStretch()

        self.installed_apps_search = QLineEdit()
        self.installed_apps_search.setPlaceholderText("🔍  " + self.tr("Caută program instalat...", "Search installed app..."))
        self.installed_apps_search.setFixedWidth(240)
        self.installed_apps_search.setFixedHeight(30)
        self.installed_apps_search.textChanged.connect(self.on_installed_app_search)
        header_row.addWidget(self.installed_apps_search)

        self.installed_apps_count_lbl = QLabel(objectName="actionPillBtn")
        header_row.addWidget(self.installed_apps_count_lbl)

        card_layout.addLayout(header_row)

        # Installed programs list
        self.installed_apps_widget = QListWidget()
        self.installed_apps_widget.setAlternatingRowColors(True)
        self.installed_apps_widget.setMinimumHeight(320)
        self.installed_apps_widget.itemSelectionChanged.connect(self.on_installed_app_selected)
        self.installed_apps_widget.itemDoubleClicked.connect(lambda _it: self.trigger_uninstall_selected())
        card_layout.addWidget(self.installed_apps_widget, 1)

        # Uninstaller Actions Row
        uninst_row = QHBoxLayout()
        uninst_row.setSpacing(8)

        self.uninstall_btn = QPushButton("🗑️ " + self.tr("Dezinstalează programul selectat", "Uninstall selected app"), objectName="primary")
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style_primary(self.uninstall_btn)
        self.uninstall_btn.clicked.connect(self.trigger_uninstall_selected)
        uninst_row.addWidget(self.uninstall_btn, 1)

        appwiz_btn = QPushButton("⚙️ " + self.tr("Panou Dezinstalare Windows", "Windows Uninstall Panel"), objectName="softCardBtn")
        appwiz_btn.setToolTip(self.tr("Deschide panoul oficial Windows pentru dezinstalare Programe și Caracteristici", "Open official Windows Installed Apps / Programs and Features panel"))
        appwiz_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        appwiz_btn.clicked.connect(open_windows_uninstaller_panel)
        uninst_row.addWidget(appwiz_btn, 1)

        refresh_apps_btn = QPushButton("⟲ " + self.tr("Reîmprospătează lista", "Refresh list"), objectName="softCardBtn")
        refresh_apps_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_apps_btn.clicked.connect(self.refresh_installed_programs)
        uninst_row.addWidget(refresh_apps_btn)

        card_layout.addLayout(uninst_row)

        # Utility Shortcuts Row
        utility_row = QHBoxLayout()
        utility_row.setSpacing(8)

        startup_btn = QPushButton(self.tr("Programe Startup", "Startup programs"), objectName="softCardBtn")
        startup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        startup_btn.clicked.connect(self.open_startup)
        utility_row.addWidget(startup_btn, 1)

        cleanup_btn = QPushButton(self.tr("Curăță reziduuri Windows Update", "Clean Windows Update residue"), objectName="softCardBtn")
        cleanup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cleanup_btn.clicked.connect(self.confirm_update_cleanup)
        utility_row.addWidget(cleanup_btn, 1)

        activation_btn = QPushButton(self.tr("Deschide Activatorul Massgravel", "Open Massgravel Activator"), objectName="softCardBtn")
        activation_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        activation_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://massgrave.dev/")))
        utility_row.addWidget(activation_btn, 1)

        card_layout.addLayout(utility_row)

        # Browser Cache Cleaning Row
        browser_row = QHBoxLayout()
        browser_row.setSpacing(8)
        for browser, label in (("chrome", "Chrome"), ("edge", "Edge"), ("firefox", "Firefox")):
            cache_button = QPushButton(self.tr(f"Curăță {label}", f"Clean {label}"), objectName="softCardBtn")
            cache_button.setCursor(Qt.CursorShape.PointingHandCursor)
            cache_button.clicked.connect(lambda _checked=False, name=browser: self.confirm_browser_cleanup(name))
            browser_row.addWidget(cache_button)
        card_layout.addLayout(browser_row)

        layout.addWidget(card, 1)

        # Populate list
        self.refresh_installed_programs()

        return page

    def refresh_installed_programs(self) -> None:
        """Query real Windows installed programs and populate the list widget."""
        if not hasattr(self, "installed_apps_widget") or self.installed_apps_widget is None:
            return

        self.installed_programs_list = [
            {
                "name": app.name,
                "publisher": app.publisher,
                "version": app.version,
                "uninstall_cmd": app.uninstall_command,
                "product_code": app.product_code,
            }
            for app in get_installed_applications()
        ]
        self.populate_installed_programs_list()

    def populate_installed_programs_list(self) -> None:
        if not hasattr(self, "installed_apps_widget") or self.installed_apps_widget is None:
            return

        self.installed_apps_widget.clear()
        query = (self.installed_apps_search.text() if self.installed_apps_search else "").strip().lower()

        visible_count = 0
        for prog in self.installed_programs_list:
            name = prog["name"]
            publisher = prog.get("publisher", "")
            version = prog.get("version", "")
            search_str = f"{name} {publisher} {version}".lower()

            if query and query not in search_str:
                continue

            visible_count += 1
            ver_tag = f" v{version}" if version else ""
            pub_tag = f"  —  {publisher}" if publisher else "  —  Aplicație Windows"
            item_text = f"📦  {name}{ver_tag}{pub_tag}"

            item = QListWidgetItem(item_text)
            item.setToolTip(f"{name}\nComandă dezinstalare: {prog.get('uninstall_cmd')}")
            item.setData(Qt.ItemDataRole.UserRole, prog)
            self.installed_apps_widget.addItem(item)

        if hasattr(self, "installed_apps_count_lbl") and self.installed_apps_count_lbl:
            self.installed_apps_count_lbl.setText(
                self.tr(f"{visible_count} aplicații", f"{visible_count} apps")
            )

        if hasattr(self, "uninstall_btn") and self.uninstall_btn:
            self.uninstall_btn.setEnabled(False)
            self.uninstall_btn.setText("🗑️ " + self.tr("Dezinstalează programul selectat", "Uninstall selected app"))

    def on_installed_app_search(self, _text: str) -> None:
        self.populate_installed_programs_list()

    def on_installed_app_selected(self) -> None:
        if not hasattr(self, "installed_apps_widget") or not self.installed_apps_widget:
            return
        items = self.installed_apps_widget.selectedItems()
        if not items:
            if hasattr(self, "uninstall_btn") and self.uninstall_btn:
                self.uninstall_btn.setEnabled(False)
                self.uninstall_btn.setText("🗑️ " + self.tr("Dezinstalează programul selectat", "Uninstall selected app"))
            return

        prog = items[0].data(Qt.ItemDataRole.UserRole)
        if prog and hasattr(self, "uninstall_btn") and self.uninstall_btn:
            self.uninstall_btn.setEnabled(True)
            short_name = prog['name'][:22] + "..." if len(prog['name']) > 22 else prog['name']
            self.uninstall_btn.setText("🗑️ " + self.tr(f"Dezinstalează {short_name}", f"Uninstall {short_name}"))

    def trigger_uninstall_selected(self) -> None:
        if not hasattr(self, "installed_apps_widget") or not self.installed_apps_widget:
            return
        items = self.installed_apps_widget.selectedItems()
        if not items:
            return

        prog = items[0].data(Qt.ItemDataRole.UserRole)
        if not prog or (not prog.get("uninstall_cmd") and not prog.get("product_code")):
            return

        if not self.confirm_uninstall_application(prog["name"]):
            return

        application = InstalledApplication(
            name=prog["name"],
            version=prog.get("version", ""),
            publisher=prog.get("publisher", ""),
            uninstall_command=prog.get("uninstall_cmd", ""),
            product_code=prog.get("product_code"),
        )
        try:
            launch_uninstaller(application)
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(
                self.tr(
                    f"Eroare la dezinstalarea {prog['name']}: {exc}",
                    f"Could not uninstall {prog['name']}: {exc}",
                ),
                10000,
            )
            return

        self.statusBar().showMessage(
            self.tr(
                f"Dezinstalatorul pentru {prog['name']} a fost pornit.",
                f"Uninstaller for {prog['name']} was launched.",
            ),
            6000,
        )
        QTimer.singleShot(3000, self.refresh_installed_programs)

    def confirm_uninstall_application(self, app_name: str) -> bool:
        dialog = QDialog(self, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setWindowTitle(self.tr("Dezinstalare aplicație", "Uninstall application"))
        dialog.setWindowIcon(self.windowIcon())
        dialog.setStyleSheet(self.styleSheet())
        dialog.setFixedWidth(440)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(16)

        title_row = QHBoxLayout()
        title = QLabel(self.tr("Dezinstalare aplicație", "Uninstall application"))
        title.setObjectName("cardTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        close_button = QPushButton("×")
        close_button.setObjectName("headerBtn")
        close_button.setFixedSize(32, 30)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(dialog.reject)
        title_row.addWidget(close_button)
        layout.addLayout(title_row)

        content = QHBoxLayout()
        content.setSpacing(14)
        icon = QLabel("!")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet(
            "background: rgba(245, 158, 11, 0.16);"
            "border: 1px solid rgba(245, 158, 11, 0.45);"
            "border-radius: 21px; color: #f59e0b;"
            "font-size: 20pt; font-weight: 700;"
        )
        content.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        message_layout = QVBoxLayout()
        message_layout.setSpacing(6)
        question = QLabel(
            self.tr(
                f"Dezinstalezi {app_name}?",
                f"Uninstall {app_name}?",
            )
        )
        question.setWordWrap(True)
        question.setStyleSheet("font-size: 11pt; font-weight: 700;")
        message_layout.addWidget(question)

        detail = QLabel(
            self.tr(
                "Va fi pornit dezinstalatorul oficial al programului.",
                "The application's official uninstaller will be launched.",
            )
        )
        detail.setObjectName("mutedLabel")
        detail.setWordWrap(True)
        message_layout.addWidget(detail)
        content.addLayout(message_layout, 1)
        layout.addLayout(content)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton(self.tr("Anulează", "Cancel"))
        cancel_button.setObjectName("softCardBtn")
        cancel_button.setMinimumWidth(110)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(dialog.reject)
        buttons.addWidget(cancel_button)

        uninstall_button = QPushButton(self.tr("Dezinstalează", "Uninstall"))
        uninstall_button.setObjectName("actionPillBtn")
        uninstall_button.setMinimumWidth(130)
        uninstall_button.setCursor(Qt.CursorShape.PointingHandCursor)
        uninstall_button.clicked.connect(dialog.accept)
        uninstall_button.setDefault(True)
        buttons.addWidget(uninstall_button)
        layout.addLayout(buttons)

        dialog.adjustSize()
        dialog.move(self.geometry().center() - dialog.rect().center())
        confirmed = dialog.exec() == QDialog.DialogCode.Accepted
        dialog.deleteLater()
        return confirmed

    def page_services(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 10)
        layout.setSpacing(12)

        # 1. Header Hero Card for Services Hub
        hero = QFrame(objectName="heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(16)

        left_hero = QVBoxLayout()
        left_hero.setSpacing(4)
        tag = QLabel(self.tr("SERVICII WINDOWS • CONTROL PARAMETRI ÎN TIMP REAL", "WINDOWS SERVICES • LIVE PARAMETERS CONTROL"))
        tag.setObjectName("cardCategory")
        tag.setStyleSheet(f"color: {'#38bdf8' if self.dark_mode else '#000000'}; font-weight: 800; letter-spacing: 1.5px;")
        left_hero.addWidget(tag)

        h_title = QLabel(self.tr("Servicii & Procese de Fundal (Octane Engine)", "Windows Services & Background Processes (Octane Engine)"), objectName="heroTitle")
        left_hero.addWidget(h_title)

        h_sub = QLabel(
            self.tr(
                "Monitorizează parametrii reali de execuție ai serviciilor Windows. Activează sau dezactivează procesele consumatoare de resurse în deplină siguranță.",
                "Monitor real Windows service parameters. Safely enable or disable background resource-heavy services in real time."
            ),
            objectName="heroSub"
        )
        h_sub.setWordWrap(True)
        left_hero.addWidget(h_sub)
        hero_layout.addLayout(left_hero, 1)

        # Right side of Hero: Summary Badge and Quick Actions
        right_hero = QVBoxLayout()
        right_hero.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_hero.setSpacing(8)

        self.services_summary_badge = QLabel(objectName="actionPillBtn")
        right_hero.addWidget(self.services_summary_badge, alignment=Qt.AlignmentFlag.AlignRight)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)

        gaming_btn = QPushButton("⚡ " + self.tr("Optimizare Gaming", "Gaming Preset"), objectName="softCardBtn")
        gaming_btn.setToolTip(self.tr("Dezactivează telemetria, SysMain, erorile și registry la distanță pentru performanță maximă", "Disables telemetry, SysMain, error reporting, and remote registry for top performance"))
        gaming_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gaming_btn.clicked.connect(self.apply_gaming_services_preset)
        actions_row.addWidget(gaming_btn)

        refresh_btn = QPushButton("⟲ " + self.tr("Reîmprospătează", "Refresh"), objectName="softCardBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_services_page)
        actions_row.addWidget(refresh_btn)

        right_hero.addLayout(actions_row)
        hero_layout.addLayout(right_hero)
        layout.addWidget(hero)

        # 2. Main Smooth Scroll Area containing the Services List
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 2, 8, 12)
        content_layout.setSpacing(8)

        self.service_status_labels.clear()
        self.service_switches.clear()

        is_dark = self.dark_mode
        badge_bg = "rgba(59, 130, 246, 0.12)" if is_dark else "rgba(37, 99, 235, 0.08)"
        badge_color = "#00d2ff" if is_dark else "#1685e8"
        badge_border = "rgba(59, 130, 246, 0.25)" if is_dark else "rgba(37, 99, 235, 0.20)"

        for title, service_name, icon, desc_ro, desc_en in SERVICES_CATALOG:
            item_frame = QFrame(objectName="taskItemRow")
            item_frame.setFixedHeight(72)
            item_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row = QHBoxLayout(item_frame)
            row.setContentsMargins(14, 10, 14, 10)
            row.setSpacing(12)

            # Left badge
            badge = QLabel(icon, objectName="cardBadge")
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"font-size: 13pt; color: {badge_color}; background: {badge_bg}; border-radius: 8px; border: 1px solid {badge_border}; font-weight: bold;")
            row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

            # Center Info Column
            text_col = QVBoxLayout()
            text_col.setSpacing(2)

            top_line = QHBoxLayout()
            top_line.setSpacing(8)
            lbl_title = QLabel(title, objectName="taskTitle")
            top_line.addWidget(lbl_title)

            id_pill = QLabel(service_name)
            id_pill.setStyleSheet("font-size: 7.5pt; color: #38bdf8; background: rgba(56, 189, 248, 0.10); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 5px; padding: 1px 6px; font-weight: 600;")
            top_line.addWidget(id_pill)

            lbl_status = QLabel(self.tr("Se încarcă...", "Loading..."))
            lbl_status.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")
            top_line.addWidget(lbl_status)
            top_line.addStretch()
            text_col.addLayout(top_line)

            lbl_desc = QLabel(self.tr(desc_ro, desc_en), objectName="taskDesc")
            lbl_desc.setWordWrap(True)
            text_col.addWidget(lbl_desc)

            row.addLayout(text_col, 1)

            switch = AnimatedToggleSwitch(item_frame, checked=False)
            switch.setEnabled(False)
            switch.toggled.connect(lambda checked, s=service_name: self.on_service_switch_toggled(s, checked))
            row.addWidget(switch, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.service_status_labels[service_name] = lbl_status
            self.service_switches[service_name] = switch

            content_layout.addWidget(item_frame)

        # 3. Dedicated Windows Update Card
        wu_frame = QFrame(objectName="taskItemRow")
        wu_frame.setFixedHeight(72)
        wu_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        wu_row = QHBoxLayout(wu_frame)
        wu_row.setContentsMargins(14, 10, 14, 10)
        wu_row.setSpacing(12)

        wu_badge = QLabel("❚❚", objectName="cardBadge")
        wu_badge.setFixedSize(36, 36)
        wu_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wu_badge.setStyleSheet("font-size: 11pt; color: #f59e0b; background: rgba(245, 158, 11, 0.12); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.25); font-weight: bold;")
        wu_row.addWidget(wu_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        wu_text = QVBoxLayout()
        wu_text.setSpacing(2)

        wu_top = QHBoxLayout()
        wu_top.setSpacing(8)
        wu_title = QLabel(self.tr("Pauzează Windows Update", "Pause Windows Update"), objectName="taskTitle")
        wu_top.addWidget(wu_title)

        wu_id = QLabel("wuauserv")
        wu_id.setStyleSheet("font-size: 7.5pt; color: #f59e0b; background: rgba(245, 158, 11, 0.10); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 5px; padding: 1px 6px; font-weight: 600;")
        wu_top.addWidget(wu_id)

        self.wu_status_lbl = QLabel(self.tr("Se încarcă...", "Loading..."))
        self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")

        wu_top.addWidget(self.wu_status_lbl)
        wu_top.addStretch()
        wu_text.addLayout(wu_top)

        wu_desc = QLabel(self.tr("Oprește descărcările automate și verificările de actualizări în timpul sesiunilor active.",
                                "Pauses automatic update downloads and background checks during active sessions."), objectName="taskDesc")
        wu_desc.setWordWrap(True)
        wu_text.addWidget(wu_desc)
        wu_row.addLayout(wu_text, 1)

        self.wu_switch = AnimatedToggleSwitch(wu_frame, checked=False)
        self.wu_switch.setEnabled(False)
        self.wu_switch.toggled.connect(self.on_windows_update_toggled)
        wu_row.addWidget(self.wu_switch, alignment=Qt.AlignmentFlag.AlignVCenter)

        content_layout.addWidget(wu_frame)
        content_layout.addStretch()

        self.services_summary_badge.setText(self.tr("Se încarcă serviciile...", "Loading services..."))

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        return page

    def refresh_services_page(self) -> None:
        """Query Windows service states in the background and update the page when ready."""
        if getattr(self, "_services_refresh_running", False):
            return
        self._services_refresh_running = True

        for switch in self.service_switches.values():
            switch.setEnabled(False)
        if hasattr(self, "wu_switch") and self.wu_switch:
            self.wu_switch.setEnabled(False)

        def fetch_all():
            results = {}
            for _title, sname, _icon, _ro, _en in SERVICES_CATALOG:
                results[sname] = get_service_info(sname)
            results["wuauserv"] = get_service_info("wuauserv")
            return results

        def on_done(results_obj):
            self._services_refresh_running = False
            if not isinstance(results_obj, dict):
                return
            enabled_cnt = 0
            disabled_cnt = 0
            stopped_cnt = 0

            for sname, info in results_obj.items():
                if sname == "wuauserv":
                    if hasattr(self, "wu_switch") and self.wu_switch:
                        is_paused = not info.get("enabled", True)
                        self.wu_switch.blockSignals(True)
                        self.wu_switch.setChecked(is_paused)
                        self.wu_switch.blockSignals(False)
                        self.wu_switch.setEnabled(True)
                    if hasattr(self, "wu_status_lbl") and self.wu_status_lbl:
                        if not info.get("enabled", True):
                            self.wu_status_lbl.setText("❚❚ " + self.tr("Actualizări Pauzate (Dezactivat)", "Updates Paused (Disabled)"))
                            self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #f59e0b; font-weight: 700;")
                        else:
                            st = self.tr("Active (Rulează)", "Active (Running)") if info.get("running") else self.tr("Active (Manual)", "Active (Manual)")
                            self.wu_status_lbl.setText("● " + st)
                            self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #10b981; font-weight: 700;")
                    continue

                lbl = self.service_status_labels.get(sname)
                sw = self.service_switches.get(sname)

                is_en = bool(info.get("enabled"))
                is_run = bool(info.get("running"))

                if is_run:
                    enabled_cnt += 1
                elif is_en:
                    stopped_cnt += 1
                else:
                    disabled_cnt += 1

                if sw is not None:
                    sw.blockSignals(True)
                    sw.setChecked(is_en)
                    sw.blockSignals(False)
                    sw.setEnabled(True)

                if lbl is not None:
                    if is_run:
                        lbl.setText("● " + self.tr(f"Rulează ({info.get('start_type_text')})", f"Running ({info.get('start_type_text')})"))
                        lbl.setStyleSheet("font-size: 8pt; color: #10b981; font-weight: 700;")
                    elif not is_en:
                        lbl.setText("○ " + self.tr("Oprit • Dezactivat", "Stopped • Disabled"))
                        lbl.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")
                    else:
                        lbl.setText("◐ " + self.tr(f"Oprit ({info.get('start_type_text')})", f"Stopped ({info.get('start_type_text')})"))
                        lbl.setStyleSheet("font-size: 8pt; color: #38bdf8; font-weight: 600;")

            if hasattr(self, "services_summary_badge") and self.services_summary_badge:
                self.services_summary_badge.setText(
                    self.tr(f"● {enabled_cnt + stopped_cnt} Active • ○ {disabled_cnt} Dezactivate",
                            f"● {enabled_cnt + stopped_cnt} Active • ○ {disabled_cnt} Disabled")
                )

        def on_failed(_error: str) -> None:
            self._services_refresh_running = False
            for switch in self.service_switches.values():
                switch.setEnabled(False)
            if hasattr(self, "wu_switch") and self.wu_switch:
                self.wu_switch.setEnabled(False)
            if hasattr(self, "services_summary_badge") and self.services_summary_badge:
                self.services_summary_badge.setText(
                    self.tr("Serviciile nu au putut fi încărcate", "Services could not be loaded")
                )

        if not self.run_background_task(fetch_all, on_done, silent=True, on_failed=on_failed):
            self._services_refresh_running = False

    def on_service_switch_toggled(self, service_name: str, enabled: bool) -> None:
        sw = self.service_switches.get(service_name)
        if sw:
            sw.setEnabled(False)
        lbl = self.service_status_labels.get(service_name)
        if lbl:
            lbl.setText(self.tr("Se aplică...", "Applying..."))
            lbl.setStyleSheet("font-size: 8pt; color: #f59e0b; font-weight: 600;")

        self.statusBar().showMessage(
            self.tr(f"Se modifică starea serviciului {service_name}...", f"Updating {service_name} service..."),
            4000,
        )

        def task():
            res = set_windows_service_state(service_name, enabled)
            fresh_info = get_service_info(service_name)
            return res, fresh_info

        def on_done(result_tuple):
            if sw:
                sw.setEnabled(True)
            if not isinstance(result_tuple, tuple):
                return
            msg, info = result_tuple
            is_en = bool(info.get("enabled"))
            is_run = bool(info.get("running"))

            if sw:
                sw.blockSignals(True)
                sw.setChecked(is_en)
                sw.blockSignals(False)

            if lbl:
                if is_run:
                    lbl.setText("● " + self.tr(f"Rulează ({info.get('start_type_text')})", f"Running ({info.get('start_type_text')})"))
                    lbl.setStyleSheet("font-size: 8pt; color: #10b981; font-weight: 700;")
                elif not is_en:
                    lbl.setText("○ " + self.tr("Oprit • Dezactivat", "Stopped • Disabled"))
                    lbl.setStyleSheet("font-size: 8pt; color: #94a3b8; font-weight: 600;")
                else:
                    lbl.setText("◐ " + self.tr(f"Oprit ({info.get('start_type_text')})", f"Stopped ({info.get('start_type_text')})"))
                    lbl.setStyleSheet("font-size: 8pt; color: #38bdf8; font-weight: 600;")

            # Update header summary badge
            if hasattr(self, "services_summary_badge") and self.services_summary_badge:
                active_c = sum(1 for s in self.service_switches.values() if s.isChecked())
                disabled_c = len(self.service_switches) - active_c
                self.services_summary_badge.setText(
                    self.tr(f"● {active_c} Active • ○ {disabled_c} Dezactivate",
                            f"● {active_c} Active • ○ {disabled_c} Disabled")
                )

            self.statusBar().showMessage(str(msg), 7000)

        self.run_background_task(task, on_done, silent=True)

    def on_windows_update_toggled(self, paused: bool) -> None:
        if hasattr(self, "wu_switch") and self.wu_switch:
            self.wu_switch.setEnabled(False)
        if hasattr(self, "wu_status_lbl") and self.wu_status_lbl:
            self.wu_status_lbl.setText(self.tr("Se aplică...", "Applying..."))
            self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #f59e0b; font-weight: 600;")

        def task():
            msg = set_windows_update_paused(paused)
            fresh = get_service_info("wuauserv")
            return msg, fresh

        def on_done(res):
            if hasattr(self, "wu_switch") and self.wu_switch:
                self.wu_switch.setEnabled(True)
            if not isinstance(res, tuple):
                return
            msg, info = res
            is_paused = not info.get("enabled", True)
            if hasattr(self, "wu_switch") and self.wu_switch:
                self.wu_switch.blockSignals(True)
                self.wu_switch.setChecked(is_paused)
                self.wu_switch.blockSignals(False)
            if hasattr(self, "wu_status_lbl") and self.wu_status_lbl:
                if is_paused:
                    self.wu_status_lbl.setText("❚❚ " + self.tr("Actualizări Pauzate (Dezactivat)", "Updates Paused (Disabled)"))
                    self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #f59e0b; font-weight: 700;")
                else:
                    st = self.tr("Active (Rulează)", "Active (Running)") if info.get("running") else self.tr("Active (Manual)", "Active (Manual)")
                    self.wu_status_lbl.setText("● " + st)
                    self.wu_status_lbl.setStyleSheet("font-size: 8pt; color: #10b981; font-weight: 700;")
            self.statusBar().showMessage(str(msg), 7000)

        self.run_background_task(task, on_done, silent=True)

    def apply_gaming_services_preset(self) -> None:
        """One-click gaming preset: disables telemetry, SysMain, Delivery Optimization, remote registry, error reporting, maps."""
        gaming_targets = ["DiagTrack", "SysMain", "DoSvc", "RemoteRegistry", "WerSvc", "MapsBroker"]
        self.statusBar().showMessage(
            self.tr("Se aplică profilul de servicii pentru Gaming...", "Applying Gaming services profile..."),
            5000
        )

        def task():
            results = []
            for sname in gaming_targets:
                res = set_windows_service_state(sname, False)
                results.append(res)
            return results

        def on_done(_res):
            self.refresh_services_page()
            self.statusBar().showMessage(
                self.tr("Profilul de servicii pentru Gaming a fost aplicat cu succes!", "Gaming services profile applied successfully!"),
                8000
            )

        self.run_background_task(task, on_done, silent=True)

    def page_settings(self) -> QWidget:
        page, layout = self.page_shell(self.tr("Setări", "Settings"), self.tr("Personalizează modul în care funcționează VATRIXTweaker.", "Customize how VATRIXTweaker works."))
        background_card = self.card(); background_layout = QHBoxLayout(background_card); background_text = QVBoxLayout()
        background_text.addWidget(QLabel(self.tr("Rulare în fundal", "Background mode"), objectName="cardTitle"))
        background_text.addWidget(QLabel(self.tr("Păstrează VATRIXTweaker activ în zona de notificări când închizi fereastra.", "Keep VATRIXTweaker running in the tray when you close the window."), objectName="muted"))
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
        result = flush_ram()
        self.statusBar().showMessage(result, 6000)
        self.refresh_memory()
        if hasattr(self, "ram_card"):
            status = get_memory_status()
            total = status.get("total", 0) / 1024 ** 3
            used = status.get("used", 0) / 1024 ** 3
            pct = int((used / total * 100)) if total else 0
            self.ram_card.update_data(
                big_stat=f"{pct}%",
                stat_sub=self.tr(f"{used:.1f} GB folosiți din {total:.1f} GB", f"{used:.1f} GB used of {total:.1f} GB"),
                status_tag=self.tr("● RAM Optimizat", "● RAM Optimized"),
            )

    def run_selected(self) -> None:
        if self.running:
            return
        selected = [name for name, check in self.action_checks.items() if check.isChecked()]
        if not selected:
            self.statusBar().showMessage(self.tr("Selectează cel puțin o setare.", "Select at least one setting."), 5000)
            return
        self.current_run_selected = selected
        self.running = True

        if hasattr(self, "opt_apply_button") and self.opt_apply_button:
            self.opt_apply_button.setText("⏳ " + self.tr("Se aplică optimizările...", "Applying optimizations..."))
            self.opt_apply_button.setEnabled(False)
        if hasattr(self, "apply_button") and self.apply_button:
            self.apply_button.setText("⏳ " + self.tr("Se aplică...", "Applying..."))
            self.apply_button.setEnabled(False)

        self.worker_thread = QThread(self)
        self.worker = OptimizerWorker(self.profile, selected)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.thread_finished)
        self.worker_thread.start()

    @Slot(int, int, str, str)
    def on_progress(self, done: int, total: int, action: str, result: str) -> None:
        self.statusBar().showMessage(f"[{done}/{total}] {action}: {result}", 5000)
        if hasattr(self, "opt_apply_button") and self.opt_apply_button:
            self.opt_apply_button.setText(f"⏳ [{done}/{total}]...")

    @Slot(list)
    def on_finished(self, _results: list[str]) -> None:
        self.settings.setValue(f"applied/{self.profile}", ",".join(getattr(self, "current_run_selected", [])))
        self.settings.sync()
        if hasattr(self, "apply_button") and self.apply_button:
            self.apply_button.setVisible(False)
            self.apply_button.setEnabled(True)
            self.apply_button.setText(self.tr("Aplică optimizările", "Apply optimizations"))

        if hasattr(self, "opt_apply_button") and self.opt_apply_button:
            self.opt_apply_button.setText("✓ " + self.tr("Optimizări aplicate cu succes!", "Optimizations applied successfully!"))
            self.opt_apply_button.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981); "
                "color: #ffffff; border: 1px solid rgba(255,255,255,0.3); border-radius: 10px; font-weight: 700; padding: 8px 14px; }"
            )
            QTimer.singleShot(3500, self._reset_apply_button)

        self.statusBar().showMessage(self.tr("Optimizarea s-a terminat cu succes.", "Optimization finished successfully."), 8000)
        self.validate_selected_actions()

    def _reset_apply_button(self) -> None:
        if hasattr(self, "opt_apply_button") and self.opt_apply_button:
            self.opt_apply_button.setText("✦  " + self.tr("Aplică selecția", "Apply selection"))
            self.style_primary(self.opt_apply_button)
            self.opt_apply_button.setEnabled(True)

    @Slot(str)
    def on_failed(self, error: str) -> None:
        self.statusBar().showMessage(self.tr(f"Optimizarea a eșuat: {error}", f"Optimization failed: {error}"), 10000)

    @Slot()
    def thread_finished(self) -> None:
        self.running = False; self.worker = None; self.worker_thread = None

    def open_startup(self) -> None:
        self.show_page("Startup")

    def toggle_autostart(self, enabled: bool) -> None:
        result = set_autostart(enabled)
        self.settings.setValue("autostart", enabled)
        self.settings.sync()
        self.statusBar().showMessage(result, 5000)

    def run_background_task(
        self,
        task: Callable[[], object],
        on_finished: Callable[[object], None],
        silent: bool = False,
        on_failed: Callable[[str], None] | None = None,
    ) -> bool:
        if not silent and (self.running or self._maintenance_running or self._background_task_running):
            self.statusBar().showMessage(
                self.tr("O altă operație rulează deja în fundal.", "Another background operation is already running."),
                5000,
            )
            return False

        thread = QThread(self)
        worker = BackgroundTaskWorker(task)

        def deliver_failed(error: str) -> None:
            self._background_task_failed(error)
            if on_failed is not None:
                on_failed(error)

        dispatcher = BackgroundTaskDispatcher(
            on_finished,
            deliver_failed,
            self,
        )
        worker.moveToThread(thread)
        item = (thread, worker)
        if not hasattr(self, "_active_bg_workers"):
            self._active_bg_workers = []
        self._active_bg_workers.append(item)

        thread.started.connect(worker.run)
        worker.finished.connect(dispatcher.deliver_finished)
        worker.failed.connect(dispatcher.deliver_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        def cleanup_bg(t=thread, w=worker, pair=item):
            try:
                if pair in self._active_bg_workers:
                    self._active_bg_workers.remove(pair)
            except Exception:
                pass
            t.deleteLater()
            dispatcher.deleteLater()

        thread.finished.connect(cleanup_bg)
        thread.start()
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
        previous = not enabled
        self._pending_service = (control, previous)
        control.setEnabled(False)
        self.statusBar().showMessage(
            self.tr(f"Se modifică starea serviciului {service_name}...", f"Updating {service_name} service..."),
            4000,
        )
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
        self.statusBar().showMessage(
            self.tr("Curățarea reziduurilor Windows Update rulează în fundal...", "Windows Update residue cleanup is running in the background..."),
            6000,
        )
        self.run_background_task(
            lambda: cleanup_update_residue(preview=False),
            lambda result: self.statusBar().showMessage(str(result), 10000),
        )

    def confirm_browser_cleanup(self, browser: str) -> None:
        self.statusBar().showMessage(
            self.tr(f"Curățarea cache-ului {browser.title()} rulează în fundal...", f"Cleaning {browser.title()} cache in the background..."),
            5000,
        )
        self.run_background_task(
            lambda: clean_browser_cache(browser, include_cookies=True),
            lambda result: self.statusBar().showMessage(str(result), 7000),
        )

    def confirm_windows_update_toggle(self, paused: bool) -> None:
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
        self.statusBar().showMessage(
            self.tr("Restaurarea setărilor rulează în fundal...", "Restoring settings in the background..."),
            5000,
        )
        self.run_background_task(
            revert_optimizations,
            lambda result: self.statusBar().showMessage(str(result), 10000),
        )

    def setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(QIcon(str(ROOT / "VATRIXTweaker.ico")), self)
        self.tray_icon.setToolTip("VATRIXTweaker")
        menu = QMenu(self)
        show_action = QAction(self.tr("Deschide VATRIXTweaker", "Open VATRIXTweaker"), self)
        show_action.triggered.connect(self.show_from_tray)
        menu.addAction(show_action)
        exit_action = QAction(self.tr("Ieșire", "Exit"), self)
        exit_action.triggered.connect(self.exit_from_tray)
        menu.addAction(exit_action)
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

    def setup_live_updates(self) -> None:
        """Setup automatic real-time telemetry updates for RAM, CPU and system metrics."""
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(2000)  # Every 2 seconds
        self.live_timer.timeout.connect(self.auto_refresh_live_data)
        self.live_timer.start()

        # Periodic background junk files check (every 45 seconds)
        self.junk_timer = QTimer(self)
        self.junk_timer.setInterval(45000)
        self.junk_timer.timeout.connect(self._auto_refresh_junk)
        self.junk_timer.start()

    def auto_refresh_live_data(self) -> None:
        """Automatically refresh RAM and dashboard status metrics in real time."""
        if getattr(self, "current_page", "") != "Home":
            return
        try:
            mem = get_memory_status()
            total = (mem.get("total") or 0) / (1024 ** 3)
            used = (mem.get("used") or 0) / (1024 ** 3)
            pct = int((used / total * 100)) if total else 0

            # 1. Update Home RAM Card safely
            if hasattr(self, "ram_card") and self.ram_card is not None:
                try:
                    tag = self.tr("● Stare normală", "● Optimal") if pct < 80 else self.tr("● Încărcare mare", "● High load")
                    self.ram_card.update_data(
                        big_stat=f"{pct}%",
                        stat_sub=self.tr(f"{used:.1f} GB folosiți din {total:.1f} GB", f"{used:.1f} GB used of {total:.1f} GB"),
                        status_tag=tag,
                    )
                except (RuntimeError, Exception):
                    pass

            # 2. Update Hero status subtitle safely
            if hasattr(self, "hero_status_sub") and self.hero_status_sub is not None:
                try:
                    self.hero_status_sub.setText(
                        self.tr(
                            f"RAM: {used:.1f}/{total:.1f} GB ({pct}%) • Auto-scan activ • Profil: {self.profile.upper()}",
                            f"RAM: {used:.1f}/{total:.1f} GB ({pct}%) • Active auto-scan • Profile: {self.profile.upper()}",
                        )
                    )
                except (RuntimeError, Exception):
                    pass

            # 3. If memory progress bar exists in Settings/Tools, update it as well
            if hasattr(self, "memory_progress") and self.memory_progress is not None:
                try:
                    self.memory_progress.setValue(pct)
                except (RuntimeError, Exception):
                    pass
            if hasattr(self, "memory_label") and self.memory_label is not None:
                try:
                    self.memory_label.setText(
                        self.tr(
                            f"RAM folosită: {used:.1f} GB din {total:.1f} GB",
                            f"RAM used: {used:.1f} GB of {total:.1f} GB",
                        )
                    )
                except (RuntimeError, Exception):
                    pass
        except Exception:
            pass

    def _auto_refresh_junk(self) -> None:
        """Periodically re-estimate temporary files in the background if idle."""
        if getattr(self, "current_page", "") != "Home":
            return
        if not self._background_task_running and not self.running and not getattr(self, "scan_running", False):
            self.estimate_temp_files_dashboard()

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
                    "VATRIXTweaker",
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

    @Slot(str)
    def _maintenance_finished(self, result: str) -> None:
        self.settings.setValue("maintenance/last_run", time.time())
        self.settings.sync()
        self.statusBar().showMessage(result, 6000)

    @Slot(str)
    def _maintenance_failed(self, error: str) -> None:
        self.statusBar().showMessage(
            self.tr(f"Întreținerea a eșuat: {error}", f"Maintenance failed: {error}"),
            10000,
        )

    @Slot()
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
        self._allow_close = True
        self._cleanup_threads_on_close()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        self.close()
        QApplication.quit()

    def _cleanup_threads_on_close(self) -> None:
        for timer_attr in ("live_timer", "junk_timer", "monitor_timer", "maintenance_timer", "_intro_advance_timer"):
            timer = getattr(self, timer_attr, None)
            if timer is not None and hasattr(timer, "isActive") and timer.isActive():
                try:
                    timer.stop()
                except Exception:
                    pass
        for th_attr in ("_background_task_thread", "_maintenance_thread", "worker_thread", "_winget_worker_thread", "_winget_detect_thread"):
            try:
                th = getattr(self, th_attr, None)
                if th is not None and hasattr(th, "isRunning") and th.isRunning():
                    th.quit()
                    th.wait(300)
            except Exception:
                pass
        for item in getattr(self, "_active_winget_workers", []):
            try:
                th = item[0]
                if th is not None and th.isRunning():
                    th.quit()
                    th.wait(300)
            except Exception:
                pass
        for item in getattr(self, "_active_bg_workers", []):
            try:
                th = item[0]
                if th is not None and th.isRunning():
                    th.quit()
                    th.wait(300)
            except Exception:
                pass

    def keyPressEvent(self, event: Any) -> None:
        if hasattr(self, "_intro_advance_timer") and self._intro_advance_timer and self._intro_advance_timer.isActive():
            self._finish_intro()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        if hasattr(self, "_intro_advance_timer") and self._intro_advance_timer and self._intro_advance_timer.isActive():
            self._finish_intro()
            event.accept()
            return
        super().mousePressEvent(event)

    def minimize_animated(self) -> None:
        self.showMinimized()

    def toggle_window_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event: Any) -> None:
        if event.type() == event.Type.WindowStateChange:
            if hasattr(self, "custom_title_bar") and self.custom_title_bar:
                self.custom_title_bar.btn_max.set_maximized(self.isMaximized())
        super().changeEvent(event)

    def nativeEvent(self, eventType: Any, message: Any) -> tuple[bool, int]:
        if sys.platform.startswith("win") and message:
            try:
                import ctypes
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                WM_NCHITTEST = 0x0084
                WM_NCLBUTTONDBLCLK = 0x00A3
                if msg.message == WM_NCLBUTTONDBLCLK and msg.wParam == 2:
                    self.toggle_window_maximized()
                    return True, 0
                if msg.message == WM_NCHITTEST:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    local_pos = self.mapFromGlobal(QPoint(x, y))
                    border = 7
                    w = self.width()
                    h = self.height()

                    # Only allow border resize if not maximized
                    if not self.isMaximized():
                        # Corners
                        if local_pos.x() < border and local_pos.y() < border:
                            return True, 13  # HTTOPLEFT
                        if local_pos.x() > w - border and local_pos.y() < border:
                            return True, 14  # HTTOPRIGHT
                        if local_pos.x() < border and local_pos.y() > h - border:
                            return True, 16  # HTBOTTOMLEFT
                        if local_pos.x() > w - border and local_pos.y() > h - border:
                            return True, 17  # HTBOTTOMRIGHT

                        # Edges
                        if local_pos.x() < border:
                            return True, 10  # HTLEFT
                        if local_pos.x() > w - border:
                            return True, 11  # HTRIGHT
                        if local_pos.y() < border:
                            return True, 12  # HTTOP
                        if local_pos.y() > h - border:
                            return True, 15  # HTBOTTOM

                    # Title bar area
                    if hasattr(self, "custom_title_bar") and self.custom_title_bar and self.custom_title_bar.isVisible():
                        if local_pos.y() <= self.custom_title_bar.height():
                            child = self.custom_title_bar.childAt(self.custom_title_bar.mapFromParent(local_pos))
                            if isinstance(child, QPushButton):
                                return False, 0
                            return True, 2  # HTCAPTION
            except Exception:
                pass

        return super().nativeEvent(eventType, message)

    def closeEvent(self, event: Any) -> None:
        self._cleanup_threads_on_close()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        event.accept()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("VATRIXTweaker")
    app.setQuitOnLastWindowClosed(True)
    window = WinTweaker()
    window.showMaximized()
    sys.exit(app.exec())
