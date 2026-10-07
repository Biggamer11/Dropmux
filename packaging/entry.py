import os, sys, pathlib, runpy
root=pathlib.Path(os.environ['APPDIR'])
# PYTHONHOME was needed only at interpreter startup, not in spawned host commands.
os.environ.pop('PYTHONHOME',None)
os.environ.pop('PYTHONNOUSERSITE',None)
child_env=dict(os.environ)
for key in ['APPDIR','APPIMAGE','ARGV0']:
    child_env.pop(key,None)
os.environ['GI_TYPELIB_PATH']=str(root/'usr/lib/girepository-1.0')
os.environ['GSETTINGS_SCHEMA_DIR']=str(root/'usr/share/glib-2.0/schemas')
os.environ['XDG_DATA_DIRS']=str(root/'usr/share')+':'+os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share')
os.environ['GTK_THEME']='Adwaita'
# GTK3 software rendering avoids loading host OpenGL driver libraries.
os.environ['GDK_GL']='disable'
os.environ.pop('GTK_PATH',None)
os.environ.pop('GTK_MODULES',None)
app=root/'usr/share/dropmux'
sys.path.insert(0,str(app))
# External writable fallback; never write into the mounted AppImage.
import backend
backend.CHILD_ENV=child_env
from tmux_runtime import prepare
backend.DEFAULT_EXECUTABLE=prepare(root)
# Rewrite image decoder paths for the current mount point.
import tempfile
cache=tempfile.NamedTemporaryFile(prefix='dropmux-pixbuf-',mode='w',delete=False)
cache.write((root/'usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache').read_text().replace('/usr/lib/',str(root/'usr/lib')+'/'))
cache.close()
import atexit
atexit.register(lambda: os.unlink(cache.name))
os.environ['GDK_PIXBUF_MODULE_FILE']=cache.name
imcache=tempfile.NamedTemporaryFile(prefix='dropmux-im-',mode='w',delete=False)
imcache.write((root/'usr/lib/gtk-3.0/3.0.0/immodules.cache').read_text().replace('/usr/lib/',str(root/'usr/lib')+'/'))
imcache.close()
atexit.register(lambda: os.unlink(imcache.name))
os.environ['GTK_IM_MODULE_FILE']=imcache.name
os.environ['GIO_MODULE_DIR']=str(root/'usr/lib/gio/modules')
import dropmux
os.environ.setdefault('DROPMUX_TASKS_FILE', str(pathlib.Path(os.environ.get('XDG_CONFIG_HOME', str(pathlib.Path.home()/'.config')))/'dropmux/tasks.json'))
# Supply catalog location through an environment override implemented in packaged source.
if sys.argv[1:]==['--version']:
    import json
    print('Dropmux AppImage slim-row-3 dev-'+json.loads((app/'build-manifest.json').read_text())['source_commit'][:7]);sys.exit(0)
if sys.argv[1:]==['--self-test']:
    import json,sqlite3,gi,subprocess,unittest
    from gi.repository import Gtk,Vte
    import test_backend
    ok=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(test_backend)).wasSuccessful()
    print(json.dumps({'python':sys.version.split()[0],'gtk':Gtk.get_major_version(),'vte':Vte.get_minor_version(),'sqlite':sqlite3.sqlite_version,'bundled_tmux':subprocess.check_output([backend.DEFAULT_EXECUTABLE,'-V'],text=True).strip(),'pythonhome_leaks': 'PYTHONHOME' in os.environ}))
    external={line.split()[-1] for line in pathlib.Path('/proc/self/maps').read_text().splitlines() if '.so' in line.split()[-1] and '/etc/' not in line.split()[-1] and line.split()[-1].startswith('/') and not line.split()[-1].startswith(str(root))}
    print('UI libraries loaded outside bundle:', sorted(external))
    sys.exit(0 if ok and not external else 1)
if sys.argv[1:]==['--integration-test']:
    sys.argv=[str(app/'test_integration.py')];runpy.run_path(sys.argv[0],run_name='__main__')
elif sys.argv[1:]==['--gui-test']:
    # Never read real Codex metadata during smoke testing.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['CODEX_HOME']=tmp
        runpy.run_path(str(app/'gui_check.py'),run_name='__main__')
else:
    sys.argv=[str(app/'dropmux.py'),*sys.argv[1:]]
    runpy.run_path(sys.argv[0],run_name='__main__')
