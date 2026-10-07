# Dropmux

Dropmux is a Linux terminal workspace. It combines a GTK/VTE terminal viewport, real tmux sessions and panes, and buttons for local Codex tasks.

## Features

- A normal movable desktop window with a native bottom control bar.
- Task buttons that attach or create a dedicated tmux session in each task's working folder.
- Read-only refresh of local Codex task names every three seconds; archived tasks and subagents are excluded.
- Real tmux pane splitting, layouts, zoom, session switching and window creation through File and Options menus.
- Terminal sessions survive hiding, quitting and reopening the GUI.
- Separate black status sections with white text for session/window, active pane path and local time/date.
- Personalization for terminal font, bar color, bar visibility, and Brushed, Diagonal, Grid or generated Marble textures.
- Saved window size and display preferences.

Task buttons select terminal workspaces. They do not launch Codex agents or submit chat prompts.

## Run

Requires Python 3, PyGObject, GTK 3, VTE 2.91 and tmux. On Arch Linux, dependencies are `python-gobject gtk3 vte3 tmux`.

```sh
python3 dropmux.py --show
```

The supplied `launch.sh` uses an existing Arch Distrobox named `codex-tools`. Edit that launcher for a different container, or run Python directly on a host with the dependencies installed.

## Keyboard and menus

Alt+T focuses task buttons; Left/Right move between them, Enter/Space activates, and Escape/Down returns to the terminal. Alt+F/O/P/H opens File, Options, Personalization or Help.

Pane/window actions live in File and Options. Hide and Quit leave tmux running; Close pane asks for confirmation before terminating that pane.

## Local settings and task metadata

Preferences are saved to `~/.config/dropmux/settings.json`. tmux runs on a dedicated `dropmux` socket.

Task discovery reads metadata from `$CODEX_HOME/state_5.sqlite` (default `~/.codex/state_5.sqlite`) using a read-only connection. This database is a Codex implementation detail; future schema changes may require updates. When unavailable, Dropmux uses an optional local `tasks.json`; copy `tasks.example.json` to get started. Task entries contain `id`, `title`, `cwd`, and a safe tmux `session` name. Personal task metadata is excluded from Git.

The terminal embeds the normal tmux client in VTE. Independent pane rendering through tmux control mode, global dropdown shortcuts, automatic reconnect and packaging remain future work. Small windows may need further layout refinement. A host fish configuration referencing files missing inside a container can produce a shell startup warning.

## Validation

```sh
python3 -m unittest test_backend.py
python3 test_integration.py
python3 gui_check.py
```

Integration and GUI checks use dedicated test tmux sockets. GUI checks require a graphical desktop and verify terminal input, pane splitting, session survival/switching, task session folders, external tmux window changes, settings, texture styles and keyboard focus.

`assets/marble-bar.png` was generated with built-in imagegen: pale ivory/light gray marble, subtle veins near the edges, quiet central space guided by the toolbar layout, and no painted text or buttons.

