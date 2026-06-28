#!/bin/bash
set -euo pipefail
#
# Install + configure the KIROTUX btrfs snapshot baseline. Run as root via
# `sudo bash` from Hyprland Tweak Tool's "Start here" tab, in a visible terminal
# so every step is shown (no black box). Idempotent — safe to re-run.
#
# KIROTUX installs btrfs + GRUB and pre-stages the Garuda-style @snapshots
# subvolume at /.snapshots (Calamares mount.conf). We configure snapper for BOTH
# the root (@) and home (@home) subvolumes: grub-btrfs can only boot the root
# snapshot, and /home is a separate subvolume, so a system rollback never reverts
# ~/.config — the home config gives you a way back to YOUR desktop config too.
# Policy: snap-pac + cleanup, NO hourly timeline.

echo '━━━ 1/7  Installing snapshot tools ━━━'
pacman -S --noconfirm --needed snapper snap-pac grub-btrfs btrfs-assistant btrfsmaintenance

echo ''
echo '━━━ 2/7  Creating snapper root config ━━━'
# snapper create-config insists on creating /.snapshots itself and aborts because
# KIROTUX pre-stages it. Detach our subvolume, let snapper build the config, delete
# snapper's subvolume, then remount ours as the snapshot store.
if [ -f /etc/snapper/configs/root ]; then
    echo 'root config already exists — skipping create-config'
elif mountpoint -q /.snapshots; then
    echo '/.snapshots is pre-staged — detaching it so snapper can create its config'
    if umount /.snapshots && rmdir /.snapshots; then
        snapper -c root create-config /
        btrfs subvolume delete /.snapshots
        mkdir -p /.snapshots
        mount /.snapshots
        chmod 750 /.snapshots
        echo 'snapper root config created; @snapshots remounted as the store'
    else
        mountpoint -q /.snapshots || mount /.snapshots 2>/dev/null || true
        echo 'ERROR: could not detach /.snapshots — left as-is, no config created'
        exit 1
    fi
else
    snapper -c root create-config /
fi

echo ''
echo '━━━ 3/7  Creating snapper home config ━━━'
# /home is the @home subvolume. snapper creates /home/.snapshots itself (KIROTUX
# does not pre-stage it), so no detach dance is needed here. This captures your
# personal config so a setup that splats ~/.config can be undone to YOUR config.
if [ -f /etc/snapper/configs/home ]; then
    echo 'home config already exists — skipping create-config'
else
    snapper -c home create-config /home
    echo 'snapper home config created (/home/.snapshots)'
fi
# snap-pac snapshots every snapper config by default; keep it OFF for home — pacman
# writes to / not /home, so a home pre/post pair on every package action is just noise.
# The home config is for the on-demand baseline only.
if [ ! -f /etc/snap-pac.ini ]; then
    printf '[home]\nsnapshot = False\n' > /etc/snap-pac.ini
    echo 'snap-pac: created /etc/snap-pac.ini excluding home from pacman snapshots'
elif ! grep -q '^\[home\]' /etc/snap-pac.ini; then
    printf '\n[home]\nsnapshot = False\n' >> /etc/snap-pac.ini
    echo 'snap-pac: home excluded from pacman snapshots'
else
    echo 'snap-pac: home already configured'
fi

echo ''
echo '━━━ 4/7  Applying Kiro policy (no hourly timeline) ━━━'
snapper -c root set-config TIMELINE_CREATE=no
snapper -c home set-config TIMELINE_CREATE=no
echo 'TIMELINE_CREATE=no on root + home — snapshots happen on pacman actions / on demand'

echo ''
echo '━━━ 5/7  Enabling snapshot timers ━━━'
systemctl enable --now snapper-cleanup.timer
# create-config silently enables snapper-timeline.timer; Kiro policy is no hourly
# timeline (TIMELINE_CREATE=no already blocks the snapshots), so disable the timer.
systemctl disable --now snapper-timeline.timer 2>/dev/null || true
echo 'snapper-timeline.timer disabled (Kiro policy: no hourly timeline)'
if systemctl list-unit-files btrfsmaintenance-refresh.path >/dev/null 2>&1; then
    systemctl enable --now btrfsmaintenance-refresh.path
    # The .path unit only fires on a config change; run the service once so the
    # scrub/balance/trim timers are installed immediately from the current conf.
    systemctl start btrfsmaintenance-refresh.service || true
    echo 'btrfsmaintenance enabled — scrub/balance/trim timers installed'
else
    echo 'btrfsmaintenance-refresh.path not found — review btrfsmaintenance units manually'
fi

echo ''
echo '━━━ 6/7  Baseline snapshots (root + home) ━━━'
# Create BEFORE generating the GRUB menu so the root baseline is in the first grub.cfg
# (grub-mkconfig only enumerates snapshots that exist now).
if snapper -c root list | grep -q 'Start-here baseline'; then
    echo 'root Start-here baseline already exists — skipping'
else
    snapper -c root create --description 'Start-here baseline'
fi
if snapper -c home list | grep -q 'Start-here baseline'; then
    echo 'home Start-here baseline already exists — skipping'
else
    snapper -c home create --description 'Start-here baseline'
fi
snapper -c root list
snapper -c home list

echo ''
echo '━━━ 7/7  Enabling grub-btrfs (boot a snapshot from the GRUB menu) ━━━'
# grub-btrfsd watches /.snapshots and regenerates the GRUB "snapshots" submenu on
# every later snapshot change (each snap-pac pre/post pair) — no manual step needed.
systemctl enable --now grub-btrfsd.service
# Generate the submenu now (the root baseline above is included) so it is bootable
# from the GRUB menu at the next reboot.
grub-mkconfig -o /boot/grub/grub.cfg
echo 'grub-btrfsd enabled; GRUB snapshots submenu generated (visible at next reboot)'

echo ''
echo 'Recovery is TWO parts, because a system snapshot never touches /home:'
echo '  1. SYSTEM  — pick a snapshot from the GRUB "Arch Linux snapshots" submenu to'
echo '     boot it read-only and roll back the root filesystem (no live ISO needed).'
echo '  2. YOUR CONFIG (~/.config) — restore the home baseline with Btrfs Assistant or'
echo '     `snapper -c home`, OR use Hyprland Tweak Tool > Restore Kiro Hyprland'
echo '     (rewrites hypr/waybar/mako/gtk to Kiro defaults).'
echo 'snap-pac keeps taking a pre/post root snapshot on every pacman action.'
