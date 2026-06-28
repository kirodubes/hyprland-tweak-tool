#!/bin/bash
set -euo pipefail
#
# Remove the KIROTUX btrfs snapshot stack — safe & reversible. Run as root via
# `sudo bash` from Hyprland Tweak Tool's "Start here" tab, in a visible terminal.
#
# Disables the snapshot timers (incl. grub-btrfsd), removes the snapper 'root'
# config, and removes the packages. It performs NO btrfs subvolume or mount
# operations: the @snapshots subvolume and every snapshot already taken are kept
# on disk. Re-running the enable script restores everything.

echo '━━━ 1/3  Disabling snapshot timers ━━━'
for unit in snapper-cleanup.timer snapper-timeline.timer grub-btrfsd.service \
            btrfsmaintenance-refresh.path btrfs-scrub.timer btrfs-balance.timer btrfs-trim.timer; do
    if systemctl is-enabled "$unit" >/dev/null 2>&1 || systemctl is-active "$unit" >/dev/null 2>&1; then
        systemctl disable --now "$unit" >/dev/null 2>&1 && echo "disabled $unit" || echo "could not disable $unit"
    else
        echo "$unit already off"
    fi
done

echo ''
echo '━━━ 2/3  Removing snapper root + home configs ━━━'
for cfg in root home; do
    if [ -f "/etc/snapper/configs/${cfg}" ]; then
        rm -f "/etc/snapper/configs/${cfg}"
        echo "removed /etc/snapper/configs/${cfg}"
    else
        echo "no snapper ${cfg} config present"
    fi
done
echo 'Snapshots already taken are KEPT (root in @snapshots, home in /home/.snapshots).'
echo 'Use Btrfs Assistant if you ever want to view or remove them.'

echo ''
echo '━━━ 3/3  Removing snapshot packages ━━━'
to_remove=''
for p in snapper snap-pac grub-btrfs btrfs-assistant btrfsmaintenance; do
    pacman -Q "$p" >/dev/null 2>&1 && to_remove="$to_remove $p" || true
done
if [ -n "$to_remove" ]; then
    echo "removing:$to_remove"
    pacman -R --noconfirm $to_remove
else
    echo 'none of the snapshot packages are installed'
fi

echo ''
echo 'Regenerating GRUB config so the snapshots submenu is cleaned up...'
grub-mkconfig -o /boot/grub/grub.cfg || true

echo ''
echo 'The disk layout (@snapshots subvolume, /.snapshots mount) is unchanged.'
echo 'Re-run "Enable Kiro snapshots" to set it all up again.'
