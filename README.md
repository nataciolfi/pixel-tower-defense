# Pixel Tower Defense

A pixel-art **tower defense with infinite waves and absurd numbers**. Build towers *anywhere* off the road,
watch enemy count, HP, damage and gold grow exponentially (millions → billions → trillions → beyond),
then **Ascend** for permanent power and do it all again.

> Add a screenshot at `docs/screenshot.png` and reference it here.

## Features

- **5 maps = 5 difficulties**, each with its own road, theme and rules (see below).
- **Free placement** – no preset slots; the only rule is "not on the road" (and not on top of another tower).
- **18 towers in 6 categories + 5 legendary towers**, each with damage / range / rate / targeting / special effect.
- **Legendary towers**: one of each per run, they level up *by killing* and are far stronger than normal towers.
- **Auto-upgrade with priorities** and speeds up to **x64** for the very long runs of high Ascension levels.
- **12 enemy types + 2 bosses**, introduced progressively; a boss every 10 waves.
- **Exponential difficulty** with a number system that never breaks (gold is an arbitrary-precision integer; combat values go to 1e300; display K, M, B, T, Qa … Vg, then scientific notation).
- **Performance by design** – all enemies live in numpy arrays; every update is a vector operation. Huge waves are merged into *bundles* so thousands of "real" enemies cost the same CPU as a few hundred.
- **Ascension (prestige)**, permanent upgrades, tower unlocks by best wave.
- **Autosave** (every wave + on exit), atomic JSON with automatic backup, main menu, pause menu, fullscreen (F11).

## Install

### Debian / Ubuntu (recommended)

Needs Debian 12+ / Ubuntu 22.04+ (python3-pygame ≥ 2.0).

```bash
# build the package from source (needs only dpkg-deb)
./packaging/debian/build-deb.sh
sudo apt install ./dist/pixel-td_0.04_all.deb     # pulls python3-pygame + python3-numpy
pixel-td                                           # or launch "Pixel Tower Defense" from your app menu
```

Or grab the `.deb` from the project's *Releases* page. Uninstall: `sudo apt remove pixel-td`.

### pip / pipx

```bash
pipx install .            # or: pip install .
pixel-td
```

### From source

```bash
pip install -r requirements.txt
PYTHONPATH=src python3 -m pixel_td
```

## Controls

| Key / mouse | Action |
|---|---|
| `1`-`7` | choose tower category tab |
| `Z` `X` `C` `V` `B` | pick the 1st-5th tower of the current tab |
| Left click | place tower / select tower / press buttons |
| Right click, `Esc` | cancel (Esc with nothing to cancel opens the menu) |
| `Space` | start next wave |
| `P` | pause |
| `+` / `-` | game speed (x1, x2, x4, x8, x16, x32, x64) |
| `G` | cycle auto-upgrade: off / priority / all |
| `U` | upgrade selected tower once |
| `Q` | **Meteor** – then click the map (damages % of max HP) |
| `W` | **Time freeze** |
| `F11` | fullscreen |

Selected tower: `UP x1 / x10 / MAX`, `PRIORITY` rank, cycle targeting (First / Last / Strongest / Weakest / Closest), sell (70 %).

**Speeds:** x1 ... x64. Above x4 the visual effects switch off to save CPU, and the simulation is time-budgeted per frame so the window stays responsive; if your CPU can't keep up the panel shows the real speed ("Running at ~x23"). Combine with **AUTO WAVE** for long runs.
Every 10 levels a tower receives a large damage bonus.

## Maps / difficulties

| Map | Difficulty | Road | Growth after wave 10 | Base damage | Healing / wave | AP bonus |
|---|---|---|---|---|---|---|
| Green Meadow | EASY | 104 tiles | +15.5 % HP | x0.7 | 6 % | x1 |
| Dusty Canyon | NORMAL | 74 | +16.4 % | x0.95 | 3 % | x1.5 |
| Frozen Pass | HARD | 59 | +16.5 % | x1.15 | 2 % | x2.2 |
| Ember Gorge | EXPERT | 42 | +16.6 % | x1.3 | 1.2 % | x3.2 |
| Void Rift | INSANE | 36 | +16.8 % | x1.5 | 0 % | x5 |

