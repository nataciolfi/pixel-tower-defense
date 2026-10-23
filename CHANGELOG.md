# Changelog

## 0.04
- **Legendary towers now use a premium currency, Legend Shards, with fixed prices** (3 / 5 / 8 / 11 / 15). They are bought
  once in the new **Legendary Vault** tab of the Ascension screen and then belong to you forever. Placing them in a run costs no
  gold; each becomes available at a fixed wave of the run (10-30). The old gold prices that scaled with the economy are gone.
- **Shards are awarded in small amounts per Ascension** (from wave 20): `1 + wave/100 + (map level-1)/2`.
- **Ascension Points scale much faster with depth**: same curve up to wave 100, then doubling every 100 waves
  (wave 500 = ~31.8K AP instead of ~2K, wave 1000 = ~3.5M). The permanent lifetime-AP damage bonus is now
  `+5% x sqrt(lifetime AP)` so the bigger payouts don't break the game.
- Fix: the Ascension screen layout/fonts, banners and menu now show both currencies; large AP values use K/M/B formatting.
- Saves keep Shards and the Vault; restoring a run with a legend automatically marks that legend as owned.
- 82 unit tests.

## 0.03
- **8 new towers** (Ballista, Flame, Shockwave, Stasis, Hexer, Overclock, Mint, Executioner) -> 18 regular towers,
  organised in **6 categories** with tabs in the build panel (`1`-`7`, `Z X C V B`).
- **5 legendary towers** (Phoenix, Midas, Thunderlord, Chronos, Reaper): one of each per run, can't be sold, level up
  by killing enemies (XP = gold value of their kills), stronger than normal towers and each with a signature ability.
- **Auto-upgrade** (`AUTO UP` / `G`: off, priority only, all) with per-tower **priority ranks** #1-#3.
- **Speeds up to x64** (x1 x2 x4 x8 x16 x32 x64) with a per-frame time budget, effects automatically off above x4 and
  a "running at ~xN" indicator when the CPU can't keep up.
- New enemy-state mechanics in the pool: stun, vulnerability, knockback, and kill attribution per tower.
- Save files now keep priorities, auto-upgrade mode, per-tower kills and legendary XP.
- 76 unit tests (was 48).

## 0.02
- **5 maps = 5 difficulties** (Green Meadow, Dusty Canyon, Frozen Pass, Ember Gorge, Void Rift): different roads
  (shorter = harder), themes, growth rates, base damage/regen, starting gold and an Ascension-Point multiplier.
  Map selection screen; runs, saves and per-map best waves remember the map.
- **Bosses**: HP no longer tied to the whole wave. It now grows only polynomially in the wave number
  (`boss_k * (1 + wave/25)` grunt-HPs), with lower armor, so bosses stay beatable at wave 30+ and beyond.
  Titan was softened too. (Before: with an area-damage build, bosses reached the base on every boss wave.)
- **Ordinary enemies are tougher**, and the late-game growth is set per map.
- **Base damage rebuilt**: every leak removes a *percentage* of the base (grunt 8%, brute 15%, boss 50-60% ...,
  times the map's multiplier, times the bundle size). Healing between waves dropped from 30% to 6%..0% depending on
  the map. New **REPAIR** button (+25% base HP for gold) so the base is a resource you manage.
- **Packs**: enemies of one type now spawn as tight squads with a random sideways offset, so crowds are dense and
  splash damage (Cannon, Mortar, Frost, Toxin) actually hits many enemies. Splash radii were increased.
- **Void tower reworked and explained**: each hit now removes 3% of the target's MAX HP at level 1 (up to 20%,
  bosses take 15% of that), hits up to 12 enemies, ignores armor/shields/dodging. The build panel and the
  tower panel now show these numbers; every tower has a plain-language description.
- Splitter children, Brutes and "rush" waves were rebalanced.


## 0.01
- 10 tower types (Archer, Cannon, Frost, Tesla, Sniper, Toxin, Laser, Mortar, Beacon, Void) with unlock progression.
- 12 enemy types + 2 bosses (Shaman healers, Splitters, shielded Aegis, slow-immune Golem, Titan boss ...).
- Ascension (prestige) system with permanent upgrades; Ascension Points also give +1% damage each.
- Autosave (after every wave and on exit), atomic JSON saves with automatic backup.
- Main menu, how-to-play, pause menu, fullscreen (F11).
- Debian package (`packaging/debian/build-deb.sh`), CI and unit tests.
