import subprocess
import unittest
from backend import Tmux


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def runner(argv, **kwargs):
            self.calls.append(argv)
            output = "%7" if argv[-1] == "#{pane_id}" else "/tmp/path with spaces"
            return subprocess.CompletedProcess(argv, 0, output, "")
        self.tmux = Tmux(runner=runner)

    def test_split_targets_real_pane_and_preserves_cwd_argument(self):
        self.tmux.split("$1")
        self.assertEqual(self.calls[-1], ["tmux", "-L", "dropmux", "split-window", "-h", "-t", "%7", "-c", "/tmp/path with spaces"])

    def test_stacked_split(self):
        self.tmux.split("$1", stacked=True)
        self.assertIn("-v", self.calls[-1])

    def test_window_targets_session(self):
        self.tmux.new_window("$2")
        self.assertEqual(self.calls[-1][3:7], ["new-window", "-t", "$2:", "-c"])

    def test_reject_invalid_session_before_sending_commands(self):
        with self.assertRaises(ValueError):
            self.tmux.ensure_session("dev:1")
        self.assertEqual(self.calls, [])

    def test_attach_does_not_kill_sessions(self):
        self.assertEqual(self.tmux.attach_argv("$2"), ["tmux", "-L", "dropmux", "attach-session", "-t", "$2"])


if __name__ == "__main__":
    unittest.main()
