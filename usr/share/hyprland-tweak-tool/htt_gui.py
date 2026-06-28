"""GUI for hyprland-tweak-tool.

HTT is a hub for installing the free community Hyprland setups. This module builds
the header bar (title · version · Support · Quit) over a tabbed Notebook; the first
tab — Setups — installs a setup via its own upstream installer. Later config-editor
tabs (Appearance, Animations, …) slot into the same Notebook.
"""

import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

import htt_baseline  # noqa: E402
import htt_setups  # noqa: E402
import log  # noqa: E402

_FUNDING = [
    ("GitHub Sponsors", "https://github.com/sponsors/erikdubois", "best value — almost all goes to the project"),
    ("Ko-fi", "https://ko-fi.com/erikdubois", "buy a coffee — one-off tip"),
    ("Patreon", "https://www.patreon.com/kiroproject", "membership tiers + perks"),
    ("YouTube membership", "https://www.youtube.com/@ErikDubois/join", "join on YouTube"),
    ("PayPal", "https://www.paypal.me/erikdubois", "direct one-off"),
]


def _section(title):
    """Return a left-aligned section heading label."""
    lbl = Gtk.Label(label=title, xalign=0)
    lbl.add_css_class("section-title")
    return lbl


def _intro(text):
    """Return a left-aligned wrapped intro/description label."""
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.add_css_class("plugin-desc")
    lbl.set_wrap(True)
    return lbl


_GREEN = "#4e9a06"
_ORANGE = "#FFA500"


def _state_markup(ok, yes, no):
    """Return Pango markup colouring a yes/no state green when ok, orange otherwise."""
    return f"<span foreground='{_GREEN if ok else _ORANGE}'>{yes if ok else no}</span>"


def _status_label():
    """Return an indented left-aligned label for a status row (markup set on refresh)."""
    lbl = Gtk.Label(xalign=0)
    lbl.set_margin_start(8)
    return lbl


def _open_link(label, uri):
    """activate-link handler — open uri in the default browser."""
    Gtk.UriLauncher.new(uri).launch(label.get_root(), None, None)
    return True


def _open_url(parent, url):
    Gtk.UriLauncher.new(url).launch(parent, None, None)


def _snapshot_needed_dialog(button, intro_text, guidance):
    """Blocking dialog telling the user to set up snapshots before one can run."""
    dlg = Gtk.Window(title="Set up snapshots first", transient_for=button.get_root(), modal=True)
    dlg.set_default_size(480, -1)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)
    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>Set up snapshots first</b>")
    box.append(heading)
    box.append(_intro(intro_text))
    detail = _intro(guidance)
    detail.set_selectable(True)
    box.append(detail)
    close = Gtk.Button(label="Close")
    close.set_halign(Gtk.Align.END)
    close.connect("clicked", lambda _w: dlg.close())
    box.append(close)
    dlg.set_child(box)
    dlg.present()


class _StatusMixin:
    """A status label in ATT-orange that auto-clears 10s after the last message."""

    def _init_status(self):
        self._status = Gtk.Label(label="", xalign=0)
        self._status.add_css_class("status-line")
        self._status.set_wrap(True)
        self._status_timeout = 0
        return self._status

    def _set_status(self, text, error=False):
        self._status.set_text(text)
        if error:
            self._status.add_css_class("status-error")
        else:
            self._status.remove_css_class("status-error")
        if self._status_timeout:
            GLib.source_remove(self._status_timeout)
            self._status_timeout = 0
        if text:
            self._status_timeout = GLib.timeout_add_seconds(10, self._clear_status)
        return False

    def _clear_status(self):
        self._status.set_text("")
        self._status.remove_css_class("status-error")
        self._status_timeout = 0
        return False


