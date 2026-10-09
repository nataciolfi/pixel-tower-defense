"""ASCII pixel-art definitions (pure data, no pygame)."""

ENEMY_ART = {
    "grunt": ["..oooo..",
              ".obbbbo.",
              "obebbebo",
              "obbbbbbo",
              ".obbbbo.",
              ".obddbo.",
              ".oo..oo.",
              ".oo..oo."],
    "runner": ["...oooo.",
               "..obbbeo",
               "..obbbbo",
               ".oobbbo.",
               "oblbbbo.",
               ".o.obbo.",
               "..o..oo.",
               ".oo..o.."],
    "brute": [".oooooo.",
              "obbbbbbo",
              "oebbbbeo",
              "obbbbbbo",
              "obdbbdbo",
              "obbbbbbo",
              ".oddddo.",
              ".oo..oo."],
    "knight": ["..oooo..",
               ".oggggo.",
               "oggeeggo",
               "oggggggo",
               "orbbbbro",
               "orbbbbro",
               ".obbbbo.",
               ".oo..oo."],
    "wraith": ["..oooo..",
               ".obbbbo.",
               "obebbebo",
               "obbbbbbo",
               "obbbbbbo",
               "obbbbbbo",
               "obobbobo",
               ".o.oo.o."],
    "boss": ["o..........o",
             "oo.oooooo.oo",
             ".oobbbbbboo.",
             ".obbbbbbbbo.",
             "obbeebbeebbo",
             "obbeebbeebbo",
             "obbbbbbbbbbo",
             "obbwwwwwwbbo",
             ".obbbbbbbbo.",
             ".oddbbbbddo.",
             ".oo.dddd.oo.",
             ".oo......oo."],
}

_O = (20, 16, 28)
ENEMY_PAL = {
    "grunt":  {"o": _O, "b": (96, 176, 72), "d": (60, 120, 50), "e": (255, 240, 120)},
    "runner": {"o": _O, "b": (230, 170, 60), "d": (170, 110, 40), "l": (255, 210, 110), "e": (255, 255, 255)},
    "brute":  {"o": _O, "b": (170, 90, 70), "d": (120, 60, 50), "e": (255, 230, 120)},
    "knight": {"o": _O, "b": (90, 100, 130), "g": (160, 170, 190), "r": (190, 60, 60), "e": (255, 220, 80)},
    "wraith": {"o": _O, "b": (150, 100, 220), "d": (100, 60, 170), "e": (255, 255, 255)},
    "boss":   {"o": (30, 10, 20), "b": (200, 50, 60), "d": (140, 30, 45), "e": (255, 230, 60),
               "w": (240, 240, 240)},
}
ENEMY_ORDER = ["grunt", "runner", "brute", "knight", "wraith", "boss"]

_BASE = [".oSSSSSSo.",
         ".osssssso.",
         ".osssssso.",
         ".oSSSSSSo.",
         "..oooooo.."]

TOWER_TOPS = {
    "archer": ["....oo....",
               "...occo...",
               "..occcco..",
               ".occwwcco.",
               ".occcccco."],
    "cannon": ["..oooooo..",
               ".oCCCCCCo.",
               "oCCwwCCCCo",
               "oCCCCCCCCo",
               ".oCCCCCCo."],
    "frost": ["....oo....",
              "...owwo...",
              "..owccwo..",
              "..occcco..",
              "...occo..."],
    "tesla": ["...oyyo...",
              "....oo....",
              "..occcco..",
              "...oyyo...",
              "..occcco.."],
    "sniper": [".....o....",
               ".....o....",
               "....occo..",
               "...occcco.",
               "..occwcco."],
    "toxin": ["...oooo...",
              "....occo..",
              "...occcco.",
              "..occyccco",
              ".occccccco"],
}
TOWER_ORDER = ["archer", "cannon", "frost", "tesla", "sniper", "toxin"]


def tower_art(key):
    return TOWER_TOPS[key] + _BASE


def tower_pal(color):
    r, g, b = color
    dark = (int(r * .6), int(g * .6), int(b * .6))
    return {"o": _O, "s": (150, 150, 165), "S": (100, 100, 118), "c": color, "C": dark,
            "w": (255, 255, 255), "y": (255, 225, 80)}
