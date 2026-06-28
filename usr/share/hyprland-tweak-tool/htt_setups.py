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

import os
import shutil
import subprocess
import tempfile
import threading

import log

CONFIG_HOME = os.path.expanduser("~/.config")

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
def _snapshot_command(setup):
    return f"sudo timeshift --create --comments 'HTT: before {setup.id}' --scripted"


def needs_snapshot(setup):
    """True when a setup is risky enough that a Timeshift snapshot is mandatory."""
    return setup.risk == "high"


def install_command(setup, label, snapshot):
    """The full command for a variant, optionally prefixed with a Timeshift snapshot."""
    cmd = setup.variants[label]
    if snapshot:
        return f"{_snapshot_command(setup)} && {cmd}"
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

SETUPS = [ML4W, OMARCHY, END4, HYDE, CAELESTIA, JAKOOLIT]


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
