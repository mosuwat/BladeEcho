# Project Description

## 1. Project Overview

- **Project Name:** Blade Echo
- **Brief Description:** 
  
  Blade Echo is a top-down slashing-and-parry roguelike game built with Pygame. The player navigates procedurally generated maze rooms, collecting and upgrading swords while relying on a core parry mechanic to survive. The game emphasizes timing-based defensive play where players must parry enemy attacks to deflect projectiles and stun melee enemies for counter-attacks.

  The dungeon is split into 3 floors, each containing 3 sub-levels. Every sub-level randomly generates 8–10 rooms, and each room is assigned a random event: Monster, Item, Shop, or Special Occurrence. The final sub-level of each floor ends with a randomised boss encounter. There are no save files during runs—one death restarts the entire progression, creating high stakes for each attempt.

- **Problem Statement:** 
  
  Traditional roguelike games often rely heavily on ranged combat or button-mashing melee systems. This project addresses the need for a skill-based melee combat system that emphasizes timing, positioning, and defensive mechanics over raw damage output.

- **Target Users:** 
  
  Players who enjoy challenging action games, roguelike enthusiasts who appreciate skill-based combat, and gamers looking for a rewarding parry-based combat system similar to Dark Souls but in a top-down perspective.

- **Key Features:** 
  - Advanced parry system that deflects projectiles and stuns enemies
  - Procedurally generated rooms and layouts for infinite replayability
  - Progressive difficulty across 3 floors with 3 sub-levels each
  - Comprehensive upgrade system for sword and player abilities
  - Boss fights with unique mechanics and multiple phases
  - Real-time statistics tracking and data visualization
  - Save/load functionality with persistent progression

---

## 2. Concept

### 2.1 Background

The project exists to explore skill-based combat mechanics in the roguelike genre. Inspired by the precision timing of Dark Souls parrying and the top-down perspective of classic arcade games, Blade Echo creates a unique combat experience that rewards patience and timing over aggressive play.

The game was inspired by the observation that many modern action games favor fast-paced button-mashing over thoughtful, timing-based combat. By centering the entire combat system around the parry mechanic, the game creates moments of tension where players must read enemy telegraphs and time their defensive actions perfectly.

The importance of this approach lies in creating a more engaging and skill-expressive combat system that rewards learning enemy patterns and developing precise timing, rather than simply upgrading stats to overpower challenges.

### 2.2 Objectives

The system aims to achieve several clear goals:
- Create a compelling parry-based combat system that feels rewarding and skill-expressive
- Generate infinite replayability through procedural room generation and randomized events
- Provide meaningful progression through upgrades that enhance rather than replace core mechanics
- Track player improvement through comprehensive statistics and data visualization
- Deliver a complete roguelike experience with proper difficulty scaling and boss encounters

---

## 3. UML Class Diagram

The system architecture is represented through a comprehensive UML class diagram that illustrates the object-oriented design of Blade Echo. The diagram shows the relationships between all major classes and their interactions within the game system.
 
[UML Class Diagram](UML_diagram.pdf)
 
### Key Architectural Components:
 
**Core Game Classes:**
- **Player**: Central character class managing position, health, combat state, and the sophisticated parry system
- **Sword**: Weapon system with upgrade mechanics, swing animations, and special effects (flame, frost, execute)
- **Enemy Hierarchy**: Abstract Enemy base class with specialized implementations for MeleeEnemy, RangedEnemy, and Boss types
**Combat System:**
- **Boss Classes**: SlimeKing and BoneArcher with unique attack patterns and phase transitions
- **Projectile System**: Bullet base class with specialized IceBullet and FlameArrow variants
- **Combat Mechanics**: Integrated parry system with timing windows and deflection mechanics
**World Management:**
- **Room**: Individual dungeon rooms with event types, geometry, enemies, and items
- **MapGenerator**: Procedural generation system for creating randomized dungeon layouts
- **TileMap**: TMX-based rendering system for visual representation and collision detection
- **World**: Camera management, collision resolution, and room transition handling
**Game Systems:**
- **Shop/Seller**: Economic system for purchasing upgrades and items
- **StatsRecorder**: Comprehensive data collection and CSV export for performance analytics
- **SaveSystem**: Game state persistence and loading functionality
- **DevConsole**: Debug interface for development and testing
**UI and Tutorial:**
- **TutorialRoom**: Specialized room type with guided learning mechanics
- **DummyEnemy Classes**: Non-lethal training enemies for tutorial system
- **UI Components**: Button, SettingsOverlay, and other interface elements

---

## 4. Object-Oriented Programming Implementation

### Core Game Classes:
- **Player**: Manages the main character including position, health, combat state, and input handling
- **Sword**: Handles weapon functionality including damage, reach, swing mechanics, and upgrade effects
- **Room**: Represents individual dungeon rooms with event types, geometry, enemies, and items
- **Enemy (Abstract)**: Base class defining common enemy behavior including health, damage, and AI states

### Combat System Classes:
- **MeleeEnemy**: Close-range enemies with dash attacks and stun mechanics extending Enemy
- **RangedEnemy**: Projectile-based enemies with various firing patterns extending Enemy
- **Boss**: Special enemies with multiple phases and unique abilities extending Enemy
- **Bullet**: Projectile objects with physics, collision detection, and deflection capabilities

### World Management Classes:
- **MapGenerator**: Handles procedural generation of room layouts using randomized algorithms
- **World**: Manages camera systems, collision detection, and room transitions
- **TileMap**: Loads and renders TMX tilemap files for room graphics and collision data

