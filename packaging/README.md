# Dropmux AppImage test build

Source: https://github.com/Biggamer11/Dropmux at 786021c, plus the local packaging changes in this folder/branch. This is an unsigned development build, not alpha1-2 and not a published release.

## Pane taskbar and workspaces

This revision is `slim-row-3`. All bottom-bar controls occupy one horizontal row. The workspace selector stays visible; pane buttons, global pins, task buttons and status sections scroll sideways when necessary. Scroll the mouse wheel over the strip or use its horizontal scrollbar. Pane buttons keep a readable minimum width instead of collapsing to tiny labels. The bottom bar's Workspace selector maps to existing tmux sessions. It switches to those sessions without recreating panes or stopping their processes. Pane buttons list every pane across the selected workspace's windows; each has a workspace/window.pane label and title. The active pane has a dot and selected state. Click a button to focus that exact existing pane. Adds, removals, title changes and external focus changes refresh automatically. Right-click any pane button for **Pin pane / Unpin pane**, or use **Pin pane / Unpin pane** to keep the active pane in the visually separate global **Pins** section on the same row. A pin jumps to the correct workspace and pane; it never starts another terminal. Pins survive app restarts while the same tmux server is running. Closed-pane pins are removed automatically, and stale pins from a previous server are discarded. Existing Codex task buttons, menus, status and personalization remain available. New workspaces use the existing File → New session action; pane creation/closing uses the existing Options actions.

## Run

Download `Dropmux-dev-786021c-x86_64-v3.AppImage`, then:

```sh
chmod +x Dropmux-dev-786021c-x86_64-v3.AppImage
./Dropmux-dev-786021c-x86_64-v3.AppImage --show
```

If FUSE mounting is unavailable, no system installation is needed:

```sh
./Dropmux-dev-786021c-x86_64-v3.AppImage --appimage-extract-and-run --show
```

The extraction option temporarily uses roughly 220 MB of disk space. The file can be moved freely. Desktop integration is optional and is not installed by this build.

## Compatibility and contents

This build was assembled from the current CachyOS machine, not an older distribution build container. It requires an **x86-64-v3 CPU (including AVX2), Linux kernel 6.1 or newer, and a working graphical Linux desktop**. It is not for ARM machines or older x86 CPUs. Cross-distribution portability is unverified; this is a test build for compatible machines.

Bundled: Python 3.14.7, PyGObject/Pycairo, GTK 3, VTE 0.84, SQLite, their linked libraries including the matching libc/loader, image decoders, schemas/icons, tmux 3.7c and terminfo. Installed Python, GTK, VTE or tmux are not required.

Still supplied by the host: kernel/display server, fonts/font configuration, /bin/sh, the user's shell, ordinary command-line programs, home directory, desktop services, and any external developer tools. There is no embedded Linux distribution or preconfigured development environment. Distrobox and Podman are not needed for host-shell operation and are not bundled. To enter a container, install/configure those separately and run `distrobox enter <name>` in the terminal. Codex itself, credentials, and task databases are not included. Without Codex metadata, ordinary terminal sessions work; optional task entries can live in `~/.config/dropmux/tasks.json` (or `$XDG_CONFIG_HOME/dropmux/tasks.json`). Override with `DROPMUX_TASKS_FILE`.

New sessions/panes use the host shell when launched directly. The original repository's `launch.sh` explicitly enters the `codex-tools` Distrobox first; that separate launch route creates sessions in the container. Attaching to an existing tmux server preserves its environment. The app uses tmux socket `dropmux`, as upstream does. Existing sessions from another tmux version may report a protocol mismatch; this build does not kill or migrate them.

## Persistence

The bundled tmux executable and libraries are copied on first launch to a versioned directory under `~/.cache/dropmux` (or `$XDG_CACHE_HOME/dropmux`), around 19 MB. This lets detached sessions continue after the AppImage unmounts. Do not remove that cache while its tmux sessions are running. Dropmux preferences remain in `~/.config/dropmux/settings.json` as upstream specifies. No global install, OS changes, credential access, or release publication is performed.

The UI uses GTK3 software rendering to avoid loading host OpenGL drivers. This setting is scoped to the UI and is not injected into terminal commands. The UI invokes its own dynamic loader with a scoped library search path. Its Python/UI environment is not passed to host shells. VTE receives TERM=xterm-256color explicitly. The tmux runtime supplies terminfo from its persistent directory.

## Rebuild locally

The script deliberately refuses to overwrite an existing AppDir. Requires the installed Arch/CachyOS Python, PyGObject, Pycairo, GTK3, VTE3, tmux, pacman, ldd and standard libraries. It reads only public system runtime files and repository source. No package-manager installation happens.

```sh
python3 packaging/build-appdir.py /absolute/path/Dropmux.AppDir
ARCH=x86_64 VERSION=dev-786021c /path/to/appimagetool \
  --no-appstream --runtime-file /path/to/runtime-x86_64 \
  /absolute/path/Dropmux.AppDir Dropmux-dev-786021c-x86_64-v3.AppImage
```

Build tools: official AppImage/appimagetool and AppImage/type2-runtime continuous releases downloaded 2026-10-07. Tool hashes accompany the delivered build report. The runtime package inventory and source commit are embedded at `usr/share/dropmux/build-manifest.json`; license notices supplied by the installed dependency packages and SPDX texts are included under `usr/share/licenses`. This build does not assign a new license to Dropmux; public redistribution beyond the requested private test needs an upstream project license and dependency source-compliance review.

## Diagnostic commands

`--version`, `--self-test`, `--integration-test`, and `--gui-test` are available. GUI checks open a temporary test window and use synthetic task metadata and isolated tmux sockets; they do not inspect the user's Codex database. Integration tests create temporary tmux sessions and remove those test sessions when finished. Use a graphical desktop for `--gui-test`.
