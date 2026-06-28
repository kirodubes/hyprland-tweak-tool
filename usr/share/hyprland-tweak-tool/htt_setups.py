"""Setup registry + install orchestration for hyprland-tweak-tool.

HTT is a *hub*: it installs the free community Hyprland setups by invoking each
project's **own** upstream installer in a visible terminal — it never bundles or
redistributes their files. This module is the engine; it is deliberately
toolkit-free (no GTK import) so it stays headless-testable, and every mutating
call runs off the UI thread and hands back a :class:`Result` rather than raising.

Modelled on ``fish-tweak-tool``'s ``ftt_fisher`` (the visible-terminal runner),
adapted from fish to bash because the installer commands use bash process
substitution (``bash <(curl …)``). The way back to a bootable Kiro Hyprland after
a system-rewriting installer is a Timeshift snapshot, prefixed onto the install
command for high-risk setups (see :func:`install_command`).
"""

import datetime
import json
import os
import shutil
import subprocess
import tempfile
import threading

import log

CONFIG_HOME = os.path.expanduser("~/.config")

# Pristine golden copy of the Kiro Hyprland config, shipped read-only by the
# kiro-hyprland package. Present only on a Kiro system; the restore action is
# hidden otherwise.
KIRO_HYPR_SOURCE = "/usr/share/kiro/hyprland"

# Timeshift writes its config only once it has been set up. "Configured" = a
# snapshot location is chosen (backup_device_uuid is non-empty).
TIMESHIFT_CONFIGS = ("/etc/timeshift/timeshift.json", "/etc/timeshift.json")

# Terminals (preferred first) used to run installers *visibly*, so the user
# always sees the exact command changing their system — no black box. Both take
# `-e <cmd>`. Alacritty is the Kiro default.
_TERMINALS = ("alacritty", "xterm")


class Setup:
    """A community Hyprland setup installable via its own upstream installer."""

    def __init__(self, id, name, tagline, homepage, variants, detect, risk="low", changes=None):
        self.id = id
        self.name = name
        self.tagline = tagline
        self.homepage = homepage
        self.variants = variants  # ordered dict: label -> install command
        self._detect = detect
        # risk "high" = the installer touches boot-critical state (bootloader,
        # display manager, pacman mirrorlist) — a Timeshift snapshot is then forced.
        self.risk = risk
        self.changes = changes  # human text: what a high-risk installer overwrites

    def is_installed(self):
        """Best-effort heuristic — drives an 'Installed' badge, never blocks install."""
        return self._detect()


