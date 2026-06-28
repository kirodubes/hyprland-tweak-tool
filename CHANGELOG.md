# Changelog

## 2026.06.28

### What Changed

- **M0 scaffold created** — stood up Hyprland Tweak Tool as a GTK4 Python app
  whose architecture mirrors fish-tweak-tool. The app launches to a header bar
  (title · Hyprland version · Support · Quit) over a centered "Coming soon"
  notice. Removed the empty `coming-soon` placeholder file.
- **Reframed as a setup hub + ML4W as the first installable setup** — replaced the
  coming-soon body with a Notebook whose first tab, **Setups**, installs a community
  Hyprland setup by running its **own** upstream installer in a visible terminal
  (HTT bundles nothing). The ML4W card offers a Rolling (Hyprland 0.55.x, default)
  / Stable variant, an opt-in "back up my Hyprland config first" snapshot, and a
  "Restore a backup…" affordance. Rolling leads because it targets 0.55.x — Kiro
  Hyprland's version. This gives HTT a shippable purpose before the (harder, Lua-
  override-layer) config editor is built.
- **Added Omarchy as the second setup** — one `SETUPS` registry entry
  (`wget -qO- https://omarchy.org/install | bash`). Its tagline flags honestly that
  Omarchy is a full-desktop *bootstrap* (rewrites the pacman mirrorlist, installs a
  whole desktop), meant for a fresh/minimal Arch — more invasive than ML4W's dotfiles.
- **Filled the setup roster — added end-4, HyDE, Caelestia, JaKooLit** — four more
  registry entries, each invoking the project's own upstream installer with an honest
  tagline: end-4 (Quickshell, builds quickshell-git + ~13 pkgs), HyDE (overwrites
  GTK/Qt/SDDM/GRUB on existing Arch), Caelestia (AUR via paru + `caelestia install`),
  JaKooLit (Arch-Hyprland installer; flags the March 2026 archival/fork). Six setups
  total; the Setups tab is a scrollable card list.
- **Bootability safety — the real concern with a hub of other people's installers.**
  Per-setup `risk` tier (`high` for Omarchy + HyDE, which rewrite the pacman mirrorlist
  / GRUB / SDDM — the things that brick a boot). Install now goes through a **consent
  dialog** naming what the installer changes; high-risk setups require a **Timeshift
  snapshot first** (`sudo timeshift --create … --scripted &&` prefixed onto the command
  in the visible terminal — that's the dependable way back to a bootable Kiro Hyprland,
  and bash `&&` means a failed snapshot aborts the install). Low-risk setups get a
  warning + an optional snapshot checkbox.
- **Post-install "Reboot now" popup** — a setup only takes effect after a reboot (ML4W
  confirmed this), so a successful install raises a dialog offering **Reboot now**
  (`systemctl reboot`) or Later.
- Replaced the misleading config-only "back up ~/.config" mechanism (it couldn't undo
  boot/DM/pacman changes) with the Timeshift snapshot; removed `snapshot_now` /
  `list_backups` / `restore_backup` and the "Restore a backup…" button.
- **Ordered the card list by reliability** — the setups that install cleanly lead
  (ML4W, then JaKooLit), with the riskier / less-reliable ones (Omarchy, end-4, HyDE,
  Caelestia) below.
- **"Restore Kiro Hyprland" — the config-level way back.** The `kiro-hyprland` package
  now ships a pristine golden copy of its config at `/usr/share/kiro/hyprland/`; HTT
  reads it to **remove** the user's hypr/waybar/mako/gtk dirs and **rewrite** Kiro's
  (each removed dir is moved to a timestamped backup under
  `~/.config/hyprland-tweak-tool/before-kiro-restore/` first). This clears leftovers a
  setup leaves behind — e.g. a foreign waybar — which an overlay copy would miss. The
  button only appears on a Kiro system (where the golden copy exists); a confirm dialog
  precedes it and a reboot/relogin prompt follows. (`kiro_restore_available`,
  `restore_kiro_hyprland`.)
- **Timeshift pre-check** (`htt_setups.timeshift_ready`) — before a required snapshot,
  verify Timeshift is installed *and* configured (a `backup_device_uuid` in
  `/etc/timeshift/timeshift.json`). If not, a high-risk install is **blocked** with a
  "Set up Timeshift first" dialog that tells the user exactly what to do
  (`sudo timeshift-gtk` → pick a location → create one snapshot). Same guard runs when
  a low-risk setup's optional snapshot is ticked. Stops a user requesting the safety
  net only to silently get none.

### Technical Details

- Entry point `hyprland-tweak-tool.py`: `Gtk.Application`
  (`com.kiro.hyprland-tweak-tool`) + `Main` window. Carries the same UTF-8-mode
  re-exec guard and locale fallback as fish-tweak-tool. `_hyprland_version()`
  parses `hyprctl version`, falling back to `Hyprland --version`, then
  `"unknown"`.
- Per-domain modules use the `htt_` prefix (parallel to `ftt_`): `htt_gui.py`
  builds the window and support dialog; `htt_config.py` stores app prefs under
  `~/.config/hyprland-tweak-tool/prefs.json` (read-modify-write so future tabs
  never clobber each other); `log.py` is the shared colored logger.
- `htt.css` carries the title / info-label / support-button / placeholder /
  status-line classes; the feature-specific classes will return with their tabs.
- Bash launcher `usr/bin/hyprland-tweak-tool` checks for `python3` and
  `Hyprland`; `.desktop` entry under `usr/share/applications/`.
- Added `.gitignore` and `.flake8` (max-line-length 120).
- New `htt_setups.py` (toolkit-free engine, modelled on `ftt_fisher.py`): a `Setup`
  data model + `SETUPS` registry (ML4W only, list-shaped for more), `run_async` →
  `run_visibly` (a **bash** adaptation of the fish runner, because the installer
  uses `bash <(curl …)` process substitution; Alacritty `-e bash <script>`, echoes
  the command first), `Result(ok, message, backup)`, and snapshot/list/restore
  helpers over `~/.config/{hypr,waybar,mako,gtk-3.0,gtk-4.0}` →
  `~/.config/hyprland-tweak-tool/backups`. `is_installed` is a best-effort badge.
- `htt_gui.py` gains a `_StatusMixin` (ATT-orange auto-clearing status line, UI
  marshalled via `GLib.idle_add`) and a `SetupsTab` of setup cards; `build()` now
  hosts a `Gtk.Notebook` instead of the coming-soon `_notice`. Install runs off the
  UI thread; the GUI is a thin client of the CLI command (ADR-001).
- `htt.css` adds `.setup-card` (+ reuses `.plugin-name` / `.plugin-desc`).

### Files Modified

- `usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py` (new)
- `usr/share/hyprland-tweak-tool/htt_gui.py` (new; reworked into the Setups hub)
- `usr/share/hyprland-tweak-tool/htt_setups.py` (new — setup registry + install engine)
- `usr/share/hyprland-tweak-tool/htt_config.py` (new)
- `usr/share/hyprland-tweak-tool/log.py` (new)
- `usr/share/hyprland-tweak-tool/htt.css` (new; `.setup-card`)
- `usr/bin/hyprland-tweak-tool` (new)
- `usr/share/applications/hyprland-tweak-tool.desktop` (new)
- `usr/share/hyprland-tweak-tool/coming-soon` (removed)
- `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `.gitignore`, `.flake8` (new)
