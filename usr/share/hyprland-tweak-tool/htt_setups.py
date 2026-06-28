"""Setup registry + install orchestration for hyprland-tweak-tool.

HTT is a *hub*: it installs the free community Hyprland setups by invoking each
project's **own** upstream installer in a visible terminal — it never bundles or
redistributes their files. This module is the engine; it is deliberately
toolkit-free (no GTK import) so it stays headless-testable, and every mutating
call runs off the UI thread and hands back a :class:`Result` rather than raising.

Modelled on ``fish-tweak-tool``'s ``ftt_fisher`` (the visible-terminal runner +
snapshot/restore helpers), adapted from fish to bash because the installer
commands use bash process substitution (``bash <(curl …)``).
"""

import datetime
import os
import shutil
import subprocess
import tempfile
import threading

import log

# Hyprland config dirs snapshotted before an install, so a setup that reshapes
# ~/.config is reversible from HTT (belt-and-suspenders alongside the setup's
# own backup logic, e.g. ML4W's restore[] manifest).
CONFIG_HOME = os.path.expanduser("~/.config")
SNAPSHOT_DIRS = ("hypr", "waybar", "mako", "gtk-3.0", "gtk-4.0")
BACKUP_DIR = os.path.expanduser("~/.config/hyprland-tweak-tool/backups")

# Terminals (preferred first) used to run installers *visibly*, so the user
# always sees the exact command changing their system — no black box. Both take
# `-e <cmd>`. Alacritty is the Kiro default.
_TERMINALS = ("alacritty", "xterm")


class Setup:
    """A community Hyprland setup installable via its own upstream installer."""

    def __init__(self, id, name, tagline, homepage, variants, detect):
        self.id = id
        self.name = name
        self.tagline = tagline
        self.homepage = homepage
        self.variants = variants  # ordered dict: label -> install command
        self._detect = detect

    def is_installed(self):
        """Best-effort heuristic — drives an 'Installed' badge, never blocks install."""
        return self._detect()


def _ml4w_installed():
    return os.path.isdir(os.path.join(CONFIG_HOME, "ml4w")) or shutil.which("ml4w-hyprland-setup") is not None


def _omarchy_installed():
    return os.path.isdir(os.path.expanduser("~/.local/share/omarchy")) or shutil.which("omarchy-menu") is not None


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
)

SETUPS = [ML4W, OMARCHY]


class Result:
    """Outcome of an install operation."""

    def __init__(self, ok, message="", backup=None):
        self.ok = ok
        self.message = message
        self.backup = backup


# ── Backup / restore ─────────────────────────────────────────────────────────


def snapshot_now():
    """Back up the existing Hyprland config dirs into a timestamped folder; return its path."""
    present = [d for d in SNAPSHOT_DIRS if os.path.isdir(os.path.join(CONFIG_HOME, d))]
    if not present:
        return None
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"hypr-{stamp}")
    os.makedirs(dest, exist_ok=True)
    for name in present:
        shutil.copytree(os.path.join(CONFIG_HOME, name), os.path.join(dest, name), dirs_exist_ok=True)
    log.log_info(f"Backed up Hyprland config to {dest}")
    return dest


def list_backups():
    """Return existing backup directories, newest first."""
    if not os.path.isdir(BACKUP_DIR):
        return []
    paths = [os.path.join(BACKUP_DIR, name) for name in os.listdir(BACKUP_DIR)]
    return sorted((p for p in paths if os.path.isdir(p)), reverse=True)


def restore_backup(path):
    """Copy each saved config dir from a backup back over ~/.config."""
    for name in os.listdir(path):
        src = os.path.join(path, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(CONFIG_HOME, name), dirs_exist_ok=True)
    log.log_info(f"Restored Hyprland config from {path}")


# ── Install orchestration ────────────────────────────────────────────────────


def run_async(command, on_done, snapshot=False):
    """Run an installer off the UI thread; call on_done(Result).

    Snapshots the Hyprland config first when ``snapshot`` is set, then runs the
    command in a visible terminal so the user sees exactly what is changing their
    system — never a black box.
    """

    def worker():
        backup = snapshot_now() if snapshot else None
        ok, message = run_visibly(command)
        on_done(Result(ok, message, backup))

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
