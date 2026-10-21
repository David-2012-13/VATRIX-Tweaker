from __future__ import annotations

import ctypes
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SystemSnapshot:
    cpu_name: str
    logical_processors: int
    cpu_load_percent: Optional[float]
    ram_total_gb: float
    ram_used_gb: float
    ram_used_percent: float
    system_drive: str
    disk_free_gb: float
    operating_system: str
    captured_at: str


class _FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_ulong), ("high", ctypes.c_ulong)]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def _file_time_value(value: _FileTime) -> int:
    return (value.high << 32) | value.low


def _sample_cpu_load(sample_seconds: float) -> Optional[float]:
    if sys.platform != "win32":
        return None

    try:
        kernel32 = ctypes.windll.kernel32
        get_system_times = kernel32.GetSystemTimes
        get_system_times.argtypes = [
            ctypes.POINTER(_FileTime),
            ctypes.POINTER(_FileTime),
            ctypes.POINTER(_FileTime),
        ]
        get_system_times.restype = ctypes.c_int
        idle_start, kernel_start, user_start = _FileTime(), _FileTime(), _FileTime()
        idle_end, kernel_end, user_end = _FileTime(), _FileTime(), _FileTime()
        if not get_system_times(
            ctypes.byref(idle_start), ctypes.byref(kernel_start), ctypes.byref(user_start)
        ):
            return None
        time.sleep(max(sample_seconds, 0.05))
        if not get_system_times(
            ctypes.byref(idle_end), ctypes.byref(kernel_end), ctypes.byref(user_end)
        ):
            return None
    except (AttributeError, OSError):
        return None

    idle_delta = _file_time_value(idle_end) - _file_time_value(idle_start)
    total_delta = (
        _file_time_value(kernel_end)
        - _file_time_value(kernel_start)
        + _file_time_value(user_end)
        - _file_time_value(user_start)
    )
    if total_delta <= 0:
        return None
    busy_percent = 100 * (1 - idle_delta / total_delta)
    return round(max(0.0, min(100.0, busy_percent)), 1)


def _get_memory_totals() -> tuple[int, int]:
    if sys.platform == "win32":
        status = _MemoryStatusEx()
        status.length = ctypes.sizeof(_MemoryStatusEx)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical), int(status.available_physical)

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        total_pages = os.sysconf("SC_PHYS_PAGES")
        available_pages = os.sysconf("SC_AVPHYS_PAGES")
        return page_size * total_pages, page_size * available_pages
    except (AttributeError, OSError, ValueError):
        return 0, 0


def _get_cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return str(name).strip()
        except (OSError, ImportError):
            pass
    return platform.processor() or platform.machine() or "Unknown CPU"


def capture_system_snapshot(sample_seconds: float = 0.25) -> SystemSnapshot:
    total_memory, available_memory = _get_memory_totals()
    used_memory = max(total_memory - available_memory, 0)
    ram_total_gb = total_memory / (1024 ** 3)
    ram_used_gb = used_memory / (1024 ** 3)
    ram_used_percent = (100 * used_memory / total_memory) if total_memory else 0.0

    if sys.platform == "win32":
        system_drive = os.environ.get("SystemDrive", "C:")
        disk_path = system_drive + "\\"
    else:
        disk_path = os.path.expanduser("~")
        system_drive = os.path.splitdrive(disk_path)[0] or "/"
    try:
        disk_free_gb = shutil.disk_usage(disk_path).free / (1024 ** 3)
    except OSError:
        disk_free_gb = 0.0

    return SystemSnapshot(
        cpu_name=_get_cpu_name(),
        logical_processors=os.cpu_count() or 1,
        cpu_load_percent=_sample_cpu_load(sample_seconds),
        ram_total_gb=round(ram_total_gb, 1),
        ram_used_gb=round(ram_used_gb, 1),
        ram_used_percent=round(ram_used_percent, 1),
        system_drive=system_drive,
        disk_free_gb=round(disk_free_gb, 1),
        operating_system=f"{platform.system()} {platform.release()}",
        captured_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def get_recommendations(snapshot: SystemSnapshot) -> list[dict[str, Optional[str]]]:
    recommendations: list[dict[str, Optional[str]]] = []
    if snapshot.ram_total_gb <= 8 or snapshot.logical_processors <= 4:
        recommendations.append({"key": "low_spec", "profile": "low_end", "action": None})
    if 0 < snapshot.disk_free_gb < 20:
        recommendations.append({"key": "low_disk", "profile": None, "action": "temp_cleanup"})
    if snapshot.cpu_load_percent is not None and snapshot.cpu_load_percent >= 80:
        recommendations.append({"key": "high_cpu", "profile": None, "action": None})
    if not recommendations:
        recommendations.append({"key": "no_bottleneck", "profile": None, "action": None})
    return recommendations