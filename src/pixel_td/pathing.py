import numpy as np
from .config import TILE


class Path:
    """Polyline path with vectorised position lookup and distance queries."""

    def __init__(self, tiles):
        pts = np.array([(tx * TILE + TILE / 2, ty * TILE + TILE / 2) for tx, ty in tiles], float)
        self.pts = pts
        self.a, self.b = pts[:-1], pts[1:]
        self.ab = self.b - self.a
        self.ab2 = (self.ab ** 2).sum(1)
        self.seg_len = np.sqrt(self.ab2)
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg_len)])
        self.total = float(self.cum[-1])
        self.start = (float(pts[0, 0]), float(pts[0, 1]))
        d = self.ab / self.seg_len[:, None]
        self.nx, self.ny = -d[:, 1], d[:, 0]          # unit normals (for lateral offsets)

    def positions(self, d, lat=None):
        """Points at path distance d. `lat` shifts each point sideways (thick crowds)."""
        x, y = np.interp(d, self.cum, self.pts[:, 0]), np.interp(d, self.cum, self.pts[:, 1])
        if lat is not None:
            seg = np.clip(np.searchsorted(self.cum, d, side="right") - 1, 0, len(self.nx) - 1)
            x = x + self.nx[seg] * lat
            y = y + self.ny[seg] * lat
        return x, y

    def distance_to(self, x, y):
        apx, apy = x - self.a[:, 0], y - self.a[:, 1]
        t = np.clip((apx * self.ab[:, 0] + apy * self.ab[:, 1]) / self.ab2, 0.0, 1.0)
        cx = self.a[:, 0] + t * self.ab[:, 0]
        cy = self.a[:, 1] + t * self.ab[:, 1]
        return float(np.min(np.hypot(x - cx, y - cy)))