class SetupsTab(_StatusMixin):
    """Install a community Hyprland setup via its own upstream installer."""

    def __init__(self):
        self._status = None
        self._status_timeout = 0
        self.widget = self._build()

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("start", "end", "top", "bottom"):
            getattr(outer, f"set_margin_{side}")(14)

        outer.append(_section("Install a Hyprland setup"))
        outer.append(
            _intro(
                "Each setup is installed by running its own official installer in a visible "
                "terminal — Hyprland Tweak Tool never bundles their files. The installer runs as "
                "you, and asks for sudo in the terminal when it needs it."
            )
        )
        outer.append(self._protection_banner())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        cards = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for setup in htt_setups.SETUPS:
            cards.append(self._card(setup))
        scrolled.set_child(cards)
        outer.append(scrolled)

        if htt_setups.kiro_restore_available():
            recover = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            recover.append(
                _intro("Tried a setup and want Kiro Hyprland back? This removes your hypr/waybar/mako/GTK "
                       "config and rewrites Kiro's (your current one is backed up first).")
            )
            restore = Gtk.Button(label="Restore Kiro Hyprland")
            restore.set_valign(Gtk.Align.CENTER)
            restore.set_halign(Gtk.Align.END)
            restore.set_hexpand(True)
            restore.connect("clicked", self._confirm_restore)
            recover.append(restore)
            outer.append(recover)

        outer.append(self._init_status())
        return outer

    def _confirm_restore(self, button):
        dlg = Gtk.Window(title="Restore Kiro Hyprland?", transient_for=button.get_root(), modal=True)
        dlg.set_default_size(480, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(18)
        heading = Gtk.Label(xalign=0)
        heading.set_markup("<b>Restore Kiro Hyprland?</b>")
        box.append(heading)
        box.append(
            _intro(
                "This removes your current hypr, waybar, mako and GTK config and rewrites Kiro's "
                "defaults — so leftovers from another setup are cleared. Your current config is moved "
                "to a backup under ~/.config/hyprland-tweak-tool/before-kiro-restore/ first. Log out "
                "and back in (or reboot) afterwards to apply."
            )
        )
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _w: dlg.close())
        go = Gtk.Button(label="Restore Kiro Hyprland")
        go.add_css_class("destructive-action")
        go.connect("clicked", self._do_restore, button, dlg)
        buttons.append(cancel)
        buttons.append(go)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _do_restore(self, go_button, anchor, dlg):
        dlg.close()
        try:
            backup = htt_setups.restore_kiro_hyprland()
        except OSError as exc:
            self._set_status(f"Restore failed: {exc}", error=True)
            return
        msg = "Kiro Hyprland config restored."
        if backup:
            msg += f" Old config backed up to {backup}."
        self._set_status(msg)
        self._show_reboot_dialog(
            anchor,
            "Kiro Hyprland restored",
            "Log out and back in (or reboot) to apply it — your session is still running the old config.",
        )

    def _card(self, setup):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("setup-card")

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = Gtk.Label(label=setup.name, xalign=0)
        name.add_css_class("plugin-name")
        name.set_hexpand(True)
        title_row.append(name)
        if htt_setups.needs_snapshot(setup):
            hazard = Gtk.Label(label="⚠ Can break your system")
            hazard.add_css_class("hazard-badge")
            hazard.set_valign(Gtk.Align.CENTER)
            title_row.append(hazard)
        if setup.is_installed():
            badge = Gtk.Label(label="Installed")
            badge.add_css_class("placeholder-badge")
            badge.set_valign(Gtk.Align.CENTER)
            title_row.append(badge)
        card.append(title_row)

        tagline = Gtk.Label(label=setup.tagline, xalign=0)
        tagline.add_css_class("plugin-desc")
        tagline.set_wrap(True)
        card.append(tagline)

        homepage = Gtk.Label(xalign=0)
        homepage.set_markup(f"<a href='{setup.homepage}'>Homepage</a>")
        homepage.connect("activate-link", _open_link)
        card.append(homepage)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_margin_top(4)
        # Only offer a variant picker when there is a real choice (e.g. ML4W's
        # Rolling/Stable). A single-variant setup just gets the Install button.
        variants = None
        if len(setup.variants) > 1:
            variants = Gtk.DropDown.new_from_strings(list(setup.variants.keys()))
            variants.set_valign(Gtk.Align.CENTER)
            variants.set_hexpand(True)
            variants.set_halign(Gtk.Align.START)
            controls.append(variants)
        install = Gtk.Button(label="Install")
        install.add_css_class("suggested-action")
        install.set_halign(Gtk.Align.END)
        install.set_hexpand(variants is None)
        install.connect("clicked", self._on_install, setup, variants)
        controls.append(install)
        card.append(controls)
        return card

    def _on_install(self, button, setup, variants):
        keys = list(setup.variants.keys())
        label = keys[variants.get_selected()] if variants is not None else keys[0]
        self._confirm_install(button, setup, label)

    def _protection_banner(self):
        """A one-line rollback-coverage banner shown above the setup cards."""
        lbl = Gtk.Label(xalign=0)
        lbl.set_wrap(True)
        state = htt_setups.protection_state()
        if state == "snapper":
            lbl.set_markup(_state_markup(
                True, "Protected: snapper + grub-btrfs are active — system rollback from the GRUB "
                "menu, desktop config via Restore Kiro Hyprland.", ""))
        elif state == "timeshift":
            lbl.set_markup("Timeshift is your fallback — a snapshot is taken before a "
                           "system-rewriting install.")
        else:
            lbl.set_markup(_state_markup(
                False, "", "No rollback set up yet — open the “Start here” tab before a "
                "system-rewriting install."))
        return lbl

    def _install_intro(self, setup):
        return (
            f"Installing {setup.name} can change boot-critical parts of your system. You need a "
            "way back first — set up a baseline, then come back and install."
        )

    def _baseline_guidance(self):
        return (
            "Open the “Start here” tab and set up a baseline:\n"
            "•  on btrfs — Enable Kiro snapshots (snapper + grub-btrfs); roll back from the GRUB menu.\n"
            "•  otherwise — set up Timeshift.\n"
            "Then come back and install."
        )

    def _confirm_install(self, button, setup, label):
        state = htt_setups.protection_state()
        high = htt_setups.needs_snapshot(setup)
        # Risky install with no rollback anywhere → gate; send the user to Start here.
        if high and state == "none":
            _snapshot_needed_dialog(button, self._install_intro(setup), self._baseline_guidance())
            return

        dlg = Gtk.Window(title=f"Install {setup.name}?", transient_for=button.get_root(), modal=True)
        dlg.set_default_size(480, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(18)

        heading = Gtk.Label(xalign=0)
        heading.set_markup(f"<b>Install {GLib.markup_escape_text(setup.name)}?</b>")
        box.append(heading)
        box.append(_intro(setup.tagline))

        snapshot_check = None
        if state == "snapper":
            # Continuous coverage already — no snapshot, no warning, just reassure.
            prot = Gtk.Label(xalign=0)
            prot.set_wrap(True)
            prot.set_markup(_state_markup(
                True, "Protected: snapper + grub-btrfs are active. Roll back the system from the GRUB "
                "menu (Arch Linux snapshots); revert your desktop config with Restore Kiro Hyprland. "
                "No snapshot needed here.", ""))
            box.append(prot)
        elif high:
            # state == "timeshift": warn, and a Timeshift snapshot is taken first.
            warn = Gtk.Label(xalign=0)
            warn.add_css_class("status-error")
            warn.set_wrap(True)
            warn.set_markup(
                f"<b>This installer {GLib.markup_escape_text(setup.changes)}</b>\n"
                "It can leave your system unbootable. A Timeshift snapshot will be taken first — "
                "restore it to get back to Kiro Hyprland."
            )
            box.append(warn)
        else:
            box.append(
                _intro(
                    "This runs the installer on your current system and changes your desktop config. "
                    "A reboot is needed afterwards to apply it."
                )
            )
            snapshot_check = Gtk.CheckButton(label="Take a system snapshot first (recommended)")
            box.append(snapshot_check)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _w: dlg.close())
        go = Gtk.Button(label="Install")
        go.add_css_class("destructive-action" if high else "suggested-action")
        go.connect("clicked", self._start_install, button, setup, label, snapshot_check, state, dlg)
        buttons.append(cancel)
        buttons.append(go)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _start_install(self, go_button, install_button, setup, label, snapshot_check, state, dlg):
        high = htt_setups.needs_snapshot(setup)
        # On snapper we trust the standing baseline (snap-pac + grub-btrfs) — never an extra
        # snapshot. Otherwise: forced before a high-risk install, or if the optional box is ticked.
        if state == "snapper":
            snapshot = False
        else:
            snapshot = (high and state == "timeshift") or (snapshot_check is not None and snapshot_check.get_active())
        if snapshot:
            ready, guidance = htt_setups.snapshot_ready()
            if not ready:
                dlg.close()
                _snapshot_needed_dialog(install_button, self._install_intro(setup), guidance)
                return
        dlg.close()
        install_button.set_sensitive(False)
        self._set_status(f"Installing {setup.name} — follow the terminal…")
        command = htt_setups.install_command(setup, label, snapshot)

        def on_done(result):
            GLib.idle_add(self._install_finished, setup, install_button, result)

        htt_setups.run_async(command, on_done)

    def _install_finished(self, setup, button, result):
        button.set_sensitive(True)
        if result.ok:
            self._set_status(f"{setup.name} installed — reboot to apply.")
            self._show_reboot_dialog(
                button,
                f"{setup.name} is installed",
                "A reboot is required for the new setup to take effect — it usually only applies after "
                "rebooting. Save your work first.",
            )
        else:
            self._set_status(f"{setup.name} install failed: {result.message or 'see terminal'}", error=True)
        return False

    def _show_reboot_dialog(self, button, heading_text, detail):
        dlg = Gtk.Window(title="Reboot to apply", transient_for=button.get_root(), modal=True)
        dlg.set_default_size(440, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(18)
        heading = Gtk.Label(xalign=0)
        heading.set_markup(f"<b>{GLib.markup_escape_text(heading_text)}</b>")
        box.append(heading)
        box.append(_intro(detail))
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        later = Gtk.Button(label="Later")
        later.connect("clicked", lambda _w: dlg.close())
        reboot = Gtk.Button(label="Reboot now")
        reboot.add_css_class("destructive-action")
        reboot.connect("clicked", self._do_reboot, dlg)
        buttons.append(later)
        buttons.append(reboot)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _do_reboot(self, button, dlg):
        dlg.close()
        try:
            subprocess.Popen(["systemctl", "reboot"])
        except OSError as exc:
            self._set_status(f"Could not reboot: {exc} — reboot manually.", error=True)


class StartHereTab(_StatusMixin):
    """Set up a snapshot baseline to roll back to before experimenting with setups."""

    def __init__(self):
        self._status = None
        self._status_timeout = 0
        self._tool_labels = {}
        self._tool_buttons = {}
        self.widget = self._build()

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("start", "end", "top", "bottom"):
            getattr(outer, f"set_margin_{side}")(14)
        outer.append(_section("Start here — set up a baseline"))
        outer.append(
            _intro(
                "Before you try any setup, set up a snapshot baseline you can return to. The "
                "setups can change boot-critical parts of your system, and a snapshot is your "
                "reliable way back to a working Kiro Hyprland."
            )
        )
        if htt_baseline.is_btrfs_root():
            self._build_btrfs(outer)
        else:
            self._build_fallback(outer)
        outer.append(self._init_status())
        return outer

    # ── btrfs: the full snapper + grub-btrfs stack ───────────────────────────
    def _build_btrfs(self, outer):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        box.append(_section("Snapshot tools"))
        for pkg in htt_baseline.PACKAGES:
            box.append(self._tool_row(pkg))

        box.append(_section("Status"))
        self._summary_label = _status_label()
        self._config_label = _status_label()
        self._home_label = _status_label()
        self._cleanup_label = _status_label()
        self._maint_label = _status_label()
        self._grub_label = _status_label()
        for lbl in (self._summary_label, self._config_label, self._home_label,
                    self._cleanup_label, self._maint_label, self._grub_label):
            box.append(lbl)

        box.append(_section("Setup"))
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._enable_btn = Gtk.Button(label="Enable Kiro snapshots")
        self._enable_btn.add_css_class("suggested-action")
        self._enable_btn.set_tooltip_text("Install any missing tools, configure snapshots, and take a baseline")
        self._enable_btn.connect("clicked", self._on_enable)
        self._disable_btn = Gtk.Button(label="Disable Kiro snapshots")
        self._disable_btn.set_tooltip_text("Remove the snapshot tools and config — snapshots already taken are kept")
        self._disable_btn.connect("clicked", self._confirm_disable)
        actions.append(self._enable_btn)
        actions.append(self._disable_btn)
        box.append(actions)

        caveat = _intro(
            "Recovery is two parts, because a system snapshot never touches /home:\n"
            "•  System — your pre-install root snapshot is a bootable entry in the GRUB menu "
            "(Arch Linux snapshots); pick it to roll back, no live ISO needed.\n"
            "•  Your config (~/.config) — restore the home baseline with Btrfs Assistant / "
            "snapper -c home, or use “Restore Kiro Hyprland” on the Setups tab."
        )
        box.append(caveat)

        scrolled.set_child(box)
        outer.append(scrolled)
        self._refresh()

    def _tool_row(self, pkg):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(xalign=0)
        label.set_margin_start(8)
        label.set_hexpand(True)
        button = Gtk.Button(label=f"Install {pkg}")
        button.connect("clicked", self._on_install_tool, pkg)
        row.append(label)
        row.append(button)
        self._tool_labels[pkg] = label
        self._tool_buttons[pkg] = button
        return row

    def _refresh(self):
        any_installed = False
        for pkg in htt_baseline.PACKAGES:
            installed = htt_baseline.package_installed(pkg)
            any_installed = any_installed or installed
            self._tool_labels[pkg].set_markup(
                f"<b>{pkg}</b> <small>— {htt_baseline.TOOL_BLURBS[pkg]}</small> — "
                + _state_markup(installed, "installed", "not installed")
            )
            self._tool_buttons[pkg].set_sensitive(not installed)

        config_ok = htt_baseline.snapper_root_configured()
        self._config_label.set_markup("Snapper root config (@, system): "
                                      + _state_markup(config_ok, "configured", "not configured"))
        home_ok = htt_baseline.snapper_home_configured()
        self._home_label.set_markup("Snapper home config (@home, ~/.config): "
                                    + _state_markup(home_ok, "configured", "not configured"))
        cleanup_ok = htt_baseline.service_enabled("snapper-cleanup.timer")
        self._cleanup_label.set_markup("Cleanup timer (prunes snap-pac pairs): "
                                       + _state_markup(cleanup_ok, "enabled", "disabled"))
        maint_ok = htt_baseline.service_enabled("btrfsmaintenance-refresh.path")
        self._maint_label.set_markup("btrfsmaintenance (scrub · balance · trim): "
                                     + _state_markup(maint_ok, "enabled", "not enabled"))
        grub_ok = htt_baseline.service_enabled("grub-btrfsd.service")
        self._grub_label.set_markup("grub-btrfs (boot-menu snapshots): "
                                    + _state_markup(grub_ok, "enabled", "not enabled"))

        active = htt_baseline.all_packages_installed() and config_ok and home_ok and cleanup_ok and grub_ok
        self._summary_label.set_markup(
            _state_markup(active, "Baseline snapshots are active", "Baseline is not set up yet")
        )
        self._disable_btn.set_sensitive(any_installed or config_ok or home_ok)
        return False

    def _on_install_tool(self, button, pkg):
        button.set_sensitive(False)
        self._set_status(f"Installing {pkg} — follow the terminal…")
        htt_setups.run_async(
            htt_baseline.install_tool_command(pkg),
            lambda result: GLib.idle_add(self._op_finished, f"{pkg} install", result),
        )

    def _on_enable(self, button):
        self._set_status("Setting up snapshots — follow the terminal…")
        htt_setups.run_async(
            htt_baseline.enable_command(),
            lambda result: GLib.idle_add(self._op_finished, "Snapshot setup", result),
        )

    def _confirm_disable(self, button):
        dlg = Gtk.Window(title="Remove snapshot stack?", transient_for=button.get_root(), modal=True)
        dlg.set_default_size(480, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(18)
        heading = Gtk.Label(xalign=0)
        heading.set_markup("<b>Remove snapshot stack?</b>")
        box.append(heading)
        box.append(
            _intro(
                "This disables the snapshot timers, removes the snapper root config, and removes "
                "snapper, snap-pac, grub-btrfs, btrfs-assistant and btrfsmaintenance. Your snapshots "
                "are kept on disk — re-running Enable sets everything up again."
            )
        )
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _w: dlg.close())
        go = Gtk.Button(label="Remove")
        go.add_css_class("destructive-action")
        go.connect("clicked", self._do_disable, dlg)
        buttons.append(cancel)
        buttons.append(go)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _do_disable(self, button, dlg):
        dlg.close()
        self._set_status("Removing snapshot stack — follow the terminal…")
        htt_setups.run_async(
            htt_baseline.disable_command(),
            lambda result: GLib.idle_add(self._op_finished, "Snapshot teardown", result),
        )

    def _op_finished(self, what, result):
        if result.ok:
            self._set_status(f"{what} finished.")
        else:
            self._set_status(f"{what} failed: {result.message or 'see terminal'}", error=True)
        self._refresh()
        return False

    # ── non-btrfs root: Timeshift baseline fallback ──────────────────────────
    def _build_fallback(self, outer):
        outer.append(
            _intro(
                "Your root filesystem is not btrfs, so the snapper + grub-btrfs stack isn't "
                "available. A default KIROTUX install uses btrfs + GRUB, where your pre-install "
                "snapshot becomes a bootable entry in the GRUB menu — the recommended layout. "
                "Here, use Timeshift as your baseline instead."
            )
        )
        ready, guidance = htt_setups.snapshot_ready()
        if not ready:
            note = _intro(guidance)
            note.set_selectable(True)
            outer.append(note)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.START)
        self._fallback_btn = Gtk.Button(label="Take a baseline snapshot")
        self._fallback_btn.add_css_class("suggested-action")
        self._fallback_btn.connect("clicked", self._on_fallback_snapshot)
        row.append(self._fallback_btn)
        outer.append(row)

    def _on_fallback_snapshot(self, button):
        ready, guidance = htt_setups.snapshot_ready()
        if not ready:
            _snapshot_needed_dialog(
                button, "A baseline snapshot is your way back if a setup breaks the system.", guidance
            )
            return
        button.set_sensitive(False)
        self._set_status("Creating a baseline snapshot — follow the terminal…")
        htt_setups.run_async(
            htt_setups.snapshot_command("HTT: Start-here baseline"),
            lambda result: GLib.idle_add(self._fallback_finished, button, result),
        )

    def _fallback_finished(self, button, result):
        button.set_sensitive(True)
        if result.ok:
            self._set_status("Baseline snapshot created.")
        else:
            self._set_status(f"Snapshot failed: {result.message or 'see terminal'}", error=True)
        return False


