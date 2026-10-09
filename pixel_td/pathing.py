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

    def positions(self, d):
        return np.interp(d, self.cum, self.pts[:, 0]), np.interp(d, self.cum, self.pts[:, 1])

    def distance_to(self, x, y):
        apx, apy = x - self.a[:, 0], y - self.a[:, 1]
        t = np.clip((apx * self.ab[:, 0] + apy * self.ab[:, 1]) / self.ab2, 0.0, 1.0)
        cx = self.a[:, 0] + t * self.ab[:, 0]
        cy = self.a[:, 1] + t * self.ab[:, 1]
        return float(np.min(np.hypot(x - cx, y - cy)))
