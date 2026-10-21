from __future__ import annotations

import subprocess
import sys
import base64
import ctypes
import csv
import io
import json
import os
import shutil
import winreg
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from temp_cleanup import format_byte_size, purge_temp_files


PROFILES = {
    "low_end": {
        "title": "Low-end PC",
        "description": "Optimizează pentru performanță maximă pe hardware vechi sau lent, fără jocuri inutile de resurse.",
        "actions": [
            {"id": "power_plan", "label": "Setează planul de alimentare pe Ultimate Performance", "handler": "set_power_plan"},
            {"id": "hibernate", "label": "Dezactivează hibernarea", "handler": "disable_hibernation"},
            {"id": "transparency", "label": "Dezactivează transparența pentru a reduce încărcarea UI", "handler": "disable_transparency"},
            {"id": "shadows", "label": "Dezactivează umbrele pentru un UI mai rapid", "handler": "disable_shadows"},
            {"id": "animations", "label": "Dezactivează animațiile și efectele vizuale", "handler": "disable_animations"},
            {"id": "background_apps", "label": "Limitează aplicațiile care rulează în fundal", "handler": "disable_background_apps"},
            {"id": "startup_delay", "label": "Elimină întârzierea aplicațiilor la pornire", "handler": "reduce_startup_delay"},
            {"id": "temp_cleanup", "label": "Curăță fișiere temporare", "handler": "clear_temp_files"},
            {"id": "restore_point", "label": "Creează un punct de restaurare a sistemului", "handler": "create_restore_point"},
            {"id": "search_indexing", "label": "Dezactivează indexarea căutării pentru a reduce încărcarea de sistem", "handler": "disable_search_indexing"},
            {"id": "sysmain", "label": "Dezactivează serviciul SysMain pentru un startup mai liber", "handler": "disable_sysmain"},
            {"id": "menu_delay", "label": "Elimină întârzierea de afișare a meniurilor", "handler": "reduce_menu_delay"},
            {"id": "visual_effects", "label": "Setează efectele vizuale Windows pentru performanță", "handler": "set_visual_effects_performance"},
            {"id": "taskbar_animations", "label": "Dezactivează animațiile barei de activități", "handler": "disable_taskbar_animations"},
            {"id": "window_animations", "label": "Dezactivează animațiile ferestrelor", "handler": "disable_window_animations"},
        ],
    },
    "gaming": {
        "title": "Gaming PC",
        "description": "Forțează performanța maximă, reduce latența și menține sistemul pregătit pentru jocuri intensive.",
        "actions": [
            {"id": "power_plan", "label": "Setează planul de alimentare pe Ultimate Performance", "handler": "set_power_plan"},
            {"id": "hibernate", "label": "Dezactivează hibernarea", "handler": "disable_hibernation"},
            {"id": "game_mode", "label": "Activează Windows Game Mode", "handler": "enable_game_mode"},
            {"id": "gamebar", "label": "Dezactivează capturarea video în fundal", "handler": "disable_gamebar"},
            {"id": "background", "label": "Închide procesele inutile din fundal", "handler": "disable_background_tasks"},
            {"id": "startup_delay", "label": "Elimină întârzierea aplicațiilor la pornire", "handler": "reduce_startup_delay"},
            {"id": "background_apps", "label": "Limitează aplicațiile care rulează în fundal", "handler": "disable_background_apps"},
            {"id": "restore_point", "label": "Creează un punct de restaurare a sistemului", "handler": "create_restore_point"},
            {"id": "search_indexing", "label": "Dezactivează indexarea căutării pentru a elibera resurse de joc", "handler": "disable_search_indexing"},
            {"id": "sysmain", "label": "Dezactivează SysMain pentru un boot mai rapid", "handler": "disable_sysmain"},
            {"id": "menu_delay", "label": "Elimină întârzierea de afișare a meniurilor", "handler": "reduce_menu_delay"},
            {"id": "visual_effects", "label": "Setează efectele vizuale Windows pentru performanță", "handler": "set_visual_effects_performance"},
            {"id": "taskbar_animations", "label": "Dezactivează animațiile barei de activități", "handler": "disable_taskbar_animations"},
            {"id": "window_animations", "label": "Dezactivează animațiile ferestrelor", "handler": "disable_window_animations"},
        ],
    },
    "office": {
        "title": "Office PC",
        "description": "Păstrează stabilitatea și viteza, fără să forțezi inutil hardware-ul de birou.",
        "actions": [
            {"id": "power_plan", "label": "Setează planul de alimentare pe Balanced", "handler": "set_power_plan"},
            {"id": "hibernate", "label": "Dezactivează hibernarea", "handler": "disable_hibernation"},
            {"id": "transparency", "label": "Activează transparența cu echilibru", "handler": "enable_transparency"},
            {"id": "updates", "label": "Verifică starea actualizărilor și a task-urilor de sistem", "handler": "check_updates"},
            {"id": "startup_delay", "label": "Elimină întârzierea aplicațiilor la pornire", "handler": "reduce_startup_delay"},
            {"id": "temp_cleanup", "label": "Curăță fișiere temporare", "handler": "clear_temp_files"},
            {"id": "restore_point", "label": "Creează un punct de restaurare a sistemului", "handler": "create_restore_point"},
            {"id": "search_indexing", "label": "Dezactivează indexarea căutării pentru o sarcină mai ușoară", "handler": "disable_search_indexing"},
            {"id": "sysmain", "label": "Dezactivează serviciul SysMain pentru stabilitate constantă", "handler": "disable_sysmain"},
            {"id": "menu_delay", "label": "Elimină întârzierea de afișare a meniurilor", "handler": "reduce_menu_delay"},
        ],
    },
    "custom": {
        "title": "Personalizat",
        "description": "Toate trucurile de performanță într-o secțiune dedicată: power plan, UI, animații, background și optimizări sistem.",
        "actions": [
            {"id": "power_plan", "label": "Setează planul de alimentare pe Ultimate Performance", "handler": "set_power_plan"},
            {"id": "hibernate", "label": "Dezactivează hibernarea", "handler": "disable_hibernation"},
            {"id": "transparency", "label": "Dezactivează transparența", "handler": "disable_transparency"},
            {"id": "shadows", "label": "Dezactivează umbrele", "handler": "disable_shadows"},
            {"id": "animations", "label": "Dezactivează animațiile", "handler": "disable_animations"},
            {"id": "temp_cleanup", "label": "Curăță fișiere temporare", "handler": "clear_temp_files"},
            {"id": "gamebar", "label": "Dezactivează Game Bar", "handler": "disable_gamebar"},
            {"id": "game_mode", "label": "Activează Windows Game Mode", "handler": "enable_game_mode"},
            {"id": "background_apps", "label": "Limitează aplicațiile care rulează în fundal", "handler": "disable_background_apps"},
            {"id": "startup_delay", "label": "Elimină întârzierea aplicațiilor la pornire", "handler": "reduce_startup_delay"},
            {"id": "background", "label": "Închide procesele inutile din fundal", "handler": "disable_background_tasks"},
            {"id": "updates", "label": "Verifică actualizările și task-urile inutile", "handler": "check_updates"},
            {"id": "restore_point", "label": "Creează un punct de restaurare a sistemului", "handler": "create_restore_point"},
            {"id": "search_indexing", "label": "Dezactivează indexarea căutării pentru un sistem mai rapid", "handler": "disable_search_indexing"},
            {"id": "sysmain", "label": "Dezactivează SysMain pentru un sistem mai răspuns", "handler": "disable_sysmain"},
            {"id": "menu_delay", "label": "Elimină întârzierea de afișare a meniurilor", "handler": "reduce_menu_delay"},
            {"id": "visual_effects", "label": "Setează efectele vizuale Windows pentru performanță", "handler": "set_visual_effects_performance"},
            {"id": "taskbar_animations", "label": "Dezactivează animațiile barei de activități", "handler": "disable_taskbar_animations"},
            {"id": "window_animations", "label": "Dezactivează animațiile ferestrelor", "handler": "disable_window_animations"},
        ],
    },
}


