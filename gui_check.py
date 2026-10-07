"""Exercise actual VTE child input and GUI detach using an isolated tmux socket."""
import os,subprocess,sys,tempfile,json
from preferences import Preferences
from gi.repository import GLib
from dropmux import Dropmux, Gdk
from types import SimpleNamespace
from backend import Tmux
temp=tempfile.TemporaryDirectory()
config=os.path.join(temp.name,'settings.json')
os.environ['CODEX_HOME']=temp.name
os.environ['DROPMUX_TASKS_FILE']=os.path.join(temp.name,'tasks.json')
with open(os.environ['DROPMUX_TASKS_FILE'],'w') as fixture:
 json.dump([{'id':'fixture','title':'Test workspace','cwd':temp.name,'session':'fixture-task'},{'id':'fixture2','title':'Second workspace','cwd':temp.name,'session':'fixture-task2'}],fixture)
app=Dropmux(application_id='io.dropmux.Test'+str(os.getpid()),config_path=config);app.tmux=Tmux(socket='dropmux-gui-test-'+str(os.getpid()))
result={'input':False,'client':False,'survived':False}
step=0

def check():
 global step
 step+=1
 if step==1:
  print('GUI startup:', app.status.get_text(), flush=True)
  if app.session is None:
   app.quit();return False
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
  result['external_sync']=len(app.tabs.get_children())==3
  rows=app.tmux.panes(app.session)
  identifiers={row[5] for row in rows}
  target=rows[0][5]
  before=len(rows)
  for _ in range(3):
   next(button for button in app.tabs.get_children() if button.pane_id==target).clicked()
  result['pane_focus_repeat']=app.tmux.pane(app.session)==target and len(app.tmux.panes(app.session))==before
  result['active_highlight']=sum(button.get_active() for button in app.tabs.get_children())==1 and next(button for button in app.tabs.get_children() if button.pane_id==target).get_active()
  app.tmux.command('select-pane','-t',target,'-T','Renamed pane')
  app.refresh()
  result['pane_rename']='Renamed pane' in next(button for button in app.tabs.get_children() if button.pane_id==target).get_label()
  choices=[]
  original_menu=app.menu
  app.menu=lambda items: choices.extend(items)
  handled=app.pane_context_menu(None,SimpleNamespace(button=3),target)
  app.menu=original_menu
  choices[0][1]()
  result['right_click_pin']=handled and choices[0][0]=='Pin pane'
  result['pin_saved']=Preferences(config).values['pane_pins']==app.preferences.values['pane_pins'] and len(app.preferences.values['pane_pins'])==1
  result['pin_visible']=any(getattr(button,'pane_id',None)==target for button in app.pinned_tabs.get_children())
  selected_session=app.session
  other_session=app.tmux.ensure_session('second')
  app.sessions.set_active_id(other_session)
  app.refresh()
  result['workspace_switch']=app.session==other_session and len(app.tabs.get_children())==1
  for _ in range(3):
   next(button for button in app.pinned_tabs.get_children() if getattr(button,'pane_id',None)==target).clicked()
   app.refresh()
  result['pin_cross_workspace']=app.session==selected_session and app.tmux.pane(app.session)==target
  result['pin_repeat_no_duplicate']={row[5] for row in app.tmux.panes(app.session)}==identifiers
  app.pin_pane_button.clicked()
  result['unpin']=not app.preferences.values['pane_pins']
  app.pin_pane_button.clicked()
  app.sessions.set_active_id(selected_session)
  app.refresh()
  result['workspace_preserved']=app.session==selected_session and {row[5] for row in app.tmux.panes(app.session)}==identifiers
  app.tmux.command('kill-pane','-t',target)
  app.refresh()
  result['closed_pin_cleanup']=not app.preferences.values['pane_pins'] and not any(getattr(button,'pane_id',None)==target for button in app.pinned_tabs.get_children())
  active_after_close=app.tmux.pane(app.session)
  app.focus_pinned_pane(target)
  result['closed_pin_no_stale_focus']=app.tmux.pane(app.session)==active_after_close
  result['pane_remove']=len(app.tabs.get_children())==before-1 and all(button.pane_id!=target for button in app.tabs.get_children())
  app.tmux.split(app.session)
  app.refresh()
  result['pane_add']=len(app.tabs.get_children())==before
  app.preferences.values['pane_pins']=[{'server':'old-server','pane':app.tmux.pane(app.session)}]
  app.refresh()
  result['old_server_pin_discarded']=not app.preferences.values['pane_pins']
  result['workspace_visible']=app.sessions.get_visible() and app.sessions.get_active_id()==app.session
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
  app.pin_pane_button.clicked()
  app.window.unmaximize()
  app.term.set_size(60,24)
  app.window.set_default_size(760,480)
  app.window.resize(760,480)
 elif step==4:
  print('Narrow geometry:',app.window.get_allocated_width(),app.window.get_preferred_width(),app.footer.get_preferred_width(),app.footer_scroll.get_preferred_width(),flush=True)
  result['narrow_width']=app.window.get_allocated_width() <= 800
  result['narrow_slim']=app.footer.get_allocated_height() <= 52
  result['narrow_one_row']=one_row()
  result['readable_labels']=all(button.get_allocated_width()>=140 for button in app.tabs.get_children())
  result['readable_targets']=all(button.get_allocated_height()>=28 for button in app.tabs.get_children())
  adjustment=app.footer_scroll.get_hadjustment()
  result['narrow_overflow']=adjustment.get_upper()>adjustment.get_page_size()
  app.scroll_footer(app.footer_scroll,SimpleNamespace(direction=Gdk.ScrollDirection.DOWN))
  result['horizontal_scroll']=adjustment.get_value()>0
  adjustment.set_value(0)
  save_screenshot('narrow')
  selected_session=app.session
  pinned_id=app.preferences.values['pane_pins'][0]['pane']
  app.sessions.set_active_id(app.tmux.ensure_session('second'))
  app.refresh()
  next(button for button in app.pinned_tabs.get_children() if getattr(button,'pane_id',None)==pinned_id).clicked()
  app.refresh()
  result['narrow_pin_transition']=app.session==selected_session and app.tmux.pane(app.session)==pinned_id
  app.window.resize(1600,700)
 elif step==5:
  result['wide_width']=app.window.get_allocated_width()>=1500
  result['wide_slim']=app.footer.get_allocated_height()<=52
  result['wide_one_row']=one_row()
  app.footer_scroll.get_hadjustment().set_value(0)
  save_screenshot('wide')
  app.quit();return False
 GLib.timeout_add_seconds(2,check)
 return False

def one_row():
 widgets=[app.sessions,app.pin_pane_button,app.tabs,app.pinned_tabs,app.toolbar,app.footer_left,app.footer_right,app.footer_clock]
 centers=[widget.translate_coordinates(app.footer,0,0)[1]+widget.get_allocated_height()/2 for widget in widgets]
 return max(centers)-min(centers)<=3

def save_screenshot(suffix):
 path=os.environ.get('DROPMUX_TEST_SCREENSHOT')
 if path:
  window=app.window.get_window()
  pixbuf=Gdk.pixbuf_get_from_window(window,0,0,app.window.get_allocated_width(),app.window.get_allocated_height())
  if pixbuf:pixbuf.savev(path.replace('.png','-'+suffix+'.png'),'png',[],[])

GLib.timeout_add_seconds(2,check)
try:
 app.run(['dropmux-gui-check','--show'])
 result['survived']=bool(app.tmux.sessions())
 print(result)
 if not all(result.values()):sys.exit(1)
finally:
 subprocess.run([app.tmux.executable,'-L',app.tmux.socket,'kill-server'],capture_output=True)
 temp.cleanup()
