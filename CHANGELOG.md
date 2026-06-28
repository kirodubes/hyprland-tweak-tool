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
- **Ordered the card list safest → most hazardous** — clean dotfile installs lead
  (ML4W, JaKooLit), heavy AUR/build ones next (end-4, Caelestia), and the
  system-breakers **last** (HyDE rewrites GRUB/SDDM; Omarchy rewrites the pacman
  mirrorlist). The two high-risk cards carry a red **"⚠ Can break your system"** hazard
  badge.
- **Dropped the superfluous variant dropdown** for single-variant setups — only ML4W
  (Rolling/Stable) shows a picker; the rest just show the Install button.
- **Added a Backup tab** with a "Back up now" on-demand full-system snapshot (same
  snapshot-ready pre-check as installs). The snapshot-needed dialog is now a shared
  module-level helper used by both the install flow and the Backup tab.
- **Snapshot backend is now filesystem-aware** — `snapshot_backend()` picks **snapper**
  on a btrfs root (`snapper -c root create`; bootable rollback from the GRUB menu with
  grub-btrfs) and falls back to **Timeshift** on ext4 and others. `snapshot_ready()`
  gives backend-specific setup guidance; all user-facing wording is now neutral
  ("system snapshot" rather than naming a tool).
- **"Restore Kiro Hyprland" — the config-level way back.** The `kiro-hyprland` package
  ships a pristine golden copy of its config at `/usr/share/kiro/kiro-hyprland/`; HTT
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
- **Reframed HTT as a free, public open-core tool** — updated `CLAUDE.md` to record the
  2026-06-28 direction change: the base tool ships free + open (public GitHub
  `kirodubes/hyprland-tweak-tool` → public `nemesis_repo`, delivered via `~/.bin/flow-htt`),
  a per-WM `hyprland-tweak-tool-premium` is the only potential paid piece (dormant). Dropped
  the M0–M3 milestone roadmap for a feature-driven "Current state & direction", and documented
  the KIROTUX install defaults (btrfs + GRUB) and why snapper is recommended over Timeshift.
- **New "Start here" first tab — establish a baseline before experimenting.** HTT installs other
  people's setups, some of which rewrite GRUB/SDDM/mirrorlist; the safety story needs the user to
  have a snapshot to roll back to *first*. Ported ATT's Btrfs page to KIROTUX: on a btrfs root the
  tab installs/configures the **snapper + snap-pac + grub-btrfs + btrfs-assistant +
  btrfsmaintenance** stack and takes a baseline snapshot — and because KIROTUX uses **GRUB**, the
  pre-install snapshot becomes a **bootable entry in the GRUB menu** (recovery without a live ISO),
  flipping ATT's systemd-boot caveat. On a non-btrfs root it falls back to a Timeshift baseline.
  Tab order is now **Start here · Setups · Backup**.
- **Baseline now covers `@home` too — fixing "ML4W half-broken after a GRUB rollback".** grub-btrfs
  can only boot the **root** snapshot, and `/home` (`@home`) is a separate subvolume, so a system
  rollback never reverts `~/.config` — a setup that splats your config survived the rollback. The
  enable script now also creates a snapper **`home`** config and takes a home baseline, so your own
  pre-experiment config is recoverable. Recovery is documented as **two parts**: system (GRUB
  snapshot) + config (restore the home baseline via Btrfs Assistant / `snapper -c home`, or
  "Restore Kiro Hyprland"). The Start-here status panel and the Setups "Protected" wording were
  updated to say so. (One GRUB pick still can't pair root + home — that's inherent to the layout.)
- **Setups warnings are now rollback-aware — stop nagging once a baseline exists.** With the
  Start-here snapper baseline, a btrfs system has *continuous* protection (snap-pac on every
  pacman action + bootable grub-btrfs rollback), so forcing an extra snapshot before each install
  is redundant. New `htt_setups.protection_state()` classifies coverage as `snapper` / `timeshift`
  / `none`, and the Setups flow keys off it: **snapper** → no gate, no snapshot, a green
  "Protected — roll back from the GRUB menu" line (fully trust the baseline); **timeshift** (ext4)
  → take a point-in-time snapshot before a high-risk install (unchanged); **none** → gate a
  high-risk install with a dialog pointing at the Start here tab. A one-line coverage banner sits
  above the setup cards.
- **Fixed the Restore golden-copy path.** `kiro-hyprland` was repackaged to install its pristine
  config at `/usr/share/kiro/kiro-hyprland/` (matching the package name), but HTT still read the
  old `/usr/share/kiro/hyprland/`. On a real KIROTUX system that made `kiro_restore_available()`
  return `False` — the "Restore Kiro Hyprland" button never appeared and a restore would have
  failed. Pointed `KIRO_HYPR_SOURCE` at the new path.

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
  UI thread; the GUI is a thin client of the install command.
- `htt.css` adds `.setup-card` (+ reuses `.plugin-name` / `.plugin-desc`).
- **Start here tab:** new toolkit-free `htt_baseline.py` (parallels ATT's `btrfs.py`) — `PACKAGES`
  incl. `grub-btrfs`, read-only state queries (`pacman -Q`, `systemctl is-enabled`,
  `/etc/snapper/configs/root`), and command builders returning `sudo …` strings run through the
  existing `htt_setups.run_async`/`run_visibly`. Privileged work lives in two auditable bash
  scripts (`scripts/baseline-snapshots-{enable,disable}.sh`, `set -euo pipefail`) invoked via
  `sudo bash <path>` (path resolved relative to `__file__`, so it works from the repo and when
  installed). `protection_state()` returns `snapper` (btrfs + `/etc/snapper/configs/root`),
  `timeshift` (non-btrfs + configured), or `none`; `SetupsTab._confirm_install`/`_start_install`
  branch on it (the `state` is threaded into `_start_install` so snapper never forces a snapshot).
  The enable script ports ATT's `/.snapshots` detach→create-config→remount dance
  (KIROTUX pre-stages `@snapshots` — verified in the Calamares `mount.conf`) and adds grub-btrfs
  (`grub-btrfsd` + `grub-mkconfig`). `htt_gui.StartHereTab` mirrors `SetupsTab`/`BackupTab` with a
  `_refresh()` that re-queries state after each op; added public `htt_setups.root_is_btrfs()`.
  No PKGBUILD change — `package()`'s `cp -a usr` ships `scripts/` automatically.

### Files Modified

- `usr/share/hyprland-tweak-tool/hyprland-tweak-tool.py` (new)
- `usr/share/hyprland-tweak-tool/htt_gui.py` (new; reworked into the Setups hub; + `StartHereTab`)
- `usr/share/hyprland-tweak-tool/htt_setups.py` (new — setup registry + install engine; + `root_is_btrfs`)
- `usr/share/hyprland-tweak-tool/htt_baseline.py` (new — "Start here" snapshot-baseline logic)
- `usr/share/hyprland-tweak-tool/scripts/baseline-snapshots-enable.sh` (new)
- `usr/share/hyprland-tweak-tool/scripts/baseline-snapshots-disable.sh` (new)
- `usr/share/hyprland-tweak-tool/htt_config.py` (new)
- `usr/share/hyprland-tweak-tool/log.py` (new)
- `usr/share/hyprland-tweak-tool/htt.css` (new; `.setup-card`)
- `usr/bin/hyprland-tweak-tool` (new)
- `usr/share/applications/hyprland-tweak-tool.desktop` (new)
- `usr/share/hyprland-tweak-tool/coming-soon` (removed)
- `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `.gitignore`, `.flake8` (new)
