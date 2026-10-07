#!/usr/bin/env python3
"""Dropmux: GTK/VTE dropdown interface to native tmux."""
import os
import json
from datetime import datetime
import shutil
import sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gtk, Gio, GLib, Gdk, Vte, Pango
import backend
from backend import Tmux
from preferences import Preferences
from task_catalog import load_tasks


class Dropmux(Gtk.Application):
    def __init__(self, application_id="io.dropmux.Terminal", config_path=None):
        super().__init__(application_id=application_id, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.preferences = Preferences(config_path)
        self.window = None
        self.tmux = Tmux()
        self.session = None
        self.snapshot = None
        self.pane_server = None
        self.pinned = self.preferences.values['pinned']
        self.fullscreen = False
        self.attaching = False

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if self.window is None:
            self.build()
            self.window.show_all()
        elif "--show" in args:
            self.window.show_all()
            self.window.present()
        elif self.window.get_visible():
            self.window.hide()
        else:
            self.window.show_all()
            self.window.present()
        self.term.grab_focus()
        return 0

    def button(self, bar, label, tooltip, callback):
        button = Gtk.Button(label=label)
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _: self.perform(callback))
        bar.pack_start(button, False, False, 0)
        return button

    def build(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Dropmux")
        self.window.set_decorated(True)
        self.window.set_default_size(self.preferences.values['width'], self.preferences.values['height'])
        self.window.set_keep_above(self.pinned)
        self.window.connect("delete-event", self.hide)
        self.window.connect('key-press-event', self.toolbar_shortcut)
        # X11 permits top placement; Wayland placement is controlled by the compositor.
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(*self.pointer_position())
        if monitor:
            area = monitor.get_workarea()
            if not self.preferences.path.exists():
                self.window.resize(area.width, max(250, area.height // 2))
            else:
                self.window.resize(min(area.width, self.preferences.values['width']), min(area.height, self.preferences.values['height']))
            self.window.move(area.x, area.y)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.window.add(root)
        root.pack_start(self.build_menubar(), False, False, 0)
        bar = Gtk.Box(spacing=3)
        self.toolbar = bar
        bar.get_style_context().add_class('status-toolbar')
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.CENTER)
        css = Gtk.CssProvider()
        css.load_from_data(b'''
        .native-footer { background: #00d700; color: black; padding: 2px 0; }
        .native-footer label { color: black; font: 12px monospace; }
        .native-footer button { min-height: 24px; padding: 2px 7px; }
        .native-footer button:checked { background-image: none; background-color: #96f0b2; border: 2px solid #143d20; }
        .status-toolbar, .status-toolbar button, .status-toolbar combobox,
        .status-toolbar box { background: transparent; background-image: none;
          border: none; box-shadow: none; color: black; }
        .status-toolbar button { min-height: 0; min-width: 0; padding: 0 5px;
          margin: 0; border-radius: 0; font: 11px monospace; }
        .status-toolbar button:hover { background: rgba(0,0,0,0.12); }
        .status-toolbar button:focus { outline: 1px solid black; }
        .marble-controls button { background: rgba(255,255,255,0.35); border: 1px solid rgba(0,0,0,0.20); border-radius: 4px; padding: 5px 5px; margin: 0 2px; }
        .marble-controls button:hover { background: rgba(255,255,255,0.7); }
        .status-toolbar label { font: 11px monospace; color: black; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.sessions = Gtk.ComboBoxText()
        self.sessions.set_tooltip_text("tmux session")
        self.sessions.connect("changed", self.session_changed)
        self.sessions.connect('key-press-event', self.navigate_toolbar)
        self.pin = Gtk.Button(label='Pinned' if self.pinned else 'Pin')
        self.catalog_path = os.environ.get('DROPMUX_TASKS_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks.json'))
        self.tasks = []
        self.sessions.set_tooltip_text("Workspace (existing tmux session)")
        self.refresh_tasks()
        accelerators = Gtk.AccelGroup()
        accelerators.connect(Gdk.KEY_t, Gdk.ModifierType.MOD1_MASK, Gtk.AccelFlags.VISIBLE, self.focus_toolbar)
        self.window.add_accel_group(accelerators)
        self.tabs = Gtk.Box(spacing=4, margin_start=6, margin_end=6)
        self.term = Vte.Terminal()
        self.term.set_font(Pango.FontDescription(self.preferences.values['font']))
        self.term.set_scrollback_lines(10000)
        self.term.set_color_background(Gdk.RGBA(0.055, 0.065, 0.085, 1))
        self.term.set_color_foreground(Gdk.RGBA(0.88, 0.90, 0.94, 1))
        self.term.connect("child-exited", self.child_exited)
        root.pack_start(self.term, True, True, 0)
        footer = Gtk.Box(spacing=8, margin_top=0)
        footer.set_size_request(-1, 40)
        self.footer = footer
        footer.set_no_show_all(True)
        self.bar_css = Gtk.CssProvider()
        footer.get_style_context().add_provider(self.bar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        footer.get_style_context().add_class('native-footer')
        self.footer_left = Gtk.Label(xalign=0, margin_start=6)
        self.footer_right = Gtk.Label(xalign=1, margin_end=6)
        self.footer_right.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.footer_right.set_max_width_chars(24)
        self.footer_clock = Gtk.Label(xalign=0.5)
        self.status_sections = []
        def section(label, tooltip):
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.NONE)
            frame.set_valign(Gtk.Align.CENTER)
            frame.set_tooltip_text(tooltip)
            frame.get_style_context().add_class("status-section")
            frame.add(label)
            self.status_sections.append(frame)
            return frame
        # One horizontal strip: workspace stays visible; the remaining controls
        # scroll sideways at narrow widths instead of wrapping or shrinking text.
        workspace = Gtk.Box(spacing=4, margin_start=6)
        workspace.set_valign(Gtk.Align.CENTER)
        workspace.pack_start(Gtk.Label(label="Workspace"), False, False, 0)
        workspace.pack_start(self.sessions, False, False, 0)
        footer.pack_start(workspace, False, False, 0)
        self.pin_pane_button = Gtk.Button(label="Pin pane")
        self.pin_pane_button.set_valign(Gtk.Align.CENTER)
        self.pin_pane_button.set_tooltip_text("Pin or unpin the active pane across workspaces")
        self.pin_pane_button.connect('clicked', lambda _: self.perform(self.toggle_pane_pin))
        self.footer_scroll = Gtk.ScrolledWindow()
        self.footer_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.footer_scroll.set_overlay_scrolling(True)
        self.footer_scroll.set_min_content_width(120)
        self.footer_scroll.connect('scroll-event', self.scroll_footer)
        self.footer_row = Gtk.Box(spacing=6)
        self.footer_row.set_valign(Gtk.Align.CENTER)
        self.footer_scroll.add(self.footer_row)
        footer.pack_start(self.footer_scroll, True, True, 0)
        self.footer_row.pack_start(self.pin_pane_button, False, False, 0)
        self.footer_row.pack_start(self.tabs, False, False, 0)
        self.footer_row.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 2)
        self.footer_row.pack_start(Gtk.Label(label="Pins"), False, False, 0)
        self.pinned_tabs = Gtk.Box(spacing=4)
        self.footer_row.pack_start(self.pinned_tabs, False, False, 0)
        self.footer_row.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 2)
        self.footer_row.pack_start(Gtk.Label(label="Tasks"), False, False, 0)
        self.footer_row.pack_start(bar, False, False, 0)
        self.footer_row.pack_start(section(self.footer_left, "Session and active tmux window"), False, False, 0)
        self.footer_row.pack_start(section(self.footer_right, "Active pane folder"), False, False, 0)
        self.footer_row.pack_start(section(self.footer_clock, "Local time and date"), False, False, 0)
        root.pack_start(footer, False, False, 0)
        self.apply_bar_style()
        if self.preferences.values["show_bar"]:
            for child in footer.get_children():
                child.show_all()
            footer.show()
        self.status = Gtk.Label(label="Ready", xalign=0, margin_start=8, margin_bottom=5)
        self.status.set_no_show_all(True)
        root.pack_start(self.status, False, False, 0)
        if not shutil.which(self.tmux.executable):
            self.status.set_text("tmux is missing. Install tmux, then restart Dropmux. See README.md.")
            for child in bar.get_children()[:-3]:
                child.set_sensitive(False)
            return
        self.perform(lambda: self.attach(self.tmux.ensure_session("main")))
        GLib.timeout_add(700, self.refresh)
        GLib.timeout_add(3000, self.refresh_tasks)

    def scroll_footer(self, widget, event):
        adjustment = self.footer_scroll.get_hadjustment()
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            _, dx, dy = event.get_scroll_deltas()
            delta = (dx if abs(dx) > abs(dy) else dy) * 60
        else:
            delta = -80 if event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT) else 80
        adjustment.set_value(max(adjustment.get_lower(), min(adjustment.get_upper() - adjustment.get_page_size(), adjustment.get_value() + delta)))
        return True

    def refresh_tasks(self):
        tasks = load_tasks(self.catalog_path)
        if tasks == self.tasks:
            return True
        focused = self.window.get_focus()
        focused_id = next((getattr(child, 'task_id', None) for child in self.toolbar.get_children() if child is focused), None)
        self.tasks = tasks
        for child in self.toolbar.get_children():
            self.toolbar.remove(child)
        for task in tasks:
            button = self.button(self.toolbar, task['title'], task['title'] + '\n' + task['cwd'],
                lambda task=task: self.select_task(task))
            button.set_size_request(120, -1)
            button.task_id = task['id']
            label = button.get_child()
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(24)
            self.toolbar.set_child_packing(button, True, True, 0, Gtk.PackType.START)
            button.connect('key-press-event', self.navigate_toolbar)
            button.show_all()
            if task['id'] == focused_id:
                button.grab_focus()
        return True

    def select_task(self, task):
        name = task['session']
        try:
            self.tmux.command('has-session', '-t', '=' + name)
        except RuntimeError:
            self.tmux.command('new-session', '-d', '-s', name, '-c', task['cwd'])
        self.attach(self.tmux.ensure_session(name))

    def build_menubar(self):
        menubar = Gtk.MenuBar()
        groups = [
            ('File', [('New session…', self.create_session),
                      ('New window', lambda: self.tmux.new_window(self.session)),
                      ('Hide', lambda: self.window.hide()), ('Quit', self.quit)]),
            ('Options', [('Split pane…', self.split_menu), ('Layouts…', self.layout_menu),
                         ('Zoom pane', lambda: self.tmux.command('resize-pane', '-Z', '-t', self.tmux.pane(self.session))),
                         ('Close pane…', self.close_pane), ('Toggle pin', self.toggle_pin), ('Fullscreen', self.toggle_fullscreen)]),
            ('Personalization', [('Terminal font…', self.choose_font),
                                 ('Bottom bar color…', self.choose_bar_color),
                                 ('Reset bar color', lambda: self.set_bar_color('#00d700'))]),
            ('Help', [('Keyboard shortcuts', self.show_shortcuts)])]
        for title, choices in groups:
            top = Gtk.MenuItem.new_with_mnemonic('_' + title)
            menu = Gtk.Menu()
            for label, callback in choices:
                item = Gtk.MenuItem(label=label)
                item.connect('activate', lambda _, callback=callback: self.perform(callback))
                menu.append(item)
            if title == 'Personalization':
                textures = Gtk.MenuItem(label='Bottom bar texture')
                texture_menu = Gtk.Menu()
                group = None
                for name, label in [('none', 'None'), ('brushed', 'Brushed'), ('diagonal', 'Diagonal'), ('grid', 'Grid'), ('marble', 'Marble')]:
                    option = Gtk.RadioMenuItem.new_with_label(group, label)
                    group = option.get_group()
                    option.set_active(name == self.preferences.values['bar_texture'])
                    option.connect('toggled', lambda item, name=name: self.set_bar_texture(name) if item.get_active() and hasattr(self, 'bar_css') else None)
                    texture_menu.append(option)
                textures.set_submenu(texture_menu)
                menu.append(textures)
                visible = Gtk.CheckMenuItem(label='Show bottom control bar')
                visible.set_active(self.preferences.values['show_bar'])
                visible.connect('toggled', self.toggle_bar)
                menu.append(visible)
            top.set_submenu(menu)
            menubar.append(top)
        return menubar

    def apply_bar_style(self):
        textures = {
            'none': 'none',
            'brushed': 'repeating-linear-gradient(0deg, rgba(255,255,255,0.14) 0px, rgba(255,255,255,0.14) 1px, rgba(0,0,0,0.06) 1px, rgba(0,0,0,0.06) 3px)',
            'diagonal': 'repeating-linear-gradient(135deg, rgba(255,255,255,0.12) 0px, rgba(255,255,255,0.12) 2px, transparent 2px, transparent 8px)',
            'grid': 'repeating-linear-gradient(0deg, rgba(0,0,0,0.08) 0px, rgba(0,0,0,0.08) 1px, transparent 1px, transparent 8px), repeating-linear-gradient(90deg, rgba(0,0,0,0.08) 0px, rgba(0,0,0,0.08) 1px, transparent 1px, transparent 8px)'
        }
        marble = Gio.File.new_for_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'marble-bar.png')).get_uri()
        textures['marble'] = 'url("' + marble + '")'
        css = '.native-footer { background-size: 100%% 100%%; background-repeat: no-repeat; background-color: %s; background-image: %s; }' % (
            self.preferences.values['bar_color'], textures[self.preferences.values['bar_texture']])
        self.bar_css.load_from_data(css.encode())
        section_css = Gtk.CssProvider()
        section_css.load_from_data(b'.status-section { background-color: #000000; background-image: none; border: 1px solid #555555; border-radius: 6px; padding: 4px 7px; margin: 0 2px; } .status-section label { color: #ffffff; font: 11px monospace; }')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), section_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)
        context = self.toolbar.get_style_context()
        if self.preferences.values['bar_texture'] == 'marble':
            context.add_class('marble-controls')
        else:
            context.remove_class('marble-controls')

    def set_bar_texture(self, texture):
        self.preferences.values['bar_texture'] = texture
        self.apply_bar_style()
        self.save_preferences()

    def set_bar_color(self, color):
        self.preferences.values['bar_color'] = color
        self.apply_bar_style()
        self.save_preferences()

    def choose_bar_color(self):
        dialog = Gtk.ColorChooserDialog(title='Bottom bar color', transient_for=self.window)
        color = Gdk.RGBA()
        color.parse(self.preferences.values['bar_color'])
        dialog.set_rgba(color)
        dialog.set_use_alpha(False)
        if dialog.run() == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            self.set_bar_color('#%02x%02x%02x' % tuple(round(v * 255) for v in (color.red, color.green, color.blue)))
        dialog.destroy()

    def toggle_bar(self, item):
        self.preferences.values['show_bar'] = item.get_active()
        if item.get_active():
            for child in self.footer.get_children():
                child.show_all()
            self.footer.show()
        else:
            self.footer.hide()
        self.save_preferences()

    def show_shortcuts(self):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
            buttons=Gtk.ButtonsType.CLOSE, text='Dropmux keyboard shortcuts')
        dialog.format_secondary_text('Alt+T: focus bottom controls\nLeft / Right: move between controls\nEnter / Space: activate\nEscape / Down: return to terminal\nAlt+F / Alt+O / Alt+P / Alt+H: open menus')
        dialog.run()
        dialog.destroy()

    def toolbar_shortcut(self, window, event):
        if event.keyval in (Gdk.KEY_t, Gdk.KEY_T) and event.state & Gdk.ModifierType.MOD1_MASK:
            if self.toolbar.get_children():
                self.toolbar.get_children()[0].grab_focus()
            return True
        return False

    def focus_toolbar(self, *_):
        if self.toolbar.get_children():
            self.toolbar.get_children()[0].grab_focus()
        return True

    def navigate_toolbar(self, widget, event):
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Down):
            self.term.grab_focus()
            return True
        if event.keyval not in (Gdk.KEY_Left, Gdk.KEY_Right):
            return False
        children = [child for child in self.toolbar.get_children() if child.get_sensitive() and child.get_visible()]
        if widget in children:
            step = -1 if event.keyval == Gdk.KEY_Left else 1
            children[(children.index(widget) + step) % len(children)].grab_focus()
            return True
        return False

    def pointer_position(self):
        seat = Gdk.Display.get_default().get_default_seat()
        _, x, y = seat.get_pointer().get_position()
        return x, y

    def hide(self, *_):
        self.save_preferences()
        self.window.hide()
        return True

    def save_preferences(self):
        if self.window is None:
            return
        if not self.fullscreen and not self.window.is_maximized():
            width, height = self.window.get_size()
            self.preferences.values.update(width=width, height=height)
        self.preferences.values['pinned'] = self.pinned
        try:
            self.preferences.save()
        except OSError as error:
            self.status.set_text('Could not save settings: '+str(error))

    def do_shutdown(self):
        self.save_preferences()
        Gtk.Application.do_shutdown(self)

    def choose_font(self):
        dialog = Gtk.FontChooserDialog(title='Terminal font', transient_for=self.window)
        dialog.set_font(self.preferences.values['font'])
        if dialog.run() == Gtk.ResponseType.OK:
            self.preferences.values['font'] = dialog.get_font()
            self.term.set_font(Pango.FontDescription(dialog.get_font()))
            self.save_preferences()
        dialog.destroy()

    def perform(self, callback):
        try:
            callback()
        except Exception as error:
            self.status.set_text(str(error))
        self.term.grab_focus()

    def attach(self, session):
        self.tmux.command("set-option", "-t", session, "mouse", "on")
        self.tmux.command("set-option", "-t", session, "status", "off")
        if self.session is not None:
            if not getattr(self, "client", None):
                raise RuntimeError("Terminal is still connecting; try again in a moment.")
            self.tmux.command("switch-client", "-c", self.client, "-t", session)
            self.session = session
            self.snapshot = None
            return
        self.session = session
        # Identify our client through its terminal tty after spawn, rather than touching other clients.
        self.attaching = True
        self.term.spawn_async(Vte.PtyFlags.DEFAULT, os.getcwd(), self.tmux.attach_argv(session),
                              [f"{key}={value}" for key, value in {**backend.CHILD_ENV, "TERM": "xterm-256color"}.items()] if backend.CHILD_ENV is not None else None, GLib.SpawnFlags.DEFAULT, None, None, -1, None, self.spawned, None)

    def spawned(self, terminal, pid, error, data):
        self.attaching = False
        if error:
            self.session = None
            self.status.set_text(str(error))
            return
        self.pid = pid
        self.client = None
        self.refresh()

    def child_exited(self, *_):
        self.session = None
        self.snapshot = None
        self.status.set_text("Detached or session ended. Choose or create a session to reconnect.")

    def refresh(self):
        try:
            sessions = self.tmux.sessions()
            if self.session and not self.attaching:
                clients = self.tmux.command("list-clients", "-F", "#{client_pid}\t#{client_name}\t#{session_id}").splitlines()
                for line in clients:
                    pid, client, session = line.split("\t")
                    if pid == str(self.pid):
                        self.client, self.session = client, session
                all_panes = self.tmux.panes()
                panes = [row for row in all_panes if row[0] == self.session]
                self.pane_server = self.tmux.command('display-message', '-p', '#{socket_path}:#{pid}:#{start_time}')
                valid_ids = {row[5] for row in all_panes}
                pins = [pin for pin in self.preferences.values['pane_pins']
                        if pin['server'] == self.pane_server and pin['pane'] in valid_ids]
                if pins != self.preferences.values['pane_pins']:
                    self.preferences.values['pane_pins'] = pins
                    self.preferences.save()
                active_pane = self.tmux.pane(self.session)
            else:
                all_panes = []
                panes = []
                active_pane = None
            if self.session:
                info = self.tmux.command('display-message', '-p', '-t', self.session + ':',
                    '[#{session_name}] #{window_index}:#{window_name}#{?window_zoomed_flag,Z,}\t#{pane_current_path}').split('\t', 1)
                self.footer_left.set_text('SESSION  ' + info[0])
                path = info[1] if len(info)>1 else ''
                self.footer_right.set_text('PATH  ' + path)
                self.footer_right.set_tooltip_text(path)
                self.footer_clock.set_text('TIME  ' + datetime.now().strftime('%H:%M · %d %b %Y'))
            pinned_ids = {pin['pane'] for pin in self.preferences.values['pane_pins']}
            pinned_rows = [row for row in all_panes if row[5] in pinned_ids]
            self.pin_pane_button.set_sensitive(bool(active_pane))
            self.pin_pane_button.set_label("Unpin pane" if active_pane in pinned_ids else "Pin pane")
            snapshot = (sessions, panes, self.session, active_pane, pinned_rows)
            if snapshot == self.snapshot:
                return True
            self.snapshot = snapshot
            self.updating = True
            self.sessions.remove_all()
            for identifier, name in sessions:
                self.sessions.append(identifier, name)
            self.sessions.set_active_id(self.session)
            self.updating = False
            for child in self.tabs.get_children():
                self.tabs.remove(child)
            for session_id, session_name, window, window_index, pane_index, pane_id, title in panes:
                active = pane_id == active_pane
                caption = " ".join(title.split()) or "Terminal"
                label = ("● " if active else "") + f"{window_index}.{pane_index} · {caption}"
                button = Gtk.ToggleButton(label=label)
                button.set_size_request(144, -1)
                button.pane_id = pane_id
                button.connect('button-press-event', lambda widget, event, pid=pane_id: self.pane_context_menu(widget, event, pid))
                button.set_active(active)
                button.set_tooltip_text(f"Focus pane {pane_id}: {session_name}/{window_index}.{pane_index} — {caption}")
                child = button.get_child()
                child.set_ellipsize(Pango.EllipsizeMode.END)
                child.set_max_width_chars(18)
                button.connect("clicked", lambda _, sid=session_id, wid=window, pid=pane_id:
                               self.perform(lambda: self.focus_pane(sid, wid, pid)))
                self.tabs.pack_start(button, False, False, 0)
            self.tabs.show_all()
            for child in self.pinned_tabs.get_children():
                self.pinned_tabs.remove(child)
            for sid, session_name, wid, window_index, pane_index, pid, title in pinned_rows:
                caption = " ".join(title.split()) or "Terminal"
                button = Gtk.Button(label=f"★ {session_name}/{window_index}.{pane_index} · {caption}")
                button.set_size_request(172, -1)
                button.pane_id = pid
                button.connect('button-press-event', lambda widget, event, pid=pid: self.pane_context_menu(widget, event, pid))
                button.get_child().set_ellipsize(Pango.EllipsizeMode.END)
                button.get_child().set_max_width_chars(18)
                button.set_tooltip_text(f"Pinned pane {pid} — switch workspace and focus {caption}")
                button.connect('clicked', lambda _, pid=pid: self.perform(lambda: self.focus_pinned_pane(pid)))
                self.pinned_tabs.pack_start(button, False, False, 0)
            if not pinned_rows:
                self.pinned_tabs.pack_start(Gtk.Label(label="—", tooltip_text="Right-click a pane or use Pin pane to add a global pin"), False, False, 0)
            self.pinned_tabs.show_all()
            if self.session:
                self.status.set_text("Native tmux · click panes to focus · drag dividers to resize · closing this window hides it")
        except Exception as error:
            self.status.set_text(str(error))
        return True

    def pane_context_menu(self, widget, event, pane):
        if event.button != 3:
            return False
        pinned = any(pin['pane'] == pane for pin in self.preferences.values['pane_pins'])
        self.menu([("Unpin pane" if pinned else "Pin pane", lambda: self.toggle_pane_pin(pane))])
        return True

    def toggle_pane_pin(self, pane=None):
        if not self.session:
            return
        self.refresh()
        pane = pane or self.tmux.pane(self.session)
        if not any(row[5] == pane for row in self.tmux.panes()):
            return
        pins = self.preferences.values['pane_pins']
        record = {'server': self.pane_server, 'pane': pane}
        self.preferences.values['pane_pins'] = [pin for pin in pins if pin != record] if record in pins else pins + [record]
        self.preferences.save()
        self.snapshot = None
        self.refresh()

    def focus_pinned_pane(self, pane):
        self.refresh()
        if not any(pin['pane'] == pane and pin['server'] == self.pane_server
                   for pin in self.preferences.values['pane_pins']):
            return
        row = next((row for row in self.tmux.panes() if row[5] == pane), None)
        if row:
            self.focus_pane(row[0], row[2], row[5])

    def focus_pane(self, session, window, pane):
        self.tmux.focus_pane(window, pane)
        if self.session != session:
            self.attach(session)
        # Rebuild even when a click toggled the already-active button off.
        self.snapshot = None
        self.refresh()
        self.term.grab_focus()

    def session_changed(self, combo):
        if getattr(self, "updating", False):
            return
        session = combo.get_active_id()
        if session:
            self.perform(lambda: self.attach(session))

    def create_session(self):
        dialog = Gtk.Dialog(title="New tmux session", transient_for=self.window, modal=True)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Create / attach", Gtk.ResponseType.OK)
        entry = Gtk.Entry(placeholder_text="Session name, e.g. dev")
        dialog.get_content_area().add(entry)
        dialog.show_all()
        response = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.attach(self.tmux.ensure_session(name))

    def menu(self, choices):
        menu = Gtk.Menu()
        for title, callback in choices:
            item = Gtk.MenuItem(label=title)
            item.connect("activate", lambda _, callback=callback: self.perform(callback))
            menu.append(item)
        menu.show_all()
        menu.popup_at_pointer(None)

    def split_menu(self):
        self.menu([("Side by side", lambda: self.tmux.split(self.session)),
                   ("Stacked", lambda: self.tmux.split(self.session, True))])

    def layout_menu(self):
        self.menu([(title, lambda layout=layout: self.tmux.command("select-layout", "-t", self.session + ":", layout))
                   for title, layout in [("Even columns", "even-horizontal"), ("Even rows", "even-vertical"),
                                         ("Main pane + stack", "main-vertical"), ("Tiled", "tiled")]])

    def close_pane(self):
        pane = self.tmux.pane(self.session)
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL, text="End focused pane?")
        dialog.format_secondary_text("This terminates the pane and may terminate its running processes. Hide keeps them running.")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.tmux.command("kill-pane", "-t", pane)

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.window.set_keep_above(self.pinned)
        self.pin.set_label("Pinned" if self.pinned else "Pin")
        self.save_preferences()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.window.fullscreen() if self.fullscreen else self.window.unfullscreen()


if __name__ == "__main__":
    app = Dropmux()
    app.run(sys.argv)
