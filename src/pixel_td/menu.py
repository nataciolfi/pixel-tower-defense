"""Non-gameplay screens: main menu, Ascension (prestige) shop and the help page."""
import random
import pygame
from . import __version__
from .config import *
from .bignum import fmt
from .meta import UPGRADES, ascend_gain
from .ui import TXT, DIM, GOLD, GREEN, RED, PURPLE, BG, BG2


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
        s.blit(g.sprites.map, (ox, oy))
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
                 (f"ASCENSION  ({fmt(g.meta.ap)} AP)", True, (110, 70, 170)), ("HOW TO PLAY", True, None),
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
                g.new_run()
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
                g.new_run()
        elif k == 2:
            g.open_meta()
        elif k == 3:
            g.scene = "help"
        elif k == 4:
            g.set_fullscreen(not g.fullscreen)
        else:
            g.quit()


class MetaScreen(Screen):
    def draw(self):
        g, ui, s, m = self.g, self.g.ui, self.g.screen, self.g.meta
        ui.modal = False
        s.fill((24, 20, 38))
        ui.text("ASCENSION", (60, 28), 40, PURPLE)
        ui.text(f"{fmt(m.ap)} AP", (SCREEN_W - 60, 24), 40, GOLD, "tr")
        ui.text(f"Lifetime AP {fmt(m.total_ap)}  =  +{m.total_ap}% damage (permanent)",
                (SCREEN_W - 60, 72), 14, DIM, "tr")
        if g.banner:
            ui.text(g.banner, (60, 82), 16, GREEN)
        else:
            ui.text("Ascend from the in-game menu to turn your best wave into permanent power.", (60, 82), 14, DIM)
        for k, u in enumerate(UPGRADES):
            r = pygame.Rect(60, 118 + k * 72, SCREEN_W - 120, 64)
            ui.box(r, BG2)
            lv = m.lv(u.key)
            ui.text(u.name, (r.x + 16, r.y + 8), 20, TXT)
            ui.text(u.desc, (r.x + 16, r.y + 38), 14, DIM)
            ui.text(f"Lv {lv}" + (f" / {u.max_level}" if u.max_level else ""), (r.x + 470, r.y + 22), 16, TXT)
            if m.at_max(u.key):
                ui.text(f"{m.effect_text(u.key)}  (MAX)", (r.x + 590, r.y + 22), 16, GOLD)
            else:
                ui.text(f"{m.effect_text(u.key)} -> {m.effect_text(u.key, lv + 1)}", (r.x + 590, r.y + 22), 16, GREEN)
                ui.text(f"{fmt(m.cost(u.key))} AP", (r.x + 800, r.y + 22), 16, PURPLE)
                if ui.button(pygame.Rect(r.right - 190, r.y + 10, 84, 44), "BUY", m.can_buy(u.key)):
                    m.buy(u.key)
                    g.save()
                if ui.button(pygame.Rect(r.right - 98, r.y + 10, 84, 44), "MAX", m.can_buy(u.key)):
                    m.buy_max(u.key)
                    g.save()
        back = "START NEW RUN" if g.banner else "BACK"
        if ui.button(pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H - 62, 300, 46), back, color=(60, 140, 70)):
            g.close_meta()


class HelpScreen(Screen):
    LINES = [
        ("GOAL", "Defend the castle from endless, exponentially growing waves. Numbers use K, M, B, T, Qa ... and beyond."),
        ("BUILD", "Pick a tower (keys 1-9, 0) and click ANYWHERE that is not on the road. Towers need a little space."),
        ("UPGRADE", "Click a tower. UP x1 / x10 / MAX. Every 10 levels a tower gets a big damage bonus."),
        ("TARGETING", "Cycle First / Last / Strongest / Weakest / Closest per tower."),
        ("TOWERS", "Archer crits, Cannon & Mortar splash, Frost slows, Tesla chains, Sniper pierces armor,"),
        ("", "Toxin poisons, Laser ramps up, Beacon buffs neighbours, Void hits % of max HP."),
        ("ENEMIES", "Shamans heal, Splitters split, Aegis wear shields, Golems ignore slows, Wraiths dodge. Bosses every 10 waves."),
        ("SKILLS", "Q: Meteor (click to aim, % max HP damage).   W: Time freeze."),
        ("KEYS", "SPACE next wave   P pause   +/- speed   U upgrade   ESC menu   Right-click cancel"),
        ("ASCEND", "Reset your run for Ascension Points (AP). Spend AP on permanent upgrades. Every AP also gives +1% damage."),
        ("UNLOCKS", "Better towers unlock when your best wave (across all runs) reaches their requirement."),
        ("SAVING", "The game autosaves after every wave and when you leave. Quitting mid-wave resumes at that wave's start."),
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
            y += 34
        if ui.button(pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H - 62, 300, 46), "BACK"):
            g.scene = "menu"
