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
| **M1** | Setups hub — install community setups via their own installers; ML4W first, backup/restore. *(in progress — ML4W done)* |
| **M2** | More setups — Omarchy, end-4, HyDE, Caelestia… one deliberate registry entry at a time. *(planned)* |
| **M3** | Appearance / Animations / Input — config editor, behind a GUI-owned override layer the Lua sources. *(planned)* |
| **M4** | Package for the private `kirotux-repo`. *(planned)* |

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
