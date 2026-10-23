import unittest
import _path  # noqa
from pixel_td.sim import Simulation, PREP, WAVE, LOST
from pixel_td.meta import Meta, ascend_gain
import json


def json_roundtrip(d):
    return json.loads(json.dumps(d))

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
        s.meta.legends = {t.key for t in TOWER_TYPES if t.legendary}
        s.gold = 10 ** 15
        s.wave = 30                                              # legends need wave 10-30 of the run
        spots = [(x, y) for y in range(20, 540, 36) for x in range(20, 940, 48)]
        for ti in range(len(TOWER_TYPES)):
            for x, y in spots:
                if s.can_place(x, y) and s.place(ti, x, y):
                    break
        s.wave = 0
        self.assertEqual(len(s.towers), len(TOWER_TYPES))
        for t in s.towers:
            if not t.tt.legendary:
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


class Maps(unittest.TestCase):
    def test_five_maps_with_rising_difficulty(self):
        from pixel_td.maps import MAPS
        self.assertEqual(len(MAPS), 5)
        self.assertEqual(len({m.key for m in MAPS}), 5)
        for a, b in zip(MAPS, MAPS[1:]):
            self.assertLess(a.level, b.level)
            self.assertLessEqual(a.hp_g, b.hp_g)
            self.assertLessEqual(a.leak_mult, b.leak_mult)
            self.assertGreaterEqual(a.regen, b.regen)
            self.assertLess(a.ap_mult, b.ap_mult)
            self.assertGreater(b.start_gold, a.start_gold)

    def test_every_map_is_playable(self):
        from pixel_td.maps import MAPS
        for m in MAPS:
            s = Simulation(seed=1, map_key=m.key)
            free = [(x, y) for x in range(14, 946, 20) for y in range(14, 546, 20) if s.can_place(x, y)]
            self.assertGreater(len(free), 300, m.key)
            self.assertFalse(s.can_place(*[float(v) for v in s.path.pts[1]]))      # corner of the road
            self.assertEqual(s.gold, m.start_gold)
            s.start_wave()
            for _ in range(60 * 90):
                s.step(1 / 60)
                if s.state != WAVE:
                    break

    def test_road_gets_shorter(self):
        from pixel_td.maps import MAPS
        lengths = [Simulation(map_key=m.key).path.total for m in MAPS]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_regen_is_small_and_repair_costs_gold(self):
        s = Simulation(seed=1, map_key="canyon")
        s.start_wave()
        s.base_hp = s.base_max * 0.5
        s.sq_pos = s.spec.n
        s._finish_wave()
        self.assertLess(s.base_hp, s.base_max * 0.6)             # healed only a few %, not 30%
        self.assertEqual(s.state, PREP)
        s.gold = 0
        self.assertFalse(s.can_repair())
        s.gold = 10 ** 9
        hp0 = s.base_hp
        self.assertTrue(s.repair())
        self.assertGreater(s.base_hp, hp0)
        self.assertLess(s.gold, 10 ** 9)

    def test_run_remembers_its_map(self):
        s = Simulation(seed=1, map_key="lava")
        snap = s.snapshot()
        s2 = Simulation(seed=2)
        s2.restore(snap)
        self.assertEqual(s2.map.key, "lava")

    def test_map_best_and_ap_multiplier(self):
        s = Simulation(seed=1, map_key="void")
        s.start_wave()
        self.assertEqual(s.meta.map_best["void"], 1)
        s.wave = 40
        easy = Simulation(seed=1, map_key="meadow"); easy.wave = 40
        self.assertGreater(s.ascend_gain(), easy.ascend_gain() * 4)