All maps start alike (waves 1-10 grow at the same rate); harder maps then scale faster, give less healing and
make every leak hurt more, but pay more Ascension Points and start with more gold.

## The base

Each enemy that reaches the castle removes a **percentage** of its HP (grunt 8 %, brute 15 %, bosses 50-60 %, multiplied by the
map's base-damage factor and by the size of the "bundle" it represents). Healing after a wave is small, so use **REPAIR** (bottom bar,
between waves): +25 % base HP for gold.

## Bosses

Boss HP is `boss_k * (1 + wave/25)` times a normal enemy's HP - it grows slowly (polynomially) while normal enemies
grow exponentially, so bosses stay beatable at any wave but still hit hard if they leak.
Overlord every 10 waves, armored & shielded Titan every 20.

## Towers

Towers are grouped in **7 tabs** (keys `1`-`7`). Pick one with `Z X C V B` or by clicking.

| Category | Tower (unlock = best wave) | Role |
|---|---|---|
| **SHOT** (marksman) | Archer (0) | cheap, fast, crits |
| | Ballista (6) | bolt pierces **everything on a line** |
| | Sniper (8) | huge hit, pierces armor, long range |
| | Laser (12) | beam ramps up on one target |
| **BLAST** (artillery) | Cannon (0) | splash |
| | Shockwave (14) | pulse hits all in range and **knocks them back** |
| | Mortar (16) | very long range, huge splash |
| **ELEM** (elemental) | Toxin (3) | poison (ignores armor) |
| | Tesla (5) | chain lightning |
| | Flame (10) | burns **every** enemy around it (ignores armor) |
| **CTRL** (control) | Frost (0) | area slow |
| | Stasis (18) | **stuns** an area (bosses 80 % less) |
| | Hexer (22) | enemies take **+X % damage from all towers** |
| **SUPP** (support) | Mint (12) | global **% gold bonus** (no range) |
| | Beacon (20) | damage aura for nearby towers |
| | Overclock (26) | **fire-rate aura** for nearby towers |
| **SPEC** (special) | Executioner (24) | instantly kills enemies under a HP threshold |
| | Void (30) | each hit removes a **% of the target's max HP** (3 % at level 1, up to 20 %), ignores armor/shields/dodge, hits up to 12 enemies; bosses take 15 % |
| **LEG** (legendary) | Phoenix (25) | splash + burn, every 6th shot is a **nova** hitting everything in range |
| | Midas (35) | enemies dying in its range drop **bonus gold** |
| | Thunderlord (45) | mega chain lightning + **Smite** (strongest enemy on the map every 5 s) |
| | Chronos (55) | permanent slow aura + periodic **Time Stop** |
| | Reaper (65) | % max-HP hits on many targets, executes weak enemies, **double XP** |

### Legendary towers

* **Premium currency: Legend Shards.** Each legend has a **fixed price in Shards** (Phoenix 3, Midas 5, Thunderlord 8, Chronos 11, Reaper 15).
  You buy it **once** in the **Legendary Vault** (Menu > Ascension > *Legendary Vault* tab) and it is yours for every future run.
* **Shards are rare:** you earn a *small* amount each time you Ascend (from wave 20): `1 + wave/100 + (map level-1)/2`
  (e.g. wave 100 on Easy = 2, wave 500 = 6, wave 500 on Insane = 8).
* In a run you can build **one of each** legend you own, **for free (no gold)**, once the run reaches its wave
  (Phoenix 10, Midas 15, Thunderlord 20, Chronos 25, Reaper 30). They can't be sold or bought up with gold.
* They **level up by killing**: XP = the gold value of the enemies they kill (Reaper earns double). Because enemy gold grows with enemy HP,
  a legendary keeps pace with the waves automatically, and one placed late catches up within a wave or two.
* No gold upgrades: damage grows `x1.25` per level (vs `x1.12` for normal towers), plus a signature ability each (see table).
* Place them where the action is: only kills *they* score give them XP (poison/burn kills count for the tower that applied it).

