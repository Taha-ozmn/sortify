# 🗂️ Sortify

> A fast, safe, dependency-free file organizer for your messiest folders.

Sortify tidies a cluttered folder (looking at you, `~/Downloads`) by moving files into clean category sub-folders — **Images, Documents, Audio, Video, Code, Archives** and more. It previews before it touches anything and can completely undo its last run.

```
  Sortify · Organizing
  /Users/you/Downloads

  ▸ Images (42 files)
      • screenshot.png
      • invoice.jpg
      … and 40 more
  ▸ Documents (18 files)
      • report.pdf

  60 files · 214.8 MB total

  ✓ Moved 60 files.
  Undo anytime:  python3 sortify.py "/Users/you/Downloads" --undo
```

## ✨ Features

- **Dry-run preview** (`--dry-run`) — see exactly what will move before anything happens
- **Full undo** (`--undo`) — reverts the last run from an auto-generated journal
- **Two modes** — sort `by type` (default) or `by date` (`YEAR/YEAR-MONTH` folders)
- **Recursive** scanning (`-r`)
- **Never overwrites** — collisions become `file (1).ext`, `file (2).ext`, …
- **Zero dependencies** — pure Python standard library, works on 3.7+
- Colored, readable output that respects `NO_COLOR`

## 🚀 Usage

```bash
# Preview the changes (recommended first step)
python3 sortify.py ~/Downloads --dry-run

# Apply
python3 sortify.py ~/Downloads

# Organize by date instead of type
python3 sortify.py ~/Downloads --by date

# Include sub-folders
python3 sortify.py ~/Downloads -r

# Changed your mind? Undo the last run.
python3 sortify.py ~/Downloads --undo
```

### Options

| Flag | Description |
|------|-------------|
| `--by {type,date}` | Sort into category folders (default) or date folders |
| `-r`, `--recursive` | Also scan sub-folders |
| `-n`, `--dry-run` | Preview without moving anything |
| `--undo` | Revert the most recent run in the folder |

## 🛟 Safety

Every applied run writes a `.sortify-journal.json` to the target folder. `--undo` reads it to restore each file to its original path and clean up empty folders. Nothing is ever deleted.

## License

[MIT](./LICENSE)