class Combat(unittest.TestCase):
    def _pack(self, n=8):
        s = Simulation(seed=3)
        s.start_wave()
        s.spec.times[:] = 0.0
        s.step(1 / 60)
        return s

    def test_area_damage_hits_whole_squads(self):
        from pixel_td.towers import tower_fire
        s = Simulation(seed=3)
        s.gold = 10 ** 6
        t = s.place(1, 100, 120)                                 # cannon between two road lanes
        t.cd = 1e9                                               # we fire it by hand below
        s.start_wave()
        hit = 0
        for _ in range(60 * 60):
            s.step(1 / 60)
            p = s.pool
            i = p.idx
            if i.size == 0:
                continue
            p.hp[i] = p.maxhp[i]                                 # nothing dies during the test
            inr = ((p.x[i] - t.x) ** 2 + (p.y[i] - t.y) ** 2) < t.range ** 2
            if int(inr.sum()) >= 4:                              # a tight squad walks through the range
                before = p.hp[i].copy()
                self.assertTrue(tower_fire(s, t))
                hit = int((p.hp[i] < before).sum())
                break
        self.assertGreaterEqual(hit, 3)                          # one shell hurt at least 3 enemies

    def test_void_hits_percent_of_max_hp_and_bosses_less(self):
        from pixel_td.towers import Tower, BY_KEY, tower_fire, VOID_BOSS
        import numpy as np
        s = Simulation(seed=3)
        s.meta.best_wave = 99
        s.gold = 10 ** 9
        s.wave = 49
        s.start_wave()                                            # wave 50: boss wave
        s.spec.times[:] = 0.0
        s.step(1 / 60)
        t = Tower(BY_KEY["void"], 0, 0, 0, s.meta)
        pool = s.pool
        i = pool.idx[0]
        pool.typ[i] = 0                                           # a normal enemy
        pool.armor[i] = 0.9
        pool.shield[i] = 1e30                                     # shield + armor must not matter
        pool.x[i], pool.y[i] = 20.0, 20.0
        t.x, t.y = 20.0, 20.0
        hp0, mx = pool.hp[i], pool.maxhp[i]
        s.towers.append(t)
        pool.hp[:] = np.where(pool.alive, pool.maxhp, 0)
        for j in pool.idx:
            if j != i:
                pool.x[j] = pool.y[j] = 5000.0
        t.mode = 2
        tower_fire(s, t)
        lost = (hp0 - pool.hp[i]) / mx
        self.assertGreater(lost, t.void_pct * 0.99)               # at least the % part landed
        self.assertGreaterEqual(t.void_pct, 0.03)
        self.assertAlmostEqual(VOID_BOSS, 0.15)

    def test_void_is_strong_from_the_start_and_scales(self):
        from pixel_td.towers import Tower, BY_KEY
        a, b = Tower(BY_KEY["void"], 0, 0, 0), Tower(BY_KEY["void"], 0, 0, 0)
        b.set_level(100)
        self.assertGreaterEqual(a.void_pct, 0.03)                 # 3% of max HP per hit at level 1
        self.assertGreaterEqual(b.void_pct, 0.15)                 # strong well before level 200
        self.assertGreater(b.void_n, a.void_n)


class Prestige(unittest.TestCase):
    def test_ap_accelerates_after_wave_100(self):
        self.assertEqual(ascend_gain(1), 0)
        # up to wave 100 the curve is polynomial; beyond it doubles every 100 waves
        self.assertAlmostEqual(ascend_gain(200) / ascend_gain(100), (2 ** 1.8) * 2, delta=0.1 * ascend_gain(200) / ascend_gain(100))
        self.assertGreater(ascend_gain(500), 250 * ascend_gain(100))      # wave 500 is hugely better than 100
        self.assertGreater(ascend_gain(1000), 50 * ascend_gain(500))
        self.assertGreater(ascend_gain(500), 30000)
        self.assertGreater(ascend_gain(10 ** 5), 10 ** 100)               # still finite and an exact int
        self.assertIsInstance(ascend_gain(10 ** 5), int)
        prev = 0
        for w in range(5, 1200, 7):                                       # strictly non-decreasing
            g = ascend_gain(w)
            self.assertGreaterEqual(g, prev)
            prev = g

    def test_shards_are_small_and_depend_on_depth_and_difficulty(self):
        from pixel_td.meta import shard_gain
        self.assertEqual(shard_gain(19, 5), 0)                            # too shallow
        self.assertEqual(shard_gain(20, 1), 1)
        self.assertLessEqual(shard_gain(100, 1), 3)
        self.assertGreater(shard_gain(500, 1), shard_gain(100, 1))
        self.assertGreater(shard_gain(50, 5), shard_gain(50, 1))          # harder map pays more
        self.assertLessEqual(shard_gain(1000, 5), 15)                     # never a flood

    def test_vault_purchase(self):
        m = Meta()
        self.assertFalse(m.buy_legend("phoenix", 3))                      # no shards yet
        m.shards = 5
        self.assertTrue(m.buy_legend("phoenix", 3))
        self.assertEqual(m.shards, 2)
        self.assertTrue(m.owns_legend("phoenix"))
        self.assertFalse(m.buy_legend("phoenix", 3))                      # can't buy twice
        self.assertEqual(m.shards, 2)
        m2 = Meta.from_dict(json_roundtrip(m.to_dict()))
        self.assertEqual((m2.shards, m2.legends), (2, {"phoenix"}))

    def test_lifetime_bonus_is_sublinear(self):
        m = Meta()
        self.assertEqual(m.lifetime_mult(), 1.0)
        m.total_ap = 100
        a = m.lifetime_mult()
        m.total_ap = 10 ** 6
        b = m.lifetime_mult()
        self.assertGreater(a, 1.4)
        self.assertLess(b, 100)                                           # +1%/AP would have been x10000

    def test_ascend_pays_ap_and_shards(self):
        import tempfile
        s = Simulation(seed=1, map_key="void")
        s.wave = 40
        self.assertEqual(s.shard_gain(), 1 + 0 + 2)                       # level-5 map
        self.assertGreater(s.ascend_gain(), 100)

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