### Auto-upgrade and priority

* **AUTO UP** button (or `G`): `OFF` -> `PRIORITY` (only towers you flagged) -> `ALL` (flagged towers first, then the cheapest upgrades).
* Select a tower and press **PRIORITY** to give it rank `#1`, `#2` or `#3`. Rank 1 is fed first (it gets all the gold it can use), then rank 2, then rank 3.
  Flagged towers show a coloured pip.
* Auto-upgrade runs inside the simulation, so it keeps working at x64 and while you are away from the build panel.

## Enemies

Grunt · Runner (fast) · Brute (HP) · Knight (armor) · Wraith (dodge + regen) · Swarm (tiny, numerous) ·
Shaman (heals allies) · Splitter (splits on death) · Aegis (shield) · Golem (huge HP, slow-immune) ·
**Overlord** (boss) · **Titan** (armored, shielded boss, every 20 waves).

## Ascension (prestige)

Choose **Ascend** from the pause menu (or after defeat / victory). Your run resets and you gain
**Ascension Points (AP)** and a few **Legend Shards**.

AP grow polynomially (`0.5 * (wave/5)^1.8`) up to wave 100 and then **double every 100 waves**, then are multiplied by the map's AP bonus
(x1 Easy ... x5 Insane). Deep runs are therefore *vastly* more rewarding than shallow ones:

| Wave reached (Easy) | AP | Shards (Easy / Insane) |
|---|---|---|
| 20 | 6 | 1 / 3 |
| 50 | 31 | 1 / 3 |
| 100 | 109 | 2 / 4 |
| 200 | 765 | 3 / 5 |
| 300 | 3,174 | 4 / 6 |
| 500 | 31,848 | 6 / 8 |
| 750 | 373,791 | 8 / 10 |
| 1000 | 3,548,901 | 11 / 13 |

Spend AP on permanent upgrades (damage, gold, attack speed, base HP, starting gold, cheaper towers, shorter skill cooldowns).
Every AP ever earned also gives a permanent damage bonus of **+5 % x sqrt(lifetime AP)** (sub-linear on purpose, so a huge
ascension doesn't trivialise everything). Reaching **wave 50** shows *Victory*, but the game continues in endless mode.

## Saves

`~/.local/share/pixel-td/save.json` (honours `$XDG_DATA_HOME`; override with `--save-dir` or `$PIXEL_TD_HOME`).
The game autosaves after every cleared wave and when you leave. Quitting mid-wave resumes at the *start* of that wave.
A `.bak` copy of the previous save is kept. `pixel-td --reset-save` wipes everything.

## Command line

```
pixel-td [--fullscreen] [--save-dir DIR] [--reset-save] [--seed N] [--version]
```

## Project layout

```
src/pixel_td/
  config.py   balance knobs        sim.py     headless simulation core
  maps.py     the 5 maps/difficulties
  bignum.py   big-number helpers   towers.py  tower stats + combat
  enemies.py  numpy enemy pool     waves.py   exponential wave generator
  meta.py     prestige             save.py    JSON saves
  sprite_data.py / sprites.py      ASCII → pixel-art surfaces (no image files)
  effects.py  particles & beams    render.py  world drawing
  ui.py       HUD                  menu.py    menu / ascension / help
  game.py     main loop & scenes   __main__.py CLI
tests/        unit tests (+ headless pygame smoke test)
packaging/    Debian package builder, desktop file, man page, icons
```

Only `render/ui/menu/sprites/effects/game` import pygame; the rest is unit-tested without a display.

## Development

```bash
make test          # unittest suite
make deb           # build the Debian package into dist/
python3 tools/make_icon.py   # regenerate icons
```

Tuning the difficulty: edit the `*_G` growth constants in `src/pixel_td/config.py`
(`HP_G`, `COUNT_G`, `GOLD_G`, `DMG_G`, `UPG_G` …). A scripted "best dps per gold" bot reaches
roughly wave 125+ on Easy/Normal and wave 20-45 on Hard/Expert/Insane (a scripted bot has no skills and
no sense of targeting - people do better).

## License

MIT – see [LICENSE](LICENSE).
