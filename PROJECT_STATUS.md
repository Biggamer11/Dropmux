# Project status and handoff

Dropmux is a working GTK/VTE and tmux terminal workspace prototype.

## Current implementation

The application is a normal movable window. It contains a terminal viewport with real tmux panes, top menus, a customizable bottom bar, and task buttons. Status areas show session/window, active pane folder, and time/date in black sections with white text.

Task buttons refresh every three seconds from local Codex metadata. They map tasks to terminal sessions and do not start agents or send chat prompts. Task names and folders are local data and are excluded from this repository.

## Last validated state

Backend unit checks passed. Isolated tmux/GUI checks verified terminal input, pane splitting, session switching/survival, task session folders, external window synchronization, settings, texture styles and toolbar keyboard focus. Task catalog checks covered renames, archived tasks, stable mappings and database fallback.

## Next work

- Refine task-button overflow and status layout at small window sizes.
- Verify visual contrast and texture placement across window sizes.
- Add packaging and an optional configurable global shortcut.
- Improve reconnect handling and preserve the distinction between hiding the GUI and terminating panes.
- Treat Codex's local database schema as an implementation detail; update the read-only adapter if it changes.

The normal tmux client is embedded in VTE. Separate per-pane rendering using tmux control mode remains future work.
