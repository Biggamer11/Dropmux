# Dropmux

**A Linux terminal workspace that brings tmux sessions and Codex tasks into one window.**

Switch between task workspaces, manage terminal panes through native menus, and keep sessions running when the window closes. Dropmux combines a GTK/VTE terminal viewport with tmux-backed sessions and a customizable control bar.

> Working prototype. Core terminal and task-session workflows are implemented; packaging and further layout refinements are in progress.

## What you can do

- **Switch by task.** Select a local Codex task to attach or create a terminal session in its working folder. Task names refresh automatically every three seconds.
- **Manage panes visually.** Split panes, choose layouts, zoom the focused pane, and create windows through the File and Options menus.
- **Keep work running.** Hide or quit the interface without ending tmux sessions, then reopen to reconnect.
- **Stay oriented.** View the active session/window, pane folder, and local date/time in separate status sections.
- **Personalize the workspace.** Change the terminal font, control-bar color, visibility, and texture. Choose Brushed, Diagonal, Grid, Marble, or no texture.
- **Work from the keyboard.** Navigate task buttons and menus without taking focus away from terminal applications permanently.

Task buttons select terminal workspaces. They do not launch Codex agents or submit chat prompts.

## Getting started

### Requirements

Linux with a graphical desktop, Python 3, PyGObject, GTK 3, VTE 2.91, and tmux.

On Arch Linux:

```sh
sudo pacman -S python-gobject gtk3 vte3 tmux
```

### Launch

```sh
git clone https://github.com/Biggamer11/Dropmux.git
cd Dropmux
python3 dropmux.py --show
```

The optional `launch.sh` starts the application in an existing Distrobox named `codex-tools`. Adapt the launcher for another container, or run directly on the host.

## Recreate the Distrobox environment

Requires Distrobox and rootless Podman on the host. The setup script does not install these host prerequisites.

To clone an existing `codex-tools` box with its installed packages, including GitHub Desktop:

```sh
./scripts/recreate-distrobox.sh --name codex-tools-copy
```

Use `--source NAME` for a differently named source. The script refuses to overwrite an existing destination. This local clone is the closest match to the current environment; it is not a portable image backup.

To rebuild on another machine:

```sh
./scripts/recreate-distrobox.sh --fresh --name codex-tools
```

This starts from `docker.io/library/archlinux:latest` and installs the explicit official Arch package set recorded in `environment/packages.arch.txt`, including GTK/VTE, tmux, fish, Git and GitHub CLI. `environment/packages.snapshot.txt` records installed versions for reference; Arch is rolling-release, so a fresh rebuild does not pin those versions.

To include the community GitHub Desktop build on a fresh box:

```sh
./scripts/recreate-distrobox.sh --fresh --name codex-tools --with-github-desktop
```

The optional flag builds the current `github-desktop-bin` AUR recipe. Inspect that recipe before opting in; the build may differ from the package version in the snapshot. Without the flag, fresh mode installs official Arch packages only.

Distrobox shares the host home by default. Account credentials, personal settings and task lists are not distributed by this script; configure accounts on the destination host as needed. Run Dropmux in the new box using the launch command printed by the script.

## Controls

| Control | Action |
| --- | --- |
| Task button | Open or attach that task's terminal session |
| File | Create sessions/windows, hide, or quit |
| Options | Split panes, choose layouts, zoom, close panes, pin, or toggle fullscreen |
| Personalization | Change font, bar color, texture, or visibility |
| Help | View keyboard shortcuts |

**Hide** and **Quit** keep tmux running. **Close pane** asks for confirmation before terminating the selected pane and its processes.

### Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Alt+T | Focus task buttons |
| Left / Right | Move between focused task buttons |
| Enter / Space | Activate the selected button |
| Escape / Down | Return focus to the terminal |
| Alt+F / O / P / H | Open File / Options / Personalization / Help |

## Settings and task discovery

Display preferences are stored in `~/.config/dropmux/settings.json`. Terminal sessions use the dedicated tmux socket `dropmux`.

Dropmux reads local Codex task metadata through a read-only connection to `$CODEX_HOME/state_5.sqlite`, defaulting to `~/.codex/state_5.sqlite`. Archived tasks and subagents are excluded. This is an internal Codex database format and may change between versions.

If task discovery is unavailable, an optional `tasks.json` provides a local fallback. Start with `tasks.example.json`; each entry contains `id`, `title`, `cwd`, and a tmux-safe `session` name. Local task lists and settings are excluded from Git.

## Current limitations

- Task-button overflow and status layouts need refinement at smaller window sizes.
- The viewport embeds a normal tmux client; independent pane rendering through tmux control mode is not implemented.
- A configurable global dropdown shortcut, automatic reconnect, and installable packages remain planned work.
- Container shells may need their own configuration if host startup files reference unavailable dependencies.

## Development checks

```sh
python3 -m unittest test_backend.py
python3 test_integration.py
python3 gui_check.py
```

Integration checks use isolated tmux sockets. GUI checks require a graphical desktop and cover terminal input, pane splitting, session switching/survival, task working folders, external window updates, preferences, textures, and keyboard focus.

The bundled marble background is a generated image asset; controls remain native, interactive UI elements over the texture.
