"""Baseline snapshot setup for hyprland-tweak-tool — the "Start here" tab logic.

Before a user experiments with the community setups (some rewrite GRUB, SDDM or the
pacman mirrorlist), they need a baseline they can roll back to. This module sets up
that baseline. It ports ATT's Btrfs page to KIROTUX, which installs **btrfs + GRUB**
by default and pre-stages the Garuda-style ``@snapshots`` subvolume at ``/.snapshots``
(Calamares ``mount.conf``). The snapshot stack is therefore snapper + snap-pac +
**grub-btrfs** + btrfs-assistant + btrfsmaintenance — grub-btrfs gives a bootable
pre-install snapshot entry in the GRUB menu, so recovery needs no live ISO.

Like :mod:`htt_setups` this module is deliberately toolkit-free (no GTK import) so it
stays headless-testable. The privileged work lives in two auditable bash scripts under
``scripts/``; the read-only state queries here run unprivileged. The GUI executes the
returned command strings through :func:`htt_setups.run_async`, so every system change
is shown in a visible terminal — never a black box.
"""

import os
import subprocess

import htt_setups

SNAPPER_CONFIG = "/etc/snapper/configs/root"

# grub-btrfs is the KIROTUX addition vs ATT (GRUB, not systemd-boot): it generates a
# "snapshots" submenu in GRUB so a pre-install snapshot can be booted read-only.
PACKAGES = ("snapper", "snap-pac", "grub-btrfs", "btrfs-assistant", "btrfsmaintenance")

# Short "what it's for" blurbs (4–6 words) shown beside each tool name.
TOOL_BLURBS = {
    "snapper": "creates and manages snapshots",
    "snap-pac": "snapshots on every pacman action",
    "grub-btrfs": "boot a snapshot from the GRUB menu",
    "btrfs-assistant": "GUI to browse and restore",
    "btrfsmaintenance": "scheduled scrub, balance and trim",
}

_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")


def is_btrfs_root():
    """True when the root filesystem is btrfs (drives the btrfs stack vs the ext4 fallback)."""
    return htt_setups.root_is_btrfs()


def package_installed(package):
    """True when a pacman package is installed. Read-only — no sudo."""
    return subprocess.run(["pacman", "-Q", package], capture_output=True).returncode == 0


def service_enabled(unit):
    """True when a systemd unit is enabled. Read-only — no sudo."""
    return subprocess.run(["systemctl", "is-enabled", unit], capture_output=True).returncode == 0


def snapper_root_configured():
    """True when the snapper 'root' config already exists."""
    return os.path.isfile(SNAPPER_CONFIG)


def all_packages_installed():
    """True when the whole snapshot stack is installed."""
    return all(package_installed(pkg) for pkg in PACKAGES)


def install_tool_command(package):
    """Command to install a single snapshot tool visibly (sudo authenticated in the terminal)."""
    return f"sudo pacman -S --needed --noconfirm {package}"


def enable_command():
    """Command to install + configure the whole snapshot stack and take a baseline snapshot."""
    return f"sudo bash {os.path.join(_SCRIPTS, 'baseline-snapshots-enable.sh')}"


def disable_command():
    """Command to remove the snapshot stack; snapshots already on disk are kept."""
    return f"sudo bash {os.path.join(_SCRIPTS, 'baseline-snapshots-disable.sh')}"
