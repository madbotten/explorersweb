Markdown
# EXPLORERS — Master Refactoring & Procedural Expansion Roadmap

## Execution Rules for the Agent (Argon)
1. **Execute ONE Phase at a time.** Do not combine phases.
2. **Preserve Backward Compatibility:** Existing save files (`saves/`) and `gametests.py` helpers must not crash when loading older character dicts.
3. **Run Unit Tests After Every Phase:** Always run `.venv/bin/python -m unittest discover -v` at the end of a phase and ensure 100% of tests pass before moving on.

---

## PHASE 1: Surgical Bug Fixes (Combat Double-Damage, Stat Typos, & Credits Carryover)
**Why First:** Fixes broken combat math and state bugs before we touch the stat formulas.

### Agent Prompt for Phase 1:
> Please read and execute **Phase 1** of `ROADMAP.md`:
>
> 1. **Fix Double-Damage Bug in `src/Battle.py`:**
>    - In `run_battle_action_melee`, `target.hurt(adjusted_damage, effect_type)` is called twice on a hit (once inside `if hit:` around line 286, and a second time inside `if hit and target.is_alive():` around line 291). Remove the first `target.hurt(...)` and `draw_life_bar(...)` so melee hits only apply damage once. Also change `if hit and target.is_alive():` to `if hit:` so that killing blows still trigger `draw_life_bar`, `battle_display_action_damage`, and `battle_display_character_hit`.
>    - In `run_battle_action_shoot`, fix the exact same double-damage bug (around lines 382 and 388) where `target.hurt(...)` is called inside `if hit:` and then called a second time inside `await self.damage_target(...)`. Remove the first `target.hurt` and `draw_life_bar`, and change `if hit and target.is_alive():` to `if hit:` so fatal shots still display damage and the hit flash.
>
> 2. **Fix `decrease_stat` Typo in `src/Character.py`:**
>    - In `Character.decrease_stat(self, stat_name, amount)` (around line 397), if `self.stats[stat_name] <= 15`, it erroneously sets `self.skills[stat_name] = 15` instead of `self.stats[stat_name] = 15`. Fix this typo so it clamps `self.stats[stat_name] = 15`.
>
> 3. **Fix `team_dead` Check in `src/Utils.py`:**
>    - In `Utils.team_dead(team)` (around line 295), it currently checks `character.stats.get("max_health", 0) <= 0`, which is a static stat that never drops when taking damage! Fix `team_dead(team)` to check `all(not character.is_alive() for character in team)` (or `character.current_health <= 0`).
>
> 4. **Fix Loop Credits Carryover in `src/EquipTeam2.py`:**
>    - On line 48, `credits = 5000` is hardcoded, ignoring credits earned in `Score.py` on Loop 2+. Update it so Loop 1 starts with `5000`, and Loop 2+ starts with `team[0].mission.get("credits", 5000) if (team and loop > 1) else 5000`.
>
> 5. **Verify with Tests:**
>    - Add a unit test in `gametests.py` confirming `team_dead()` returns `False` when a member has `current_health > 0` and `True` when all members have `current_health == 0`, and a test for `decrease_stat()` clamping `stats` (not `skills`) at 15. Run `.venv/bin/python -m unittest discover -v`.

---

## PHASE 2: The 3-Layer Character Stat Architecture (`Character.py`)
**Why Second:** Establishes the 18 Sub-Stats -> 6 Core Attributes -> 11 Derived Stats hierarchy and locks it in with unit tests.

### The 3-Layer Matrix Specification:
* **Layer 1: 18 Sub-Stats** (Generated via `bell_curve_stat()` for non-robots; stored in `self.sub_stats` or `self.stats`):
  * **Strength** = `round((brawn + stamina + resilience) / 3)`
  * **Coordination** = `round((fine_manipulation + agility + reflexes) / 3)`
  * **Intelligence** = `round((logic + memory + guile) / 3)`
  * **Willpower** = `round((focus + composure + tenacity) / 3)`
  * **Charisma** = `round((beauty + charm + command) / 3)`
  * **Courage** = `round((valor + nerve + resolve) / 3)`