# ================================================================================================
from pixel_td.towers import (CATEGORIES, cat_indices, INDEX, legend_level, legend_xp_for, legend_tick,
                             tower_fire)
from pixel_td.config import SPEEDS
from pixel_td import enemies as E
import numpy as np


def arena(seed=1, n=6):
    """A sim with n enemies spawned and frozen in place so tests can position them by hand."""
    s = Simulation(seed=seed)
    s.meta.best_wave = 99
    s.gold = 10 ** 15
    s.start_wave()
    s.spec.times[:] = 0.0
    s.step(1 / 60)
    p = s.pool
    for j in p.idx:
        p.armor[j] = 0.0
        p.evade[j] = 0.0
        p.shield[j] = 0.0
        p.hp[j] = p.maxhp[j] = 1000.0
        p.speed[j] = 0.0
    return s


def free_tower(s, key, x, y, level=1):
    t = Tower(BY_KEY[key], float(x), float(y), 0, s.meta)
    t.set_level(level)
    t.cd = 1e9                                           # fired by hand in the tests
    s._register(t)
    s.recompute_buffs()
    return t


class Categories(unittest.TestCase):
    def test_every_tower_has_exactly_one_category(self):
        keys = {c[0] for c in CATEGORIES}
        self.assertEqual(len(CATEGORIES), 7)
        for t in TOWER_TYPES:
            self.assertIn(t.cat, keys)
        total = sum(len(cat_indices(c[0])) for c in CATEGORIES)
        self.assertEqual(total, len(TOWER_TYPES))

    def test_counts(self):
        regular = [t for t in TOWER_TYPES if not t.legendary]
        legends = [t for t in TOWER_TYPES if t.legendary]
        self.assertEqual(len(regular), 18)
        self.assertEqual(len(legends), 5)
        self.assertTrue(all(t.cat == "LEG" for t in legends))
        self.assertTrue(all(len(cat_indices(c[0])) <= 6 for c in CATEGORIES))

    def test_original_indices_unchanged(self):
        self.assertEqual([TOWER_TYPES[i].key for i in range(10)],
                         ["archer", "cannon", "frost", "tesla", "sniper", "toxin", "laser", "mortar", "beacon", "void"])


