# utils.py -- common stuffs and things used by more than one other file
import os
import sys
import pickle
import shutil
import random
import pygame
try:
    import pygame.mixer
    import pygame.font
except Exception:
    pass
from pathlib import Path

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
DARK_CYAN = (15, 33, 32)

SCREEN_WIDTH = 1500 # 1600
SCREEN_HEIGHT = 900 # 1000

# description, required item, required people, required kills
# locations: vault, officer's quarters, officer's quarters, ai core
MISSION_GOALS = [
    ("MISSION: The team must obtain a Trilisk artifact known to be in pirate possession at the mission point.", ["valneeth"], [], []),
    ("MISSION: The team must capture the pirate named Jalorith known to be at the mission point.", [], ["Jalorith"], []),
    ("MISSION: The team must neutralize all pirate officers at the mission point.", [], [], [6]),
    ("MISSION: The team must discover the location of a secret base called Yoria.", ["datachip"], [], []),
]

def team_alive(team):
    for member in team:
        if member.is_alive():
            return True
    return False

def random_alive_member(team):
    if team_alive(team):
        while True:
            member = random.choice(team)
            if member.is_alive():
                return member

    else:
        return None

def num_items_on_team(team, item_name):
    count = 0
    for member in team:
        for item in member.equipment:
            if item.name == item_name:
                count += 1
    return count

def color_for_stat(value):
    if (value < 50):
        return RED
    elif (value > 75):
        return GREEN
    else:
        return CYAN

def color_for_skill(value):
    if (value > 75):
        return GREEN
    else:
        return CYAN

