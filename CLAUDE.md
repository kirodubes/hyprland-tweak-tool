# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Hyprland Tweak Tool (HTT) is a standalone GTK4 Python application for the
[Hyprland](https://hyprland.org/) Wayland compositor. It is a **hub** that installs the
polished community Hyprland setups by running each project's own official installer in a
visible terminal — it never bundles or redistributes their files. It is a post-install,
per-user tool. Its architecture mirrors **fish-tweak-tool**; read that project first when
extending this one.

HTT is the **free, public base tool** under KIROTUX's open-core model (set 2026-06-28, ADR-011):
the base tool ships free + open and is funded by donations, while a **premium** per-WM SKU
(`hyprland-tweak-tool-premium`) is the only potential paid piece — currently **dormant**, not
built, may never ship. Source for the base tool lives on public GitHub
(`kirodubes/hyprland-tweak-tool` — this repo's `origin`) and the package publishes to the
**public `nemesis_repo`**, *not* the private `kirotux-repo`. Deliver changes with
`~/.bin/flow-htt` (push source → build in chroot → publish to nemesis_repo).

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
├── htt_gui.py               # GUI: header bar + Notebook (Start here · Setups · Backup)
├── htt_setups.py            # Setup registry + install/restore engine (toolkit-free, headless-testable)
├── htt_baseline.py          # "Start here" tab logic: btrfs snapshot stack (toolkit-free)
├── htt_config.py            # App preferences (window size, …)
├── log.py                   # Logging: log_section / log_info / log_success / ...
├── htt.css                  # GTK4 stylesheet
└── scripts/                 # Privileged bash payloads run via `sudo bash` in a visible terminal
    ├── baseline-snapshots-enable.sh
    └── baseline-snapshots-disable.sh
```

`htt_setups.py` and `htt_baseline.py` are deliberately GTK-free (like fish-tweak-tool's
`ftt_fisher`) so they stay unit-testable. Each setup is installed by running that project's
**own** upstream installer in a visible terminal (`run_visibly`, a bash adaptation of
`ftt_fisher.run_visibly`). Mutating calls run in a daemon thread and hand back a
`Result(ok, message)`. System-rewriting setups (those that touch the bootloader, display manager
or pacman mirrorlist) are marked high-risk and require a snapshot first.

`htt_baseline.py` ports ATT's Btrfs page (`btrfs.py` / `btrfs_gui.py`) to KIROTUX: it sets up the
snapper + grub-btrfs snapshot baseline (the multi-step privileged work lives in `scripts/`, run
via `sudo bash <path>` so every step is shown in the terminal). On a non-btrfs root the
"Start here" tab falls back to a Timeshift baseline via the existing `htt_setups` helpers.

Modules are prefixed `htt_` (parallel to fish-tweak-tool's `ftt_`). The entry point keeps the
hyphenated `hyprland-tweak-tool.py` name because it is executed, never imported.

### Data Locations

| What              | Path                                            |
|-------------------|-------------------------------------------------|
| App preferences   | `~/.config/hyprland-tweak-tool/prefs.json`      |
| Kiro golden config| `/usr/share/kiro/kiro-hyprland/` (read-only, restore source) |

## Current state & direction

The milestone (M0–M3) roadmap has been **dropped** — work is now feature-driven, not sequenced.

What exists today:

- **"Start here" tab** (done, first tab): sets up a snapshot baseline to roll back to before
  experimenting. On btrfs it installs/configures the snapper + grub-btrfs stack (ATT's Btrfs page
  ported — bootable snapshots from the GRUB menu); on ext4 it falls back to a Timeshift baseline.
- **Setups hub** (done): installs the community setups via their own installers (ML4W,
  JaKooLit, Omarchy, end-4, HyDE, Caelestia), ordered safest → most hazardous with a hazard
  marker on the system-rewriting ones; per-setup risk tier, consent dialog, mandatory system
  snapshot for high-risk, a snapshot-ready pre-check, a post-install reboot prompt, and a
  "Restore Kiro Hyprland" reset from the golden copy.
- **Backup tab** (done): on-demand full-system snapshot (snapper on btrfs, Timeshift otherwise).

Possible future work (no committed order):

- **Config editor** (Appearance / Animations / Input). The Kiro Hyprland config is a Lua
  program (`hyprland.lua`). **Do not edit it directly** — a GUI should own a separate declarative
  override file that the Lua *sources*; humans own the base Lua. `hyprctl keyword` does NOT work
  on a Lua config — apply via edit + `hyprctl reload`.

## KIROTUX install defaults & snapshot strategy

A KIROTUX Hyprland system installs with **btrfs** (the recommended default in the Calamares
`partition.conf` — `defaultFileSystemType: btrfs`, with ext4/xfs/f2fs still pickable) and
**GRUB** (`kiro_bootloader.conf` `efiBootLoader: grub`; BIOS already used GRUB). HTT should
assume this layout by default.

**Recommend snapper, not Timeshift, on a KIROTUX system.** Timeshift is on board as the
fallback, but on the default btrfs + GRUB layout snapper (with `grub-btrfs`) gives a
**bootable pre-install snapshot in the GRUB menu** — so when a community setup *fails to
install Hyprland* or leaves the system unbootable, the user can roll back straight from GRUB.
That is the exact failure mode this hub guards against, and the reason snapper is preferred.
`snapshot_backend()` already picks snapper on a btrfs root and falls back to Timeshift on
ext4/others; surface snapper as the recommended path when the root is btrfs.

**Recovery is two parts — grub-btrfs can only boot the root snapshot.** The KIROTUX layout puts
`/home` on a separate `@home` subvolume, so a system (root `@`) rollback never reverts `~/.config`.
A single GRUB-menu pick therefore cannot restore both; the home side is always a second action. So
the Start-here baseline configures snapper for **both `root` and `home`** (`snapper -c home`), and
the recovery story is: **(1) system** — boot the root snapshot from the GRUB "Arch Linux snapshots"
submenu; **(2) config** — restore the home baseline (Btrfs Assistant / `snapper -c home`) or use
**Restore Kiro Hyprland** (surgical golden-copy revert of hypr/waybar/mako/gtk). Don't document the
GRUB rollback as a complete way back on its own.

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