class BackupTab(_StatusMixin):
    """Take a full-system snapshot on demand."""

    def __init__(self):
        self._status = None
        self._status_timeout = 0
        self.widget = self._build()

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("start", "end", "top", "bottom"):
            getattr(outer, f"set_margin_{side}")(14)
        outer.append(_section("Backup"))
        outer.append(
            _intro(
                "Take a full-system snapshot you can roll back to — your way out if a setup "
                "breaks the system. It runs in a visible terminal and asks for sudo there."
            )
        )
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.START)
        backup = Gtk.Button(label="Back up now")
        backup.add_css_class("suggested-action")
        backup.connect("clicked", self._on_backup)
        row.append(backup)
        outer.append(row)
        outer.append(self._init_status())
        return outer

    def _on_backup(self, button):
        ready, guidance = htt_setups.snapshot_ready()
        if not ready:
            _snapshot_needed_dialog(
                button,
                "A backup takes a full system snapshot — your way back if a setup breaks.",
                guidance,
            )
            return
        button.set_sensitive(False)
        self._set_status("Creating a snapshot — follow the terminal…")

        def on_done(result):
            GLib.idle_add(self._backup_finished, button, result)

        htt_setups.run_async(htt_setups.snapshot_command("HTT: manual backup"), on_done)

    def _backup_finished(self, button, result):
        button.set_sensitive(True)
        if result.ok:
            self._set_status("Backup snapshot created.")
        else:
            self._set_status(f"Backup failed: {result.message or 'see terminal'}", error=True)
        return False


