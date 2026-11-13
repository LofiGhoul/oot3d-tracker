# OoT3D 100% Tracker

A GTK4/libadwaita app for Linux that reads an Ocarina of Time 3D save slot and shows
how close you are to 100%. You get an overall completion percentage and a checklist per category:

| Category | What's tracked |
|---|---|
| Pieces of Heart | All 36, by region, with step-by-step instructions for each |
| Gold Skulltulas | All 100, grouped by area (Master Quest dungeons too) |
| Skulltula House rewards | The 10 / 20 / 30 / 40 / 50 token rewards |
| Heart Containers | The 8 boss Heart Containers |
| Stones & Medallions | 3 Spiritual Stones, 6 Medallions, Stone of Agony, Gerudo's Card |
| Songs | All 12 |
| Items | 19 inventory items, including Longshot and the Ocarina of Time |
| Equipment | Swords (including Biggoron's Sword), shields, tunics, boots |
| Upgrades | Quivers, bomb and bullet bags, gauntlets, scales, wallets, stick and nut capacity, magic, Double Defense |
| Bottles | All 4 |

## Run

    python3 oot3d_tracker.py [path/to/save file]

or `./install.sh` once to add it to your app launcher (and `oot3d-tracker` to `~/.local/bin`).

- **Open** (Ctrl+O) a slot file, or drop one on the window. Saves dumped with
  Checkpoint/JKSM or taken from Citra/Azahar/Lime3DS all work.
- If the other slots sit in the same folder, they show up as tabs.
- Tap a category to open its checklist. **All / Missing** filters it.
- In Pieces of Heart, tap a piece to expand step-by-step instructions (written for the 3DS version).
- The window reloads by itself when the save file changes, so you can keep it open
  next to an emulator. Ctrl+R reloads by hand.
- It remembers the last file you opened. On first run it looks in emulator folders
  (all three regions: USA, EUR, JPN) and `~/Downloads`.

Needs only Python 3 with PyGObject, GTK 4 and libadwaita ≥ 1.7. It reads the save and never writes to it.

## Icons (optional, bring your own)

No game artwork ships with this app. If you have your own item icons, put them in either
`icons/` next to `oot3d_tracker.py` (git ignores this folder) or
`~/.local/share/oot3d-tracker/icons/`. Each category page then shows a grid of its icons,
with the ones you're missing faded.

Name each file after the check id in `checklist.py` without its prefix
(`.png`, `.svg`, `.webp` or `.jpg`): `i_hookshot` → `hookshot.png`,
`s_lullaby` → `lullaby.png`, `e_mirror_shield` → `mirror_shield.png`.

## How it decides

- Everything is read straight from the save: scene flags (chests, collectibles),
  event flags, Gold Skulltula flags, the inventory, and the equipment, upgrade and quest bitfields.
- Which flag belongs to which check comes from the
  [OoT3D Randomizer](https://github.com/gamestabled/OoT3D_Randomizer)'s location table, which
  records the scene and flag of every item in the 3DS version.
- The slot file is found by its `ZELDAZ` marker, so it doesn't matter exactly how it was dumped.
- If your hearts show more pieces than the flags account for, the hearts page says so.
- The overall percentage counts each check once, even when it appears in two sections
  (for example, the 50-token reward is also a Piece of Heart).
- Not tracked: the trading sequences, masks, Big Poe captures, cows and small keys.

`oot3d_save.py` also works from the command line: `python3 oot3d_save.py save00.bin`.
Piece instructions live in `guide.py`, and the other checklists in `checklist.py`.
