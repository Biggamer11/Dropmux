"""Small tmux command boundary; UI state remains owned by tmux."""
import subprocess

CHILD_ENV = None
DEFAULT_EXECUTABLE = "tmux"


class Tmux:
    def __init__(self, executable=None, socket="dropmux", runner=subprocess.run):
        self.executable, self.socket, self.runner = executable or DEFAULT_EXECUTABLE, socket, runner

    def command(self, *args):
        result = self.runner([self.executable, "-L", self.socket, *args],
                             capture_output=True, text=True, timeout=3,
                             **({"env": CHILD_ENV} if CHILD_ENV is not None else {}))
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "tmux command failed")
        return result.stdout.strip()

    def ensure_session(self, name):
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
            raise ValueError("Use letters, numbers, underscores, or hyphens for session names.")
        try:
            self.command("has-session", "-t", "=" + name)
        except RuntimeError:
            self.command("new-session", "-d", "-s", name)
        return self.command("display-message", "-p", "-t", "=" + name + ":", "#{session_id}")

    def sessions(self):
        return [line.split("\t", 1) for line in self.command("list-sessions", "-F", "#{session_id}\t#{session_name}").splitlines()]

    def windows(self, session):
        return [line.split("\t", 2) for line in self.command("list-windows", "-t", session, "-F", "#{window_id}\t#{window_name}\t#{window_active}").splitlines()]

    def panes(self, session=None):
        fields = "#{session_id}\t#{session_name}\t#{window_id}\t#{window_index}\t#{pane_index}\t#{pane_id}\t#{pane_title}"
        return [row.split("\t", 6) for row in self.command("list-panes", *(["-s", "-t", session] if session else ["-a"]), "-F", fields).splitlines()
                if len(row.split("\t", 6)) == 7]

    def focus_pane(self, window, pane):
        self.command("select-window", "-t", window)
        self.command("select-pane", "-t", pane)

    def pane(self, session):
        return self.command("display-message", "-p", "-t", session + ":", "#{pane_id}")

    def split(self, session, stacked=False):
        pane = self.pane(session)
        cwd = self.command("display-message", "-p", "-t", pane, "#{pane_current_path}")
        self.command("split-window", "-v" if stacked else "-h", "-t", pane, "-c", cwd)

    def new_window(self, session):
        pane = self.pane(session)
        cwd = self.command("display-message", "-p", "-t", pane, "#{pane_current_path}")
        self.command("new-window", "-t", session + ":", "-c", cwd)

    def attach_argv(self, session):
        return [self.executable, "-L", self.socket, "attach-session", "-t", session]