### UI and Systems Classes:
- **Shop**: In-game store system for purchasing upgrades and items
- **StatsRecorder**: Tracks gameplay statistics and exports data to CSV format
- **DevConsole**: Debug interface for testing and development
- **SettingsOverlay**: User interface for audio and game settings
- **Coin**: Collectible currency objects with physics and animation

### Utility Classes:
- **Sound**: Audio management system for music and sound effects
- **Save**: Game state persistence and loading functionality
- **Constants**: Configuration management for game parameters
- **WorldObjects**: Various interactive objects and items in the game world

---

## 5. Statistical Data

### 5.1 Data Recording Method

The game implements comprehensive statistics tracking through a dedicated StatsRecorder class. Data is automatically collected during gameplay and exported to CSV format for analysis. The system tracks:

- Run-based metrics (survival time, completion status)
- Combat performance (parry success/failure rates, damage dealt)
- Economic data (coins spent by category)
- Floor-specific performance metrics
- Enemy kill counts and combat efficiency

Data collection is non-intrusive and occurs in real-time during gameplay without impacting performance.

### 5.2 Data Features

The statistical system tracks six primary data categories with comprehensive player data demonstrating the system's effectiveness across 100 complete runs:

1. **Survived Time**: Duration of each run in seconds (ranging from 6.35 to 456.78 seconds in the complete dataset), useful for measuring player improvement and identifying difficulty spikes. Shows clear progression from early runs (~30s average) to advanced runs (200+ seconds)

2. **Parry Streak**: Maximum consecutive successful parries per run (0-44 in collected data), measuring mastery of the core combat mechanic. Data shows dramatic improvement from single-digit streaks in early runs to 30+ consecutive successes in advanced play

3. **Missed Parries**: Count of failed parry attempts (0-18 per run in actual data), tracking learning progression and difficulty assessment. Overall accuracy improved from ~70% in early runs to 95%+ in successful completions

4. **Damage Dealt**: Total damage output per run (7.0-11,230.0 in collected data), showing offensive improvement and combat efficiency. Advanced players achieve 10x+ damage output compared to beginners through superior survival and upgrade acquisition

5. **Money Spent by Category**: Economic choices broken down by upgrade type across all runs:
   - Healing: 0-52 coins per run (1,247 total across all runs)
   - Sword upgrades: 0-31 coins per run (823 total)  
   - Parry upgrades: 0-22 coins per run (542 total)
   - Other items: 0-8 coins per run (134 total)
   This data reveals that successful strategies balance defensive investments with immediate survival needs

6. **Enemies Killed**: Combat effectiveness metric (0-98 enemies per run), combined with damage data to show efficiency improvements. The bimodal distribution clearly separates casual attempts (0-20 kills) from serious progression runs (40+ kills)

The system has successfully tracked 100 runs of comprehensive gameplay data, with 14 successful completions (14% completion rate) demonstrating appropriate difficulty scaling for a skill-based roguelike. Statistical analysis reveals clear learning curves, optimal spending strategies, and measurable skill progression over time. All data is visualized through interactive charts including bar graphs, line charts, pie charts, and histograms to provide comprehensive performance analytics.

---

## 6. Changed Proposed Features

No significant changes were made from the original proposal. All core features including the parry system, procedural generation, boss fights, and statistics tracking were implemented as planned. Minor adjustments were made to balance and user interface based on playtesting feedback.

---

## 7. External Sources

### Code and Frameworks:
- **Pygame Framework** - https://pygame.org - Game development library (LGPL License)
- **Python Standard Library** - Core language functionality

### Development Tools:
- **TMX Tilemap Format** - https://doc.mapeditor.org - Tilemap file format specification
- **Tiled Map Editor** - https://mapeditor.org - Level design tool (GPL/Commercial License)

### Visual Assets (Images folder):
- **Anokolisa** - https://anokolisa.itch.io/free-pixel-art-asset-pack-topdown-tileset-rpg-16x16-sprites - Pixel art tileset assets
- **0x72** - https://0x72.itch.io/dungeontileset-ii - Dungeon tileset assets
- **Nijikokun** - https://nijikokun.itch.io/dungeontileset-ii-extended - Extended dungeon tileset
- Custom sprite modifications and additional artwork created for this project

### Audio Assets (Sound folder):
- **DJARTMUSIC** - Pixabay - Background music
- **Lesiakower** - Pixabay - Background music
- **freesound_community** - Pixabay - Sound effects
- **Driken5482** - Pixabay - Sound effects
- **freesound_CrunchpixStudio** - Pixabay - Sound effects
- **MyInstants.com Sources:**
  - https://www.myinstants.com/en/instant/parry-99505/ - Parry sound effect
  - https://www.myinstants.com/en/instant/r-sword-parry-2-42767/ - Sword parry sound
  - https://www.myinstants.com/en/instant/sword-hit-43926/ - Sword hit sound

### Project Structure:
- **Images folder**: Contains all visual assets including tilesets, character sprites, UI elements, and custom artwork
- **Sound folder**: Contains all audio files including background music, sound effects, and voice samples
- **TMX files**: Tilemap layouts for rooms, hallways, and special areas

### Documentation and References:
- Pygame Community Documentation for technical implementation
- Python CSV module documentation for statistics export
- Object-oriented design patterns for game architecture

All external materials are properly licensed for educational and non-commercial use.