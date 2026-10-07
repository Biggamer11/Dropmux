"""Small tmux command boundary; UI state remains owned by tmux."""
import subprocess


class Tmux:
    def __init__(self, executable="tmux", socket="dropmux", runner=subprocess.run):
        self.executable, self.socket, self.runner = executable, socket, runner

    def command(self, *args):
        result = self.runner([self.executable, "-L", self.socket, *args],
                             capture_output=True, text=True, timeout=3)
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
