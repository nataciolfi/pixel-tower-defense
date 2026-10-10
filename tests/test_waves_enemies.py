import unittest
import numpy as np
import _path  # noqa
from pixel_td import enemies as E
from pixel_td.config import MAX_ENT_PER_WAVE
from pixel_td.pathing import Path
from pixel_td.config import PATH_TILES
from pixel_td.waves import make_wave, enemy_count, hp_base, wave_bonus, wave_preview


class Waves(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(0)

    def test_exponential_growth(self):
        for f in (enemy_count, hp_base, wave_bonus):
            self.assertGreater(f(60), f(30) * 2)
            self.assertGreater(f(120), f(60) * 2)

    def test_huge_numbers_supported(self):
        self.assertGreater(hp_base(200), 1e12)             # trillions
        self.assertLess(hp_base(2000), 1e300 * 10)

    def test_enemy_introduction(self):
        names = lambda w: set(wave_preview(w)["names"])
        self.assertEqual(names(1), {"Grunt"})
        self.assertIn("Runner", names(2))
        self.assertIn("Golem", names(20))
        self.assertNotIn("Golem", names(19))

    def test_entity_cap_and_bundling(self):
        s = make_wave(300, self.rng)
        self.assertLessEqual(s.n, MAX_ENT_PER_WAVE + 8)
        self.assertGreater(s.bundle.max(), 100)
        self.assertLess(abs(s.total_real - s.bundle.sum()) / s.total_real, 1e-9)

    def test_boss_waves(self):
        for w, t in ((10, E.OVERLORD), (20, E.TITAN), (30, E.OVERLORD)):
            s = make_wave(w, self.rng)
            self.assertTrue(s.boss)
            self.assertEqual(s.typ[-1], t)
        self.assertFalse(make_wave(11, self.rng).boss)


class Pool(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(1)
        self.path = Path(PATH_TILES)
        self.pool = E.EnemyPool(64, self.path, self.rng)

    def spawn(self, w):
        s = make_wave(w, self.rng)
        self.pool.spawn(s, 0, s.n)
        return s

    def test_move_and_leak(self):
        self.spawn(1)
        self.assertGreater(self.pool.count, 0)
        leaked = 0.0
        for _ in range(60 * 200):
            leaked += self.pool.move(1 / 60)
            if not self.pool.alive.any():
                break
        self.assertGreater(leaked, 0)

    def test_damage_shield_and_reap(self):
        s = self.spawn(1)
        i = self.pool.idx[:1]
        self.pool.shield[i] = 5.0
        self.pool.armor[i] = 0.0
        self.pool.evade[i] = 0.0
        hp0 = self.pool.hp[i].copy()
        self.pool.damage(i, 3.0)
        self.assertEqual(self.pool.hp[i][0], hp0[0])       # fully absorbed by shield
        self.pool.damage(i, 4.0)
        self.assertAlmostEqual(self.pool.hp[i][0], hp0[0] - 2.0)
        self.pool.true_damage(i, 1e9)
        gold, real, xs, ys, ts = self.pool.reap()
        self.assertGreater(gold, 0)
        self.assertGreater(real, 0)

    def test_splitter_spawns_children(self):
        s = make_wave(12, self.rng)
        self.pool.spawn(s, 0, 1)
        i = self.pool.idx[0]
        self.pool.typ[i] = E.SPLITTER
        self.pool.hp[i] = 0.0
        self.pool.reap()
        self.assertEqual(self.pool.count, 2)
        self.assertTrue((self.pool.typ[self.pool.idx] == E.SPLITLING).all())

    def test_slow_resist(self):
        s = make_wave(1, self.rng)
        self.pool.spawn(s, 0, 1)
        i = self.pool.idx
        self.pool.sres[i] = 1.0
        self.pool.apply_slow(i, 0.8, 2.0)
        self.assertEqual(self.pool.slow[i][0], 0.0)


if __name__ == "__main__":
    unittest.main()