class NewMechanics(unittest.TestCase):
    def test_stun_stops_movement_and_bosses_resist(self):
        s = Simulation(seed=1)
        s.start_wave(); s.spec.times[:] = 0; s.step(1 / 60)
        p = s.pool
        i = p.idx[:1]
        d0 = float(p.dist[i][0])
        p.apply_stun(i, 1.0)
        for _ in range(30):
            p.move(1 / 60)
        self.assertAlmostEqual(float(p.dist[i][0]), d0, places=6)
        p.typ[i] = E.OVERLORD
        p.stun_t[i] = 0.0
        p.apply_stun(i, 1.0)
        self.assertLess(float(p.stun_t[i][0]), 0.3)

    def test_vulnerability_increases_damage(self):
        s = arena()
        p = s.pool
        i = p.idx[:1]
        hp = float(p.hp[i][0])
        p.damage(i, 100.0)
        base = hp - float(p.hp[i][0])
        p.hp[i] = hp
        p.apply_vuln(i, 0.5, 3.0)
        p.damage(i, 100.0)
        self.assertAlmostEqual((hp - float(p.hp[i][0])) / base, 1.5, places=6)

    def test_knockback_pushes_back_less_for_bosses(self):
        s = arena()
        p = s.pool
        a, b = p.idx[:2]
        p.dist[a] = p.dist[b] = 100.0
        p.typ[b] = E.OVERLORD
        p.knockback(np.array([a, b]), 40.0)
        self.assertAlmostEqual(float(p.dist[a]), 60.0)
        self.assertGreater(float(p.dist[b]), 80.0)
        p.knockback(np.array([a]), 1000.0)
        self.assertEqual(float(p.dist[a]), 0.0)                  # never negative

    def test_ballista_pierces_a_line(self):
        s = arena()
        p = s.pool
        t = free_tower(s, "ballista", 100, 100)
        ids = list(p.idx[:6])
        for k, j in enumerate(ids[:5]):                          # five enemies on the firing line
            p.x[j], p.y[j] = 160.0 + 20 * k, 100.0
        p.x[ids[5]], p.y[ids[5]] = 200.0, 160.0                   # one far off the line
        for j in ids:
            p.dist[j] = p.x[j]                                    # "First" = furthest along
        t.mode = 0
        before = p.hp[ids].copy()
        self.assertTrue(tower_fire(s, t))
        hit = int((p.hp[ids] < before).sum())
        self.assertGreaterEqual(hit, 5)
        self.assertEqual(float(p.hp[ids[5]]), float(before[5]))

    def test_executioner_executes_only_below_threshold(self):
        s = arena()
        p = s.pool
        t = free_tower(s, "exec", 100, 100)
        a, b = p.idx[:2]
        p.x[a], p.y[a] = 120.0, 100.0
        p.x[b], p.y[b] = 5000.0, 5000.0
        p.hp[a] = 100.0                                           # 10% < 15%
        t.mode = 3
        tower_fire(s, t)
        self.assertLessEqual(float(p.hp[a]), 0.0)
        p.hp[a] = 900.0
        p.hp[b] = 1000.0
        tower_fire(s, t)
        self.assertGreater(float(p.hp[a]), 0.0)

    def test_mint_gives_global_gold_bonus(self):
        s = Simulation(seed=1)
        s.meta.best_wave = 99
        s.gold = 10 ** 9
        base = s.gold_mult()
        m = s.place(INDEX["mint"], 100, 120)
        self.assertGreater(s.gold_mult(), base)
        b1 = s.mint_bonus
        s.upgrade(m, 20)
        self.assertGreater(s.mint_bonus, b1)
        s.sell(m)
        self.assertEqual(s.mint_bonus, 0.0)

    def test_overclock_speeds_up_nearby_towers_only(self):
        s = Simulation(seed=1)
        s.meta.best_wave = 99
        s.gold = 10 ** 9
        near = s.place(0, 100, 120)
        far = s.place(0, 500, 120)
        s.place(INDEX["overclock"], 160, 120)
        self.assertGreater(near.haste, 1.0)
        self.assertEqual(far.haste, 1.0)

    def test_new_towers_have_unlock_and_art(self):
        from pixel_td.sprite_data import TOWER_ORDER
        self.assertEqual([t.key for t in TOWER_TYPES], TOWER_ORDER)
        self.assertEqual(SPEEDS, sorted(SPEEDS))
        self.assertGreaterEqual(max(SPEEDS), 64)


