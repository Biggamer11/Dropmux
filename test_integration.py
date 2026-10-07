import os
import subprocess
import tempfile
import time
import unittest
from backend import Tmux

class RealTmuxTest(unittest.TestCase):
 def test_real_panes_windows_input_and_survival(self):
  socket='dropmux-test-'+str(os.getpid())
  def runner(argv,**kwargs):
   return subprocess.run(argv,env={**os.environ,'SHELL':'/bin/sh'},**kwargs)
  tmux=Tmux(socket=socket,runner=runner)
  try:
   session=tmux.ensure_session('test')
   self.assertTrue(session.startswith('$'))
   first=tmux.pane(session)
   time.sleep(.2)
   tmux.command('send-keys','-t',first,'printf "DROP%s_OK\\n" MUX','Enter')
   for _ in range(30):
    capture=tmux.command('capture-pane','-p','-t',first)
    if 'DROPMUX_OK' in capture:break
    time.sleep(.1)
   self.assertIn('DROPMUX_OK',capture)
   cwd=tmux.command('display-message','-p','-t',first,'#{pane_current_path}')
   tmux.split(session)
   self.assertEqual(len(tmux.command('list-panes','-t',session+':').splitlines()),2)
   self.assertEqual(tmux.command('display-message','-p','-t',tmux.pane(session),'#{pane_current_path}'),cwd)
   tmux.split(session,True)
   self.assertEqual(len(tmux.command('list-panes','-t',session+':').splitlines()),3)
   tmux.command('select-layout','-t',session+':','tiled')
   tmux.command('resize-pane','-Z','-t',tmux.pane(session))
   tmux.new_window(session)
   self.assertEqual(len(tmux.windows(session)),2)
   self.assertTrue(tmux.command('has-session','-t',session)== '')
  finally:
   subprocess.run(['tmux','-L',socket,'kill-server'],capture_output=True)

if __name__=='__main__':unittest.main()