def _repair_mojibake(value):
    """Repair text that was accidentally decoded as Latin-1 instead of UTF-8."""
    if isinstance(value, str):
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, dict):
        return {key: _repair_mojibake(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_mojibake(item) for item in value]
    return value


PROFILES = _repair_mojibake(PROFILES)


def _add_profile_actions():
    """Add conservative profile-specific tweaks after the base profile data loads."""
    extra_actions = {
        "low_end": [
            {"id": "widgets", "label": "Dezactivează Windows Widgets pentru a reduce încărcarea în fundal", "handler": "disable_widgets"},
            {"id": "notifications", "label": "Dezactivează notificările pentru a reduce întreruperile", "handler": "disable_notifications"},
            {"id": "web_search", "label": "Dezactivează rezultatele web din căutarea Start", "handler": "disable_web_search"},
            {"id": "remove_bloatware", "label": "Elimină aplicațiile Windows opționale (bloatware)", "handler": "remove_bloatware"},
            {"id": "remove_edge", "label": "Dezinstalează Microsoft Edge", "handler": "remove_edge"},
        ],
        "gaming": [
            {"id": "hags", "label": "Activează programarea GPU accelerată hardware pentru jocuri", "handler": "enable_hags"},
            {"id": "widgets", "label": "Dezactivează Windows Widgets în timpul jocurilor", "handler": "disable_widgets"},
            {"id": "notifications", "label": "Dezactivează notificările în timpul jocurilor", "handler": "disable_notifications"},
            {"id": "remove_bloatware", "label": "Elimină aplicațiile Windows opționale (bloatware)", "handler": "remove_bloatware"},
            {"id": "remove_edge", "label": "Dezinstalează Microsoft Edge", "handler": "remove_edge"},
        ],
        "office": [
            {"id": "widgets", "label": "Dezactivează Windows Widgets pentru un desktop mai curat", "handler": "disable_widgets"},
            {"id": "web_search", "label": "Dezactivează rezultatele web din căutarea Start", "handler": "disable_web_search"},
            {"id": "remove_bloatware", "label": "Elimină aplicațiile Windows opționale (bloatware)", "handler": "remove_bloatware"},
            {"id": "remove_edge", "label": "Dezinstalează Microsoft Edge", "handler": "remove_edge"},
        ],
        "custom": [
            {"id": "hags", "label": "Activează programarea GPU accelerată hardware", "handler": "enable_hags"},
            {"id": "widgets", "label": "Dezactivează Windows Widgets", "handler": "disable_widgets"},
            {"id": "notifications", "label": "Dezactivează notificările", "handler": "disable_notifications"},
            {"id": "web_search", "label": "Dezactivează rezultatele web din căutarea Start", "handler": "disable_web_search"},
            {"id": "search_indexing_on", "label": "Activează indexarea Windows Search", "handler": "enable_search_indexing"},
            {"id": "remove_bloatware", "label": "Elimină aplicațiile Windows opționale (bloatware)", "handler": "remove_bloatware"},
            {"id": "remove_edge", "label": "Dezinstalează Microsoft Edge", "handler": "remove_edge"},
        ],
    }
    for profile_name, actions in extra_actions.items():
        PROFILES[profile_name]["actions"].extend(actions)

    system_actions = [
        {"id": "telemetry", "label": "Dezactivează telemetria Windows", "handler": "disable_telemetry"},
        {"id": "prefetch", "label": "Curăță memoria cache Prefetch", "handler": "clean_prefetch"},
        {"id": "nagle", "label": "Optimizează latența rețelei (Nagle)", "handler": "optimize_nagle"},
    ]
    for profile in PROFILES.values():
        existing = {action["id"] for action in profile["actions"]}
        profile["actions"].extend(action for action in system_actions if action["id"] not in existing)

    for action in PROFILES["office"]["actions"]:
        if action["id"] == "search_indexing":
            action.update(
                label="Păstrează indexarea Windows Search activă pentru căutări rapide",
                handler="enable_search_indexing",
            )


_add_profile_actions()

# Restore points are intentionally not part of WinTweaker's optimization flow.
# Keep this filter close to the profile source so future profile additions cannot
# silently reintroduce an automatic restore-point side effect.
for _profile in PROFILES.values():
    _profile["actions"] = [
        action for action in _profile["actions"] if action["id"] != "restore_point"
    ]


def get_available_profiles() -> dict:
    return {
        key: {
            "title": profile["title"],
            "description": profile["description"],
            "actions": profile["actions"],
        }
        for key, profile in PROFILES.items()
    }


def get_profile_names() -> List[str]:
    return list(PROFILES.keys())


def build_plan(profile_name: str) -> List[dict]:
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown profile: {profile_name}")
    return list(profile["actions"])


def _silent_process_kwargs() -> dict:
    """Return subprocess options that prevent console windows on Windows."""
    if not _is_windows():
        return {}
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startup_info,
    }


