"""GUI for hyprland-tweak-tool.

HTT is a hub for installing the free community Hyprland setups. This module builds
the header bar (title · version · Support · Quit) over a tabbed Notebook; the first
tab — Setups — installs a setup via its own upstream installer. Later config-editor
tabs (Appearance, Animations, …) slot into the same Notebook.
"""

import os

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

        restore = Gtk.Button(label="Restore a backup…")
        restore.set_halign(Gtk.Align.START)
        restore.connect("clicked", self._on_restore)
        outer.append(restore)
        outer.append(self._init_status())
        return outer

    def _card(self, setup):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("setup-card")

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = Gtk.Label(label=setup.name, xalign=0)
        name.add_css_class("plugin-name")
        name.set_hexpand(True)
        title_row.append(name)
        if setup.is_installed():
            badge = Gtk.Label(label="Installed")
            badge.add_css_class("placeholder-badge")
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
        variants = Gtk.DropDown.new_from_strings(list(setup.variants.keys()))
        variants.set_valign(Gtk.Align.CENTER)
        backup = Gtk.CheckButton(label="Back up my Hyprland config first")
        backup.set_active(True)
        backup.set_valign(Gtk.Align.CENTER)
        install = Gtk.Button(label="Install")
        install.add_css_class("suggested-action")
        install.set_halign(Gtk.Align.END)
        install.set_hexpand(True)
        install.connect("clicked", self._on_install, setup, variants, backup)
        controls.append(variants)
        controls.append(backup)
        controls.append(install)
        card.append(controls)
        return card

    def _on_install(self, button, setup, variants, backup):
        label = list(setup.variants.keys())[variants.get_selected()]
        command = setup.variants[label]
        button.set_sensitive(False)
        self._set_status(f"Installing {setup.name} — follow the terminal…")

        def on_done(result):
            GLib.idle_add(self._install_finished, setup, button, result)

        htt_setups.run_async(command, on_done, snapshot=backup.get_active())

    def _install_finished(self, setup, button, result):
        button.set_sensitive(True)
        if result.ok:
            msg = f"{setup.name} installed."
            if result.backup:
                msg += f" Backup: {result.backup}"
            self._set_status(msg)
        else:
            self._set_status(f"{setup.name} install failed: {result.message or 'see terminal'}", error=True)
        return False

    def _on_restore(self, button):
        backups = htt_setups.list_backups()
        if not backups:
            self._set_status("No backups yet — they are made before an install.")
            return
        dlg = Gtk.Window(title="Restore a backup", transient_for=button.get_root(), modal=True)
        dlg.set_default_size(420, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{side}")(16)
        box.append(
            _intro("Restoring copies the saved config back over ~/.config (hypr, waybar, mako, gtk). Pick a snapshot:")
        )
        chooser = Gtk.DropDown.new_from_strings([os.path.basename(p) for p in backups])
        box.append(chooser)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _w: dlg.close())
        confirm = Gtk.Button(label="Restore")
        confirm.add_css_class("destructive-action")
        confirm.connect("clicked", self._do_restore, backups, chooser, dlg)
        buttons.append(cancel)
        buttons.append(confirm)
        box.append(buttons)
        dlg.set_child(box)
        dlg.present()

    def _do_restore(self, button, backups, chooser, dlg):
        path = backups[chooser.get_selected()]
        dlg.close()
        try:
            htt_setups.restore_backup(path)
            self._set_status(f"Restored from {os.path.basename(path)}.")
        except OSError as exc:
            self._set_status(f"Restore failed: {exc}", error=True)


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
    root.append(notebook)

    window.set_child(root)
    log.debug_print(f"GUI built (Hyprland {hyprland_version})")