* **Layer 2: 6 Core Attributes** (`strength`, `coordination`, `intelligence`, `willpower`, `charisma`, `courage`) — rolled up as the rounded average of their 3 respective sub-stats.
* **Layer 3: 11 Derived Stats** — calculated from the finer-grained sub-stats (with fallback to core stats if `sub_stats` are overridden in legacy tests):
  * `offense` = `round((reflexes + nerve + focus) / 3)`
  * `defense` = `round((agility + resilience + composure) / 3)`
  * `deception` = `round((guile + charm + nerve) / 3)`
  * `evasion` = `round((agility + reflexes + guile) / 3)`
  * `analyze` = `round((logic + memory + focus) / 3)`
  * `max_health` = `stamina + resilience + tenacity` (scaled * 2/3 or `round((stamina + resilience) + tenacity)` — keep scale ~100–120 to match existing balance: `round((stamina + resilience + tenacity) * 2 / 3)`)
  * `movement` = `brawn + stamina + agility`
  * `meleecombat` = `evasion + brawn + valor` (scaled: `evasion + round((brawn + valor) / 2)`)
  * `perception` = `round((focus + reflexes + memory) / 3)`
  * `surprise` = `evasion + perception`
  * `leadership` = `command + resolve + logic`

### Agent Prompt for Phase 2:
> Please read and execute **Phase 2** of `ROADMAP.md`:
>
> 1. **Implement the 3-Layer Stat System in `src/Character.py`:**
>    - Define `SUB_STAT_MAP` mapping the 6 core attributes to their 3 sub-stats:
>      - `"strength"`: `("brawn", "stamina", "resilience")`
>      - `"coordination"`: `("fine_manipulation", "agility", "reflexes")`
>      - `"intelligence"`: `("logic", "memory", "guile")`
>      - `"willpower"`: `("focus", "composure", "tenacity")`
>      - `"charisma"`: `("beauty", "charm", "command")`
>      - `"courage"`: `("valor", "nerve", "resolve")`
>    - Add `recalculate_stats(self)` on `Character`. When sub-stats are generated in `__init__`, store the 18 sub-stats in `self.sub_stats` (and serialize/deserialize `sub_stats` in `to_dict()` / `from_dict()`, auto-populating `sub_stats` from core stats if loading an old save that lacks `sub_stats`).
>    - Have `recalculate_stats(self)` compute the 6 core attributes from `self.sub_stats` (each as the `round()` average of its 3 sub-stats) and then compute the derived stats (`offense`, `defense`, `deception`, `evasion`, `analyze`, `max_health`, `movement`, `meleecombat`, `perception`, `surprise`, `leadership`).
>    - **Important Backward Compatibility for `gametests.py`:** Keep a helper method or ensure that if a test directly overrides `c.stats["willpower"] = 60` without touching `sub_stats`, existing tests in `TestHealthMorale` and `TestInitiative` continue to pass!
>    - Update `ChooseTeam4.py` and `EquipTeam2.py` hover/stat displays so hovering over a Core Attribute in `ChooseTeam4.py` shows both its description AND its 3 sub-stat values (e.g., `"Strength (Brawn: 65, Stamina: 58, Resilience: 72) — Determines physical power and endurance"`).
>
> 2. **Verify with Tests:**
>    - Add a `TestThreeLayerStats` test case in `gametests.py` verifying that all 18 sub-stats generate within `[25, 95]`, roll up accurately into the 6 core stats, and survive `to_dict()` / `from_dict()` serialization. Run `.venv/bin/python -m unittest discover -v`.

---

## PHASE 3: Consolidate & Smart-Weight Voyage Training Events (`Voyage.py` & `ReturnVoyage.py`)
**Why Third:** Eliminates ~600 lines of duplicated training event definitions across `Voyage.py` and `ReturnVoyage.py` and makes crew training intelligent.

