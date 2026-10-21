from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional


_REPARSE_POINT = 0x400


@dataclass(frozen=True)
class TempCleanupEstimate:
    bytes_total: int
    file_count: int
    skipped: int
    directories: tuple[str, ...]


@dataclass(frozen=True)
class TempCleanupResult:
    deleted_files: int
    deleted_bytes: int
    skipped: int
    directories: tuple[str, ...]


def format_byte_size(num: int) -> str:
    value = float(max(num, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{int(num)} B"


def temp_directories() -> list[str]:
    candidates = [
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp") if os.environ.get("LOCALAPPDATA") else None,
    ]
    unique: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        if not raw:
            continue
        try:
            resolved = os.path.abspath(raw)
            key = os.path.normcase(resolved)
        except OSError:
            continue
        if key in seen or not os.path.isdir(resolved):
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def estimate_temp_cleanup(roots: Optional[Iterable[str]] = None) -> TempCleanupEstimate:
    directories = tuple(roots) if roots is not None else tuple(temp_directories())
    total = 0
    files = 0
    skipped = 0
    for _path, size, readable in _walk_temp_files(directories):
        if readable:
            total += size
            files += 1
        else:
            skipped += 1
    return TempCleanupEstimate(
        bytes_total=total,
        file_count=files,
        skipped=skipped,
        directories=directories,
    )


def purge_temp_files(roots: Optional[Iterable[str]] = None) -> TempCleanupResult:
    directories = tuple(roots) if roots is not None else tuple(temp_directories())
    deleted_files = 0
    deleted_bytes = 0
    skipped = 0

    for path, size, readable in _walk_temp_files(directories):
        try:
            os.remove(path)
        except OSError:
            skipped += 1
            continue
        deleted_files += 1
        if readable:
            deleted_bytes += size

    for root in directories:
        _remove_empty_directories(root)

    return TempCleanupResult(
        deleted_files=deleted_files,
        deleted_bytes=deleted_bytes,
        skipped=skipped,
        directories=directories,
    )


def _is_reparse_point(path: str) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & _REPARSE_POINT) or os.path.islink(path)


def _walk_temp_files(directories: Iterable[str]) -> Iterator[tuple[str, int, bool]]:
    for root in directories:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            dirnames[:] = [
                name
                for name in dirnames
                if not _is_reparse_point(os.path.join(dirpath, name))
            ]
            for name in filenames:
                path = os.path.join(dirpath, name)
                if _is_reparse_point(path):
                    continue
                try:
                    yield path, os.path.getsize(path), True
                except OSError:
                    yield path, 0, False


def _remove_empty_directories(root: str) -> None:
    for dirpath, dirnames, filenames in os.walk(root, topdown=False, followlinks=False):
        if dirpath == root:
            continue
        if filenames or dirnames:
            continue
        try:
            os.rmdir(dirpath)
        except OSError:
            continue
