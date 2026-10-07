"""Keep bundled tmux runtime on disk so detached sessions survive AppImage unmount."""
import hashlib, os, pathlib, shutil, tempfile

def prepare(root):
    source=root/'usr/lib/dropmux-tmux'
    digest=hashlib.sha256()
    for p in sorted(source.rglob("*")):
        if p.is_file():
            digest.update(str(p.relative_to(source)).encode());digest.update(p.read_bytes())
    base=pathlib.Path(os.environ.get('XDG_CACHE_HOME',str(pathlib.Path.home()/'.cache')))/'dropmux'
    base.mkdir(parents=True,exist_ok=True,mode=0o700)
    dest=base/('tmux-'+digest.hexdigest()[:16])
    if not dest.exists():
        staging=pathlib.Path(tempfile.mkdtemp(prefix='.tmux-',dir=base))
        try:
            for p in source.iterdir():
                if p.is_dir():shutil.copytree(p,staging/p.name)
                else:shutil.copy2(p,staging/p.name)
            launcher=staging/'launch-tmux'
            launcher.write_text('#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport TERMINFO_DIRS="$HERE/terminfo:/usr/share/terminfo:/lib/terminfo"\nexec "$HERE/ld-linux-x86-64.so.2" --library-path "$HERE" "$HERE/tmux" "$@"\n')
            launcher.chmod(0o700)
            try:staging.rename(dest)
            except FileExistsError:shutil.rmtree(staging)
        except BaseException:
            if staging.exists():shutil.rmtree(staging)
            raise
    return str(dest/'launch-tmux')