def resource_path(relative_path):
    """Get the absolute path to a resource, handles both dev and PyInstaller .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_all_files_in_directory3(directory: str):
    """Get a dictionary of all files in a directory with their resolved paths."""
    # Ensure the input directory is resolved to an absolute Path object
    abs_directory = Path(directory).resolve()
    files = {}
    for file_path in abs_directory.rglob('*'):  # Recursively iterate over all files
        if file_path.is_file():  # Only include files
            rel_path = file_path.relative_to(abs_directory)  # Relative path
            files[str(rel_path)] = str(file_path)  # Store paths as strings
    return files

def save_team(filename, team):
    team_data = [character.to_dict() for character in team]
    with open(filename, "wb") as team_file:
        pickle.dump(team_data, team_file)
    return team_data

def load_team(filename):
    with open(filename, "rb") as team_file:
        return pickle.load(team_file)

# ---------------------------------------------------------------------------
# Named save/load system — saves/{team_name}/loop_{L}_{stage_name}_stage.pkl
# ---------------------------------------------------------------------------
SAVES_DIR = "saves"

# Human-readable stage names used in save filenames
STAGE_NAMES = {
    1: "choose",
    2: "orders",
    3: "equip",
    4: "voyage",
    5: "mission",
    6: "return",
}
STAGE_NUMBERS = {v: k for k, v in STAGE_NAMES.items()}

def save_path(team_name: str, loop: int, stage: int) -> str:
    """Return the path for saves/{team_name}/loop_{loop}_{name}_stage.pkl."""
    folder = team_name.replace(" ", "_")
    name   = STAGE_NAMES.get(stage, f"stage{stage}")
    return os.path.join(SAVES_DIR, folder, f"loop_{loop}_{name}_stage.pkl")

def save_team_named(team_name: str, loop: int, stage: int, team: list) -> list:
    """Save team to the named path; create the directory if needed. Returns team_data."""
    path = save_path(team_name, loop, stage)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    team_data = [character.to_dict() for character in team]
    with open(path, "wb") as f:
        pickle.dump(team_data, f)
    return team_data

def load_team_named(team_name: str, loop: int, stage: int) -> list:
    """Load from saves/{team_name}/loop_{loop}_{name}_stage.pkl."""
    path = save_path(team_name, loop, stage)
    with open(path, "rb") as f:
        return pickle.load(f)

def latest_saves_for_team(team_name: str) -> dict:
    """Return {stage_int: highest_loop} for every stage that has a save file."""
    folder   = team_name.replace(" ", "_")
    team_dir = os.path.join(SAVES_DIR, folder)
    result   = {}
    if not os.path.isdir(team_dir):
        return result
    for fname in os.listdir(team_dir):
        if not fname.endswith(".pkl"):
            continue
        stem  = fname[:-4]   # strip .pkl
        parts = stem.split("_")
        # Pattern: loop_{L}_{name}_stage  →  ['loop', L, name, 'stage']
        if len(parts) == 4 and parts[0] == "loop" and parts[3] == "stage":
            try:
                lp = int(parts[1])
                st = STAGE_NUMBERS.get(parts[2])
                if st is not None:
                    if st not in result or lp > result[st]:
                        result[st] = lp
            except ValueError:
                pass
    return result

def list_teams() -> list:
    """Return all team-name subfolders found under saves/."""
    if not os.path.isdir(SAVES_DIR):
        return []
    return [
        d for d in os.listdir(SAVES_DIR)
        if os.path.isdir(os.path.join(SAVES_DIR, d)) and not d.startswith(".")
    ]

def delete_team(team_name: str) -> None:
    """Permanently delete all save files for the given team."""
    folder   = team_name.replace(" ", "_")
    team_dir = os.path.join(SAVES_DIR, folder)
    if os.path.isdir(team_dir):
        shutil.rmtree(team_dir)

_SOUND_CACHE = {}

def load_sound(filename):
    try:
        if not hasattr(pygame, "mixer"):
            return None
        ogg_path = filename.rsplit(".", 1)[0] + ".ogg"
        if os.path.exists(resource_path(ogg_path)):
            filename = ogg_path
        sound_path = resource_path(filename)
        if sound_path in _SOUND_CACHE:
            return _SOUND_CACHE[sound_path]
        if os.path.exists(sound_path):
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            this_sound = pygame.mixer.Sound(sound_path)
            this_sound.set_volume(0.5)
            _SOUND_CACHE[sound_path] = this_sound
            return this_sound
        else:
            print(f"sound file not found: {sound_path}")
    except Exception as e:
        print(f"Warning: could not load sound {filename}: {e}")
    return None

def play_weapon_sound(weapon):
    energy_weapons = {"laser pistol", "laser rifle"}
    sonic_weapons = {"blaster rifle", "stunner"}
    slashing_weapons = {"slicer", "stun baton"}
    piercing_weapons = {"carbine", "pistol", "magnum"}
    concussion_weapons = {"launcher"}

    sound = None
    if weapon in concussion_weapons:
        sound = load_sound("music/launcher.ogg")
    elif weapon in energy_weapons or weapon in sonic_weapons:
        sound = load_sound("music/laser.ogg")
    elif weapon in piercing_weapons:
        sound = load_sound("music/pistol.ogg")
    elif weapon in slashing_weapons:
        sound = load_sound("music/melee.ogg")

    if sound:
        try:
            sound.play()
        except Exception as e:
            print(f"Warning: could not play sound: {e}")

def play_background_music(path, pygame):
    try:
        if not hasattr(pygame, "mixer"):
            return
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        ogg_path = path.rsplit(".", 1)[0] + ".ogg"
        if os.path.exists(resource_path(ogg_path)):
            path = ogg_path
        background_music_path = resource_path(path)
        if os.path.exists(background_music_path):
            pygame.mixer.music.load(background_music_path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)  # -1 means the music will loop indefinitely
        else:
            print("Background music file not found.")
    except Exception as e:
        print(f"Warning: could not load background music {path}: {e}")

def play_battle_music(pygame):
    try:
        if not hasattr(pygame, "mixer"):
            return
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        background_music_path = resource_path("music/fight3.ogg")
        if not os.path.exists(background_music_path):
            background_music_path = resource_path("music/fight3.mp3")
        if os.path.exists(background_music_path):
            pygame.mixer.music.load(background_music_path)
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)  # -1 means the music will loop indefinitely
        else:
            print("Background music file not found.")
    except Exception as e:
        print(f"Warning: could not load battle music: {e}")

# positive difficulty modifiers are easier
def roll_string(roll, skill_name, stat_name, difficulty_modifier):
    result = f"Roll: {roll} vs "
    if skill_name is not None and stat_name is not None:
        result += f"{skill_name} and {stat_name} "
    elif skill_name is not None:
        result += f"{skill_name} "
    elif stat_name is not None:
        result += f"{stat_name} "
    if difficulty_modifier < 0:
        result += f" (difficulty {abs(difficulty_modifier)})"
    elif difficulty_modifier > 0:
        result += f" (difficulty -{difficulty_modifier})"
    return result

def determine_best_team_member(team, stat_name, skill_name):
    def score(member):
        stat_score = member.get_effective_stat_level(stat_name)
        # learning=False: we're only comparing, not performing the action
        skill_score = member.get_effective_skill_level(skill_name, learning=False)
        return stat_score + skill_score

    best_score = max(score(member) for member in team if member)

    for member in team:
        if score(member) > 0 and score(member) == best_score:
            return member

    return None

def team_size(team):
    """ Calculates combat team size including ranged bots and melee bots"""
    team_size = 0
    for member in team:
        team_size += 1
    return team_size

def clear_team_last_action(team):
    for member in team:
        member.last_action = None

def team_dead(team):
    return all(not character.is_alive() for character in team)

def add_team_mission_param(team, key, param):
    for member in team:
        member.mission[key] = param

def team_mission_success(team):
    for member in team:
        member.mission_points += 100

def team_has_item(team, item_name):
    for member in team:
        if member.has_item(item_name):
            return True
    return False


# Tier ordering for upgrade logic
_TIER_ORDER = {"C": 0, "B": 1, "A": 2, "S": 3}
_TIER_UPGRADE_CHANCE = {"C": 1.0, "B": 0.5, "A": 0.25}

def get_needed_item(team, all_items):
    """Analyse the team and return (recipient, Item) for one useful unkeyed item,
    or None if nothing can be found.

    On each call a 50/50 mode is chosen:
      Mode A (gap-first): per character, try to fill a gear gap; fall back to
                          a tier upgrade if no gap is found.
      Mode B (upgrade-first): per character, attempt a tier upgrade only.

    Characters are examined in random order. Robots are never recipients.
    """
    from Item import item_base_name, item_class, upgrade_item_class

    candidates = [m for m in team if m.is_alive() and not m.is_robot()]
    random.shuffle(candidates)

    gap_first = random.random() < 0.5

    def _gap_item(member):
        """Return the item key for the first gear gap found in all_items, or None."""
        gaps = []
        if not member.has_ranged_weapon():
            gaps.append("laser pistol C")
        if not member.has_melee_weapon():
            gaps.append("slicer C")
        if member.has_skill("Exoskeleton Systems") and \
                not member.has_item("exoskeleton") and \
                not member.has_item("powered armor"):
            gaps.append("exoskeleton C")
        if member.has_skill("Medicine") and not member.has_item("medikit"):
            gaps.append("medikit C")
        if member.has_skill("Stealth") and not member.has_item("stealth orb"):
            gaps.append("stealth orb C")
        if not any(i.type == "armor" for i in member.equipment):
            gaps.append("veer suit C")
        for key in gaps:
            if key in all_items:
                return key
        return gaps[0] if gaps else None

    def _upgrade_item(member):
        """Return (old_item, new_item) for the best upgrade opportunity, or None."""
        upgradeable = [
            i for i in member.equipment
            if i.type in ("weapon", "armor") and item_class(i.name) in _TIER_UPGRADE_CHANCE
        ]
        if not upgradeable:
            return None
        # Find best current tier across the member's gear
        best_tier = max(upgradeable, key=lambda i: _TIER_ORDER[item_class(i.name)])
        tier = item_class(best_tier.name)
        if random.random() > _TIER_UPGRADE_CHANCE[tier]:
            return None  # Probability check failed
        # Among items at that tier, pick the highest-effect one
        at_tier = [i for i in upgradeable if item_class(i.name) == tier]
        old_item = max(at_tier, key=lambda i: i.effect)
        new_item = upgrade_item_class(old_item, all_items)
        if new_item is None:
            return None
        return old_item, new_item

    for member in candidates:
        if gap_first:
            gap_key = _gap_item(member)
            if gap_key and gap_key in all_items:
                return member, all_items[gap_key]
            result = _upgrade_item(member)
            if result:
                return member, result[1]
        else:
            result = _upgrade_item(member)
            if result:
                return member, result[1]

    return None

# Returns true if anyone on team can make skill check against skill_name
# positive difficulty modifiers are easier
def team_skill_check(team, skill_name, difficulty_modifier):
    for member in team:
        roll = random.randint(1, 100)
        if member.skill_check(roll, skill_name, difficulty_modifier):
            return True
    return False

def team_needs_heal(team):
    return any(
        member.current_health > 0 and member.type == "team"
        and member.current_health < 0.75 * member.stats["max_health"]
        for member in team
    )

def heal_team_by(team, amount):
    bio_team = [m for m in team if m.type == "team"]
    for member in bio_team:
        if member.current_health > 0:  # Only heal alive members
            member.current_health = min(
                member.stats["max_health"],   # cap at max-HP stat
                member.current_health + amount
            )
            # Healing raises morale toward the current health ratio
            member.morale_from_health()


class EventContext:
    def __init__(self, pre_description, post_description, num_enemies, stat_name, skill_name, location,
                 calculate_outcome, all_items, name=None, is_goal=False):
        self.name = name
        self.is_goal = is_goal
        self.num_enemies = num_enemies
        self.location = location
        self.stat_name = stat_name
        self.skill_name = skill_name
        self.pre_description = pre_description
        self.post_description = post_description
        self.calculate_outcome = calculate_outcome
        self.all_items = all_items
        self.battle = None
        self.team = None
        self.screen = None
        self.font = None
        self.background = None
        self.location_font = None
        self.enemies = None
        self.brazen_bonus = 0

    def add_run_params(self, team, screen, font, background, location_font):
        self.team = team
        self.screen = screen
        self.font = font
        self.background = background
        self.location_font = location_font



