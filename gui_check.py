"""Exercise actual VTE child input and GUI detach using an isolated tmux socket."""
import os,subprocess,sys,tempfile
from preferences import Preferences
from gi.repository import GLib
from dropmux import Dropmux, Gdk
from types import SimpleNamespace
from backend import Tmux
temp=tempfile.TemporaryDirectory()
config=os.path.join(temp.name,'settings.json')
app=Dropmux(application_id='io.dropmux.Test'+str(os.getpid()),config_path=config);app.tmux=Tmux(socket='dropmux-gui-test-'+str(os.getpid()))
result={'input':False,'client':False,'survived':False}
step=0

def check():
 global step
 step+=1
 if step==1:
  result['client']=bool(getattr(app,'client',None))
  app.term.feed_child(b'printf "GUI%s_OK\\n" INPUT\r')
 elif step==2:
  result['input']='GUIINPUT_OK' in app.tmux.command('capture-pane','-p','-t',app.tmux.pane(app.session))
  app.tmux.split(app.session)
  other=app.tmux.ensure_session('second')
  app.attach(other)
  result['switch']=app.session==other
  app.attach(app.tmux.ensure_session('main'))
  result['panes']=len(app.tmux.command('list-panes','-t',app.session+':').splitlines())==2
  app.window.hide()
  result['hidden_alive']=bool(app.tmux.sessions())
  app.window.show_all()
 elif step==3:
  previous=app.session
  app.select_task({'session':'task-check','cwd':temp.name})
  result['task_switch']=app.tmux.command('display-message','-p','-t',app.session+':','#{pane_current_path}')==temp.name
  app.attach(previous)
  app.tmux.new_window(app.session)
  app.refresh()
  result['external_sync']=len(app.tabs.get_children())==2
  for texture in ('none', 'brushed', 'diagonal', 'grid', 'marble'):
   app.set_bar_texture(texture)
  result['textures']=True
  app.toggle_pin()
  app.preferences.values['font']='Monospace 13'
  app.save_preferences()
  loaded=Preferences(config).values
  result['saved_settings']=loaded['font']=='Monospace 13' and loaded['pinned']==app.pinned
  app.toolbar_shortcut(app.window,SimpleNamespace(keyval=Gdk.KEY_t,state=Gdk.ModifierType.MOD1_MASK))
  children=app.toolbar.get_children()
  app.navigate_toolbar(children[0],SimpleNamespace(keyval=Gdk.KEY_Right))
  result['arrow_focus']=app.window.get_focus() is children[1]
  app.navigate_toolbar(children[1],SimpleNamespace(keyval=Gdk.KEY_Escape))
  result['terminal_focus']=app.window.get_focus() is app.term
  app.quit();return False
 return True

GLib.timeout_add_seconds(2,check)
try:
 app.run(['dropmux-gui-check','--show'])
 result['survived']=bool(app.tmux.sessions())
 print(result)
 if not all(result.values()):sys.exit(1)
finally:
 subprocess.run(['tmux','-L',app.tmux.socket,'kill-server'],capture_output=True)
 temp.cleanup()