# A pre-install system snapshot is the only dependable way back to a bootable
# Kiro Hyprland after a system-rewriting installer. Kiro ships Timeshift; the
# snapshot runs in the visible terminal so the user authenticates sudo there.
def _root_is_btrfs():
    try:
        with open("/proc/mounts", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "/" and parts[2] == "btrfs":
                    return True
    except OSError:
        pass
    return False


def snapshot_backend():
    """Pick the snapshot tool by filesystem: snapper on a btrfs root, Timeshift otherwise.

    btrfs + snapper + grub-btrfs gives bootable rollback snapshots in the GRUB menu — the real
    way back from a broken install. Timeshift is the portable fallback on ext4 and friends.
    """
    return "snapper" if _root_is_btrfs() else "timeshift"


def snapshot_command(comment):
    """The create-snapshot command for the active backend (runs with sudo in the terminal)."""
    if snapshot_backend() == "snapper":
        return f"sudo snapper -c root create -d '{comment}'"
    return f"sudo timeshift --create --comments '{comment}' --scripted"


def needs_snapshot(setup):
    """True when a setup is risky enough that a Timeshift snapshot is mandatory."""
    return setup.risk == "high"


def kiro_restore_available():
    """True when the kiro-hyprland golden copy is present (i.e. this is a Kiro system)."""
    return os.path.isdir(KIRO_HYPR_SOURCE) and bool(os.listdir(KIRO_HYPR_SOURCE))


def restore_kiro_hyprland():
    """Remove the user's Hyprland config dirs and rewrite Kiro's pristine copy.

    Each replaced dir is first moved to a timestamped backup (so a foreign waybar,
    mako, etc. is gone from ~/.config but still recoverable). Returns the backup
    dir path, or None if nothing needed backing up.
    """
    names = sorted(n for n in os.listdir(KIRO_HYPR_SOURCE) if os.path.isdir(os.path.join(KIRO_HYPR_SOURCE, n)))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(CONFIG_HOME, "hyprland-tweak-tool", "before-kiro-restore", stamp)
    backed_up = False
    for name in names:
        target = os.path.join(CONFIG_HOME, name)
        if os.path.exists(target):
            os.makedirs(backup, exist_ok=True)
            shutil.move(target, os.path.join(backup, name))
            backed_up = True
        shutil.copytree(os.path.join(KIRO_HYPR_SOURCE, name), target)
    log.log_info(f"Restored Kiro Hyprland config from {KIRO_HYPR_SOURCE}")
    return backup if backed_up else None


def snapshot_ready():
    """Return (ready, guidance) for the active backend; ready=False blocks a required snapshot."""
    if snapshot_backend() == "snapper":
        return _snapper_ready()
    return _timeshift_ready()


def _snapper_ready():
    if shutil.which("snapper") is None:
        return False, (
            "This is a btrfs system but snapper is not installed — it gives you bootable rollback "
            "snapshots from the GRUB menu. Install it:  sudo pacman -S snapper snap-pac grub-btrfs"
        )
    if not os.path.exists("/etc/snapper/configs/root"):
        return False, (
            "snapper is installed but has no 'root' config. Create one:  "
            "sudo snapper -c root create-config /  — then try again."
        )
    return True, ""


def _timeshift_ready():
    if shutil.which("timeshift") is None:
        return False, (
            "Timeshift is not installed — it is your way back if an install breaks the system. "
            "Install it first:  sudo pacman -S timeshift"
        )
    path = next((p for p in TIMESHIFT_CONFIGS if os.path.exists(p)), None)
    if path is None:
        return False, (
            "Timeshift is installed but not set up yet. Open Timeshift (run: sudo timeshift-gtk), choose "
            "a snapshot type and location, and create one snapshot — then try the install again."
        )
    try:
        with open(path, encoding="utf-8") as f:
            configured = bool(json.load(f).get("backup_device_uuid"))
    except (OSError, ValueError):
        # Config exists but unreadable — Timeshift has been set up at least once; don't block.
        return True, ""
    if not configured:
        return False, (
            "Timeshift has no snapshot location set. Open Timeshift (run: sudo timeshift-gtk), pick a "
            "device/location, and create one snapshot — then try the install again."
        )
    return True, ""


def install_command(setup, label, snapshot):
    """The full command for a variant, optionally prefixed with a system snapshot."""
    cmd = setup.variants[label]
    if snapshot:
        return f"{snapshot_command('HTT: before ' + setup.id)} && {cmd}"
    return cmd


def _ml4w_installed():
    return os.path.isdir(os.path.join(CONFIG_HOME, "ml4w")) or shutil.which("ml4w-hyprland-setup") is not None


def _omarchy_installed():
    return os.path.isdir(os.path.expanduser("~/.local/share/omarchy")) or shutil.which("omarchy-menu") is not None


def _end4_installed():
    return os.path.isdir(os.path.expanduser("~/.config/illogical-impulse")) or os.path.isdir(
        os.path.expanduser("~/.config/quickshell/ii")
    )


def _hyde_installed():
    return os.path.isdir(os.path.expanduser("~/.config/hyde")) or shutil.which("hyde-shell") is not None


def _caelestia_installed():
    return shutil.which("caelestia") is not None or os.path.isdir(os.path.expanduser("~/.config/caelestia"))


def _jakoolit_installed():
    return os.path.isdir(os.path.expanduser("~/.config/hypr/UserConfigs"))


# The registry. One entry today; list-shaped so adding Omarchy / end-4 / … later
# is a single literal with no code change. ML4W rolling targets Hyprland 0.55.x —
# exactly Kiro Hyprland's version — so it leads as the default variant.
ML4W = Setup(
    id="ml4w",
    name="ML4W — My Linux For Work",
    tagline="A polished Hyprland desktop with its own GTK settings apps. Single-command installer "
    "with an anti-clobber restore manifest.",
    homepage="https://www.ml4w.com",
    variants={
        "Rolling (Hyprland 0.55.x)": "bash <(curl -s https://ml4w.com/os/rolling)",
        "Stable": "bash <(curl -s https://ml4w.com/os/stable)",
    },
    detect=_ml4w_installed,
)

# Omarchy is a full-desktop *bootstrap* by DHH/Basecamp, not dotfiles: it rewrites
# the pacman mirrorlist and installs a whole curated desktop. It expects a fresh /
# minimal Arch — far more invasive than ML4W — so the tagline says so plainly.
OMARCHY = Setup(
    id="omarchy",
    name="Omarchy",
    tagline="A full curated Hyprland desktop (DHH / Basecamp). A bootstrap, not dotfiles — it "
    "rewrites your pacman mirrorlist and installs a whole desktop; meant for a fresh/minimal Arch.",
    homepage="https://omarchy.org",
    variants={
        "Install": "wget -qO- https://omarchy.org/install | bash",
    },
    detect=_omarchy_installed,
    risk="high",
    changes="rewrites your pacman mirrorlist to Omarchy's mirror and installs a whole desktop. "
    "It is built for a fresh/minimal Arch — on a configured Kiro system it can break pacman and boot.",
)

END4 = Setup(
    id="end4",
    name="end-4 — illogical-impulse",
    tagline="The most-starred Hyprland desktop (end-4). A Quickshell (Qt6/QML) shell with a Super+I "
    "settings GUI. Heavy: builds quickshell-git and ~13 packages; Arch is the canonical target.",
    homepage="https://github.com/end-4/dots-hyprland",
    variants={
        "Install": "git clone https://github.com/end-4/dots-hyprland.git ~/dots-hyprland "
        "&& cd ~/dots-hyprland && ./setup",
    },
    detect=_end4_installed,
)

HYDE = Setup(
    id="hyde",
    name="HyDE",
    tagline="A broad, org-maintained Hyprland rice (HyDE Project). Installs onto existing Arch and "
    "overwrites GTK/Qt/SDDM/GRUB configs — back up first. Arch-only.",
    homepage="https://github.com/HyDE-Project/HyDE",
    variants={
        "Install": "git clone --depth 1 https://github.com/HyDE-Project/HyDE ~/HyDE "
        "&& cd ~/HyDE/Scripts && ./install.sh",
    },
    detect=_hyde_installed,
    risk="high",
    changes="overwrites your GRUB (bootloader) and SDDM (login) configs, plus GTK/Qt theming. "
    "A broken SDDM or GRUB config can leave you without a graphical login or unable to boot.",
)

CAELESTIA = Setup(
    id="caelestia",
    name="Caelestia",
    tagline="A Material-You Quickshell desktop (Caelestia). Installed from the AUR via paru, then "
    "`caelestia install`. Arch + AUR only; compiled C++ shell, Hyprland-coupled.",
    homepage="https://github.com/caelestia-dots/caelestia",
    variants={
        "Install": "paru -S caelestia-cli && caelestia install",
    },
    detect=_caelestia_installed,
)

JAKOOLIT = Setup(
    id="jakoolit",
    name="JaKooLit — Hyprland-Dots",
    tagline="The most-starred general Hyprland dotfiles (JaKooLit). Clones the Arch-Hyprland "
    "installer, which backs up ~/.config first. Note: archived March 2026, continued as a fork.",
    homepage="https://github.com/JaKooLit/Hyprland-Dots",
    variants={
        "Install": "git clone --depth=1 https://github.com/JaKooLit/Arch-Hyprland.git ~/Arch-Hyprland "
        "&& cd ~/Arch-Hyprland && chmod +x install.sh && ./install.sh",
    },
    detect=_jakoolit_installed,
)

# Ordered safest → most hazardous. The clean dotfile installs lead (ML4W, JaKooLit);
# the heavy AUR/build ones follow (end-4, Caelestia); the system-breakers that touch
# boot-critical state are LAST and carry a hazard marker (HyDE rewrites GRUB/SDDM;
# Omarchy rewrites the pacman mirrorlist as a fresh-Arch bootstrap).
SETUPS = [ML4W, JAKOOLIT, END4, CAELESTIA, HYDE, OMARCHY]


class Result:
    """Outcome of an install operation."""

    def __init__(self, ok, message=""):
        self.ok = ok
        self.message = message


# ── Install orchestration ────────────────────────────────────────────────────


def run_async(command, on_done):
    """Run an installer off the UI thread; call on_done(Result).

    The command runs in a visible terminal so the user sees exactly what is
    changing their system — never a black box. When a Timeshift snapshot is
    required it is already prefixed onto the command by :func:`install_command`.
    """

    def worker():
        ok, message = run_visibly(command)
        on_done(Result(ok, message))

    threading.Thread(target=worker, daemon=True).start()


def _find_terminal():
    for term in _TERMINALS:
        if shutil.which(term):
            return term
    return None


def _terminal_script(command, status_path):
    """Build the bash script the terminal runs: echo the command, run it, save status."""
    display = command.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "#!/bin/bash\n"
        'printf "\\033[36mHyprland Tweak Tool is running this command on your system:\\033[0m\\n\\n"\n'
        f'printf "    {display}\\n\\n"\n'
        f"{command}\n"
        "status=$?\n"
        f'echo "$status" > "{status_path}"\n'
        "echo\n"
        'if [ "$status" -eq 0 ]; then\n'
        '    printf "\\033[32mDone (success). Press enter to close.\\033[0m\\n"\n'
        "else\n"
        '    printf "\\033[31mFailed (exit %s). Press enter to close.\\033[0m\\n" "$status"\n'
        "fi\n"
        "read -r _\n"
    )


def run_visibly(command):
    """Run an installer in a visible terminal; return (ok, message).

    Falls back to a silent in-process run only when no terminal is available.
    """
    log.log_info(f"$ {command}")
    term = _find_terminal()
    if not term:
        try:
            rc = subprocess.run(["bash", "-c", command], timeout=1800).returncode
            return rc == 0, ""
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)

    script_fd, script_path = tempfile.mkstemp(prefix="htt-", suffix=".sh")
    status_fd, status_path = tempfile.mkstemp(prefix="htt-status-")
    os.close(status_fd)
    try:
        with os.fdopen(script_fd, "w", encoding="utf-8") as f:
            f.write(_terminal_script(command, status_path))
        subprocess.run([term, "-e", "bash", script_path], timeout=1800)
        with open(status_path, encoding="utf-8") as f:
            rc = int(f.read().strip() or "1")
        return rc == 0, ""
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    finally:
        for path in (script_path, status_path):
            try:
                os.unlink(path)
            except OSError:
                pass
