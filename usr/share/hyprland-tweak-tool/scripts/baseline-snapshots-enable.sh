#!/bin/bash
set -euo pipefail
#
# Install + configure the KIROTUX btrfs snapshot baseline. Run as root via
# `sudo bash` from Hyprland Tweak Tool's "Start here" tab, in a visible terminal
# so every step is shown (no black box). Idempotent — safe to re-run.
#
# KIROTUX installs btrfs + GRUB and pre-stages the Garuda-style @snapshots
# subvolume at /.snapshots (Calamares mount.conf). Policy: snap-pac + cleanup,
# NO hourly timeline. grub-btrfs adds a bootable snapshot entry to the GRUB menu.

echo '━━━ 1/6  Installing snapshot tools ━━━'
pacman -S --noconfirm --needed snapper snap-pac grub-btrfs btrfs-assistant btrfsmaintenance

echo ''
echo '━━━ 2/6  Creating snapper root config ━━━'
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
echo '━━━ 3/6  Applying Kiro policy (no hourly timeline) ━━━'
snapper -c root set-config TIMELINE_CREATE=no
echo 'TIMELINE_CREATE=no  — snapshots happen on pacman actions via snap-pac'

echo ''
echo '━━━ 4/6  Enabling snapshot timers ━━━'
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
echo '━━━ 5/6  Baseline snapshot ━━━'
# Create the baseline BEFORE generating the GRUB menu so it is guaranteed to appear
# in the first grub.cfg (grub-mkconfig only enumerates snapshots that exist now).
if snapper -c root list | grep -q 'Start-here baseline'; then
    echo 'Start-here baseline snapshot already exists — skipping'
else
    snapper -c root create --description 'Start-here baseline'
fi
snapper -c root list

echo ''
echo '━━━ 6/6  Enabling grub-btrfs (boot a snapshot from the GRUB menu) ━━━'
# grub-btrfsd watches /.snapshots and regenerates the GRUB "snapshots" submenu on
# every later snapshot change (each snap-pac pre/post pair) — no manual step needed.
systemctl enable --now grub-btrfsd.service
# Generate the submenu now (the baseline above is included) so it is bootable
# from the GRUB menu at the next reboot.
grub-mkconfig -o /boot/grub/grub.cfg
echo 'grub-btrfsd enabled; GRUB snapshots submenu generated (visible at next reboot)'

echo ''
echo 'snap-pac now creates a pre/post snapshot pair on every pacman action, and'
echo 'grub-btrfsd refreshes the menu automatically. The GRUB "Arch Linux snapshots"'
echo 'submenu appears at the NEXT reboot. If an experiment leaves you unable to boot,'
echo 'pick a snapshot there to boot it read-only and roll back — no live ISO needed.'
echo 'Btrfs Assistant also does rollback from a running system.'
