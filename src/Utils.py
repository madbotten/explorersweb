# utils.py -- common stuffs and things used by more than one other file
import os
import sys
import pickle
import random
import pygame
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
    ("MISSION: The team must neutralize all the pirates at the mission point.", [], [], [30]),
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

def load_sound(filename):
    sound_path = resource_path(filename)
    if os.path.exists(sound_path):
        pygame.mixer.init()
        this_sound = pygame.mixer.Sound(sound_path)
        this_sound.set_volume(0.5)
        return this_sound
    else:
        print("sound file not found.")

LASER_SOUND = load_sound("music/laser.mp3")
PISTOL_SOUND = load_sound("music/pistol.mp3")
MELEE_SOUND = load_sound("music/melee.mp3")
LAUNCHER_SOUND = load_sound("music/launcher.mp3")

def play_weapon_sound(weapon):
    energy_weapons = {"laser pistol", "laser rifle"}
    sonic_weapons = {"blaster rifle", "stunner"}
    slashing_weapons = {"slicer", "stun baton"}
    piercing_weapons = {"carbine", "pistol", "magnum"}
    concussion_weapons = {"launcher"}

    if weapon in concussion_weapons:
        LAUNCHER_SOUND.play()
    elif weapon in energy_weapons:
        LASER_SOUND.play()
    elif weapon in sonic_weapons:
        LASER_SOUND.play()
    elif weapon in piercing_weapons:
        PISTOL_SOUND.play()
    elif weapon in slashing_weapons:
        MELEE_SOUND.play()

def play_background_music(path, pygame):
    background_music_path = resource_path(path)
    if os.path.exists(background_music_path):
        pygame.mixer.music.load(background_music_path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)  # -1 means the music will loop indefinitely
    else:
        print("Background music file not found.")

def play_battle_music(pygame):
    background_music_path = resource_path("music/fight3.mp3")
    if os.path.exists(background_music_path):
        pygame.mixer.music.load(background_music_path)
        pygame.mixer.music.set_volume(0.6)
        pygame.mixer.music.play(-1)  # -1 means the music will loop indefinitely
    else:
        print("Background music file not found.")

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
    return all(character.stats.get("lifelevel", 0) <= 0 for character in team)

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
        member.stats["lifelevel"] > 0 and member.type == "team" and member.stats["lifelevel"] < 0.75 * member.max_lifelevel()
        for member in team
    )

def heal_team_by(team, amount):
    bio_team = [m for m in team if m.type == "team"]
    for member in bio_team:
        if member.stats["lifelevel"] > 0:  # Only heal alive members
            member.stats["lifelevel"] = min(
                member.max_lifelevel(),
                member.stats["lifelevel"] + amount
            )


class EventContext:
    def __init__(self, pre_description, post_description, num_enemies, stat_name, skill_name, location,
                 calculate_outcome, all_items):
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