class Legends(unittest.TestCase):
    def setUp(self):
        self.s = Simulation(seed=1)
        self.s.meta.best_wave = 99
        self.s.meta.legends = {t.key for t in TOWER_TYPES if t.legendary}   # bought in the Vault
        self.s.wave = 30
        self.s.gold = 10 ** 15

    def test_only_one_of_each_per_run(self):
        s = self.s
        ti = INDEX["phoenix"]
        self.assertIsNotNone(s.place(ti, 100, 120))
        self.assertIsNone(s.place(ti, 200, 120))                   # second Phoenix refused
        self.assertIsNotNone(s.place(INDEX["midas"], 300, 120))    # a different legend is fine
        self.assertEqual(sum(1 for t in s.towers if t.tt.key == "phoenix"), 1)

    def test_must_be_bought_in_the_vault_and_reach_its_wave(self):
        s = Simulation(seed=1)
        s.gold = 10 ** 15
        ti = INDEX["phoenix"]
        s.wave = 99
        self.assertEqual(s.legend_state(ti), "vault")             # not owned yet, even at wave 99
        self.assertIsNone(s.place(ti, 100, 120))
        s.meta.legends.add("phoenix")
        s.wave = 3
        self.assertEqual(s.legend_state(ti), "wave")              # owned, run not far enough
        self.assertIsNone(s.place(ti, 100, 120))
        s.wave = BY_KEY["phoenix"].unlock
        self.assertEqual(s.legend_state(ti), "ready")
        self.assertIsNotNone(s.place(ti, 100, 120))
        self.assertEqual(s.legend_state(ti), "built")

    def test_cannot_be_sold_or_bought_up(self):
        s = self.s
        t = s.place(INDEX["reaper"], 100, 120)
        g = s.gold
        self.assertEqual(s.upgrade(t, 5), 0)
        s.sell(t)
        self.assertIn(t, s.towers)
        self.assertEqual(s.gold, g)

    def test_price_is_fixed_in_shards_and_costs_no_gold(self):
        s = self.s
        ti = INDEX["phoenix"]
        for wave in (0, 30, 200, 600):
            s.wave = wave
            self.assertEqual(s.build_cost(ti), 0)                  # never any gold price
        before = s.gold
        s.wave = 30
        s.place(ti, 100, 120)
        self.assertEqual(s.gold, before)
        prices = [BY_KEY[k].cost for k in ("phoenix", "midas", "thunder", "chronos", "reaper")]
        self.assertEqual(prices, sorted(prices))                   # fixed, ascending
        self.assertLessEqual(prices[0], 5)                         # affordable after a few ascensions

    def test_legends_do_not_make_normal_towers_pricier(self):
        s = self.s
        c0 = s.build_cost(0)
        s.place(INDEX["phoenix"], 100, 120)
        self.assertEqual(s.build_cost(0), c0)

    def test_levels_from_xp(self):
        self.assertEqual(legend_level(0), 1)
        self.assertEqual(legend_level(legend_xp_for(10)), 10)
        self.assertEqual(legend_level(legend_xp_for(10) - 1), 9)
        self.assertGreater(legend_level(1e30), 80)
        t = Tower(BY_KEY["phoenix"], 0, 0, 0)
        d1 = t.damage
        self.assertTrue(t.add_xp(legend_xp_for(6)))
        self.assertEqual(t.level, 6)
        self.assertAlmostEqual(t.damage / d1, 1.25 ** 5, places=6)
        self.assertFalse(t.add_xp(0.0))

    def test_kills_credit_xp_to_the_killer(self):
        s = arena()
        t = free_tower(s, "phoenix", 100, 100)
        p = s.pool
        j = p.idx[0]
        p.src[j] = t.uid
        p.hp[j] = 0.0
        g = float(p.gold[j])
        s.step(1 / 60)
        self.assertGreater(t.kills, 0)
        self.assertAlmostEqual(t.xp, g, places=6)
        # a kill credited to nobody gives nobody XP
        t.xp = 0.0
        k = p.idx[0]
        p.src[k] = -1
        p.hp[k] = 0.0
        s.step(1 / 60)
        self.assertEqual(t.xp, 0.0)

    def test_reaper_earns_double_xp(self):
        s = arena()
        r = free_tower(s, "reaper", 100, 100)
        p = s.pool
        j = p.idx[0]
        p.src[j] = r.uid
        p.hp[j] = 0.0
        g = float(p.gold[j])
        s.step(1 / 60)
        self.assertAlmostEqual(r.xp, 2 * g, places=6)

    def test_legend_catches_up_in_one_wave_when_bought_late(self):
        t = Tower(BY_KEY["phoenix"], 0, 0, 0)
        t.add_xp(5e6)                                             # one late wave of kills
        self.assertGreater(t.level, 40)

    def test_midas_pays_bonus_gold_for_kills_in_range(self):
        s = arena()
        m = free_tower(s, "midas", 100, 100)
        p = s.pool
        j = p.idx[0]
        p.x[j], p.y[j] = 110.0, 100.0
        p.hp[j] = 0.0
        p.gold[j] = 1e6
        g = float(p.gold[j])
        before = s.gold
        s.step(1 / 60)
        self.assertAlmostEqual((s.gold - before) / g, 1.0 + m.gold_bonus, places=3)

    def test_thunderlord_smites_the_strongest_anywhere(self):
        s = arena()
        t = free_tower(s, "thunder", 100, 100)
        p = s.pool
        j = p.idx[2]
        p.hp[j] = 5000.0                                          # strongest, far outside any range
        p.x[j], p.y[j] = 900.0, 500.0
        t.timer = 0.0
        before = float(p.hp[j])
        legend_tick(s, t, 1 / 60)
        self.assertLess(float(p.hp[j]), before)

    def test_chronos_slows_and_stops_time(self):
        s = arena()
        t = free_tower(s, "chronos", 100, 100)
        p = s.pool
        j = p.idx[0]
        p.x[j], p.y[j] = 150.0, 100.0
        t.aura_t = 0.0
        t.stop_t = 0.0
        legend_tick(s, t, 1 / 60)
        self.assertGreater(float(p.slow[j]), 0.3)
        self.assertGreater(float(p.stun_t[j]), 0.5)


