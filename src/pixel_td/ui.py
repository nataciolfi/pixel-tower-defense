"""Immediate-mode HUD. Buttons return True when clicked; clicks are consumed so the map
underneath never sees them."""
import pygame
from .config import *
from .bignum import fmt
from .towers import TOWER_TYPES, MODE_NAMES
from .waves import wave_preview
from .sim import PREP, WAVE, LOST

BG = (34, 30, 50)
BG2 = (48, 42, 70)
EDGE = (14, 12, 22)
TXT = (235, 235, 245)
DIM = (150, 150, 175)
GOLD = (255, 215, 80)
GREEN = (110, 230, 120)
RED = (255, 100, 100)
PURPLE = (200, 150, 255)


class UI:
    def __init__(self, screen, fonts, sprites):
        self.s, self.f, self.sp = screen, fonts, sprites
        self.mouse, self.click = (0, 0), False
        self.modal = False
        self._c = {}
        self._big = {}

    def begin(self, mouse, click):
        self.mouse, self.click = mouse, click

    # ---- primitives ----------------------------------------------------------------
    def text(self, s, pos, size=16, color=TXT, anchor="tl"):
        k = (s, size, color)
        img = self._c.get(k)
        if img is None:
            if len(self._c) > 800:
                self._c.clear()
            img = self._c[k] = self.f[size].render(s, False, color)
        r = img.get_rect()
        setattr(r, {"tl": "topleft", "tr": "topright", "c": "center", "tc": "midtop", "ml": "midleft"}[anchor], pos)
        self.s.blit(img, r)
        return r

    def title(self, s, cy, color=GOLD, scale=2):
        k = (s, color, scale)
        img = self._big.get(k)
        if img is None:
            base = self.f[40].render(s, False, color)
            shadow = self.f[40].render(s, False, (20, 10, 30))
            w, h = base.get_width() * scale, base.get_height() * scale
            img = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
            img.blit(pygame.transform.scale(shadow, (w, h)), (6, 6))
            img.blit(pygame.transform.scale(base, (w, h)), (0, 0))
            self._big[k] = img
        self.s.blit(img, (SCREEN_W // 2 - img.get_width() // 2, cy - img.get_height() // 2))

    def box(self, rect, fill=BG2, edge=EDGE):
        pygame.draw.rect(self.s, edge, rect)
        pygame.draw.rect(self.s, fill, rect.inflate(-4, -4))

    def button(self, rect, label, enabled=True, selected=False, sub=None, modal=False, color=None, size=16):
        blocked = self.modal and not modal
        hover = rect.collidepoint(self.mouse) and not blocked
        base = color or ((90, 80, 140) if selected else (66, 58, 100))
        if not enabled:
            base = (44, 40, 60)
        elif hover:
            base = tuple(min(255, c + 24) for c in base)
        self.box(rect, base)
        pygame.draw.rect(self.s, tuple(min(255, c + 40) for c in base), (rect.x + 2, rect.y + 2, rect.w - 4, 2))
        col = TXT if enabled else (110, 110, 130)
        if sub is None:
            self.text(label, rect.center, size, col, "c")
        else:
            self.text(label, (rect.centerx, rect.y + rect.h // 2 - 9), size, col, "c")
            self.text(sub[0], (rect.centerx, rect.y + rect.h // 2 + 9), 12, sub[1] if enabled else (110, 110, 130), "c")
        if hover and self.click and enabled:
            self.click = False
            return True
        return False

    def hovered(self, rect):
        return rect.collidepoint(self.mouse) and not self.modal

    def dim(self, rect=None, alpha=160):
        r = rect or pygame.Rect(0, 0, SCREEN_W, SCREEN_H)
        shade = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        self.s.blit(shade, (r.x, r.y))

    # ---- HUD ------------------------------------------------------------------------
    def draw(self, g):
        self.modal = g.modal()
        self._top(g)
        self._panel(g)
        self._bottom(g)
        self._overlay(g)

    def _top(self, g):
        sim, s = g.sim, self.s
        pygame.draw.rect(s, BG, (0, 0, MAP_W, TOP_H))
        pygame.draw.rect(s, EDGE, (0, TOP_H - 3, MAP_W, 3))
        s.fill(GOLD, (12, 14, 16, 16)); s.fill((255, 245, 170), (14, 16, 6, 6))
        self.text("GOLD", (36, 6), 12, DIM)
        self.text(fmt(sim.gold), (36, 22), 24, GOLD)
        bx, bw = 230, 250
        self.text("BASE", (bx, 6), 12, DIM)
        s.fill(EDGE, (bx, 22, bw, 22))
        r = max(0.0, min(1.0, sim.base_hp / sim.base_max))
        s.fill((220, 70, 70) if r < .3 else (90, 200, 100), (bx + 3, 25, int((bw - 6) * r), 16))
        self.text(f"{fmt(sim.base_hp)} / {fmt(sim.base_max)}", (bx + bw // 2, 33), 14, (255, 255, 255), "c")
        self.text("WAVE", (510, 6), 12, DIM)
        self.text(str(sim.wave), (510, 22), 24, TXT)
        self.text("ENEMIES LEFT", (600, 6), 12, DIM)
        self.text(fmt(sim.remaining()) if sim.state == WAVE else "-", (600, 22), 24, (255, 170, 120))
        self.text("BEST", (770, 6), 12, DIM)
        self.text(str(sim.meta.best_wave), (770, 22), 24, TXT)
        if self.button(pygame.Rect(MAP_W - 92, 8, 82, 40), "MENU"):
            g.pause_menu = True

    def _panel(self, g):
        sim, s = g.sim, self.s
        pygame.draw.rect(s, BG, (PANEL_X, 0, PANEL_W, SCREEN_H))
        pygame.draw.rect(s, EDGE, (PANEL_X, 0, 4, SCREEN_H))
        self.text("BUILD  (keys 1-9, 0)", (PANEL_X + 14, 10), 14, DIM)
        g.hover_type = None
        for i, tt in enumerate(TOWER_TYPES):
            col, row = i % 2, i // 2
            r = pygame.Rect(PANEL_X + 12 + col * 152, 30 + row * 48, 146, 44)
            locked = not sim.unlocked(i)
            cost = sim.build_cost(i)
            ok = sim.gold >= cost and not locked
            if self.hovered(r):
                g.hover_type = i
            if self.button(r, "", not locked, selected=(g.placing == i)):
                g.placing, g.selected, g.meteor_armed = i, None, False
            s.blit(self.sp.tower[i], (r.x + 2, r.y + 2), (0, 0, 40, 40))
            self.text(tt.name, (r.x + 46, r.y + 6), 14, TXT if not locked else DIM)
            if locked:
                self.text(f"Wave {tt.unlock}", (r.x + 46, r.y + 24), 14, RED)
            else:
                self.text(fmt(cost), (r.x + 46, r.y + 24), 14, GREEN if ok else RED)

        info = pygame.Rect(PANEL_X + 12, 274, 296, 250)
        self.box(info, BG2)
        ix, iy = info.x + 10, info.y + 8
        if g.placing is not None or (g.selected is None and g.hover_type is not None):
            self._type_info(g, g.placing if g.placing is not None else g.hover_type, ix, iy)
        elif g.selected is not None:
            self._selected(g, ix, iy)
        else:
            for n, line in enumerate(["Pick a tower, then click", "anywhere off the road.", "",
                                      "Click a tower to upgrade.", "", "Q: Meteor   W: Time freeze",
                                      "SPACE: next wave  P: pause", "+/-: speed   ESC: menu"]):
                self.text(line, (ix, iy + n * 20), 14, DIM)

        pf = sim.state == PREP
        if self.button(pygame.Rect(PANEL_X + 12, 530, 296, 44),
                       "START WAVE %d" % (sim.wave + 1) if pf else "WAVE %d RUNNING" % sim.wave,
                       enabled=pf, color=(60, 140, 70)):
            sim.start_wave()
        if self.button(pygame.Rect(PANEL_X + 12, 582, 144, 40), "RESUME" if g.paused else "PAUSE", selected=g.paused):
            g.paused = not g.paused
        if self.button(pygame.Rect(PANEL_X + 164, 582, 144, 40), "AUTO: ON" if g.auto else "AUTO: OFF", selected=g.auto):
            g.auto = not g.auto
        for i, sp in enumerate(SPEEDS):
            if self.button(pygame.Rect(PANEL_X + 12 + i * 75, 630, 71, 40), f"x{sp}", selected=(g.speed == i)):
                g.speed = i
        self.text("Autosaves after every wave", (PANEL_X + 160, 692), 12, DIM, "tc")

    def _type_info(self, g, ti, ix, iy):
        sim = g.sim
        tt = TOWER_TYPES[ti]
        self.text(tt.name, (ix, iy), 20, tt.color)
        self.text(tt.desc, (ix, iy + 26), 14, DIM)
        beacon = tt.key == "beacon"
        rows = [("Range" if not beacon else "Aura range", f"{tt.range:.0f}")]
        if not beacon:
            rows = [("Damage", fmt(tt.dmg)), ("Range", f"{tt.range:.0f}"), ("Rate", f"{tt.rate:.2f}/s"),
                    ("Target", MODE_NAMES[tt.mode])]
        rows.append(("Cost", fmt(sim.build_cost(ti))))
        for n, (k, v) in enumerate(rows):
            self.text(k, (ix, iy + 54 + n * 20), 14, DIM)
            self.text(v, (ix + 110, iy + 54 + n * 20), 14, TXT)
        if not sim.unlocked(ti):
            self.text(f"LOCKED: reach wave {tt.unlock}", (ix, iy + 170), 14, RED)
            self.text(f"(best so far: {sim.meta.best_wave})", (ix, iy + 188), 14, DIM)
        elif g.placing is not None:
            self.text("Click map to place anywhere", (ix, iy + 170), 14, GREEN)
            self.text("off the road. Right-click: cancel", (ix, iy + 188), 14, GREEN)

    def _selected(self, g, ix, iy):
        sim, t = g.sim, g.selected
        tt = t.tt
        self.text(f"{tt.name}  Lv {t.level}", (ix, iy), 20, tt.color)
        nxt = type(t)(tt, 0, 0, 0, t.meta)
        nxt.set_level(t.level + 1)
        if tt.key == "beacon":
            n = sum(1 for o in sim.towers if o is not t and o.tt.key != "beacon"
                    and (o.x - t.x) ** 2 + (o.y - t.y) ** 2 <= t.range ** 2)
            rows = [("Aura", f"+{t.aura*100:.0f}%", f"-> +{nxt.aura*100:.0f}%"),
                    ("Range", f"{t.range:.0f}", ""), ("Buffing", f"{n} towers", ""), ("", "", "")]
        else:
            star = "*" if t.buff > 1 else ""
            rows = [("Damage", fmt(t.damage * t.buff) + star, f"-> {fmt(nxt.damage * t.buff)}"),
                    ("Range", f"{t.range:.0f}", ""), ("Rate", f"{t.rate:.2f}/s", ""),
                    ("Effect", t.special_text(), "")]
        for n, (k, v, extra) in enumerate(rows):
            y = iy + 26 + n * 18
            self.text(k, (ix, y), 14, DIM)
            self.text(v, (ix + 76, y), 14, TXT)
            if extra:
                self.text(extra, (ix + 184, y), 14, GREEN)
        if tt.key != "beacon":
            self.text("Target", (ix, iy + 108), 14, DIM)
            if self.button(pygame.Rect(ix + 70, iy + 102, 206, 26), "< %s >" % MODE_NAMES[t.mode]):
                t.mode = (t.mode + 1) % len(MODE_NAMES)
        by = iy + 136
        c1, c10 = t.cost_levels(1), t.cost_levels(10)
        nmax = t.max_levels(sim.gold)
        specs = [("UP x1", c1, 1), ("UP x10", c10, 10),
                 (f"MAX +{nmax}" if nmax else "MAX", t.cost_levels(nmax) if nmax else c1, -1)]
        for k, (lab, cost, n) in enumerate(specs):
            ok = sim.gold >= cost and (n != -1 or nmax > 0)
            if self.button(pygame.Rect(ix + k * 98, by, 92, 44), lab, ok, sub=(fmt(cost), GREEN)):
                sim.upgrade(t, n)
        if self.button(pygame.Rect(ix, by + 52, 276, 28), f"SELL  +{fmt(t.sell_value())}", color=(120, 56, 56)):
            sim.sell(t)
            g.selected = None

    def _bottom(self, g):
        sim, s = g.sim, self.s
        pygame.draw.rect(s, BG, (0, BOTTOM_Y, MAP_W, SCREEN_H - BOTTOM_Y))
        pygame.draw.rect(s, EDGE, (0, BOTTOM_Y, MAP_W, 3))
        for k, (lab, cd, tot, armed, act) in enumerate([
                ("METEOR [Q]", sim.cd_meteor, sim.meteor_total, g.meteor_armed, "m"),
                ("FREEZE [W]", sim.cd_freeze, sim.freeze_total, sim.freeze_t > 0, "f")]):
            r = pygame.Rect(12 + k * 160, BOTTOM_Y + 12, 150, 42)
            ready = cd <= 0
            if self.button(r, lab if ready else f"{cd:.0f}s", ready, selected=armed,
                           color=(150, 80, 30) if act == "m" else (50, 100, 150)):
                g.use_skill(act)
            if not ready:
                s.fill((0, 0, 0), (r.x + 4, r.bottom - 8, int((r.w - 8) * (1 - cd / tot)), 4))
        for n, (txt, col) in enumerate(sim.log[-3:]):
            self.text(txt, (12, BOTTOM_Y + 64 + n * 14), 12, col)
        w = sim.wave + 1
        p = wave_preview(w)
        x = 350
        self.text(f"NEXT: WAVE {w}" + (f"   *** {p['boss_name']} ***" if p["boss"] else ""), (x, BOTTOM_Y + 12), 16,
                  RED if p["boss"] else TXT)
        self.text(f"Enemies: {fmt(p['total'])}   HP each: {fmt(p['hp'])}" + ("  (merged)" if p["bundled"] else ""),
                  (x, BOTTOM_Y + 36), 14, DIM)
        names = ", ".join(p["names"])
        self.text("Types: " + (names if len(names) < 70 else names[:67] + "..."), (x, BOTTOM_Y + 56), 14, DIM)
        gain = g.ascend_gain()
        self.text(f"Kills: {fmt(sim.kills)}   Towers: {len(sim.towers)}   Ascend now: +{gain} AP",
                  (x, BOTTOM_Y + 76), 14, PURPLE if gain else DIM)

    # ---- dialogs ----------------------------------------------------------------------
    def dialog(self, title, color, lines, buttons, w=460):
        """buttons: list of (label, enabled, color) -> returns index clicked or -1."""
        h = 150 + 24 * len(lines) + 56 * len(buttons)
        self.dim(pygame.Rect(MAP_X, MAP_Y, MAP_W, MAP_H))
        box = pygame.Rect(MAP_W // 2 - w // 2, MAP_Y + max(10, (MAP_H - h) // 2), w, h)
        self.box(box, BG)
        cx = box.centerx
        self.text(title, (cx, box.y + 42), 40, color, "c")
        for n, ln in enumerate(lines):
            self.text(ln, (cx, box.y + 92 + n * 24), 14, TXT, "c")
        y = box.y + 112 + 24 * len(lines)
        hit = -1
        for k, (lab, en, col) in enumerate(buttons):
            if self.button(pygame.Rect(cx - 150, y + k * 56, 300, 46), lab, en, modal=True, color=col):
                hit = k
        return hit

    def _overlay(self, g):
        sim = g.sim
        if g.paused and not g.modal():
            self.text("PAUSED", (MAP_W // 2, MAP_Y + 120), 40, (255, 255, 255), "c")
        gain = g.ascend_gain()
        asc = (f"ASCEND  (+{gain} AP)", gain > 0, (110, 70, 170))
        if sim.state == LOST:
            k = self.dialog("DEFEAT", RED, [f"Reached wave {sim.wave}   Kills {fmt(sim.kills)}",
                                            "Ascend to bank permanent bonuses."],
                            [("RESTART RUN", True, (60, 140, 70)), asc, ("MAIN MENU", True, None)])
            if k == 0: g.restart()
            elif k == 1: g.ascend()
            elif k == 2: g.to_menu()
        elif sim.won and not g.win_ack:
            k = self.dialog("VICTORY!", GOLD, [f"Wave {sim.wave} cleared. The numbers only go up...",
                                               "Keep going in endless mode, or Ascend."],
                            [("ENDLESS MODE", True, (60, 140, 70)), asc, ("MAIN MENU", True, None)])
            if k == 0: g.win_ack = True
            elif k == 1: g.ascend()
            elif k == 2: g.to_menu()
        elif g.pause_menu:
            k = self.dialog("PAUSED", TXT, [f"Wave {sim.wave}   Ascend would give +{gain} AP"],
                            [("RESUME", True, (60, 140, 70)), asc, ("SAVE & MAIN MENU", True, None)])
            if k == 0: g.pause_menu = False
            elif k == 1: g.ascend()
            elif k == 2: g.to_menu()