### Agent Prompt for Phase 3:
> Please read and execute **Phase 3** of `ROADMAP.md`:
>
> 1. **Create a Data-Driven Training Generator:**
>    - In `src/Location.py` (or `src/Utils.py`), create a `TRAINING_SCENARIOS` dictionary mapping each skill name to a list of `(location_key, pre_description, post_description)` tuples using the existing descriptions from `Voyage.py`.
>    - Write a function `build_procedural_training_event(team, locations, all_items)` that:
>      - 70% of the time picks a skill from `TRAINING_SCENARIOS` that at least one living non-robot crew member has at proficiency `>= 50` (if any exist).
>      - 30% of the time picks any skill from `TRAINING_SCENARIOS` at random.
>      - Returns an `Event` instance configured with `calculate_outcome_training`.
>
> 2. **Refactor `src/Voyage.py` and `src/ReturnVoyage.py`:**
>    - Remove the ~35 hardcoded `training_*` `Event` objects from `repeatable_events` in both `Voyage.py` and `ReturnVoyage.py`.
>    - Keep the non-training repeatable events (interactions, crafting, found_items, rest/debates) in `repeatable_events`, and give the event selector a dedicated probability branch (e.g., 55% training via `build_procedural_training_event`, 25% interaction/crafting/found_items from `repeatable_events`, 20% `optional_singular_events`) so the event pacing stays identical while training is dynamically generated.
>
> 3. **Verify with Tests:**
>    - Add unit tests in `gametests.py` testing `build_procedural_training_event` to confirm it returns valid `Event` objects and favors skills known by the team. Run `.venv/bin/python -m unittest discover -v`.

---

## PHASE 4: Universal Multi-Approach Challenge Engine & All 31 Pirate Locations (`Location.py` & `Mission.py`)
**Why Fourth:** Replaces one-off `calculate_outcome_*` functions with a reusable data-driven obstacle engine and unlocks the 23 unused Pirate rooms.

### Agent Prompt for Phase 4:
> Please read and execute **Phase 4** of `ROADMAP.md`:
>
> 1. **Tag All 31 Pirate Locations in `src/Location.py`:**
>    - Add a `tags` tuple to every room in `PIRATE_LOCATION_ATTRIBUTES` (and store `self.tags = tags` on `Location`):
>      - `"combat"`: `barracks`, `guard room`, `checkpoint`, `training room`, `drone launch`
>      - `"tech"`: `radar tower`, `war room`, `environmental control`, `artifact analysis`
>      - `"medical"`: `medical bay`, `implant room`, `bioaugmentation`
>      - `"supply"`: `armory`, `depot`, `parts bay`, `storage`, `fabrication`, `workshop`, `vehicle bay`
>      - `"corridor"`: `corridor`, `cargo lift`, `new chamber`, `well`, `canteen`, `game room`, `smuggler's den`
>      - `"goal"`: `ai core`, `officer's quarters`, `vault`, `prison`
>
> 2. **Build `resolve_procedural_challenge` in `src/Mission.py`:**
>    - Create a `CHALLENGE_ARCHETYPES` dictionary in `src/Mission.py` with 8 reusable challenge templates (`"LOCKED_PORTAL"`, `"SECURITY_GRID"`, `"INTEL_CONSOLE"`, `"HAZARD_LEAK"`, `"MEDICAL_CACHE"`, `"CYBER_IMPLANT_BAY"`, `"SUPPLY_LOCKER"`, `"CAPTIVE_CELL"`).
>    - Each archetype defines:
>      - `approaches`: ordered list of dicts supporting item bypass (`{"item": "cutter"}`), robot bypass (`{"robot": "hackbot"}`), or skill/stat checks (`{"stat": "intelligence", "skill": "Hacking", "diff": 0}`).
>      - `reward`: dict specifying reward (`"points"`, `"heal"`, `"found_item"`, `"shortcut"` which reduces `rooms_to_goal` by 1, or `"stat_boost"`).
>      - `penalty`: dict specifying failure effect (`"detour"` which adds +2 to `rooms_to_goal`, `"damage_all"`, or `"demoralize"`).
>    - Write a single `async def resolve_procedural_challenge(team, archetype_key, screen, font)` function that processes any archetype from `CHALLENGE_ARCHETYPES`.
>
> 3. **Procedural Room Generation & `MissionOrders` Integration in `src/Mission.py`:**
>    - Wire `team[0].mission.get("options")` into `Mission.py`:
>      - `"focus"`: `rooms_to_goal = random.randint(4, 5)` and lower encounter rate with `"supply"` rooms.
>      - `"flex"`: `rooms_to_goal = random.randint(6, 8)` and higher weight for `"supply"` and `"tech"` rooms that grant items and bonus mission points.
>    - Wire `team[0].mission.get("means")` (`"pacifist"` / `"just"`): in `Character.choose_ranged_weapon()` and `choose_melee_weapon()`, prefer non-lethal weapons (`stunner`, `stun baton`) when `means == "pacifist"` if the character carries one.
>    - Build room events dynamically from all non-goal Pirate locations using their tags so all 31 Pirate rooms appear across playthroughs.
>
> 4. **Verify with Tests:**
>    - Add unit tests in `gametests.py` for `resolve_procedural_challenge` (testing item bypass, skill pass, and fallback penalty) and location tag loading. Run `.venv/bin/python -m unittest discover -v`.

