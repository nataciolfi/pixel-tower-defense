"""Immediate-mode HUD. Buttons return True when clicked; clicks are consumed so the map
underneath never sees them."""
import pygame
from .config import *
from .bignum import fmt
from .towers import TOWER_TYPES, MODE_NAMES, CATEGORIES, cat_indices
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
DIFF_COLORS = [(110, 230, 120), (230, 220, 110), (255, 170, 80), (255, 100, 100), (200, 120, 255)]


class UI:
    def __init__(self, screen, fonts, sprites):
        self.s, self.f, self.sp = screen, fonts, sprites
        self.mouse, self.click = (0, 0), False
        self.modal = False
        self._c = {}
        self._big = {}
        self._wrap = {}

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

    def wrap(self, text, width, size):
        key = (text, width, size)
        out = self._wrap.get(key)
        if out is None:
            f, lines, cur = self.f[size], [], ""
            for w in text.split():
                t = (cur + " " + w).strip()
                if f.size(t)[0] <= width:
                    cur = t
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            out = self._wrap[key] = lines
        return out

    def shard_icon(self, x, y, px=2):
        """Tiny pixel diamond = Legend Shard (premium currency)."""
        rows = [(2, 2), (1, 4), (0, 6), (1, 4), (2, 2)]
        for j, (off, w) in enumerate(rows):
            self.s.fill((120, 230, 255), (x + off * px, y + j * px, w * px, px))
        self.s.fill((235, 252, 255), (x + 2 * px, y + px, px, px))

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
        self.text("WAVE", (500, 6), 12, DIM)
        self.text(str(sim.wave), (500, 22), 24, TXT)
        self.text("ENEMIES LEFT", (570, 6), 12, DIM)
        self.text(fmt(sim.remaining()) if sim.state == WAVE else "-", (570, 22), 24, (255, 170, 120))
        self.text("BEST", (700, 6), 12, DIM)
        self.text(str(sim.meta.map_best.get(sim.map.key, 0)), (700, 22), 24, TXT)
        self.text(sim.map.difficulty, (762, 6), 12, DIFF_COLORS[sim.map.level - 1])
        self.text(sim.map.name, (762, 24), 14, TXT)
        if self.button(pygame.Rect(MAP_W - 80, 8, 72, 40), "MENU"):
            g.pause_menu = True

    AUTO_NAMES = ["OFF", "PRIORITY", "ALL"]
    AUTO_HINTS = ["Auto-upgrade is OFF",
                  "Auto-upgrading PRIORITY towers only",
                  "Auto-upgrading priority first, then all"]
    PRIO_COLORS = {1: (255, 90, 90), 2: (255, 160, 60), 3: (255, 225, 80)}

    def _panel(self, g):
        sim, s = g.sim, self.s
        pygame.draw.rect(s, BG, (PANEL_X, 0, PANEL_W, SCREEN_H))
        pygame.draw.rect(s, EDGE, (PANEL_X, 0, 4, SCREEN_H))
        # ---- category tabs ----------------------------------------------------------------
        x = PANEL_X + 12
        for ci, (ck, short, full, blurb) in enumerate(CATEGORIES):
            w = int(len(short) * 7.4) + 10
            col = (120, 90, 30) if ck == "LEG" else None
            if self.button(pygame.Rect(x, 6, w, 22), short, selected=(g.cat == ci), size=12, color=col if g.cat != ci else (200, 150, 40)):
                g.cat = ci
            x += w + 2
        ck, short, full, blurb = CATEGORIES[g.cat]
        for n, ln in enumerate(self.wrap(f"{full}: {blurb}", 276, 12)[:2]):
            self.text(ln, (PANEL_X + 14, 33 + n * 14), 12, DIM)
        # ---- tower grid -------------------------------------------------------------------
        g.hover_type = None
        for n, i in enumerate(cat_indices(ck)):
            tt = TOWER_TYPES[i]
            col, row = n % 2, n // 2
            r = pygame.Rect(PANEL_X + 12 + col * 152, 64 + row * 48, 146, 44)
            locked = not sim.unlocked(i)
            owned = tt.legendary and sim.has_legend(tt.key)
            cost = sim.build_cost(i)
            ok = sim.gold >= cost and not locked and not owned
            if self.hovered(r):
                g.hover_type = i
            tint = (110, 80, 20) if tt.legendary and not locked else None
            if self.button(r, "", not locked and not owned, selected=(g.placing == i), color=tint):
                g.placing, g.selected, g.meteor_armed = i, None, False
            s.blit(self.sp.tower[i], (r.x + 2, r.y + 2), (0, 0, 40, 40))
            self.text(tt.name, (r.x + 46, r.y + 6), 14, TXT if not locked else DIM)
            if tt.legendary:
                label, lc = {"vault": ("VAULT", RED), "wave": (f"Wave {tt.unlock}", RED),
                             "built": ("BUILT", GOLD), "ready": ("READY", GREEN)}[sim.legend_state(i)]
                self.text(label, (r.x + 46, r.y + 24), 14, lc)
            elif locked:
                self.text(f"Wave {tt.unlock}", (r.x + 46, r.y + 24), 14, RED)
            else:
                self.text(fmt(cost), (r.x + 46, r.y + 24), 14, GREEN if ok else RED)

        info = pygame.Rect(PANEL_X + 12, 216, 296, 308)
        self.box(info, BG2)
        ix, iy = info.x + 10, info.y + 8
        if g.placing is not None or (g.selected is None and g.hover_type is not None):
            self._type_info(g, g.placing if g.placing is not None else g.hover_type, ix, iy)
        elif g.selected is not None:
            self._selected(g, ix, iy)
        else:
            for n, line in enumerate(["Pick a category tab, then a", "tower, then click anywhere off", "the road to build it.", "",
                                      "Click a tower to upgrade it.", "AUTO UP spends gold for you;", "give towers PRIORITY to feed",
                                      "them first.", "", "Q: Meteor  W: Freeze  G: auto-up",
                                      "1-7: tabs  Z X C V: pick tower", "SPACE: wave  P: pause  +/-: speed"]):
                self.text(line, (ix, iy + n * 19), 14, DIM)

        # ---- controls ---------------------------------------------------------------------
        pf = sim.state == PREP
        if self.button(pygame.Rect(PANEL_X + 12, 530, 296, 40),
                       "START WAVE %d" % (sim.wave + 1) if pf else "WAVE %d RUNNING" % sim.wave,
                       enabled=pf, color=(60, 140, 70)):
            sim.start_wave()
        if self.button(pygame.Rect(PANEL_X + 12, 574, 96, 42), "RESUME" if g.paused else "PAUSE", selected=g.paused):
            g.paused = not g.paused
        if self.button(pygame.Rect(PANEL_X + 112, 574, 96, 42), "AUTO WAVE", selected=g.auto,
                       sub=("ON" if g.auto else "OFF", GREEN if g.auto else DIM)):
            g.auto = not g.auto
        if self.button(pygame.Rect(PANEL_X + 212, 574, 96, 42), "AUTO UP", selected=sim.auto_mode > 0,
                       sub=(self.AUTO_NAMES[sim.auto_mode], GREEN if sim.auto_mode else DIM)):
            sim.auto_mode = (sim.auto_mode + 1) % 3
        self.text(self.AUTO_HINTS[sim.auto_mode], (PANEL_X + 160, 620), 12, DIM, "tc")
        for i, sp in enumerate(SPEEDS):
            if self.button(pygame.Rect(PANEL_X + 12 + i * 42, 638, 40, 34), f"x{sp}", selected=(g.speed == i), size=14):
                g.set_speed(i)
        want = SPEEDS[g.speed]
        if want > 1 and g.eff_speed < 0.85 * want and not g.paused:
            self.text(f"Running at ~x{g.eff_speed:.0f} (CPU limit)", (PANEL_X + 160, 678), 12, (255, 190, 110), "tc")
        else:
            self.text("Autosaves after every wave", (PANEL_X + 160, 678), 12, DIM, "tc")
        if want > FX_MAX_SPEED_INDEX and SPEEDS.index(want) > FX_MAX_SPEED_INDEX:
            self.text("Effects off at this speed", (PANEL_X + 160, 696), 12, (130, 130, 160), "tc")

    def _type_info(self, g, ti, ix, iy):
        sim = g.sim
        tt = TOWER_TYPES[ti]
        self.text(tt.name + ("  [LEGENDARY]" if tt.legendary else ""), (ix, iy), 20, tt.color)
        if tt.cost and tt.range and not tt.legendary and tt.rate <= 0:
            rows = [("Aura range", f"{tt.range:.0f}")] if tt.key != "mint" else [("Range", "global")]
        elif tt.rate <= 0:
            rows = [("Range", "global" if tt.key == "mint" else f"{tt.range:.0f}")]
        else:
            rows = [("Damage", fmt(tt.dmg)), ("Range", f"{tt.range:.0f}"), ("Rate", f"{tt.rate:.2f}/s"),
                    ("Target", MODE_NAMES[tt.mode])]
        rows.append(("Cost", f"{tt.cost} Shards" if tt.legendary else fmt(sim.build_cost(ti))))
        for n, (k, v) in enumerate(rows):
            self.text(k, (ix, iy + 26 + n * 18), 14, DIM)
            self.text(v, (ix + 110, iy + 26 + n * 18), 14, TXT)
        for n, line in enumerate(self.wrap(tt.long or tt.desc, 276, 12)[:8]):
            self.text(line, (ix, iy + 126 + n * 15), 12, (205, 205, 225))
        if tt.legendary:
            st = sim.legend_state(ti)
            self.text(f"Vault price: {tt.cost} Shards (one time, fixed)", (ix, iy + 244), 12, GOLD)
            msg = {"vault": "Not owned: buy it in Menu > Ascension > Vault.",
                   "wave": f"Owned. Available from wave {tt.unlock} of a run.",
                   "built": "Already built in this run.",
                   "ready": "Ready: placing it costs no gold."}[st]
            self.text(msg, (ix, iy + 259), 12, RED if st in ("vault", "wave") else GREEN)
            self.text("ONE per run. Levels up from kills. Can't be sold.", (ix, iy + 274), 12, GOLD)
        elif not sim.unlocked(ti):
            self.text(f"LOCKED: reach wave {tt.unlock} (best {sim.meta.best_wave})", (ix, iy + 282), 12, RED)
        if g.placing is not None and sim.unlocked(ti) and not (tt.legendary and sim.has_legend(tt.key)):
            self.text("Click to place, right-click cancels", (ix, iy + 289 if tt.legendary else iy + 282), 12, GREEN)

    def _selected(self, g, ix, iy):
        sim, t = g.sim, g.selected
        tt = t.tt
        self.text(f"{tt.name}  Lv {t.level}", (ix, iy), 20, tt.color)
        nxt = type(t)(tt, 0, 0, 0, t.meta)
        nxt.set_level(t.level + 1)
        if tt.key in ("beacon", "overclock"):
            n = sum(1 for o in sim.towers if o is not t and o.rate > 0
                    and (o.x - t.x) ** 2 + (o.y - t.y) ** 2 <= t.range ** 2)
            val = t.aura if tt.key == "beacon" else t.haste_aura
            nv = nxt.aura if tt.key == "beacon" else nxt.haste_aura
            what = "Dmg aura" if tt.key == "beacon" else "Speed aura"
            rows = [(what, f"+{val*100:.0f}%", f"-> +{nv*100:.0f}%"),
                    ("Range", f"{t.range:.0f}", ""), ("Buffing", f"{n} towers", "")]
        elif tt.key == "mint":
            rows = [("Gold bonus", f"+{t.mint_aura*100:.0f}%", f"-> +{nxt.mint_aura*100:.0f}%"),
                    ("Total Mints", f"+{sim.mint_bonus*100:.0f}% gold", "")]
        else:
            star = "*" if t.buff > 1 else ""
            rows = [("Damage", fmt(t.damage * t.buff) + star, "" if tt.legendary else f"-> {fmt(nxt.damage * t.buff)}"),
                    ("Range", f"{t.range:.0f}", ""),
                    ("Rate", f"{t.rate * t.haste:.2f}/s", ""),
                    ("Effect", t.special_text(), "")]
            rows += [(k, v, "") for k, v in t.detail_lines()]
        rows.append(("Kills", fmt(t.kills), ""))
        for n, (k, v, extra) in enumerate(rows[:7]):
            y = iy + 24 + n * 17
            self.text(k, (ix, y), 14, DIM)
            self.text(v, (ix + 84, y), 14, TXT)
            if extra:
                self.text(extra, (ix + 192, y), 14, GREEN)
        if t.rate > 0:
            self.text("Target", (ix, iy + 152), 14, DIM)
            if self.button(pygame.Rect(ix + 70, iy + 146, 206, 24), "< %s >" % MODE_NAMES[t.mode]):
                t.mode = (t.mode + 1) % len(MODE_NAMES)
        if tt.legendary:
            from .towers import legend_xp_for
            self.text("SOULS (XP)", (ix, iy + 180), 14, GOLD)
            bar = pygame.Rect(ix, iy + 200, 276, 16)
            self.box(bar, (30, 26, 44))
            self.s.fill((255, 200, 60), (bar.x + 3, bar.y + 3, int((bar.w - 6) * t.xp_progress()), bar.h - 6))
            self.text(f"{fmt(t.xp)} / {fmt(legend_xp_for(t.level + 1))}", (bar.centerx, bar.centery), 12, (255, 255, 255), "c")
            for n, ln in enumerate(self.wrap("Gains XP from the gold value of enemies it kills. Levels up on its own "
                                             "and grows stronger every level. Cannot be sold or bought up.", 276, 12)[:5]):
                self.text(ln, (ix, iy + 224 + n * 15), 12, (205, 205, 225))
            return
        # priority (auto-upgrade order)
        pr = t.prio
        if self.button(pygame.Rect(ix, iy + 176, 276, 24), "PRIORITY: " + ("none" if not pr else f"#{pr}"),
                       selected=pr > 0, size=14, color=self.PRIO_COLORS.get(pr)):
            t.prio = (pr + 1) % 4
        by = iy + 204
        c1, c10 = t.cost_levels(1), t.cost_levels(10)
        nmax = t.max_levels(sim.gold)
        specs = [("UP x1", c1, 1), ("UP x10", c10, 10),
                 (f"MAX +{nmax}" if nmax else "MAX", t.cost_levels(nmax) if nmax else c1, -1)]
        for k, (lab, cost, n) in enumerate(specs):
            ok = sim.gold >= cost and (n != -1 or nmax > 0)
            if self.button(pygame.Rect(ix + k * 98, by, 92, 42), lab, ok, sub=(fmt(cost), GREEN)):
                sim.upgrade(t, n)
        if self.button(pygame.Rect(ix, by + 48, 276, 26), f"SELL  +{fmt(t.sell_value())}", color=(120, 56, 56)):
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
            self.text(txt, (12, BOTTOM_Y + 60 + n * 12), 12, col)
        rr = pygame.Rect(332, BOTTOM_Y + 12, 190, 42)
        price = sim.repair_price()
        full = sim.base_hp >= sim.base_max
        if self.button(rr, "BASE FULL" if full else "REPAIR +25%", sim.can_repair(), color=(40, 110, 80),
                       sub=None if full else (fmt(price) if sim.state == PREP else "between waves",
                                              GREEN if sim.gold >= price else RED)):
            sim.repair()
        w = sim.wave + 1
        p = wave_preview(w, sim.map)
        x = 540
        self.text(f"NEXT: WAVE {w}" + (f"  *** {p['boss_name']} ***" if p["boss"] else ""), (x, BOTTOM_Y + 10), 16,
                  RED if p["boss"] else TXT)
        self.text(f"Enemies {fmt(p['total'])}   HP each {fmt(p['hp'])}" + (" (merged)" if p["bundled"] else ""),
                  (x, BOTTOM_Y + 32), 14, DIM)
        if p["boss"]:
            self.text(f"Boss HP {fmt(p['boss_hp'])}", (x, BOTTOM_Y + 50), 14, (255, 150, 150))
        else:
            names = ", ".join(p["names"])
            self.text("Types: " + (names if len(names) < 38 else names[:35] + "..."), (x, BOTTOM_Y + 50), 14, DIM)
        gain, sg = g.ascend_gain(), sim.shard_gain()
        self.text(f"Kills {fmt(sim.kills)}  Towers {len(sim.towers)}  Ascend +{fmt(gain)} AP" + (f" +{sg} SH" if sg else ""),
                  (x, BOTTOM_Y + 70), 14, PURPLE if gain else DIM)
        self.text(f"Repair heals 25% of base HP. After each wave it only regens {sim.map.regen*100:.1f}%.",
                  (12, BOTTOM_Y + 94), 12, (130, 130, 160))

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
        gain, sg = g.ascend_gain(), sim.shard_gain()
        asc = (f"ASCEND  (+{fmt(gain)} AP" + (f", +{sg} SH)" if sg else ")"), gain > 0, (110, 70, 170))
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
            k = self.dialog("PAUSED", TXT, [f"Wave {sim.wave}   Ascend would give +{fmt(gain)} AP" + (f" and +{sg} Shards" if sg else "")],
                            [("RESUME", True, (60, 140, 70)), asc, ("SAVE & MAIN MENU", True, None)])
            if k == 0: g.pause_menu = False
            elif k == 1: g.ascend()
            elif k == 2: g.to_menu()
