"""Save-file handling. JSON, atomic writes, automatic .bak fallback.

Location (Linux): $PIXEL_TD_HOME, else $XDG_DATA_HOME/pixel-td, else ~/.local/share/pixel-td
"""
import json
import os
import shutil
import sys
from .config import APP_ID, SAVE_VERSION


def default_dir():
    env = os.environ.get("PIXEL_TD_HOME")
    if env:
        return env
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_ID)


class SaveStore:
    def __init__(self, directory=None):
        self.dir = directory or default_dir()
        self.path = os.path.join(self.dir, "save.json")
        self.bak = self.path + ".bak"

    @staticmethod
    def _read(p):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError("bad save")
        return d

    def load(self):
        for p in (self.path, self.bak):
            try:
                return self._read(p)
            except (OSError, ValueError):
                continue
        return {}

    def write(self, data):
        data = dict(data, version=SAVE_VERSION)
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(self.path):
                shutil.copy2(self.path, self.bak)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def wipe(self):
        for p in (self.path, self.bak):
            try:
                os.remove(p)
            except OSError:
                pass
