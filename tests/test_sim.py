import unittest
import _path  # noqa
from pixel_td.sim import Simulation, PREP, WAVE, LOST
from pixel_td.meta import Meta, ascend_gain
from pixel_td.towers import TOWER_TYPES, Tower, BY_KEY
from pixel_td.config import START_GOLD


def run_wave(sim, limit=60 * 600):
    sim.start_wave()
    n = 0
    while sim.state == WAVE and n < limit:
        sim.step(1 / 60)
        n += 1


class Placement(unittest.TestCase):
    def test_free_placement_rules(self):
        s = Simulation(seed=1)
        self.assertFalse(s.can_place(100, 60))            # on the road (row 1)
        self.assertTrue(s.can_place(100, 120))            # between roads
        self.assertFalse(s.can_place(-5, 120))            # off-map
        t = s.place(0, 100, 120)
        self.assertIsNotNone(t)
        self.assertFalse(s.can_place(110, 120))           # overlaps the first tower
        self.assertTrue(s.can_place(160, 120))

    def test_gold_and_costs(self):
        s = Simulation(seed=1)
        c0 = s.build_cost(0)
        s.place(0, 100, 120)
        self.assertGreater(s.build_cost(0), c0)           # cost rises with tower count
        self.assertEqual(s.gold, START_GOLD - c0)

    def test_locked_towers(self):
        s = Simulation(seed=1)
        s.gold = 10 ** 9
        self.assertIsNone(s.place(9, 100, 120))           # Void is locked at best wave 0
        s.meta.best_wave = 30
        self.assertIsNotNone(s.place(9, 100, 120))

    def test_upgrade_sell(self):
        s = Simulation(seed=1)
        s.gold = 10 ** 6
        t = s.place(0, 100, 120)
        g0 = s.gold
        self.assertEqual(s.upgrade(t, 3), 3)
        self.assertEqual(t.level, 4)
        self.assertLess(s.gold, g0)
        n = s.upgrade(t, -1)
        self.assertGreater(n, 0)
        self.assertLess(s.gold, t.cost_levels(1))
        before = s.gold
        s.sell(t)
        self.assertGreater(s.gold, before)
        self.assertEqual(s.towers, [])

    def test_beacon_buff(self):
        s = Simulation(seed=1)
        s.meta.best_wave = 99
        s.gold = 10 ** 6
        a = s.place(0, 100, 120)
        self.assertEqual(a.buff, 1.0)
        b = s.place(8, 160, 120)
        self.assertGreater(a.buff, 1.0)
        s.sell(b)
        self.assertEqual(a.buff, 1.0)


class Gameplay(unittest.TestCase):
    def test_wave_one_cleared_by_archers(self):
        s = Simulation(seed=3)
        for x in (100, 160, 220):
            s.place(0, x, 120)
        run_wave(s)
        self.assertEqual(s.state, PREP)
        self.assertEqual(s.waves_cleared, 1)
        self.assertGreater(s.gold, 0)

    def test_defeat(self):
        s = Simulation(seed=3)
        for _ in range(60):                               # no towers: leaks eventually win
            run_wave(s)
            if s.state == LOST:
                break
        self.assertEqual(s.state, LOST)

    def test_every_tower_type_fires(self):
        s = Simulation(seed=5)
        s.meta.best_wave = 99
        s.gold = 10 ** 12
        for ti in range(len(TOWER_TYPES)):
            s.place(ti, 100 + 60 * ti, 120)
        for t in s.towers:
            s.upgrade(t, 10)
        for _ in range(25):
            run_wave(s)
            if s.state == LOST:
                break
        self.assertGreater(s.kills, 0)

    def test_skills(self):
        s = Simulation(seed=2)
        self.assertTrue(s.cast_freeze())
        self.assertFalse(s.cast_freeze())
        self.assertTrue(s.cast_meteor(200, 60))
        self.assertGreater(s.cd_meteor, 0)

    def test_numbers_get_absurd(self):
        s = Simulation(seed=2)
        s.wave = 250
        s.start_wave()
        self.assertGreater(s.spec.hp.max(), 1e12)
        self.assertGreater(s.base_max, 1e9)


class SaveRestore(unittest.TestCase):
    def test_roundtrip(self):
        s = Simulation(seed=1)
        s.gold = 10 ** 400                                # beyond float range: Python int
        s.place(0, 100, 120)
        s.towers[0].set_level(33)
        s.wave = 7
        gold = s.gold
        snap = s.snapshot()
        import json
        snap = json.loads(json.dumps(snap))
        s2 = Simulation(seed=9)
        s2.restore(snap)
        self.assertEqual(s2.wave, 7)
        self.assertEqual(s2.gold, gold)
        self.assertGreater(s2.gold, 10 ** 399)
        self.assertEqual(s2.towers[0].level, 33)

    def test_midwave_saves_checkpoint(self):
        s = Simulation(seed=1)
        s.place(0, 100, 120)
        s.start_wave()
        s.step(1 / 60)
        snap = s.save_snapshot()
        self.assertEqual(snap["wave"], 0)                 # resumes before the running wave


class Prestige(unittest.TestCase):
    def test_gain_curve(self):
        self.assertEqual(ascend_gain(1), 0)
        self.assertGreaterEqual(ascend_gain(10), 1)
        self.assertGreater(ascend_gain(100), ascend_gain(50) * 2)

    def test_shop_and_effects(self):
        m = Meta()
        m.ap = 100
        d0 = m.dmg_mult()
        self.assertTrue(m.buy("dmg"))
        self.assertGreater(m.dmg_mult(), d0)
        n = m.buy_max("disc")
        self.assertLessEqual(m.lv("disc"), 20)
        self.assertGreaterEqual(m.build_mult(), 0.6)
        m2 = Meta.from_dict(m.to_dict())
        self.assertEqual(m2.levels, m.levels)
        self.assertEqual(m2.ap, m.ap)

    def test_meta_applies_to_sim(self):
        m = Meta()
        m.levels["start"] = 3
        m.levels["dmg"] = 5
        s = Simulation(seed=1, meta=m)
        self.assertGreater(s.gold, START_GOLD)
        t = Tower(BY_KEY["archer"], 0, 0, 0, m)
        base = Tower(BY_KEY["archer"], 0, 0, 0, None)
        self.assertGreater(t.damage, base.damage)

    def test_corrupt_meta_is_safe(self):
        self.assertEqual(Meta.from_dict(None).ap, 0)
        self.assertEqual(Meta.from_dict({"levels": {"nope": 5, "dmg": -3}}).lv("dmg"), 0)


if __name__ == "__main__":
    unittest.main()
