# Blade Echo

## Project Description
- Project by: Suwat Teiwasuculmetri
- Game Genre: Action, Roguelike, Top-down
- Student ID: 6810545956

A top-down slashing-and-parry roguelike game built with Pygame. The player navigates procedurally generated maze rooms, collecting and upgrading swords while relying on a core parry mechanic to survive. There are no save files—one death restarts the entire run.

The dungeon is split into 3 floors, each containing 3 sub-levels. Every sub-level randomly generates 8–10 rooms, and each room is assigned a random event: Monster, Item, Shop, or Special Occurrence. The final sub-level of each floor ends with a randomised boss encounter.

---

## Installation

To Clone this project:
```sh
https://github.com/mosuwat/BladeEcho.git
```

To create and run Python Environment for This project:

Windows:
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Mac:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running Guide

After activate Python Environment of this project, you can process to run the game by:

Windows:
```bat
python main.py
```

Mac:
```sh
python3 main.py
```

---

## Tutorial / Usage

### Controls:
- **Movement**: W, A, S, D keys
- **Attack**: Left mouse click (slash with sword)
- **Parry**: SPACE key (timing-based defensive mechanic)
- **Map**: M key (view minimap)
- **Shop**: E key (when near shop)
- **Settings**: ESC key
- **Buffs View**: TAB key
- **Dev Console**: ` (backtick) key

### Gameplay:
1. Start with the tutorial to learn basic mechanics
2. Navigate through procedurally generated rooms
3. Fight enemies using sword attacks and parrying
4. Collect coins and items to upgrade your character
5. Visit shops to purchase upgrades
6. Survive through 3 floors with 3 sub-levels each
7. Face bosses at the end of each floor

### Core Mechanics:
- **Parrying**: Time your parry (SPACE) just before enemy attacks to deflect bullets or stun melee enemies
- **Sword Combat**: Click to swing your sword at enemies
- **Progression**: Collect items and buy upgrades to become stronger
- **Room Events**: Each room can contain monsters, items, shops, or special events

---

## Game Features

### Core Mechanics:
- **Advanced Parry System**: Deflect projectiles back at enemies and stun melee attackers
- **Dynamic Sword Combat**: Upgradeable sword with various effects (flame, frost, execute)
- **Procedural Generation**: Each run features randomly generated rooms and layouts
- **Progressive Difficulty**: 3 floors with 3 sub-levels each, increasing in difficulty

### Combat Features:
- Multiple enemy types with different attack patterns
- Boss fights with unique mechanics and phases
- Upgradeable player stats (health, damage, parry effectiveness)
- Special sword effects and abilities

### Progression System:
- Shop system with various upgrades
- Item collection and buff system
- Persistent statistics tracking
- Save/load functionality

### Technical Features:
- Custom tilemap rendering system
- Collision detection and physics
- Sound and music management
- Statistics recording and visualization
- Developer console for testing

---

## Known Bugs

- Monster sometimes stuck between gate and the wall.
- Ranged boss sometime does not teleport to middle of the map when collsion with north wall.

---

## Unfinished Works

All core features are complete as per the project requirements.

---

## External Sources

### Visual Assets:
- **Anokolisa** - https://anokolisa.itch.io/free-pixel-art-asset-pack-topdown-tileset-rpg-16x16-sprites [pixel art tileset]
- **0x72** - https://0x72.itch.io/dungeontileset-ii [dungeon tileset]
- **Nijikokun** - https://nijikokun.itch.io/dungeontileset-ii-extended [extended dungeon tileset]
- Custom sprite modifications and additional artwork [game graphics]

### Audio Assets:
- **DJARTMUSIC** - Pixabay [background music]
- **Lesiakower** - Pixabay [background music]
- **freesound_community** - Pixabay [sound effects]
- **Driken5482** - Pixabay [sound effects]
- **freesound_CrunchpixStudio** - Pixabay [sound effects]
- **Parry sound effects** - https://www.myinstants.com [game audio]
- **Sword combat sounds** - https://www.myinstants.com [game audio]

### Code and Frameworks:
- **Pygame Framework** - https://pygame.org [game framework]
- **TMX Tilemap Format** - https://doc.mapeditor.org [tilemap system]
- **Tiled Map Editor** - https://mapeditor.org [level design tool]

### Additional Assets:
- **Images folder**: Contains all visual assets including tilesets, sprites, and UI elements
- **Sound folder**: Contains all audio files including music and sound effects
