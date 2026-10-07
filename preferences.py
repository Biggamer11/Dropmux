"""Validated, atomically saved local display preferences."""
import json
import os
from pathlib import Path

DEFAULTS = {'width': 1100, 'height': 500, 'pinned': True, 'font': 'Monospace 11', 'bar_color': '#00d700', 'show_bar': True, 'bar_texture': 'brushed'}

class Preferences:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'dropmux'/'settings.json'
        self.values = dict(DEFAULTS)
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict):
                return
            for key, low, high in [('width', 640, 7680), ('height', 250, 4320)]:
                value = data.get(key)
                if type(value) is int:
                    self.values[key] = min(high, max(low, value))
            if type(data.get('show_bar')) is bool:
                self.values['show_bar'] = data['show_bar']
            if data.get('bar_texture') in ('none', 'brushed', 'diagonal', 'grid', 'marble'):
                self.values['bar_texture'] = data['bar_texture']
            color = data.get('bar_color')
            if isinstance(color, str) and len(color) == 7 and color.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in color[1:]):
                self.values['bar_color'] = color
            if type(data.get('pinned')) is bool:
                self.values['pinned'] = data['pinned']
            if isinstance(data.get('font'), str) and 0 < len(data['font']) <= 100:
                self.values['font'] = data['font']
        except (OSError, ValueError):
            pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.values, indent=2)+'\n')
        temporary.replace(self.path)
