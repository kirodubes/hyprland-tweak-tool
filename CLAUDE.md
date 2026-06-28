# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Hyprland Tweak Tool (HTT) is a standalone GTK4 Python application for the
[Hyprland](https://hyprland.org/) Wayland compositor. It is a **hub** that installs the
polished community Hyprland setups by running each project's own official installer in a
visible terminal — it never bundles or redistributes their files. It is a post-install,
per-user tool. Its architecture mirrors **fish-tweak-tool**; read that project first when
extending this one.

- **Language**: Python 3.8+
- **GUI Framework**: GTK4 + PyGObject
- **Entry Point**: `usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py`
- **Launcher**: `usr/bin/hyprland-tweak-tool`
- **Desktop Entry**: `usr/share/applications/hyprland-tweak-tool.desktop`
- **Runs as normal user** — no sudo, no pkexec; never add root escalation. Installers that
  need root ask for it themselves, in the visible terminal.

## Architecture

```
usr/share/hyprland-tweak-tool/
├── hyprland-tweak-tool.py   # Entry point: Gtk.Application + Main window
├── htt_gui.py               # GUI: header bar + Notebook (Setups tab; more tabs later)
├── htt_setups.py            # Setup registry + install/restore engine (toolkit-free, headless-testable)
├── htt_config.py            # App preferences (window size, …)
├── log.py                   # Logging: log_section / log_info / log_success / ...
└── htt.css                  # GTK4 stylesheet
```

`htt_setups.py` is deliberately GTK-free (like fish-tweak-tool's `ftt_fisher`) so it stays
unit-testable. Each setup is installed by running that project's **own** upstream installer in a
visible terminal (`run_visibly`, a bash adaptation of `ftt_fisher.run_visibly`). Mutating calls
run in a daemon thread and hand back a `Result(ok, message)`. System-rewriting setups (those
that touch the bootloader, display manager or pacman mirrorlist) are marked high-risk and require
a Timeshift snapshot first.

Modules are prefixed `htt_` (parallel to fish-tweak-tool's `ftt_`). The entry point keeps the
hyphenated `hyprland-tweak-tool.py` name because it is executed, never imported.

### Data Locations

| What              | Path                                            |
|-------------------|-------------------------------------------------|
| App preferences   | `~/.config/hyprland-tweak-tool/prefs.json`      |
| Kiro golden config| `/usr/share/kiro/hyprland/` (read-only, restore source) |

## Roadmap (milestones)

- **M0** — Scaffold (done): GTK4 skeleton, launcher, desktop entry.
- **M1** — Setups hub (done): install the community setups via their own installers (ML4W,
  JaKooLit, Omarchy, end-4, HyDE, Caelestia), ordered safest → most hazardous with a hazard
  marker on the system-rewriting ones; per-setup risk tier, consent dialog, mandatory Timeshift
  snapshot for high-risk, a Timeshift-ready pre-check, a post-install reboot prompt, and a
  "Restore Kiro Hyprland" reset from the golden copy.
- **M2** — Config editor (Appearance / Animations / Input). The Kiro Hyprland config is a Lua
  program (`hyprland.lua`). **Do not edit it directly** — a GUI should own a separate declarative
  override file that the Lua *sources*; humans own the base Lua. `hyprctl keyword` does NOT work
  on a Lua config — apply via edit + `hyprctl reload`.
- **M3** — Backup & recovery tab (manual snapshot, rollback).

## Development Patterns

### Logging

All output uses `log.py` (never bare `print()`): `log_section` / `log_info` /
`log_success` / `log_warn` / `log_error` / `debug_print` / `log_timing`.

### GTK4 Callbacks

Unused GTK signal parameters are named `_widget` (never `widget`).

### Subprocess

Never use `subprocess.call()` from a GUI callback — always `Popen` in a daemon thread. Any
command that *changes the user's system* must run in a **visible terminal** that prints the exact
command first — never a hidden subprocess.

### Markup

Ampersands in `set_markup()` must be escaped as `&amp;` (or via `GLib.markup_escape_text`) or the
label renders empty.

### Verifying the GUI

Render-test with a throwaway `NON_UNIQUE` app id, never the real
`com.kiro.hyprland-tweak-tool` (single-instance: a remote launch won't activate).
**Never `pkill` to clear leftovers** — it kills the user's own running instance.

### Code Style

- `ruff check` must pass before any Python work is considered done; auto-fix without asking.
- Max line length: 120. `snake_case` funcs/vars, `PascalCase` classes.
- One-line docstrings on public functions/methods (PEP 257); private (`_`-prefixed) functions
  don't require them.
- Section dividers (`# ── Name ──────`) only in functions 50+ lines.

## Running the Application

```bash
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py        # direct (no sudo)
hyprland-tweak-tool                                                # via launcher
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py --debug
```