def _show_support_dialog(window):
    dlg = Gtk.Window(title="Support Kiro", transient_for=window, modal=True)
    dlg.set_default_size(440, -1)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)

    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>Support Kiro</b>")
    box.append(heading)

    intro = Gtk.Label(xalign=0)
    intro.add_css_class("info-label")
    intro.set_wrap(True)
    intro.set_max_width_chars(52)
    intro.set_label(
        "Kiro and its tools are built by one person, for the community — and kept free. "
        "If Hyprland Tweak Tool saves you time, a little support keeps the work going. "
        "Thank you for being here."
    )
    box.append(intro)

    for name, url, note in _FUNDING:
        btn = Gtk.Button()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{name}</b>")
        sub = Gtk.Label(label=note, xalign=0)
        sub.add_css_class("info-label")
        content.append(label)
        content.append(sub)
        btn.set_child(content)
        btn.connect("clicked", lambda _w, u=url: _open_url(dlg, u))
        box.append(btn)

    close = Gtk.Button(label="Close")
    close.set_halign(Gtk.Align.END)
    close.connect("clicked", lambda _w: dlg.close())
    box.append(close)

    dlg.set_child(box)
    dlg.present()


def build(window, hyprland_version):
    """Populate the window with a header bar and the tabbed hub."""
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header.set_margin_start(12)
    header.set_margin_end(12)
    header.set_margin_top(10)
    header.set_margin_bottom(8)
    title = Gtk.Label(label="Hyprland Tweak Tool", xalign=0)
    title.set_name("title")
    title.set_hexpand(True)
    ver_text = f"Hyprland v{hyprland_version}" if hyprland_version[:1].isdigit() else f"Hyprland {hyprland_version}"
    lbl_version = Gtk.Label(label=ver_text)
    lbl_version.add_css_class("info-label")
    lbl_version.set_valign(Gtk.Align.CENTER)
    btn_support = Gtk.Button(label="♥ Support")
    btn_support.set_tooltip_text("Support Kiro's development")
    btn_support.add_css_class("support-button")
    btn_support.connect("clicked", lambda _w: _show_support_dialog(window))
    btn_quit = Gtk.Button(label="Quit")
    btn_quit.connect("clicked", lambda _w: window.close())
    header.append(title)
    header.append(lbl_version)
    header.append(btn_support)
    header.append(btn_quit)
    root.append(header)
    root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    notebook = Gtk.Notebook()
    notebook.set_scrollable(True)
    notebook.set_vexpand(True)
    notebook.append_page(StartHereTab().widget, Gtk.Label(label="Start here"))
    notebook.append_page(SetupsTab().widget, Gtk.Label(label="Setups"))
    notebook.append_page(BackupTab().widget, Gtk.Label(label="Backup"))
    root.append(notebook)

    window.set_child(root)
    log.debug_print(f"GUI built (Hyprland {hyprland_version})")
