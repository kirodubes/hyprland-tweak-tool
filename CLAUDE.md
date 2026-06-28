# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Hyprland Tweak Tool (HTT) is a standalone GTK4 Python application for configuring
the [Hyprland](https://hyprland.org/) Wayland compositor. It is a post-install,
per-user tool (no sudo). Its architecture deliberately mirrors **fish-tweak-tool**
(`~/KIRO/fish-tweak-tool`) — read that project first when extending this one.

This is a **KIROTUX** product (Kiro's premium Hyprland edition): it lives in
`~/KIROTUX/`, never goes into KIB, and is private — do not publish without
explicit OK.

- **Language**: Python 3.8+
- **GUI Framework**: GTK4 + PyGObject
- **Entry Point**: `usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py`
- **Launcher**: `usr/bin/hyprland-tweak-tool`
- **Desktop Entry**: `usr/share/applications/hyprland-tweak-tool.desktop`
- **Runs as normal user** — no sudo, no pkexec; never add root escalation

## Architecture

```
usr/share/hyprland-tweak-tool/
├── hyprland-tweak-tool.py   # Entry point: Gtk.Application + Main window
├── htt_gui.py               # GUI: header bar + Notebook (Setups tab; config tabs later)
├── htt_setups.py            # Setup registry + install engine (toolkit-free, headless-testable)
├── htt_config.py            # App preferences (window size, …)
├── log.py                   # Logging: log_section / log_info / log_success / ...
└── htt.css                  # GTK4 stylesheet
```

`htt_setups.py` is deliberately GTK-free (like fish-tweak-tool's `ftt_fisher`) so it stays
unit-testable. HTT is a **hub**: it installs each community setup by running that project's
**own** upstream installer in a visible terminal (`run_visibly`, a bash adaptation of
`ftt_fisher.run_visibly`) — it never bundles or redistributes their files. Mutating calls run
in a daemon thread and hand back a `Result(ok, message, backup)`; a snapshot of the Hyprland
config dirs is taken before install so it's reversible.

Modules are prefixed `htt_` (parallel to fish-tweak-tool's `ftt_`). The entry
point keeps the hyphenated `hyprland-tweak-tool.py` name because it is executed,
never imported.

### Data Locations

| What              | Path                                            |
|-------------------|-------------------------------------------------|
| App preferences   | `~/.config/hyprland-tweak-tool/prefs.json`      |
| User Hyprland conf| `~/.config/hypr/hyprland.conf` (M1+ only)       |

## Roadmap (milestones)

HTT's reason-to-exist is now the **setup hub** (install the free community Hyprland setups),
not the config editor — the editor faces the ADR-002 "Lua is GUI-hostile" problem and lands later.

- **M0** — Scaffold (done): GTK4 skeleton, launcher, desktop entry.
- **M1** — Setups hub (in progress): install setups via their own installers; **ML4W done**
  (Rolling default = Hyprland 0.55.x; backup-first + restore).
- **M2** — More setups: Omarchy, end-4, HyDE, Caelestia, JaKooLit — one deliberate `SETUPS`
  registry entry at a time (ADR-003/004: each upstream installer is inherited maintenance).
- **M3** — Config editor (Appearance / Animations / Input). **Do not edit `hyprland.lua`
  directly.** Per the HQ decision register (ADR-002), the GUI owns a declarative override file
  the Lua *sources*; humans own the base Lua. `hyprctl keyword` does NOT work on a Lua config —
  apply via edit + `hyprctl reload`. See the Kiro-HQ/Kirotux decision register before building.
- **M4** — Package for the private `kirotux-repo`.

## Development Patterns

### Logging

All output uses `log.py` (never bare `print()`): `log_section` / `log_info` /
`log_success` / `log_warn` / `log_error` / `debug_print` / `log_timing`.

### GTK4 Callbacks

Unused GTK signal parameters are named `_widget` (never `widget`).

### Subprocess

Never use `subprocess.call()` from a GUI callback — always `Popen` in a daemon
thread. Any command that *changes the user's system* must run in a **visible
terminal** that prints the exact command first — never a hidden subprocess.

### Markup

Ampersands in `set_markup()` must be escaped as `&amp;` or the label renders empty.

### Verifying the GUI

Render-test with a throwaway `NON_UNIQUE` app id, never the real
`com.kiro.hyprland-tweak-tool` (single-instance: a remote launch won't activate).
**Never `pkill` to clear leftovers** — it kills the user's own running instance.

### Code Style

- `ruff check` must pass before any Python work is considered done; auto-fix
  without asking.
- Max line length: 120. `snake_case` funcs/vars, `PascalCase` classes.
- One-line docstrings on public functions/methods (PEP 257); private
  (`_`-prefixed) functions don't require them.
- Section dividers (`# ── Name ──────`) only in functions 50+ lines.

## Running the Application

```bash
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py        # direct (no sudo)
hyprland-tweak-tool                                                # via launcher
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py --debug
```
