"""Non-gameplay screens: main menu, Ascension (prestige) shop and the help page."""
import random
import pygame
from . import __version__
from .config import *
from .bignum import fmt
from .meta import UPGRADES
from .ui import TXT, DIM, GOLD, GREEN, RED, PURPLE, BG, BG2, DIFF_COLORS
from .maps import MAPS
from .towers import TOWER_TYPES, INDEX


class Screen:
    def __init__(self, g):
        self.g = g

    def update(self, dt):
        pass


class Menu(Screen):
    def __init__(self, g):
        super().__init__(g)
        rnd = random.Random(3)
        total = g.sim.path.total
        self.march = [(rnd.uniform(0, total), rnd.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11])) for _ in range(14)]
        self.t = 0.0
        self.confirm = False
        self.shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.shade.fill((10, 8, 20, 165))

    def update(self, dt):
        self.t += dt

    def draw(self):
        g, ui, s = self.g, self.g.ui, self.g.screen
        s.fill((20, 18, 30))
        ox, oy = (SCREEN_W - MAP_W) // 2, 70
        s.blit(g.sprites.maps[g.sim.map.key], (ox, oy))
        path, total = g.sim.path, g.sim.path.total
        for d0, ty in self.march:
            d = (d0 + self.t * (60 + 25 * (ty % 3))) % total
            x, y = path.positions(d)
            spr = g.sprites.enemy[ty][0]
            s.blit(spr, (ox + int(x) - spr.get_width() // 2, oy + int(y) - spr.get_height() // 2))
        s.blit(self.shade, (0, 0))
        ui.title("PIXEL TOWER", 92)
        ui.title("DEFENSE", 176, (255, 240, 200))
        ui.text("Infinite waves.  Absurd numbers.", (SCREEN_W // 2, 238), 16, DIM, "c")

        ui.modal = self.confirm
        x, y0, w, h, gap = SCREEN_W // 2 - 160, 276, 320, 46, 10
        run = g.run_data
        cont = f"CONTINUE  (wave {run['wave']})" if run else "CONTINUE"
        items = [(cont, run is not None, (60, 140, 70)), ("NEW GAME", True, None),
                 (f"ASCENSION  ({fmt(g.meta.ap)} AP | {fmt(g.meta.shards)} SH)", True, (110, 70, 170)), ("HOW TO PLAY", True, None),
                 ("FULLSCREEN: ON" if g.fullscreen else "FULLSCREEN: OFF", True, None), ("QUIT", True, (120, 56, 56))]
        for k, (lab, en, col) in enumerate(items):
            if ui.button(pygame.Rect(x, y0 + k * (h + gap), w, h), lab, en, color=col):
                self._click(k)
        m = g.meta
        ui.text(f"v{__version__}    Best wave {m.best_wave}    Ascensions {m.ascensions}    "
                f"Lifetime kills {fmt(m.lifetime_kills)}", (SCREEN_W // 2, SCREEN_H - 40), 14, DIM, "c")
        ui.text(f"Save: {g.store.path}", (SCREEN_W // 2, SCREEN_H - 20), 12, (100, 100, 125), "c")

        if self.confirm:
            ui.dim()
            box = pygame.Rect(SCREEN_W // 2 - 230, 250, 460, 210)
            ui.box(box, BG)
            ui.text("Start a new game?", (box.centerx, box.y + 40), 24, TXT, "c")
            ui.text("Your current run will be lost.", (box.centerx, box.y + 78), 14, DIM, "c")
            ui.text("Ascension progress is kept.", (box.centerx, box.y + 98), 14, DIM, "c")
            if ui.button(pygame.Rect(box.x + 30, box.y + 140, 190, 46), "YES, NEW GAME", modal=True, color=(60, 140, 70)):
                self.confirm = False
                g.scene = "maps"
            if ui.button(pygame.Rect(box.x + 240, box.y + 140, 190, 46), "CANCEL", modal=True):
                self.confirm = False

    def _click(self, k):
        g = self.g
        if k == 0:
            g.continue_run()
        elif k == 1:
            if g.run_data:
                self.confirm = True
            else:
                g.scene = "maps"
        elif k == 2:
            g.open_meta()
        elif k == 3:
            g.scene = "help"
        elif k == 4:
            g.set_fullscreen(not g.fullscreen)
        else:
            g.quit()


class MapSelect(Screen):
    """Choose one of the five maps (= difficulties) for a new run."""

    def draw(self):
        g, ui, s, m = self.g, self.g.ui, self.g.screen, self.g.meta
        ui.modal = False
        s.fill((24, 20, 38))
        ui.text("SELECT MAP", (SCREEN_W // 2, 40), 40, GOLD, "c")
        ui.text("Each map is a difficulty. Harder maps pay more Ascension Points.", (SCREEN_W // 2, 78), 14, DIM, "c")
        cw, gap = 228, 12
        x0 = (SCREEN_W - (5 * cw + 4 * gap)) // 2
        for i, mp in enumerate(MAPS):
            r = pygame.Rect(x0 + i * (cw + gap), 104, cw, 500)
            ui.box(r, BG2)
            col = DIFF_COLORS[mp.level - 1]
            s.blit(g.sprites.previews[mp.key], (r.x + 6, r.y + 6))
            ui.text(mp.name, (r.centerx, r.y + 150), 16, TXT, "c")
            ui.text(mp.difficulty, (r.centerx, r.y + 176), 20, col, "c")
            for k in range(5):
                s.fill(col if k < mp.level else (60, 56, 80), (r.centerx - 45 + k * 20, r.y + 198, 14, 14))
            for n, ln in enumerate(ui.wrap(mp.desc, cw - 20, 12)[:3]):
                ui.text(ln, (r.x + 10, r.y + 224 + n * 15), 12, (205, 205, 225))
            tiles = int(round(g.map_paths[mp.key] / 40))
            rows = [("Road", f"{tiles} tiles"),
                    ("Enemy HP", f"+{(mp.hp_g - 1) * 100:.1f}%/wave"),
                    ("Enemy count", f"+{(mp.count_g - 1) * 100:.1f}%/wave"),
                    ("Base damage", f"x{mp.leak_mult:g}"),
                    ("Base regen", f"{mp.regen * 100:g}%/wave"),
                    ("Start gold", f"{mp.start_gold}"),
                    ("AP bonus", f"x{mp.ap_mult:g}")]
            for n, (k, v) in enumerate(rows):
                ui.text(k, (r.x + 10, r.y + 278 + n * 18), 12, DIM)
                ui.text(v, (r.right - 10, r.y + 278 + n * 18), 12, TXT, "tr")
            best = m.map_best.get(mp.key, 0)
            ui.text(f"Your best: wave {best}" if best else "Not played yet", (r.centerx, r.y + 418), 14,
                    GOLD if best else DIM, "c")
            if ui.button(pygame.Rect(r.x + 14, r.y + 444, cw - 28, 44), "PLAY", color=(60, 140, 70)):
                g.new_run(mp.key)
        if ui.button(pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H - 62, 300, 46), "BACK"):
            g.scene = "menu"


class MetaScreen(Screen):
    """Ascension: permanent upgrades (AP) and the Legendary Vault (Legend Shards)."""

    def draw(self):
        g, ui, s, m = self.g, self.g.ui, self.g.screen, self.g.meta
        ui.modal = False
        s.fill((24, 20, 38))
        ui.text("ASCENSION", (60, 24), 40, PURPLE)
        ui.text(f"{fmt(m.ap)} AP", (SCREEN_W - 60, 20), 24, GOLD, "tr")
        ui.shard_icon(SCREEN_W - 60 - 24 - 12 * 2, 56, 2)
        ui.text(f"{fmt(m.shards)} Shards", (SCREEN_W - 60, 52), 24, (140, 235, 255), "tr")
        ui.text(f"Lifetime AP {fmt(m.total_ap)}  =  x{m.lifetime_mult():.2f} damage (permanent, +5% x sqrt(AP))",
                (60, 74), 14, DIM)
        if g.banner:
            ui.text(g.banner, (60, 92), 14, GREEN)
        # tabs
        for k, name in enumerate(("UPGRADES  (AP)", "LEGENDARY VAULT  (Shards)")):
            if ui.button(pygame.Rect(60 + k * 262, 114, 256, 32), name, selected=(g.meta_tab == k),
                         color=(110, 80, 20) if k == 1 and g.meta_tab != 1 else None, size=14):
                g.meta_tab = k
        if g.meta_tab == 0:
            self._upgrades(g, ui, m)
        else:
            self._vault(g, ui, s, m)
        back = "START NEW RUN" if g.banner else "BACK"
        if ui.button(pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H - 62, 300, 46), back, color=(60, 140, 70)):
            g.close_meta()

    def _upgrades(self, g, ui, m):
        for k, u in enumerate(UPGRADES):
            r = pygame.Rect(60, 156 + k * 66, SCREEN_W - 120, 60)
            ui.box(r, BG2)
            lv = m.lv(u.key)
            ui.text(u.name, (r.x + 16, r.y + 8), 20, TXT)
            ui.text(u.desc, (r.x + 16, r.y + 36), 14, DIM)
            ui.text(f"Lv {lv}" + (f" / {u.max_level}" if u.max_level else ""), (r.x + 470, r.y + 20), 16, TXT)
            if m.at_max(u.key):
                ui.text(f"{m.effect_text(u.key)}  (MAX)", (r.x + 590, r.y + 20), 16, GOLD)
            else:
                ui.text(f"{m.effect_text(u.key)} -> {m.effect_text(u.key, lv + 1)}", (r.x + 590, r.y + 20), 16, GREEN)
                ui.text(f"{fmt(m.cost(u.key))} AP", (r.x + 800, r.y + 20), 16, PURPLE)
                if ui.button(pygame.Rect(r.right - 190, r.y + 8, 84, 44), "BUY", m.can_buy(u.key)):
                    m.buy(u.key)
                    g.save()
                if ui.button(pygame.Rect(r.right - 98, r.y + 8, 84, 44), "MAX", m.can_buy(u.key)):
                    m.buy_max(u.key)
                    g.save()

    def _vault(self, g, ui, s, m):
        ui.text("Legendary towers are bought ONCE with Legend Shards (fixed prices) and then stay yours forever.",
                (60, 158), 14, TXT)
        ui.text("Shards are earned in small amounts every time you Ascend (from wave 20). In a run you may build ONE of "
                "each, for free, once the run reaches its wave.", (60, 176), 12, DIM)
        for k, key in enumerate(("phoenix", "midas", "thunder", "chronos", "reaper")):
            ti = INDEX[key]
            tt = TOWER_TYPES[ti]
            r = pygame.Rect(60, 200 + k * 78, SCREEN_W - 120, 72)
            ui.box(r, (60, 48, 30) if m.owns_legend(key) else BG2)
            s.blit(g.sprites.tower[ti], (r.x + 12, r.y + 16))
            ui.text(tt.name, (r.x + 68, r.y + 8), 20, tt.color)
            ui.text(f"Available from wave {tt.unlock} of a run", (r.x + 68, r.y + 34), 12, DIM)
            for n, ln in enumerate(ui.wrap(tt.long, 560, 12)[:3]):
                ui.text(ln, (r.x + 330, r.y + 8 + n * 15), 12, (205, 205, 225))
            if m.owns_legend(key):
                ui.text("OWNED", (r.right - 90, r.y + 26), 20, GOLD, "c")
            else:
                ui.shard_icon(r.right - 232, r.y + 28, 2)
                ui.text(f"{tt.cost}", (r.right - 214, r.y + 24), 20, (140, 235, 255))
                if ui.button(pygame.Rect(r.right - 150, r.y + 14, 130, 44), "BUY", m.can_buy_legend(key, tt.cost),
                             color=(120, 90, 20)):
                    m.buy_legend(key, tt.cost)
                    g.save()


class HelpScreen(Screen):
    LINES = [
        ("GOAL", "Defend the castle from endless, exponentially growing waves. Numbers use K, M, B, T, Qa ... and beyond."),
        ("BUILD", "Pick a category tab (keys 1-7), then a tower (Z X C V), and click ANYWHERE that is not on the road."),
        ("UPGRADE", "Click a tower: UP x1 / x10 / MAX. Every 10 levels a tower gets a big damage bonus."),
        ("AUTO UP", "Spends your gold on upgrades for you (G cycles OFF / PRIORITY / ALL). PRIORITY #1-#3 on a tower feeds it first."),
        ("TARGETING", "Cycle First / Last / Strongest / Weakest / Closest per tower."),
        ("TOWERS", "18 towers in 6 categories: marksman, artillery, elemental, control, support and special."),
        ("LEGENDS", "5 legendary towers, ONE of each per run: bought once in the Vault (Menu > Ascension) with Legend Shards,"),
        ("", "then free to place from a set wave of each run. They can't be sold and level up from the enemies they kill (XP)."),
        ("VOID", "Each hit removes a % of the target's MAX HP (ignores armor, shields, dodge). Bosses take 15%."),
        ("MAPS", "Five maps = five difficulties (shorter road, faster growth, less healing). Harder maps pay more AP."),
        ("BASE", "Leaks hurt: each enemy removes a % of the base. It barely heals - use REPAIR between waves."),
        ("ENEMIES", "Shamans heal, Splitters split, Aegis wear shields, Golems ignore slows, Wraiths dodge. Bosses every 10 waves."),
        ("SPEED", "x1 to x64 (+/-). Above x4 visual effects switch off. Combine with AUTO WAVE for long runs."),
        ("SKILLS", "Q: Meteor (click to aim, % max HP damage).   W: Time freeze."),
        ("ASCEND", "Reset your run for AP (grows faster and faster after wave 100) and a few Shards. AP buy upgrades, Shards buy legends."),
        ("SAVING", "Autosaves after every wave and when you leave. Quitting mid-wave resumes at that wave's start."),
    ]

    def draw(self):
        g, ui, s = self.g, self.g.ui, self.g.screen
        ui.modal = False
        s.fill((24, 20, 38))
        ui.text("HOW TO PLAY", (60, 28), 40, GOLD)
        y = 100
        for head, body in self.LINES:
            if head:
                ui.text(head, (60, y), 16, PURPLE)
            ui.text(body, (200, y), 14, TXT)
            y += 28
        if ui.button(pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H - 62, 300, 46), "BACK"):
            g.scene = "menu"