def _run_silent(command: List[str], *, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        capture_output=True,
        text=text,
        check=False,
        **_silent_process_kwargs(),
    )


def _run_windows_command(command: List[str]) -> str:
    try:
        result = _run_silent(command)
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()

        if result.returncode != 0:
            return error or output or "Comandă eșuată."

        return output or "Success."
    except FileNotFoundError:
        return "Comanda nu a fost găsită pe sistem."
    except Exception as exc:  # pragma: no cover - defensive branch
        return f"Eroare: {exc}"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _set_registry_dword(key: str, name: str, value: int) -> str:
    return _set_registry_value(key, name, "REG_DWORD", str(value))


def _set_registry_value(key: str, name: str, value_type: str, value: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command([
        "reg", "add", key, "/v", name, "/t", value_type, "/d", value, "/f"
    ])


def disable_background_apps(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
        "GlobalUserDisabled",
        1,
    )


def reduce_startup_delay(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
        "StartupDelayInMSec",
        0,
    )


def reduce_menu_delay(profile_name: str) -> str:
    return _set_registry_value(
        r"HKCU\Control Panel\Desktop",
        "MenuShowDelay",
        "REG_SZ",
        "0",
    )


def set_visual_effects_performance(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
        "VisualFXSetting",
        2,
    )


def disable_taskbar_animations(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarAnimations",
        0,
    )


def disable_window_animations(profile_name: str) -> str:
    return _set_registry_value(
        r"HKCU\Control Panel\Desktop\WindowMetrics",
        "MinAnimate",
        "REG_SZ",
        "0",
    )


def disable_widgets(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarDa",
        0,
    )


def disable_notifications(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications",
        "ToastEnabled",
        0,
    )


def disable_web_search(profile_name: str) -> str:
    results = [
        _set_registry_dword(
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
            "BingSearchEnabled",
            0,
        ),
        _set_registry_dword(
            r"HKCU\Software\Policies\Microsoft\Windows\Explorer",
            "DisableSearchBoxSuggestions",
            1,
        ),
    ]
    return "; ".join(results)


def enable_search_indexing(profile_name: str) -> str:
    if not _is_windows():
        return "FuncÈ›ie disponibilÄƒ doar pe Windows."
    results = [
        _run_windows_command(["sc", "config", "WSearch", "start=", "delayed-auto"]),
        _run_windows_command(["sc", "start", "WSearch"]),
    ]
    return "; ".join(part for part in results if part)


def enable_hags(profile_name: str) -> str:
    return _set_registry_dword(
        r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
        "HwSchMode",
        2,
    )


def remove_bloatware(profile_name: str) -> str:
    if not _is_windows():
        return "FuncÈ›ie disponibilÄƒ doar pe Windows."

    script = (
        "$patterns = @('*BingNews*','*BingWeather*','*MicrosoftNews*',"
        "'*Weather*','*News*','*Windows.Client.WebExperience*','*Widgets*',"
        "'*Clipchamp*','*MicrosoftTeams*','*MicrosoftOfficeHub*',"
        "'*XboxApp*','*XboxGamingOverlay*','*Xbox.TCUI*','*XboxSpeechToTextOverlay*',"
        "'*SolitaireCollection*','*GetHelp*','*Getstarted*','*YourPhone*',"
        "'*WindowsFeedbackHub*','*ZuneMusic*','*ZuneVideo*'); "
        "$installed = @(Get-AppxPackage -AllUsers | Where-Object { "
        "$name = $_.Name; @($patterns | Where-Object { $name -like $_ }).Count -gt 0 }); "
        "$removed = 0; $installed | ForEach-Object { "
        "try { Remove-AppxPackage -Package $_.PackageFullName -AllUsers -ErrorAction Stop; $removed++ } catch { "
        "try { Remove-AppxPackage -Package $_.PackageFullName -ErrorAction Stop; $removed++ } catch {} } }; "
        "$provisioned = @(Get-AppxProvisionedPackage -Online | Where-Object { "
        "$name = $_.DisplayName; @($patterns | Where-Object { $name -like $_ }).Count -gt 0 }); "
        "$deprovisioned = 0; $provisioned | ForEach-Object { "
        "try { Remove-AppxProvisionedPackage -Online -PackageName $_.PackageName -ErrorAction Stop | Out-Null; $deprovisioned++ } catch {} }; "
        "Write-Output ('Removed installed packages: ' + $removed + '; removed provisioned packages: ' + $deprovisioned)"
    )
    return _run_windows_command([
        "powershell",
        "-NoProfile",
        "-Command",
        script,
    ])


def remove_edge(profile_name: str) -> str:
    if not _is_windows():
        return "FuncÈ›ie disponibilÄƒ doar pe Windows."
    policy_result = _set_registry_dword(
        r"HKLM\SOFTWARE\Policies\Microsoft\EdgeUpdate",
        "Uninstall{56eb18f8-b008-4cbd-b6d2-8c97fe7e9062}",
        1,
    )
    winget_result = _run_windows_command([
        "winget",
        "uninstall",
        "--id",
        "Microsoft.Edge",
        "--exact",
        "--silent",
        "--source",
        "winget",
        "--accept-source-agreements",
    ])
    return f"Registry: {policy_result}; Winget: {winget_result}"


def enable_game_mode(profile_name: str) -> str:
    key = r"HKCU\Software\Microsoft\GameBar"
    results = [
        _set_registry_dword(key, "AutoGameModeEnabled", 1),
        _set_registry_dword(key, "AllowAutoGameMode", 1),
    ]
    return "; ".join(results)


def set_power_plan(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    mapping = {
        "low_end": "e9a42b02-d5df-448d-979d-f5dce4a4c32d",
        "gaming": "e9a42b02-d5df-448d-979d-f5dce4a4c32d",
        "office": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    }

    target = mapping.get(profile_name, "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
    result = _run_windows_command(["powercfg", "/setactive", target])

    if "not found" in result.lower() or "invalid" in result.lower():
        fallback = {
            "low_end": "scheme_max",
            "gaming": "scheme_max",
            "office": "scheme_balanced",
        }
        target_fallback = fallback.get(profile_name, "scheme_balanced")
        return _run_windows_command(["powercfg", "/setactive", target_fallback])

    return result


def disable_hibernation(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command(["powercfg", "/h", "off"])


def disable_transparency(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command([
        "reg",
        "add",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
        "/v",
        "EnableTransparency",
        "/t",
        "REG_DWORD",
        "/d",
        "0",
        "/f",
    ])


def enable_transparency(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command([
        "reg",
        "add",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
        "/v",
        "EnableTransparency",
        "/t",
        "REG_DWORD",
        "/d",
        "1",
        "/f",
    ])


def clear_temp_files(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    result = purge_temp_files()
    return (
        f"Șterse {result.deleted_files} fișiere ({format_byte_size(result.deleted_bytes)}); "
        f"{result.skipped} omise deoarece erau folosite."
    )


def disable_gamebar(profile_name: str) -> str:
    results = [
        _set_registry_dword(
            r"HKCU\Software\Microsoft\GameConfigStore", "GameDVR_Enabled", 0
        ),
        _set_registry_dword(
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0
        ),
    ]
    return "; ".join(results)


def disable_background_tasks(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "IDLE", "0"]) or "Setările de consum au fost ajustate."


def disable_search_indexing(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    results = [
        _run_windows_command(["sc", "config", "WSearch", "start=", "disabled"]),
        _run_windows_command(["sc", "stop", "WSearch"]),
    ]
    return "; ".join(part for part in results if part)


def disable_sysmain(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    results = [
        _run_windows_command(["sc", "config", "SysMain", "start=", "disabled"]),
        _run_windows_command(["sc", "stop", "SysMain"]),
    ]
    return "; ".join(part for part in results if part)


def create_restore_point(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    return _run_windows_command([
        "powershell",
        "-NoProfile",
        "-Command",
        "Checkpoint-Computer -Description 'WinTweaker restore point' -RestorePointType MODIFY_SETTINGS",
    ])


_DISABLED_STARTUP_KEY = r"Software\WinTweaker\DisabledStartup"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_token(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _startup_token_value(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")


def get_startup_entries() -> List[dict]:
    """Return startup entries from Run registry keys and Startup folders."""
    if not _is_windows():
        return []

    entries = []
    registry_locations = [
        ("HKCU", winreg.HKEY_CURRENT_USER, "Current user"),
        ("HKLM", winreg.HKEY_LOCAL_MACHINE, "All users"),
    ]
    for hive_name, hive, location in registry_locations:
        try:
            with winreg.OpenKey(hive, _RUN_KEY) as key:
                index = 0
                while True:
                    try:
                        name, command, _value_type = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    entries.append({
                        "id": f"registry|{hive_name}|{name}",
                        "name": name,
                        "command": str(command),
                        "location": f"{location} Run",
                        "enabled": True,
                        "kind": "registry",
                        "hive": hive_name,
                    })
                    index += 1
        except OSError:
            pass

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _DISABLED_STARTUP_KEY) as key:
            index = 0
            while True:
                try:
                    token = winreg.EnumKey(key, index)
                except OSError:
                    break
                try:
                    with winreg.OpenKey(key, token) as entry_key:
                        values = {
                            winreg.EnumValue(entry_key, value_index)[0]: winreg.EnumValue(entry_key, value_index)[1]
                            for value_index in range(winreg.QueryInfoKey(entry_key)[1])
                        }
                    original_id = _startup_token_value(token)
                    entries.append({
                        "id": original_id,
                        "name": values.get("Name", original_id),
                        "command": values.get("Command", ""),
                        "location": values.get("Location", "Disabled startup"),
                        "enabled": False,
                        "kind": "registry",
                        "hive": values.get("Hive", "HKCU"),
                    })
                except (OSError, UnicodeError):
                    pass
                index += 1
    except OSError:
        pass

    startup_folders = [
        Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup",
        Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup",
    ]
    for folder in startup_folders:
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.name.lower() != "desktop.ini" and not path.name.endswith(".disabled"):
                entries.append({
                    "id": f"folder|{path}",
                    "name": path.name,
                    "command": str(path),
                    "location": "Startup folder",
                    "enabled": True,
                    "kind": "folder",
                    "path": str(path),
                })
            elif path.is_file() and path.name.lower() != "desktop.ini" and path.name.endswith(".disabled"):
                entries.append({
                    "id": f"folder|{path.with_name(path.name[:-9])}",
                    "name": path.name[:-9],
                    "command": str(path),
                    "location": "Startup folder",
                    "enabled": False,
                    "kind": "folder",
                    "path": str(path),
                })
    return sorted(entries, key=lambda item: (not item["enabled"], item["name"].lower()))


def set_startup_entry_enabled(entry: dict, enabled: bool) -> str:
    """Enable or disable one startup entry in its real Windows location."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    try:
        if entry.get("kind") == "folder":
            path = Path(entry["path"])
            if enabled:
                target = path.with_name(path.name[:-9]) if path.name.endswith(".disabled") else path
                if path != target and path.exists():
                    path.rename(target)
                return "Startup entry enabled."
            target = path.with_name(path.name + ".disabled") if not path.name.endswith(".disabled") else path
            if path != target and path.exists():
                path.rename(target)
            return "Startup entry disabled."

        hive = winreg.HKEY_LOCAL_MACHINE if entry.get("hive") == "HKLM" else winreg.HKEY_CURRENT_USER
        if not enabled:
            with winreg.OpenKey(hive, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, entry["name"])
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{_DISABLED_STARTUP_KEY}\\{_startup_token(entry['id'])}") as key:
                winreg.SetValueEx(key, "Hive", 0, winreg.REG_SZ, entry.get("hive", "HKCU"))
                winreg.SetValueEx(key, "Name", 0, winreg.REG_SZ, entry["name"])
                winreg.SetValueEx(key, "Command", 0, winreg.REG_SZ, entry["command"])
                winreg.SetValueEx(key, "Location", 0, winreg.REG_SZ, entry["location"])
            return "Startup entry disabled."

        with winreg.CreateKey(hive, _RUN_KEY) as key:
            winreg.SetValueEx(key, entry["name"], 0, winreg.REG_SZ, entry["command"])
        disabled_key = f"{_DISABLED_STARTUP_KEY}\\{_startup_token(entry['id'])}"
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, disabled_key)
        except FileNotFoundError:
            pass
        return "Startup entry enabled."
    except (OSError, PermissionError) as exc:
        return f"Startup change failed: {exc}"


def disable_startup_entry(entry: dict) -> str:
    """Backward-compatible wrapper used by the legacy Tkinter UI."""
    return set_startup_entry_enabled(entry, False)


def set_autostart(enabled: bool) -> str:
    """Enable or disable WinTweaker in the current user's Run key."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    command = f'"{sys.executable}"'
    if not getattr(sys, "frozen", False):
        command += f' "{Path(__file__).resolve()}"'
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, "WinTweaker", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "WinTweaker")
                except FileNotFoundError:
                    pass
        return "Startup setting updated."
    except (OSError, PermissionError) as exc:
        return f"Startup setting failed: {exc}"


def get_memory_status() -> dict:
    if not _is_windows():
        return {"total": 0, "available": 0, "used": 0}
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong), ("available_extended", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    return {"total": status.total, "available": status.available, "used": status.total - status.available}


def flush_ram() -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    before = get_memory_status()["available"]
    try:
        tasklist = _run_silent(["tasklist", "/fo", "csv", "/nh"])
        process_ids = []
        for row in csv.reader(io.StringIO(tasklist.stdout or "")):
            if len(row) >= 2 and row[1].isdigit():
                process_ids.append(int(row[1]))
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        handles = 0
        for pid in process_ids:
            handle = kernel32.OpenProcess(0x0400 | 0x0100, False, pid)
            if handle:
                if psapi.EmptyWorkingSet(handle):
                    handles += 1
                kernel32.CloseHandle(handle)
        after = get_memory_status()["available"]
        freed = max(0, after - before)
        return f"RAM optimized: {freed // (1024 * 1024)} MB released across {handles} processes."
    except (OSError, RuntimeError) as exc:
        return f"RAM optimization failed: {exc}"


def get_battery_status() -> dict:
    """Read battery status through CIM without creating a report on disk."""
    if not _is_windows():
        return {"available": False, "message": "Battery information is available only on Windows."}
    script = (
        "$out = @{available = $false}; "
        "$b = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1 "
        "Name,DeviceID,EstimatedChargeRemaining,BatteryStatus,DesignVoltage,EstimatedRunTime; "
        "if ($b) { $out.available = $true; $out.battery = $b; "
        "$s = Get-CimInstance -Namespace root\\wmi -ClassName BatteryStaticData -ErrorAction SilentlyContinue | Select-Object -First 1 DesignedCapacity; "
        "$f = Get-CimInstance -Namespace root\\wmi -ClassName BatteryFullChargedCapacity -ErrorAction SilentlyContinue | Select-Object -First 1 FullChargedCapacity; "
        "$r = Get-CimInstance -Namespace root\\wmi -ClassName BatteryStatus -ErrorAction SilentlyContinue | Select-Object -First 1 ChargeRate,DischargeRate,Charging,Discharging,PowerOnline; "
        "if ($s) { $out.static = $s }; if ($f) { $out.full = $f }; if ($r) { $out.rate = $r } }; "
        "$out | ConvertTo-Json -Compress"
    )
    try:
        result = _run_silent(["powershell", "-NoProfile", "-Command", script])
        data = json.loads(result.stdout.strip() or '{"available":false}')
        return data
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"available": False, "message": str(exc)}


def get_system_specs() -> dict:
    """Collect detailed hardware and operating system information through CIM."""
    if not _is_windows():
        return {}
    script = (
        "$cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1 "
        "Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed; "
        "$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue | Select-Object -First 1 "
        "Caption,Version,BuildNumber,OSArchitecture,LastBootUpTime,InstallDate; "
        "$gpu = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object Name,DriverVersion,AdapterRAM,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate); "
        "$mem = @(Get-CimInstance Win32_PhysicalMemory -ErrorAction SilentlyContinue | Select-Object Capacity,Speed,ConfiguredClockSpeed,Manufacturer,FormFactor); "
        "$disk = @(Get-CimInstance Win32_DiskDrive -ErrorAction SilentlyContinue | Select-Object Model,Size,InterfaceType); "
        "$board = Get-CimInstance Win32_BaseBoard -ErrorAction SilentlyContinue | Select-Object -First 1 Manufacturer,Product; "
        "$bios = Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue | Select-Object -First 1 Manufacturer,SMBIOSBIOSVersion; "
        "$sys = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue | Select-Object -First 1 Manufacturer,Model,SystemFamily; "
        "$net = @(Get-CimInstance Win32_NetworkAdapter -Filter 'PhysicalAdapter=true AND NetEnabled=true' -ErrorAction SilentlyContinue | Select-Object -First 3 Name,Speed); "
        "[pscustomobject]@{cpu=$cpu;os=$os;gpu=$gpu;memory=$mem;disks=$disk;board=$board;bios=$bios;system=$sys;network=$net} | ConvertTo-Json -Depth 3 -Compress"
    )
    try:
        result = _run_silent(["powershell", "-NoProfile", "-Command", script])
        return json.loads(result.stdout.strip() or "{}")
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def get_hardware_info() -> tuple[dict, dict]:
    """Collect system specs and battery wear concurrently to minimize wait time."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        specs_future = executor.submit(get_system_specs)
        battery_future = executor.submit(get_battery_status)
        return specs_future.result(), battery_future.result()


def cleanup_update_residue(preview: bool = True) -> str:
    """Preview or clean Windows update residue after explicit user confirmation."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    targets = [
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SoftwareDistribution" / "Download",
        Path(os.environ.get("SystemDrive", "C:")) / "Windows.old",
    ]
    existing = [str(path) for path in targets if path.exists()]
    if preview:
        return "Ținte găsite: " + (", ".join(existing) if existing else "niciuna")
    cleanup = (
        "DISM.exe /Online /Cleanup-Image /StartComponentCleanup; "
        "$download = Join-Path $env:SystemRoot 'SoftwareDistribution\\Download'; "
        "if (Test-Path -LiteralPath $download) { Remove-Item -LiteralPath $download -Recurse -Force -ErrorAction SilentlyContinue }; "
        "$old = Join-Path $env:SystemDrive 'Windows.old'; "
        "if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force -ErrorAction Stop }; "
        "Write-Output 'Windows update residue cleanup completed.'"
    )
    return _run_windows_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cleanup])


def run_periodic_maintenance() -> str:
    """Run conservative maintenance tasks; no registry or service changes."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    ram_result = flush_ram()
    recycle = _run_windows_command([
        "powershell", "-NoProfile", "-Command",
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; Write-Output 'Recycle Bin cleaned.'",
    ])
    return f"{ram_result} {recycle}".strip()


def clean_browser_cache(browser: str, include_cookies: bool = False) -> str:
    """Remove only known cache folders for a selected browser."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    locations = {
        "chrome": [local / r"Google\Chrome\User Data\Default\Cache", local / r"Google\Chrome\User Data\Default\Code Cache"],
        "edge": [local / r"Microsoft\Edge\User Data\Default\Cache", local / r"Microsoft\Edge\User Data\Default\Code Cache"],
        "firefox": [roaming / r"Mozilla\Firefox\Profiles"],
    }
    targets = locations.get(browser.lower(), [])
    if browser.lower() == "firefox":
        targets = [profile / name for profile in targets[0].glob("*") for name in ("cache2", "startupCache") if profile.is_dir()]
    removed = 0
    for target in targets:
        if not target.exists():
            continue
        try:
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
            removed += 1
        except OSError:
            continue
    if include_cookies:
        cookie_names = {"chrome": "Cookies", "edge": "Cookies", "firefox": "cookies.sqlite"}
        cookie_name = cookie_names.get(browser.lower())
        if cookie_name:
            roots = [local / r"Google\Chrome\User Data\Default", local / r"Microsoft\Edge\User Data\Default"] if browser.lower() != "firefox" else [roaming / r"Mozilla\Firefox\Profiles"]
            for root in roots:
                for cookie in root.rglob(cookie_name):
                    try:
                        cookie.unlink(missing_ok=True); removed += 1
                    except OSError:
                        pass
    return f"{browser}: {removed} locații curățate. Închide browserul pentru rezultate complete."


def set_windows_update_paused(paused: bool) -> str:
    """Pause or restore Windows Update service; requires administrator rights."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    if paused:
        commands = [["sc.exe", "stop", "wuauserv"], ["sc.exe", "config", "wuauserv", "start=", "disabled"]]
    else:
        commands = [["sc.exe", "config", "wuauserv", "start=", "auto"], ["sc.exe", "start", "wuauserv"]]
    results = []
    for command in commands:
        result = _run_silent(command)
        results.append((result.stdout or result.stderr).strip())
    return " ".join(item for item in results if item) or "Windows Update setting updated."


def get_windows_service_state(service_name: str) -> bool | None:
    """Return True when a service is not disabled, False when disabled."""
    if not _is_windows():
        return None
    result = _run_silent(["sc.exe", "qc", service_name])
    if result.returncode != 0:
        return None
    output = (result.stdout or "")
    marker = "START_TYPE"
    for line in output.splitlines():
        if marker in line:
            return "4" not in line.split(":", 1)[-1]
    return None


def set_windows_service_state(service_name: str, enabled: bool) -> str:
    """Enable/start or stop/disable a Windows service."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    commands = (
        [["sc.exe", "config", service_name, "start=", "auto"], ["sc.exe", "start", service_name]]
        if enabled
        else [["sc.exe", "stop", service_name], ["sc.exe", "config", service_name, "start=", "disabled"]]
    )
    results = []
    failed = False
    for command in commands:
        result = _run_silent(command)
        output = (result.stdout or result.stderr or "").strip()
        results.append(output)
        failed = failed or result.returncode != 0
    if failed:
        return f"Service change failed: {' '.join(item for item in results if item)}"
    return f"Service {'enabled' if enabled else 'disabled'}: {service_name}."


def detect_optimization_drift(selected_ids: Iterable[str]) -> list[str]:
    """Return known optimization IDs whose observable value no longer matches."""
    if not _is_windows():
        return []
    drift: list[str] = []
    checks = {
        "telemetry": (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
        "transparency": (r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0),
        "search_indexing": (r"HKLM\SYSTEM\CurrentControlSet\Services\WSearch", "Start", 4),
        "sysmain": (r"HKLM\SYSTEM\CurrentControlSet\Services\SysMain", "Start", 4),
    }
    for action_id in selected_ids:
        check = checks.get(action_id)
        if not check:
            continue
        key_path, name, expected = check
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE if key_path.startswith("HKLM") else winreg.HKEY_CURRENT_USER, key_path.replace("HKLM\\", "").replace("HKCU\\", "")) as key:
                value, _ = winreg.QueryValueEx(key, name)
            if int(value) != expected:
                drift.append(action_id)
        except (OSError, ValueError):
            drift.append(action_id)
    return drift


def get_optimization_state(action_id: str, handler: str | None = None) -> str:
    """Return whether a tweak is already active, can be applied, or is unknown."""
    if not _is_windows():
        return "unknown"
    checks = {
        "telemetry": (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
        "transparency": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0 if handler != "enable_transparency" else 1),
        "shadows": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ListviewShadow", 0),
        "hibernate": (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Power", "HibernateEnabled", 0),
        "gamebar": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
        "game_mode": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1),
        "background_apps": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", 1),
        "startup_delay": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec", 0),
        "search_indexing": (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WSearch", "Start", 2 if handler == "enable_search_indexing" else 4),
        "sysmain": (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\SysMain", "Start", 4),
    }
    check = checks.get(action_id)
    if check is None:
        return "unknown"
    hive, path, name, expected = check
    try:
        with winreg.OpenKey(hive, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
        return "already_applied" if int(value) == expected else "can_apply"
    except (OSError, TypeError, ValueError):
        return "can_apply"


def check_updates(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return "Verifică în Windows Update și în Task Scheduler dacă există procese de fundal inutile."


def disable_shadows(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command([
        "reg",
        "add",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced",
        "/v",
        "ListviewShadow", 
        "/t",
        "REG_DWORD",
        "/d",
        "0",
        "/f",
    ])


def disable_telemetry(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    results = [
        _set_registry_dword(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
        _set_registry_dword(r"HKCU\Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0),
    ]
    return "; ".join(results)


def clean_prefetch(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    script = "Get-ChildItem -LiteralPath $env:SystemRoot\\Prefetch -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"
    return _run_windows_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]) or "Prefetch cache cleaned."


def optimize_nagle(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    script = (
        "$base='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces'; "
        "Get-ChildItem $base -ErrorAction SilentlyContinue | ForEach-Object { "
        "New-ItemProperty -Path $_.PSPath -Name TcpAckFrequency -PropertyType DWord -Value 1 -Force | Out-Null; "
        "New-ItemProperty -Path $_.PSPath -Name TCPNoDelay -PropertyType DWord -Value 1 -Force | Out-Null }; "
        "Write-Output 'Nagle TCP settings optimized.'"
    )
    return _run_windows_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])


def disable_animations(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    return _run_windows_command([
        "reg",
        "add",
        "HKCU\\Control Panel\\Desktop",
        "/v",
        "UserPreferencesMask",
        "/t",
        "REG_BINARY",
        "/d",
        "90,00,00,00",
        "/f",
    ])


HANDLERS = {
    "set_power_plan": set_power_plan,
    "disable_hibernation": disable_hibernation,
    "disable_transparency": disable_transparency,
    "enable_transparency": enable_transparency,
    "clear_temp_files": clear_temp_files,
    "disable_gamebar": disable_gamebar,
    "disable_background_tasks": disable_background_tasks,
    "check_updates": check_updates,
    "disable_shadows": disable_shadows,
    "disable_animations": disable_animations,
    "disable_telemetry": disable_telemetry,
    "clean_prefetch": clean_prefetch,
    "optimize_nagle": optimize_nagle,
    "disable_background_apps": disable_background_apps,
    "reduce_startup_delay": reduce_startup_delay,
    "reduce_menu_delay": reduce_menu_delay,
    "set_visual_effects_performance": set_visual_effects_performance,
    "disable_taskbar_animations": disable_taskbar_animations,
    "disable_window_animations": disable_window_animations,
    "disable_widgets": disable_widgets,
    "disable_notifications": disable_notifications,
    "disable_web_search": disable_web_search,
    "enable_search_indexing": enable_search_indexing,
    "enable_hags": enable_hags,
    "remove_bloatware": remove_bloatware,
    "remove_edge": remove_edge,
    "enable_game_mode": enable_game_mode,
    "disable_search_indexing": disable_search_indexing,
    "disable_sysmain": disable_sysmain,
    "create_restore_point": create_restore_point,
}


_BACKUP_DIR = Path(os.environ.get("PROGRAMDATA", Path.home())) / "WinTweaker" / "backups"
_BACKUP_KEYS = {
    "hkcu_desktop": r"HKCU\Control Panel\Desktop",
    "hkcu_explorer": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
    "hkcu_gamebar": r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR",
    "hklm_telemetry": r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
}


def _create_optimization_snapshot() -> None:
    if not _is_windows():
        return
    try:
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        for name, key in _BACKUP_KEYS.items():
            destination = _BACKUP_DIR / f"{name}.reg"
            if not destination.exists():
                _run_silent(["reg", "export", key, str(destination), "/y"], text=False)
    except OSError:
        pass


def revert_optimizations() -> str:
    """Restore registry snapshots created before the first optimization run."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    if not _BACKUP_DIR.exists():
        return "Nu există un backup WinTweaker pentru restaurare."
    restored = 0
    for backup in _BACKUP_DIR.glob("*.reg"):
        result = _run_silent(["reg", "import", str(backup)])
        if result.returncode == 0:
            restored += 1
    return f"Au fost restaurate {restored} backup-uri de registry. Unele modificări pot necesita restart."


def apply_profile(
    profile_name: str,
    selected_ids: Optional[Iterable[str]] = None,
    progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
) -> List[str]:
    _create_optimization_snapshot()
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ValueError(f"Profile '{profile_name}' nu există.")

    wanted = set(selected_ids) if selected_ids is not None else {action["id"] for action in profile["actions"]}
    results: List[str] = []
    actions = [action for action in profile["actions"] if action["id"] in wanted]
    total = len(actions)

    for completed, action in enumerate(actions, start=1):

        handler = HANDLERS.get(action["handler"])
        if handler is None:
            results.append(f"{action['label']}: Handler lipsă.")
            continue

        try:
            outcome = handler(profile_name)
        except Exception as exc:  # pragma: no cover - defensive branch
            outcome = f"Eroare: {exc}"

        results.append(f"{action['label']}: {outcome}")
        if progress_callback:
            progress_callback(completed, total, action["label"], outcome)

    return results