---

## PHASE 5: Loop 2+ "Derelict Vessel & Klackon" Theatre (`Location.py`, `Character.py`, `Event.py`, `Mission.py`)
**Why Fifth:** Uses the Tag & Challenge engine from Phase 4 to light up all 25 Derelict rooms and the Klackon enemy portraits on Loop 2+.

### Agent Prompt for Phase 5:
> Please read and execute **Phase 5** of `ROADMAP.md`:
>
> 1. **Add Derelict Locations in `src/Location.py`:**
>    - Define `DERELICT_LOCATION_ATTRIBUTES` for all 26 `.jpg` files in `locations/derelict/` (`analysisbay`, `armory`, `barracks1`, `barracks2`, `biolab`, `bridge`, `captainquarters`, `corridor`, `empty`, `engineering`, `fabrication`, `generator`, `implant`, `medbay`, `navigation`, `orechamber`, `parts`, `quarters1`, `quarters2`, `robotshop`, `s-corridor`, `shipsweapons`, `shuttlebay`, `suitroom`, `throneroom`, `warpchamber`) with atmospheric descriptions, connections, and room tags (`"combat"`, `"tech"`, `"medical"`, `"supply"`, `"corridor"`, `"goal"`).
>    - Add `load_derelict_locations()`.
>
> 2. **Add Klackon Enemies & Difficulty Scaling in `src/Character.py` and `src/Event.py`:**
>    - In `Character.__init__`, support `type == "klackon"`, loading a random portrait from `portraits/klackons/klackon{1..3}.jpg`, setting `self.occupation = "klackon"`, and giving them high melee/strength/resilience stats and natural weapons/armor. Make `is_pirate()` (or a generalized `is_enemy()`) return `True` for both `"pirate"` and `"klackon"` so `Battle.py` renders them on the right side in red without breaking any existing battle code.
>    - Add a `mission_enemies(num_enemies, items, theatre="pirates", loop=1)` function in `src/Event.py` that spawns Pirates for `"pirates"` and Klackons for `"derelict"`, and scales enemy stats/gear tiers gently for `loop >= 2`.
>
> 3. **Procedural Mission Contracts by Loop in `src/Utils.py`, `src/MissionOrders.py`, and `src/Mission.py`:**
>    - On odd loops (`loop % 2 == 1`), set the mission theatre to `"pirates"`. On even loops (`loop % 2 == 0`), set the mission theatre to `"derelict"`.
>    - Add `DERELICT_MISSION_GOALS` in `src/Utils.py` targeting Derelict goal rooms (`throneroom`, `warpchamber`, `biolab`, `bridge`) with procedural artifact/specimen/broodmother names, and wire `MissionOrders.py` and `Mission.py` to select the goal list and location loader matching the current `loop`'s theatre.
>
> 4. **Verify with Tests:**
>    - Add unit tests in `gametests.py` verifying `load_derelict_locations()`, `Character(1, "klackon")` creation, and `mission_enemies()` scaling. Run `.venv/bin/python -m unittest discover -v`.