#!/usr/bin/env python3
"""
Sortify — a fast, safe, dependency-free file organizer.

Tidies a messy folder by moving files into clean category sub-folders
(Images, Documents, Audio, Video, Archives, Code, ...). Supports a
non-destructive dry-run preview, recursive scanning, "by date" mode and a
full undo of the last run via an auto-generated journal.

Usage examples
--------------
    python3 sortify.py ~/Downloads --dry-run
    python3 sortify.py ~/Downloads
    python3 sortify.py ~/Downloads --by date
    python3 sortify.py ~/Downloads --undo

Zero third-party dependencies. Works on Python 3.7+.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------- 
# Category map: folder name -> set of extensions (lowercase, with dot)
# -----------------------------------------------------------------------------
CATEGORIES: dict[str, set[str]] = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
               ".heic", ".tiff", ".ico", ".raw"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md",
                  ".tex", ".pages", ".epub"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
    "Presentations": {".ppt", ".pptx", ".key", ".odp"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".tgz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp",
             ".go", ".rs", ".rb", ".php", ".sh", ".json", ".xml", ".yml",
             ".yaml", ".sql", ".ipynb"},
    "Installers": {".dmg", ".pkg", ".exe", ".msi", ".deb", ".rpm", ".apk"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
}

OTHER = "Other"
JOURNAL = ".sortify-journal.json"


# ----------------------------------------------------------------------------- 
# Tiny ANSI color helper (auto-disables when not a TTY or NO_COLOR is set)
# -----------------------------------------------------------------------------
class C:
    enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @staticmethod
    def _w(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if C.enabled else s

    dim = staticmethod(lambda s: C._w("2", s))
    bold = staticmethod(lambda s: C._w("1", s))
    green = staticmethod(lambda s: C._w("32", s))
    yellow = staticmethod(lambda s: C._w("33", s))
    blue = staticmethod(lambda s: C._w("34", s))
    cyan = staticmethod(lambda s: C._w("36", s))
    red = staticmethod(lambda s: C._w("31", s))


def category_for(ext: str) -> str:
    ext = ext.lower()
    for name, exts in CATEGORIES.items():
        if ext in exts:
            return name
    return OTHER


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def unique_destination(dest: Path) -> Path:
    """Avoid clobbering: file.txt -> file (1).txt -> file (2).txt ..."""
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def collect_files(root: Path, recursive: bool) -> list[Path]:
    skip_dirs = set(CATEGORIES) | {OTHER}
    files: list[Path] = []
    if recursive:
        for path in root.rglob("*"):
            if path.is_file() and not path.name.startswith(".") \
                    and skip_dirs.isdisjoint(set(p.name for p in path.parents)):
                files.append(path)
    else:
        for path in root.iterdir():
            if path.is_file() and not path.name.startswith("."):
                files.append(path)
    return files


def target_folder(root: Path, path: Path, mode: str) -> Path:
    if mode == "date":
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return root / mtime.strftime("%Y") / mtime.strftime("%Y-%m")
    return root / category_for(path.suffix)


def organize(root: Path, mode: str, recursive: bool, dry_run: bool) -> None:
    files = collect_files(root, recursive)
    if not files:
        print(C.yellow("Nothing to organize — the folder is already tidy. ✨"))
        return

    plan: list[tuple[Path, Path]] = []
    for f in files:
        folder = target_folder(root, f, mode)
        dest = unique_destination(folder / f.name)
        if dest.parent.resolve() != f.parent.resolve():
            plan.append((f, dest))

    if not plan:
        print(C.yellow("Everything is already in the right place. ✨"))
        return

    # Summary grouped by destination folder
    groups: dict[str, list[tuple[Path, Path]]] = {}
    total_size = 0
    for src, dest in plan:
        groups.setdefault(dest.parent.name, []).append((src, dest))
        try:
            total_size += src.stat().st_size
        except OSError:
            pass

    header = "DRY RUN — no files moved" if dry_run else "Organizing"
    print(C.bold(C.cyan(f"\n  Sortify · {header}")))
    print(C.dim(f"  {root}\n"))

    for folder in sorted(groups):
        items = groups[folder]
        print(f"  {C.blue('▸')} {C.bold(folder)} {C.dim(f'({len(items)} files)')}")
        for src, _dest in items[:6]:
            print(f"      {C.dim('•')} {src.name}")
        if len(items) > 6:
            print(C.dim(f"      … and {len(items) - 6} more"))

    print()
    print(C.dim(f"  {len(plan)} files · {human_size(total_size)} total"))

    if dry_run:
        print(C.yellow("\n  Re-run without --dry-run to apply these changes.\n"))
        return

    moved: list[dict[str, str]] = []
    for src, dest in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dest))
            moved.append({"from": str(src), "to": str(dest)})
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(C.red(f"  ! Failed to move {src.name}: {exc}"))

    journal_path = root / JOURNAL
    journal_path.write_text(json.dumps({
        "created": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "moves": moved,
    }, indent=2))

    print(C.green(f"\n  ✓ Moved {len(moved)} files."))
    print(C.dim(f"  Undo anytime:  python3 {Path(sys.argv[0]).name} \"{root}\" --undo\n"))


def undo(root: Path) -> None:
    journal_path = root / JOURNAL
    if not journal_path.exists():
        print(C.red("  No journal found — nothing to undo in this folder."))
        return

    data = json.loads(journal_path.read_text())
    moves = data.get("moves", [])
    restored = 0
    # Reverse order so nested dirs unwind cleanly.
    for entry in reversed(moves):
        src, dest = Path(entry["to"]), Path(entry["from"])
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(src), str(unique_destination(dest)))
                restored += 1
            except Exception as exc:  # noqa: BLE001
                print(C.red(f"  ! Failed to restore {src.name}: {exc}"))

    # Remove now-empty category folders we may have created.
    for folder in set(CATEGORIES) | {OTHER}:
        p = root / folder
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()

    journal_path.unlink(missing_ok=True)
    print(C.green(f"\n  ↩ Restored {restored} files to their original location.\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sortify",
        description="Tidy a messy folder by sorting files into clean sub-folders.",
    )
    parser.add_argument("folder", type=str, help="The folder to organize.")
    parser.add_argument("--by", choices=["type", "date"], default="type",
                        help="Sort into category folders (default) or YEAR/YEAR-MONTH folders.")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Also scan sub-folders.")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Preview the changes without moving anything.")
    parser.add_argument("--undo", action="store_true",
                        help="Revert the most recent run in this folder.")
    args = parser.parse_args(argv)

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        print(C.red(f"  Error: '{root}' is not a directory."))
        return 1

    try:
        if args.undo:
            undo(root)
        else:
            organize(root, args.by, args.recursive, args.dry_run)
    except KeyboardInterrupt:
        print(C.yellow("\n  Cancelled."))
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
