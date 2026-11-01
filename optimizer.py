from __future__ import annotations

import subprocess
import sys
import base64
import ctypes
import csv
import io
import json
import os
import re
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
            {"id": "power_plan", "label": "Setează planul de alimentare pe Ultimate Performance", "handler": "set_power_plan"},
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
    kwargs = _silent_process_kwargs()
    if text:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
    return subprocess.run(
        command,
        capture_output=True,
        text=text,
        check=False,
        **kwargs,
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
    res = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
        "GlobalUserDisabled",
        1,
    )
    return "Aplicațiile de fundal au fost limitate." if "success" in res.lower() else res


def reduce_startup_delay(profile_name: str) -> str:
    res = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
        "StartupDelayInMSec",
        0,
    )
    return "Întârzierea la pornire a fost eliminată." if "success" in res.lower() else res


def reduce_menu_delay(profile_name: str) -> str:
    res = _set_registry_value(
        r"HKCU\Control Panel\Desktop",
        "MenuShowDelay",
        "REG_SZ",
        "0",
    )
    return "Întârzierea meniurilor a fost redusă la 0ms." if "success" in res.lower() else res


def set_visual_effects_performance(profile_name: str) -> str:
    res = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
        "VisualFXSetting",
        2,
    )
    return "Efectele vizuale au fost setate pentru performanță maximă." if "success" in res.lower() else res


def disable_taskbar_animations(profile_name: str) -> str:
    res = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarAnimations",
        0,
    )
    return "Animațiile barei de activități au fost dezactivate." if "success" in res.lower() else res


def disable_window_animations(profile_name: str) -> str:
    res = _set_registry_value(
        r"HKCU\Control Panel\Desktop\WindowMetrics",
        "MinAnimate",
        "REG_SZ",
        "0",
    )
    return "Animațiile ferestrelor au fost dezactivate." if "success" in res.lower() else res


def disable_widgets(profile_name: str) -> str:
    res1 = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarDa",
        0,
    )
    res2 = _set_registry_dword(
        r"HKLM\SOFTWARE\Policies\Microsoft\Dsh",
        "AllowNewsAndInterests",
        0,
    )
    if "success" in res1.lower() or "success" in res2.lower():
        return "Windows Widgets au fost dezactivate."
    if "access is denied" in res1.lower() or "access is denied" in res2.lower():
        return "Dezactivarea Widgets necesită drepturi de administrator."
    return res1


def disable_notifications(profile_name: str) -> str:
    res = _set_registry_dword(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications",
        "ToastEnabled",
        0,
    )
    return "Notificările Windows au fost dezactivate." if "success" in res.lower() else res


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
    return "Căutarea web din meniul Start a fost dezactivată." if any("success" in r.lower() for r in results) else "; ".join(results)


