# Hyprland Tweak Tool

A GTK4 hub for the [Hyprland](https://hyprland.org/) Wayland compositor.

Hyprland Tweak Tool is first a **setup hub**: it installs the polished free
community Hyprland setups by running each project's own official installer in a
visible terminal — no bundling, no sudo from the app. Later milestones add a
config editor for appearance, animations, keybindings, input and monitors.

> **Status: Setups hub (walking skeleton).** The first tab installs **ML4W** via
> its upstream installer, backing up your Hyprland config first and offering
> restore. The architecture (GTK4 `Gtk.Application` → `htt_gui` → toolkit-free
> `htt_setups` engine) mirrors
> [fish-tweak-tool](https://github.com/kirodubes/fish-tweak-tool).

## Roadmap

| Milestone | Scope |
|-----------|-------|
| **M0** | Scaffold — GTK4 skeleton, launcher, desktop entry. *(done)* |
| **M1** | Setups hub — install the community setups (ML4W, JaKooLit, Omarchy, end-4, HyDE, Caelestia) via their own installers, with risk markers, Timeshift safety, and a Restore action. *(done)* |
| **M2** | Config editor — Appearance / Animations / Input, via a GUI-owned override file the Lua config sources. *(planned)* |
| **M3** | Backup & recovery tab — manual snapshot, rollback. *(planned)* |

## Requirements

- `hyprland` — the compositor being configured
- GTK4 + PyGObject (`python-gobject`)

## Running

```bash
# Via launcher (after installation)
hyprland-tweak-tool

# Directly from the source tree
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py

# With debug output
python3 usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py --debug
```

No sudo required — runs as the current user.

## License

GPL-3.0 — see [LICENSE](LICENSE)
