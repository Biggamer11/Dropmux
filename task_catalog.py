"""Read local Codex task metadata without modifying Codex state."""
import json
import os
from pathlib import Path
import sqlite3

def load_tasks(snapshot_path, database=None):
    try:
        snapshot = json.loads(Path(snapshot_path).read_text())
    except (OSError, ValueError):
        snapshot = []
    mappings = {task['id']: task['session'] for task in snapshot}
    database = Path(database) if database else Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))/'state_5.sqlite'
    if not database.exists():
        return snapshot
    try:
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=0.2) as connection:
            rows = connection.execute("SELECT id, COALESCE(NULLIF(name, ''), title), cwd FROM threads WHERE archived=0 AND source IN ('vscode','cli','app') AND agent_role IS NULL ORDER BY is_pinned DESC, created_at DESC").fetchall()
        return [{'id': identifier, 'title': title or 'Untitled task', 'cwd': cwd,
                 'session': mappings.get(identifier, 'task-'+identifier.replace('-', ''))}
                for identifier, title, cwd in rows if Path(cwd).is_dir()]
    except (sqlite3.Error, OSError):
        return snapshot
