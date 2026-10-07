#!/usr/bin/env python3
"""Build a local-runtime AppDir. No downloads or system changes."""
import os, pathlib, shutil, subprocess, sys, re, json
root=pathlib.Path(__file__).resolve().parents[1]
out=pathlib.Path(sys.argv[1]).resolve()
if out.exists(): raise SystemExit('Refusing to overwrite existing AppDir')
lib=out/'usr/lib'; lib.mkdir(parents=True)
inputs=set()
def copy(src,dst):
    src=pathlib.Path(src); dst=pathlib.Path(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    else: shutil.copy2(src,dst)
    inputs.add(str(src))
version=f'python{sys.version_info.major}.{sys.version_info.minor}'
stdlib=pathlib.Path('/usr/lib')/version
shutil.copytree(stdlib,lib/version,ignore=shutil.ignore_patterns('site-packages','__pycache__','*.pyc','test','tests','tkinter','idlelib','ensurepip'))
for name in ['gi','cairo']:
    copy(stdlib/'site-packages'/name,lib/version/'site-packages'/name)
copy(sys.executable,out/'usr/bin/python3')
for name in ['dropmux.py','backend.py','preferences.py','task_catalog.py','assets','test_backend.py','test_integration.py','gui_check.py']:
    copy(root/name,out/'usr/share/dropmux'/name)
# Ask GI for exact namespace dependency closure and shared libraries.
import gi
gi.require_version('GIRepository','3.0')
from gi.repository import GIRepository
repo=GIRepository.Repository.new(); namespaces=set()
def namespace(name,ver):
    if name in namespaces:return
    repo.require(name,ver,0); namespaces.add(name)
    for dep in repo.get_dependencies(name) or []:
        n,v=dep.rsplit('-',1);namespace(n,v)
namespace('Gtk','3.0');namespace('Vte','2.91');namespace('PangoCairo','1.0')
seeds=[]
for name in namespaces:
    copy(repo.get_typelib_path(name),lib/'girepository-1.0'/pathlib.Path(repo.get_typelib_path(name)).name)
    for raw in set(re.findall(rb'lib[A-Za-z0-9_+.-]+\.so(?:\.[0-9]+)*', pathlib.Path(repo.get_typelib_path(name)).read_bytes())):
        so=raw.decode()
        if so:seeds.append(pathlib.Path('/usr/lib')/so)
# Pixbuf image decoders, including SVG, and GTK input methods.
for rel in ['gdk-pixbuf-2.0/2.10.0/loaders','gtk-3.0/3.0.0/immodules']:
    copy(pathlib.Path('/usr/lib')/rel,lib/rel)
    seeds.extend((lib/rel).glob('*.so'))
seeds += [out/'usr/bin/python3']+list((lib/version).rglob('*.so'))
seen=set()
def dependencies(path):
    path=pathlib.Path(path)
    key=str(path.resolve())
    if key in seen:return
    seen.add(key)
    if not str(path).startswith(str(out)):copy(path,lib/path.name)
    result=subprocess.run(['ldd',str(path)],capture_output=True,text=True)
    if 'not found' in result.stdout:raise RuntimeError(result.stdout)
    for dep in re.findall(r'(?:=>\s+|^\s*)(/\S+)',result.stdout,re.M):dependencies(dep)
for seed in seeds:dependencies(seed)
for rel in ['glib-2.0/schemas','icons/Adwaita','icons/hicolor','themes/Default','themes/Emacs']:
    src=pathlib.Path('/usr/share')/rel
    if src.exists():copy(src,out/'usr/share'/rel)
copy('/etc/fonts',out/'usr/etc/fonts')
# A separate persistent tmux runtime avoids depending on the AppImage mount.
copy('/usr/bin/tmux',out/'usr/lib/dropmux-tmux/tmux')
copy('/usr/share/terminfo',out/'usr/lib/dropmux-tmux/terminfo')
tmux_ldd=subprocess.check_output(['ldd','/usr/bin/tmux'],text=True)
for dep in re.findall(r'(?:=>\s+|^\s*)(/\S+)',tmux_ldd,re.M):
    copy(dep,out/'usr/lib/dropmux-tmux'/pathlib.Path(dep).name)
copy('/usr/lib/gtk-3.0/3.0.0/immodules.cache',lib/'gtk-3.0/3.0.0/immodules.cache')
copy('/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache',lib/'gdk-pixbuf-2.0/2.10.0/loaders.cache')
copy(root/'packaging/tmux-runtime.py',out/'usr/share/dropmux/tmux_runtime.py')
# Retain available dependency license notices and package provenance.
packages=set()
for path in inputs | {str(stdlib/'os.py')}:
    p=subprocess.run(['pacman','-Qqo',path],capture_output=True,text=True)
    packages.update(p.stdout.splitlines())
for pkg in packages:
    src=pathlib.Path('/usr/share/licenses')/pkg
    if src.exists():copy(src,out/'usr/share/licenses'/pkg)
copy('/usr/share/licenses/spdx',out/'usr/share/licenses/spdx')
manifest={'packaging_revision':'slim-row-3', 'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
          'packages':subprocess.check_output(['pacman','-Q',*sorted(packages)],text=True).splitlines(),
          'host_requirements':['x86-64-v3 CPU','Linux kernel >= 6.1','graphical Linux desktop','host shell and fonts'],
          'note':'Local CachyOS runtime snapshot; cross-distribution compatibility not yet verified.'}
(out/'usr/share/dropmux/build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
copy(root/'packaging/AppRun',out/'AppRun');(out/'AppRun').chmod(0o755)
copy(root/'packaging/entry.py',out/'usr/share/dropmux/entry.py')
(out/'dropmux.desktop').write_text('[Desktop Entry]\nType=Application\nName=Dropmux\nExec=AppRun --show\nIcon=dropmux\nCategories=System;TerminalEmulator;\nTerminal=false\n')
(out/'dropmux.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect width="256" height="256" rx="40" fill="#152128"/><path d="M52 74l48 42-48 42M124 170h80" fill="none" stroke="#00d778" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/></svg>')
print(f'Built {out}; {len(seen)} runtime libraries/extensions')