class AutoUpgrade(unittest.TestCase):
    def setUp(self):
        self.s = Simulation(seed=1)
        self.s.meta.best_wave = 99
        self.s.gold = 10 ** 9
        self.a = self.s.place(0, 100, 120)
        self.b = self.s.place(0, 200, 120)
        self.s.gold = 0

    def test_off_does_nothing(self):
        self.s.gold = 10 ** 9
        self.s.auto_upgrade()
        self.assertEqual((self.a.level, self.b.level), (1, 1))

    def test_priority_only_mode(self):
        s = self.s
        s.auto_mode = 1
        self.a.prio = 1
        s.gold = 10 ** 6
        s.auto_upgrade()
        self.assertGreater(self.a.level, 5)
        self.assertEqual(self.b.level, 1)                         # not flagged -> untouched

    def test_all_mode_feeds_priority_first_then_the_rest(self):
        s = self.s
        s.auto_mode = 2
        self.b.prio = 1
        s.gold = self.b.cost_levels(4) + 5                        # exactly enough for 4 levels of b
        s.auto_upgrade()
        self.assertEqual(self.b.level, 5)                         # all the gold went to the priority tower
        self.assertEqual(self.a.level, 1)
        s.gold = 10 ** 9
        s.auto_upgrade()
        self.assertGreater(self.a.level, 1)                       # then everything else

    def test_rank_one_beats_rank_two(self):
        s = self.s
        s.auto_mode = 1
        self.a.prio = 2
        self.b.prio = 1
        s.gold = self.b.cost_levels(3) + 5
        s.auto_upgrade()
        self.assertEqual(self.b.level, 4)
        self.assertEqual(self.a.level, 1)

    def test_runs_automatically_while_the_sim_steps(self):
        s = self.s
        s.auto_mode = 2
        s.gold = 10 ** 6
        for _ in range(30):
            s.step(1 / 60)
        self.assertGreater(self.a.level + self.b.level, 2)

    def test_state_is_saved(self):
        s = self.s
        s.auto_mode = 2
        self.a.prio = 3
        s.gold = 10 ** 9
        s.meta.legends.add("phoenix")
        s.wave = 12
        s.place(INDEX["phoenix"], 300, 120)
        s.wave = 0
        leg = [t for t in s.towers if t.tt.legendary][0]
        leg.add_xp(1234.0)
        import json
        snap = json.loads(json.dumps(s.snapshot()))
        s2 = Simulation(seed=2)
        s2.restore(snap)
        self.assertEqual(s2.auto_mode, 2)
        self.assertEqual([t.prio for t in s2.towers if t.tt.key == "archer"], [3, 0])
        leg2 = [t for t in s2.towers if t.tt.legendary][0]
        self.assertAlmostEqual(leg2.xp, 1234.0)
        self.assertEqual(leg2.level, legend_level(1234.0))
        self.assertEqual(len({t.uid for t in s2.towers}), len(s2.towers))


if __name__ == "__main__":
    unittest.main()