def enable_search_indexing(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    cfg = _run_windows_command(["sc", "config", "WSearch", "start=", "delayed-auto"])
    start = _run_windows_command(["sc", "start", "WSearch"])
    if "success" in cfg.lower() or "1056" in start or "success" in start.lower():
        return "Serviciul Windows Search a fost activat."
    if "access is denied" in cfg.lower() or "access is denied" in start.lower():
        return "Activarea Windows Search necesită drepturi de administrator."
    return f"{cfg}; {start}"


def enable_hags(profile_name: str) -> str:
    res = _set_registry_dword(
        r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
        "HwSchMode",
        2,
    )
    if "success" in res.lower():
        return "Programarea GPU accelerată hardware (HAGS) a fost activată."
    if "access is denied" in res.lower():
        return "Activarea HAGS necesită drepturi de administrator."
    return res


def remove_bloatware(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

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
        "Write-Output ('Aplicații bloatware eliminate: ' + $removed + '; pachete deprovisionate: ' + $deprovisioned)"
    )
    return _run_windows_command([
        "powershell",
        "-NoProfile",
        "-Command",
        script,
    ])


def remove_edge(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
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
    return f"Dezinstalare Edge: {winget_result}"


def enable_game_mode(profile_name: str) -> str:
    key = r"HKCU\Software\Microsoft\GameBar"
    results = [
        _set_registry_dword(key, "AutoGameModeEnabled", 1),
        _set_registry_dword(key, "AllowAutoGameMode", 1),
    ]
    return "Windows Game Mode a fost activat." if any("success" in r.lower() for r in results) else "; ".join(results)


def set_power_plan(profile_name: str = "") -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    # All profiles activate Ultimate Performance
    list_out = _run_windows_command(["powercfg", "/list"])
    schemes = {}
    for line in list_out.splitlines():
        match = re.search(r"GUID:\s*([a-f0-9\-]+)\s*\((.+?)\)", line, re.I)
        if match:
            guid = match.group(1).strip()
            name = match.group(2).replace("*", "").strip().lower()
            schemes[name] = guid

    # Look for existing Ultimate Performance scheme (strictly official "Ultimate Performance")
    target_guid = schemes.get("ultimate performance")
    if not target_guid:
        for name, guid in schemes.items():
            if "ultimate performance" in name:
                target_guid = guid
                break

    # If not yet duplicated on this machine, duplicate the template
    if not target_guid:
        dup_res = _run_windows_command(["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-979d-f5dce4a4c32d"])
        match = re.search(r"GUID:\s*([a-f0-9\-]+)", dup_res, re.I)
        if match:
            target_guid = match.group(1).strip()

    if target_guid:
        act_res = _run_windows_command(["powercfg", "/setactive", target_guid])
        if "not found" not in act_res.lower() and "invalid" not in act_res.lower() and "eroare" not in act_res.lower():
            return "Planul de alimentare a fost setat pe Ultimate Performance (Performanță Maximă)."

    # Fallback to High Performance (scheme_min - NEVER scheme_max which is Power Saver!)
    for name, guid in schemes.items():
        if "high performance" in name or "performanță ridicată" in name:
            target_guid = guid
            break
    if not target_guid:
        target_guid = "scheme_min"

    _run_windows_command(["powercfg", "/setactive", target_guid])
    return "Planul de alimentare a fost setat pe High Performance (Performanță Ridicată)."


def disable_hibernation(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    res = _run_windows_command(["powercfg", "/h", "off"])
    if "success" in res.lower() or not res.strip():
        return "Hibernarea a fost dezactivată (spațiu hiberfil eliberat)."
    if "administrator" in res.lower():
        return "Dezactivarea hibernării necesită drepturi de administrator."
    return res


def disable_transparency(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    res = _run_windows_command([
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
    return "Transparența a fost dezactivată." if "success" in res.lower() else res


def enable_transparency(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    res = _run_windows_command([
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
    return "Transparența a fost activată." if "success" in res.lower() else res


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
    return "Captura video în fundal (GameBar) a fost dezactivată." if any("success" in r.lower() for r in results) else "; ".join(results)


def disable_background_tasks(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    _run_windows_command(["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMIN", "100"])
    _run_windows_command(["powercfg", "/setactive", "SCHEME_CURRENT"])
    _set_registry_dword(r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", 1)
    return "Performanța procesorului și sarcinile de fundal au fost optimizate."


def disable_search_indexing(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    cfg = _run_windows_command(["sc", "config", "WSearch", "start=", "disabled"])
    stop = _run_windows_command(["sc", "stop", "WSearch"])
    if "success" in cfg.lower() or "1062" in stop or "success" in stop.lower():
        return "Serviciul Windows Search a fost dezactivat."
    if "access is denied" in cfg.lower() or "access is denied" in stop.lower():
        return "Dezactivarea Windows Search necesită drepturi de administrator."
    return f"{cfg}; {stop}"


def disable_sysmain(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    cfg = _run_windows_command(["sc", "config", "SysMain", "start=", "disabled"])
    stop = _run_windows_command(["sc", "stop", "SysMain"])
    if "success" in cfg.lower() or "1062" in stop or "success" in stop.lower():
        return "Serviciul SysMain a fost dezactivat."
    if "access is denied" in cfg.lower() or "access is denied" in stop.lower():
        return "Dezactivarea SysMain necesită drepturi de administrator."
    return f"{cfg}; {stop}"


def create_restore_point(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    return _run_windows_command([
        "powershell",
        "-NoProfile",
        "-Command",
        "Checkpoint-Computer -Description 'VATRIXTweaker restore point' -RestorePointType MODIFY_SETTINGS",
    ])


_DISABLED_STARTUP_KEY = r"Software\VATRIXTweaker\DisabledStartup"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_token(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _startup_token_value(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")


def format_startup_display_name(raw: str) -> str:
    low = raw.lower().strip()
    if "securityhealth" in low:
        return "Windows Security"
    if "microsoftedge" in low:
        return "Microsoft Edge"
    if "canva" in low:
        return "Canva"
    if "msteams" in low or low == "teams":
        return "Microsoft Teams"
    if "operabrowserassistant" in low or "browser assistant" in low:
        return "Opera Browser Assistant"
    if "operastable" in low or low == "opera":
        return "Opera Browser"
    if "ollama" in low:
        return "Ollama AI"
    return raw


def get_startup_entries() -> List[dict]:
    """Return all startup entries from Windows Run registry keys, Startup folders, Disabled stores and UWP apps."""
    if not _is_windows():
        return []

    entries = []
    seen = set()

    # 1. Classic Registry Run keys (HKCU, HKLM, WOW6432Node)
    reg_locs = [
        ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Current user Run"),
        ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "All users Run"),
        ("HKLM-32", winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "All users (32-bit) Run"),
    ]
    for hive_name, hive, subkey, location in reg_locs:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    name, command, _ = winreg.EnumValue(key, index)
                    raw_name = name.strip()
                    if raw_name.lower() in ("wintweaker", "vatrixtweaker"):
                        continue
                    clean_name = format_startup_display_name(raw_name)

                    # Check if Task Manager StartupApproved has marked it disabled
                    is_enabled = True
                    try:
                        approved_sub = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" if hive_name == "HKCU" else (
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32" if hive_name == "HKLM-32" else
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
                        )
                        appr_hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
                        with winreg.OpenKey(appr_hive, approved_sub) as ak:
                            val, _ = winreg.QueryValueEx(ak, raw_name)
                            if len(val) > 0 and val[0] % 2 != 0:
                                is_enabled = False
                    except OSError:
                        pass

                    seen.add(raw_name.lower())
                    seen.add(clean_name.lower())
                    entries.append({
                        "id": f"registry|{hive_name}|{raw_name}",
                        "name": clean_name,
                        "raw_name": raw_name,
                        "command": str(command),
                        "location": location,
                        "enabled": is_enabled,
                        "kind": "registry",
                        "hive": hive_name,
                    })
        except OSError:
            pass

    # 2. Disabled Startup keys in VATRIXTweaker and WinTweaker stores
    for store_path in (r"Software\VATRIXTweaker\DisabledStartup", r"Software\WinTweaker\DisabledStartup"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, store_path) as key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    token = winreg.EnumKey(key, index)
                    try:
                        with winreg.OpenKey(key, token) as entry_key:
                            values = {
                                winreg.EnumValue(entry_key, vi)[0]: winreg.EnumValue(entry_key, vi)[1]
                                for vi in range(winreg.QueryInfoKey(entry_key)[1])
                            }
                        original_id = _startup_token_value(token)
                        raw_name = values.get("RawName") or values.get("Name") or original_id
                        clean_name = format_startup_display_name(raw_name)
                        if raw_name.lower() in ("wintweaker", "vatrixtweaker") or clean_name.lower() in ("wintweaker", "vatrixtweaker"):
                            continue
                        if raw_name.lower() in seen or clean_name.lower() in seen:
                            continue
                        seen.add(raw_name.lower())
                        seen.add(clean_name.lower())
                        entries.append({
                            "id": original_id if original_id.startswith("registry|") else f"disabled|{store_path}|{token}",
                            "name": clean_name,
                            "raw_name": raw_name,
                            "command": values.get("Command", ""),
                            "location": values.get("Location", "Disabled startup"),
                            "enabled": False,
                            "kind": "disabled_store",
                            "hive": values.get("Hive", "HKCU"),
                            "token": token,
                            "store_path": store_path,
                        })
                    except (OSError, UnicodeError):
                        pass
        except OSError:
            pass

    # 3. Startup Folders
    startup_folders = [
        (Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup", "User Startup folder"),
        (Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup", "All users Startup folder"),
    ]
    for folder, location in startup_folders:
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.name.lower() != "desktop.ini":
                is_disabled = path.name.endswith(".disabled")
                base_file_name = path.name[:-9] if is_disabled else path.name
                clean_name = base_file_name.removesuffix(".lnk")
                if clean_name.lower() in seen or clean_name.lower() in ("wintweaker", "vatrixtweaker"):
                    continue
                seen.add(clean_name.lower())
                seen.add(base_file_name.lower())
                entries.append({
                    "id": f"folder|{path}",
                    "name": format_startup_display_name(clean_name),
                    "raw_name": path.name,
                    "command": str(path),
                    "location": location,
                    "enabled": not is_disabled,
                    "kind": "folder",
                    "path": str(path),
                })

    # 4. AppModel UWP Package StartupTasks (Teams, Spotify, etc.)
    try:
        base = r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as k:
            for i in range(winreg.QueryInfoKey(k)[0]):
                pkg = winreg.EnumKey(k, i)
                try:
                    pkg_path = f"{base}\\{pkg}"
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, pkg_path) as pk:
                        for j in range(winreg.QueryInfoKey(pk)[0]):
                            sub = winreg.EnumKey(pk, j)
                            if "startuptask" in sub.lower():
                                task_path = f"{pkg_path}\\{sub}"
                                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, task_path) as tk:
                                    state_val, _ = winreg.QueryValueEx(tk, "State")
                                    app_clean = pkg.split("_")[0]
                                    clean_name = format_startup_display_name(app_clean)
                                    if clean_name.lower() in ("wintweaker", "vatrixtweaker"):
                                        continue
                                    if clean_name.lower() in seen or sub.lower() in seen:
                                        continue
                                    seen.add(clean_name.lower())
                                    seen.add(sub.lower())
                                    entries.append({
                                        "id": f"uwp|{task_path}",
                                        "name": clean_name,
                                        "raw_name": sub,
                                        "command": f"Pachet UWP ({sub})",
                                        "location": "Aplicație Windows (UWP)",
                                        "enabled": (state_val == 2),
                                        "kind": "uwp",
                                        "task_path": task_path,
                                    })
                except OSError:
                    pass
    except OSError:
        pass

    # 5. Remaining StartupApproved items with detectable real commands
    edge_dirs = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / r"Microsoft\Edge\Application\msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / r"Microsoft\Edge\Application\msedge.exe",
    ]
    edge_exe = next((p for p in edge_dirs if p.exists()), None)
    if edge_exe and "microsoft edge" not in seen and "edge" not in seen:
        is_edge_enabled = False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run") as ak:
                for i in range(winreg.QueryInfoKey(ak)[1]):
                    n, v, _ = winreg.EnumValue(ak, i)
                    if "edge" in n.lower() and len(v) > 0 and v[0] % 2 == 0:
                        is_edge_enabled = True
        except OSError:
            pass

        seen.add("microsoft edge")
        seen.add("edge")
        entries.append({
            "id": "known|MicrosoftEdge",
            "name": "Microsoft Edge",
            "raw_name": "MicrosoftEdgeAutoLaunch",
            "command": f'"{edge_exe}" --no-startup-window --win-session-start',
            "location": "Pornire automată Edge",
            "enabled": is_edge_enabled,
            "kind": "registry",
            "hive": "HKCU",
        })

    return sorted(entries, key=lambda item: (not item["enabled"], item["name"].lower()))


def set_startup_entry_enabled(entry: dict, enabled: bool) -> str:
    """Enable or disable one startup entry in its real Windows location."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    try:
        kind = entry.get("kind")
        raw_name = entry.get("raw_name") or entry.get("name")
        hive_name = entry.get("hive") or entry.get("hive_name") or "HKCU"
        hive = winreg.HKEY_LOCAL_MACHINE if hive_name.startswith("HKLM") else winreg.HKEY_CURRENT_USER

        # 1. UWP Startup Tasks
        if kind == "uwp":
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, entry["task_path"], 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "State", 0, winreg.REG_DWORD, 2 if enabled else 1)
            entry["enabled"] = enabled
            return "Pornirea automată UWP a fost activată." if enabled else "Pornirea automată UWP a fost dezactivată."

        # 2. Startup Folders
        if kind == "folder":
            path = Path(entry["path"])
            if enabled:
                target = path.with_name(path.name[:-9]) if path.name.endswith(".disabled") else path
                if path != target and path.exists():
                    path.rename(target)
                entry["path"] = str(target)
                entry["enabled"] = True
                try:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder") as ak:
                        b = bytearray(b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                        winreg.SetValueEx(ak, target.name, 0, winreg.REG_BINARY, bytes(b))
                except OSError:
                    pass
                return "Pornirea automată a fost activată."
            else:
                target = path.with_name(path.name + ".disabled") if not path.name.endswith(".disabled") else path
                if path != target and path.exists():
                    path.rename(target)
                entry["path"] = str(target)
                entry["enabled"] = False
                try:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder") as ak:
                        b = bytearray(b"\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                        winreg.SetValueEx(ak, path.name, 0, winreg.REG_BINARY, bytes(b))
                except OSError:
                    pass
                return "Pornirea automată a fost dezactivată."

        # 3. Registry Run & Disabled Stores
        if kind in ("registry", "disabled_store", "known_edge") or not enabled:
            if enabled:
                cmd = entry.get("command", "")
                if not cmd:
                    for st in (r"Software\VATRIXTweaker\DisabledStartup", r"Software\WinTweaker\DisabledStartup"):
                        try:
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, st) as k:
                                for i in range(winreg.QueryInfoKey(k)[0]):
                                    tok = winreg.EnumKey(k, i)
                                    with winreg.OpenKey(k, tok) as sk:
                                        c_val, _ = winreg.QueryValueEx(sk, "Command")
                                        n_val, _ = winreg.QueryValueEx(sk, "Name")
                                        if raw_name.lower() in (n_val.lower(), tok.lower()):
                                            cmd = c_val
                                            break
                        except OSError:
                            pass
                if not cmd:
                    return "Eroare: comanda aplicației nu a fost găsită."

                # Write to Run key
                with winreg.CreateKey(hive, _RUN_KEY) as k:
                    winreg.SetValueEx(k, raw_name, 0, winreg.REG_SZ, cmd)

                # Delete from DisabledStartup in both VATRIXTweaker and WinTweaker
                for st in (r"Software\VATRIXTweaker\DisabledStartup", r"Software\WinTweaker\DisabledStartup"):
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, st, 0, winreg.KEY_SET_VALUE) as sk:
                            tok = entry.get("token") or _startup_token(entry.get("id", ""))
                            winreg.DeleteKey(sk, tok)
                    except OSError:
                        pass

                # Set Task Manager StartupApproved to 0x02 (Enabled)
                try:
                    approved_sub = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
                    with winreg.CreateKey(hive, approved_sub) as ak:
                        b = bytearray(b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                        winreg.SetValueEx(ak, raw_name, 0, winreg.REG_BINARY, bytes(b))
                except OSError:
                    pass

                entry["enabled"] = True
                entry["kind"] = "registry"
                return "Pornirea automată a fost activată."

            else:
                # Disabling: Read command if not present
                cmd = entry.get("command", "")
                if not cmd:
                    try:
                        with winreg.OpenKey(hive, _RUN_KEY) as k:
                            cmd, _ = winreg.QueryValueEx(k, raw_name)
                    except OSError:
                        pass

                # Save to DisabledStartup
                tok_id = entry.get("id") or f"registry|{hive_name}|{raw_name}"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{_DISABLED_STARTUP_KEY}\\{_startup_token(tok_id)}") as k:
                    winreg.SetValueEx(k, "Hive", 0, winreg.REG_SZ, hive_name)
                    winreg.SetValueEx(k, "Name", 0, winreg.REG_SZ, entry.get("name") or raw_name)
                    winreg.SetValueEx(k, "RawName", 0, winreg.REG_SZ, raw_name)
                    winreg.SetValueEx(k, "Command", 0, winreg.REG_SZ, cmd)
                    winreg.SetValueEx(k, "Location", 0, winreg.REG_SZ, entry.get("location") or f"{hive_name} Run")

                # Delete from Run key using exact raw_name
                try:
                    with winreg.OpenKey(hive, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                        winreg.DeleteValue(k, raw_name)
                except OSError:
                    pass

                # Set Task Manager StartupApproved to 0x03 (Disabled)
                try:
                    approved_sub = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
                    with winreg.CreateKey(hive, approved_sub) as ak:
                        b = bytearray(b"\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                        winreg.SetValueEx(ak, raw_name, 0, winreg.REG_BINARY, bytes(b))
                except OSError:
                    pass

                entry["enabled"] = False
                entry["kind"] = "disabled_store"
                return "Pornirea automată a fost dezactivată."

        # 4. Approved legacy Task Manager entries
        if kind == "approved":
            with winreg.OpenKey(hive, entry["subkey"], 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                val, typ = winreg.QueryValueEx(k, entry["val_name"])
                b = bytearray(val) if val else bytearray(b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                b[0] = 0x02 if enabled else 0x03
                winreg.SetValueEx(k, entry["val_name"], 0, winreg.REG_BINARY, bytes(b))
            entry["enabled"] = enabled
            return "Pornirea automată a fost activată." if enabled else "Pornirea automată a fost dezactivată."

        return "Stare neschimbată."
    except (OSError, PermissionError) as exc:
        return f"Eroare modificare startup: {exc}"


def disable_startup_entry(entry: dict) -> str:
    """Backward-compatible wrapper used by the legacy Tkinter UI."""
    return set_startup_entry_enabled(entry, False)


def extract_startup_exe_name(command: str) -> str:
    """Extract the executable image name from a startup command."""
    if not command:
        return ""
    import re
    cmd = command.strip()
    match = re.search(r'["\']?([^"\']+\.exe)["\']?', cmd, re.IGNORECASE)
    if match:
        return Path(match.group(1)).name.lower()
    parts = cmd.split()
    if parts:
        return Path(parts[0].strip('"\'')).name.lower()
    return ""


def is_startup_app_running(command: str) -> bool:
    """Return True if the startup app's process is currently running."""
    exe_name = extract_startup_exe_name(command)
    if not exe_name or not _is_windows():
        return False
    try:
        res = _run_silent(["tasklist.exe", "/FI", f"IMAGENAME eq {exe_name}", "/NH"])
        return exe_name.lower() in (res.stdout or "").lower()
    except Exception:
        return False


def launch_startup_app(command: str) -> str:
    """Launch the startup application immediately."""
    if not command or not _is_windows():
        return "Comandă indisponibilă."
    try:
        subprocess.Popen(command, shell=True, **_silent_process_kwargs())
        return "Aplicația a fost pornită."
    except Exception as exc:
        return f"Eroare pornire aplicație: {exc}"


def close_startup_app(command: str) -> str:
    """Terminate the startup application's running process."""
    exe_name = extract_startup_exe_name(command)
    if not exe_name or not _is_windows():
        return "Nume executabil indisponibil."
    try:
        res = _run_silent(["taskkill.exe", "/F", "/IM", exe_name])
        if res.returncode == 0:
            return f"Procesul {exe_name} a fost oprit."
        return f"Procesul {exe_name} nu rulează sau este deja oprit."
    except Exception as exc:
        return f"Eroare închidere proces: {exc}"


def get_installed_programs() -> List[dict]:
    """Query Windows registry for installed applications that can be uninstalled."""
    if not _is_windows():
        return []

    uninstall_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    programs = []
    seen = set()

    for hive, path in uninstall_keys:
        try:
            with winreg.OpenKey(hive, path) as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    subkey_name = winreg.EnumKey(k, i)
                    try:
                        with winreg.OpenKey(k, subkey_name) as sk:
                            vals = {}
                            for j in range(winreg.QueryInfoKey(sk)[1]):
                                v_name, v_val, _ = winreg.EnumValue(sk, j)
                                vals[v_name] = v_val

                            disp_name = str(vals.get("DisplayName", "")).strip()
                            uninst_cmd = str(vals.get("UninstallString", "")).strip()
                            quiet_cmd = str(vals.get("QuietUninstallString", "")).strip()
                            publisher = str(vals.get("Publisher", "")).strip()
                            version = str(vals.get("DisplayVersion", "")).strip()
                            install_loc = str(vals.get("InstallLocation", "")).strip()

                            # Filter system updates / hidden components
                            if not disp_name or not uninst_cmd or vals.get("SystemComponent") == 1:
                                continue
                            if disp_name.lower() in seen:
                                continue

                            seen.add(disp_name.lower())
                            programs.append({
                                "name": disp_name,
                                "publisher": publisher,
                                "version": version,
                                "install_loc": install_loc,
                                "uninstall_cmd": uninst_cmd,
                                "quiet_cmd": quiet_cmd or uninst_cmd,
                                "key_name": subkey_name,
                            })
                    except OSError:
                        pass
        except OSError:
            pass

    return sorted(programs, key=lambda x: x["name"].lower())


def uninstall_program(uninstall_cmd: str) -> str:
    """Launch the application's uninstaller."""
    if not uninstall_cmd or not _is_windows():
        return "Comandă de dezinstalare indisponibilă."
    try:
        expanded_cmd = os.path.expandvars(uninstall_cmd)
        subprocess.Popen(expanded_cmd, shell=True, **_silent_process_kwargs())
        return "Programul de dezinstalare a fost pornit."
    except Exception as exc:
        return f"Eroare la lansarea dezinstalării: {exc}"


def open_windows_uninstaller_panel() -> str:
    """Open Windows Programs and Features / Installed Apps settings."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    try:
        subprocess.Popen("explorer.exe ms-settings:appsfeatures", shell=True)
        return "Panoul de dezinstalare a fost deschis."
    except Exception:
        try:
            subprocess.Popen("control.exe appwiz.cpl", shell=True)
            return "Panoul Programe și Caracteristici a fost deschis."
        except Exception as exc:
            return f"Eroare deschidere panou: {exc}"


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
                winreg.SetValueEx(key, "VATRIXTweaker", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "VATRIXTweaker")
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


class _SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", ctypes.c_ulong),
        ("dwCurrentState", ctypes.c_ulong),
        ("dwControlsAccepted", ctypes.c_ulong),
        ("dwWin32ExitCode", ctypes.c_ulong),
        ("dwServiceSpecificExitCode", ctypes.c_ulong),
        ("dwCheckPoint", ctypes.c_ulong),
        ("dwWaitHint", ctypes.c_ulong),
    ]


def get_service_info(service_name: str) -> dict:
    """Read detailed service parameters directly from Windows registry and in-process SCManager in <1ms."""
    if not _is_windows():
        return {
            "exists": False,
            "enabled": False,
            "running": False,
            "start_type": None,
            "start_type_text": "N/A",
            "status_text": "Disponibil doar pe Windows",
        }

    start_type = None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"SYSTEM\\CurrentControlSet\\Services\\{service_name}") as k:
            start_type, _ = winreg.QueryValueEx(k, "Start")
    except OSError:
        pass

    if start_type is None:
        return {
            "exists": False,
            "enabled": False,
            "running": False,
            "start_type": None,
            "start_type_text": "Neinstalat",
            "status_text": "Serviciu negasit",
        }

    is_disabled = (start_type == 4)
    is_enabled = not is_disabled

    # In-process Windows SCManager query (instantaneous, 0ms)
    is_running = False
    advapi = ctypes.windll.advapi32
    advapi.OpenSCManagerW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
    advapi.OpenSCManagerW.restype = ctypes.c_void_p
    advapi.OpenServiceW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong]
    advapi.OpenServiceW.restype = ctypes.c_void_p
    advapi.CloseServiceHandle.argtypes = [ctypes.c_void_p]
    advapi.CloseServiceHandle.restype = ctypes.c_long
    advapi.QueryServiceStatus.argtypes = [ctypes.c_void_p, ctypes.POINTER(_SERVICE_STATUS)]
    advapi.QueryServiceStatus.restype = ctypes.c_long

    sch = advapi.OpenSCManagerW(None, None, 0x0001)  # SC_MANAGER_CONNECT
    if sch:
        sh = advapi.OpenServiceW(sch, service_name, 0x0004)  # SERVICE_QUERY_STATUS
        if sh:
            st = _SERVICE_STATUS()
            if advapi.QueryServiceStatus(sh, ctypes.byref(st)):
                is_running = (st.dwCurrentState == 4)  # 4 = SERVICE_RUNNING
            advapi.CloseServiceHandle(sh)
        advapi.CloseServiceHandle(sch)

    # Special handling for Delivery Optimization (DoSvc)
    if service_name.lower() in ("dosvc", "deliveryoptimization"):
        do_policy = None
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization") as k:
                do_policy, _ = winreg.QueryValueEx(k, "DODownloadMode")
        except OSError:
            pass
        if do_policy is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\DeliveryOptimization") as k:
                    do_policy, _ = winreg.QueryValueEx(k, "SystemSettingsDownloadMode")
            except OSError:
                pass
        if do_policy == 0 or start_type == 4:
            is_disabled = True
            is_enabled = False

    start_type_map = {
        0: "Boot",
        1: "System",
        2: "Automat",
        3: "Manual",
        4: "Dezactivat",
    }
    st_text = start_type_map.get(start_type, str(start_type))

    if is_running:
        status_text = f"Rulează • {st_text}"
    elif is_disabled:
        status_text = "Oprit • Dezactivat"
    else:
        status_text = f"Oprit • {st_text}"

    return {
        "exists": True,
        "enabled": is_enabled,
        "running": is_running,
        "start_type": start_type,
        "start_type_text": st_text,
        "status_text": status_text,
    }


def get_windows_service_state(service_name: str) -> bool | None:
    """Return True when a service is not disabled, False when disabled."""
    info = get_service_info(service_name)
    if not info.get("exists"):
        return None
    return bool(info.get("enabled"))


def set_windows_service_state(service_name: str, enabled: bool) -> str:
    """Enable/start or stop/disable a Windows service safely without false failures."""
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."

    # Special handling for Delivery Optimization (Windows blocks 'sc.exe config DoSvc' via API)
    if service_name.lower() in ("dosvc", "deliveryoptimization"):
        if enabled:
            _set_registry_dword(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode", 1)
            _set_registry_dword(r"HKCU\Software\Microsoft\Windows\CurrentVersion\DeliveryOptimization", "SystemSettingsDownloadMode", 1)
            _set_registry_dword(r"HKLM\SYSTEM\CurrentControlSet\Services\DoSvc", "Start", 3)
            _run_silent(["sc.exe", "start", "DoSvc"])
            _run_silent(["powershell", "-NoProfile", "-Command", "Start-Service -Name DoSvc -ErrorAction SilentlyContinue"])
            return "Serviciul Delivery Optimization a fost activat (P2P activ)."
        else:
            _run_silent(["sc.exe", "stop", "DoSvc"])
            _run_silent(["powershell", "-NoProfile", "-Command", "Stop-Service -Name DoSvc -Force -ErrorAction SilentlyContinue"])
            _run_silent(["taskkill.exe", "/F", "/FI", "SERVICES eq DoSvc"])
            _set_registry_dword(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode", 0)
            _set_registry_dword(r"HKCU\Software\Microsoft\Windows\CurrentVersion\DeliveryOptimization", "SystemSettingsDownloadMode", 0)
            _set_registry_dword(r"HKLM\SYSTEM\CurrentControlSet\Services\DoSvc", "Start", 4)
            return "Serviciul Delivery Optimization a fost oprit si dezactivat (P2P oprit)."

    if enabled:
        config_res = _run_silent(["sc.exe", "config", service_name, "start=", "auto"])
        if config_res.returncode != 0:
            err = (config_res.stderr or config_res.stdout or "").strip()
            return f"Eroare configurare serviciu: {err}"
        start_res = _run_silent(["sc.exe", "start", service_name])
        start_out = (start_res.stdout or start_res.stderr or "").strip()
        if start_res.returncode != 0 and "1056" not in start_out:
            return f"Serviciu setat pe Automat ({start_out})"
        return f"Serviciul {service_name} a fost activat (Automat, pornit)."
    else:
        _run_silent(["sc.exe", "stop", service_name])
        config_res = _run_silent(["sc.exe", "config", service_name, "start=", "disabled"])
        if config_res.returncode != 0:
            err = (config_res.stderr or config_res.stdout or "").strip()
            return f"Eroare dezactivare serviciu: {err}"
        return f"Serviciul {service_name} a fost oprit și dezactivat."


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
    if action_id == "power_plan":
        try:
            res = _run_silent(["powercfg", "/getactivescheme"])
            out = (res.stdout or "").lower()
            if "ultimate performance" in out:
                return "already_applied"
            return "can_apply"
        except Exception:
            return "can_apply"
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
    res = _run_windows_command([
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
    return "Umbrele de sistem au fost dezactivate." if "success" in res.lower() else res


def disable_telemetry(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    results = [
        _set_registry_dword(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
        _set_registry_dword(r"HKCU\Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0),
    ]
    return "Telemetria Windows a fost dezactivată." if any("success" in r.lower() for r in results) else "; ".join(results)


def clean_prefetch(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    script = "Get-ChildItem -LiteralPath $env:SystemRoot\\Prefetch -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"
    res = _run_windows_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
    if "success" in res.lower() or not res.strip():
        return "Cache-ul Prefetch a fost curățat."
    return res


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
    res = _run_windows_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
    if "nagle" in res.lower() or "success" in res.lower():
        return "Latența rețelei (Nagle) a fost optimizată."
    return res


def disable_animations(profile_name: str) -> str:
    if not _is_windows():
        return "Funcție disponibilă doar pe Windows."
    _set_registry_value(r"HKCU\Control Panel\Desktop\WindowMetrics", "MinAnimate", "REG_SZ", "0")
    _set_registry_dword(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", 0)
    res = _run_windows_command([
        "reg",
        "add",
        "HKCU\\Control Panel\\Desktop",
        "/v",
        "UserPreferencesMask",
        "/t",
        "REG_BINARY",
        "/d",
        "90000000",
        "/f",
    ])
    return "Animațiile de sistem au fost dezactivate." if "success" in res.lower() else res


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


_BACKUP_DIR = Path(os.environ.get("PROGRAMDATA", Path.home())) / "VATRIXTweaker" / "backups"
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
        return "Nu există un backup VATRIXTweaker pentru restaurare."
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
