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


def _open_link(label, uri):
    """activate-link handler — open uri in the default browser."""
    Gtk.UriLauncher.new(uri).launch(label.get_root(), None, None)
    return True


def _open_url(parent, url):
    Gtk.UriLauncher.new(url).launch(parent, None, None)


def _timeshift_needed_dialog(button, intro_text, guidance):
    """Blocking dialog telling the user to set Timeshift up before a snapshot can run."""
    dlg = Gtk.Window(title="Set up Timeshift first", transient_for=button.get_root(), modal=True)
    dlg.set_default_size(480, -1)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)
    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>Set up Timeshift first</b>")
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
                "terminal — Hyprland Tweak Tool never bundles their files. Back up first; the "
                "installer runs as you, and asks for sudo in the terminal when it needs it."
            )
        )

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

    def _install_intro(self, setup):
        return (
            f"Installing {setup.name} can change boot-critical parts of your system. A Timeshift "
            "snapshot is your only reliable way back to Kiro Hyprland, so the install is blocked "
            "until Timeshift is ready."
        )

    def _confirm_install(self, button, setup, label):
        high = htt_setups.needs_snapshot(setup)
        if high:
            ready, guidance = htt_setups.timeshift_ready()
            if not ready:
                _timeshift_needed_dialog(button, self._install_intro(setup), guidance)
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

        if high:
            warn = Gtk.Label(xalign=0)
            warn.add_css_class("status-error")
            warn.set_wrap(True)
            warn.set_markup(
                f"<b>This installer {GLib.markup_escape_text(setup.changes)}</b>\n"
                "It can leave your system unbootable. A Timeshift snapshot will be taken first — "
                "restore it to get back to Kiro Hyprland."
            )
            box.append(warn)
            snapshot_check = None
        else:
            box.append(
                _intro(
                    "This runs the installer on your current system and changes your desktop config. "
                    "A reboot is needed afterwards to apply it."
                )
            )
            snapshot_check = Gtk.CheckButton(label="Take a Timeshift snapshot first (recommended)")
            box.append(snapshot_check)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _w: dlg.close())
        go = Gtk.Button(label="Install")
        go.add_css_class("destructive-action" if high else "suggested-action")
        go.connect("clicked", self._start_install, button, setup, label, snapshot_check, dlg)
        buttons.append(cancel)
        buttons.append(go)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _start_install(self, go_button, install_button, setup, label, snapshot_check, dlg):
        snapshot = htt_setups.needs_snapshot(setup) or (snapshot_check is not None and snapshot_check.get_active())
        if snapshot:
            ready, guidance = htt_setups.timeshift_ready()
            if not ready:
                dlg.close()
                _timeshift_needed_dialog(install_button, self._install_intro(setup), guidance)
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


class BackupTab(_StatusMixin):
    """Take a full-system Timeshift snapshot on demand."""

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
                "Take a full-system Timeshift snapshot you can roll back to — your way out if a setup "
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
        ready, guidance = htt_setups.timeshift_ready()
        if not ready:
            _timeshift_needed_dialog(
                button,
                "A backup takes a full Timeshift system snapshot — your way back if a setup breaks.",
                guidance,
            )
            return
        button.set_sensitive(False)
        self._set_status("Creating a Timeshift snapshot — follow the terminal…")

        def on_done(result):
            GLib.idle_add(self._backup_finished, button, result)

        htt_setups.run_async(htt_setups.manual_snapshot_command(), on_done)

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
    notebook.append_page(SetupsTab().widget, Gtk.Label(label="Setups"))
    notebook.append_page(BackupTab().widget, Gtk.Label(label="Backup"))
    root.append(notebook)

    window.set_child(root)
    log.debug_print(f"GUI built (Hyprland {hyprland_version})")
