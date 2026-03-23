from itertools import filterfalse
from typing import Any

import pygame
import random
import os
import copy

from Battle import BattleAction
from Utils import *
from Item import *

# Directory path for character portraits
portraits_dir = "portraits/"
TOP_EDGE = 30
CHARACTER_BOX_WIDTH = 90
CHARACTER_BOX_HEIGHT = 100

class Character:
    def __init__(self, index, type, width=CHARACTER_BOX_WIDTH, height=CHARACTER_BOX_HEIGHT):
        self.type = type
        print("new character type is " + type)
        if type == "pirate":
            self.name = "pirate" + str(index)
            self.occupation = "pirate"
        if type == "team":
            self.name = self.make_name()
            self.occupation = random.choice(self.occupations)
        self.index = index
        self.rect = pygame.Rect(22, TOP_EDGE, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
        self.stats = self.generate_random_stats()
        self.stats["offense"] = round((self.stats["coordination"] + self.stats["courage"]) / 2)
        self.stats["defense"] = round((self.stats["coordination"] + self.stats["strength"]) / 2)
        self.stats["deception"] = round((self.stats["courage"] + self.stats["charisma"]) / 2)
        self.stats["evasion"] = round((self.stats["intelligence"] + self.stats["coordination"]) / 2)
        self.stats["analyze"] = round((self.stats["intelligence"] + self.stats["willpower"]) / 2)
        self.stats["lifelevel"] = self.stats["strength"] + self.stats["willpower"]
        self.stats["movement"] = self.stats["strength"] + self.stats["willpower"] + self.stats["coordination"]
        self.stats["meleecombat"] = self.stats["evasion"] + self.stats["strength"]
        self.stats["surprise"] = self.stats["deception"] + self.stats["evasion"]
        self.stats["leadership"] = self.stats["intelligence"] + self.stats["charisma"] + self.stats["courage"]

        self.homeworld = random.choice(self.homeworlds)
        self.event = random.choice(self.events)
        self.goal = random.choice(self.goals)
        # "mission_index", "methods", "means", "options"
        self.mission = {}
        if type != "robot":
            self.history = f"{self.name}, a {self.occupation} from {self.homeworld}, {self.event}. They now aim to {self.goal}."
        else:
            self.history = "A robot."

        # A list of Item objects
        self.equipment = []
        self.mission_points = 0
        # for robots
        self.max_life = 0
        # Reference to the team list this character belongs to (set externally)
        self.team = None

        self.morale = 100
        self.current_health = self.stats["lifelevel"]

        self.vetted = False
        self.psychotic = False
        self.traitor = False

        if type != "robot":
            if random.randint(1, 100) < 25:
                self.history += "\nPassed a truth test against stated goals."
                self.traitor = False
            if random.randint(1, 100) < 35:
                self.history += "\nPassed rigorous testing of stated skills."
                self.vetted = True
            if random.randint(1, 100) < 15:
                self.history += "\nFully vetted by the Space Force."
                self.traitor = False
                self.vetted = True
            if random.randint(1, 100) < 5:
                self.history += "\nPresented recommendation letter from Admiral " + self.make_name() + "."
                self.traitor = False
                self.vetted = True
                self.psychotic = False
            if random.randint(1, 100) < 75:
                self.history += "\nPsych analysis: Passed."
                self.psychotic = False
            elif random.randint(1, 100) < 50:
                self.history += "\nPsych analysis: Borderline."
                roll = random.randint(1, 100)
                if roll < 10:
                    self.psychotic = True
            elif random.randint(1, 100) < 50:
                self.history += "\nPsych analysis: Indeterminate."
                roll = random.randint(1, 100)
                if roll < 15:
                    self.psychotic = True
            else:
                self.history += "\nPsych analysis: Failed."
                roll = random.randint(1, 100)
                if roll < 25:
                    self.psychotic = True

            self.history += "\n" + random.choice(self.personality_types)

        # Generate and assign major skills
        self.skills = self.assign_skills(self.stats["intelligence"], self.stats["willpower"])

        if type != "robot":
          if type == "team":
            portrait_path = resource_path(f"portraits/character{index}.jpg")
          elif type == "pirate":
            portrait_path = resource_path(f"portraits/pirate{index}.jpg")
          try:
            self.portrait = pygame.image.load(portrait_path)  # Load the portrait image
            self.portrait = pygame.transform.scale(self.portrait, (width, height))
          except pygame.error:
            print(f"Failed to load image")

        self.location = (-1, -1)
        self.battle_index = 0
        self.last_action = BattleAction.NONE

    def is_combative_personality(self):
        if any(sub in self.history for sub in ("narcissist", "aggressive")) or self.psychotic:
            return True

    def is_pirate(self):
       return self.occupation == "pirate"

    def get_health_ratio(self):
        # SHOULD this be get_effective_stat("livelevel) ?
        return self.stats["lifelevel"] / self.max_lifelevel()

    def get_morale_ratio(self):
        return self.morale / 100

    def max_lifelevel(self):
        base_lifeforce = self.stats["strength"] + self.stats["willpower"]
        if self.has_item("stimulant"):
            base_lifeforce += 50
        return base_lifeforce

    def get_lifelevel(self):
        return self.stats["lifelevel"]

    def is_alive(self):
        return self.stats["lifelevel"] > 0

    def demoralize(self, amount):
        self.morale -= amount
        if self.morale <= 0:
            self.morale = 0

    def encourage(self, amount):
        self.morale += amount
        if self.morale > 100:
            self.morale = 100

    # Apply the pain and return True if they died
    def hurt(self, damage, damage_type):
        # Some items protect from damage
        if self.has_item("holofier") and random.randint(1, 100) < 33:
            return False
        if self.has_item("veer suit") and damage_type == "impact":
            damage = damage - 8
        if self.has_item("power shield") and damage_type == "energy":
            damage = damage - 8
        if self.has_item("powered armor"):
            damage = damage - 12

        # always do at least 1 point on hit
        damage = max(1, damage)

        # being wounded also demoralizes
        self.morale = max(0, self.morale - damage)

        self.stats["lifelevel"] = max(0, self.stats["lifelevel"] - damage)
        if self.stats["lifelevel"] <= 0:
            return True
        return False

    # Make a skill check which degrades with injury
    # positive difficulty modifiers are easier
    def skill_check(self, roll, skill_name, difficulty_modifier):
        if skill_name is None:
            return True
        ability = self.get_effective_skill_level(skill_name)
        health = self.get_morale_ratio()
        if roll < (ability * health) + difficulty_modifier:
            return True
        return False

   # positive difficulty modifiers are easier
    def stat_and_skill_check(self, roll, stat_name, skill_name, difficulty_modifier):
        if skill_name is None:
            return self.stat_check(roll, stat_name, difficulty_modifier)
        if stat_name is None:
            return self.skill_check(roll, skill_name, difficulty_modifier)

        ability = self.get_effective_skill_level(skill_name)
        ability += self.get_effective_stat_level(stat_name)
        health = self.get_morale_ratio()
        if roll < (ability * health) + difficulty_modifier:
            return True
        return False

    # positive difficulty modifiers are easier
    def stat_check(self, roll, stat_name, difficulty_modifier):
        if stat_name is None:
            return True
        print("stat check for " + stat_name + " with difficulty " + str(difficulty_modifier))
        if self.stats["lifelevel"] < 0:
            self.stats["lifelevel"] = 0
        ability = self.get_effective_stat_level(stat_name)
        print("Ability is " + str(ability))
        health = self.get_health_ratio()
        print("Health is " + health)
        print("Roll is " + str(roll))
        if roll < (ability * health) + difficulty_modifier:
            return True
        return False

    def increase_skill(self, skill_name, amount):
        if skill_name is None:
            return
        if self.has_skill(skill_name):
            self.skills[skill_name] += amount
        else: self.skills[skill_name] = amount + 3

    def decrease_skill(self, skill_name, amount):
        if skill_name is None:
            return
        if self.has_skill(skill_name):
            self.skills[skill_name] -= amount
            if self.skills[skill_name] <= 0:
                self.skills[skill_name] = 0

    def increase_stat(self, stat_name, amount):
        if stat_name is None:
            return
        self.stats[stat_name] += amount

    def decrease_stat(self, stat_name, amount):
        if stat_name is None:
            return
        self.stats[stat_name] -= amount
        if self.stats[stat_name] <= 15:
            self.skills[stat_name] = 15

    # If encumbered and team has no mulebot, evasion will suffer
    def is_encumbered(self):
        if self.team and any(m.occupation == "mulebot" for m in self.team):
            return False
        total_mass = self.get_carried_mass()
        return total_mass > (self.get_effective_stat_level("strength") / 2)

    def get_carried_mass(self):
       total_mass = 0
       for item in self.equipment:
           total_mass += item.mass
       return total_mass

    # Effective stat level without health ratio (applied in skill check)
    def get_effective_skill_level(self, skill_name):
        if skill_name is None:
            return 1
        total = 0
        if "Hacking" == skill_name:
            if self.has_item("hackerbot"):
                total += 30
        if "Ships Systems" == skill_name or "Robot Repair" == skill_name:
            if self.has_item("mechbot"):
                total += 40
            if self.has_item("techbot"):
                total += 40
        if "Artifact Analysis" == skill_name:
            if self.has_item("scanner"):
                total += 40
        if "Medicine" == skill_name:
            if self.has_item("medibot"):
                total += 40

        if self.has_skill(skill_name):
            total += self.skills[skill_name]
        return total

    # Effective stat level without health ratio (applied in skill check)
    def get_effective_stat_level(self, stat_name):
        if stat_name is None:
            return 0
        total = self.stats[stat_name]
        if "strength" == stat_name:
            if self.has_item("exoskeleton"):
                total += 50
        if "evasion" == stat_name:
            if self.is_encumbered():
                total -= 20
        if "analyze" == stat_name:
            if self.has_item("scanner"):
                total += 30
        return total

    # Effective evasion with health ratio
    def get_effective_combat_evasion(self):
        intelligence = self.get_effective_stat_level("intelligence")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        evasion = round((intelligence + coordination) / 2)
        evasion += military_science / 10
        if self.is_encumbered():
            evasion = max(0, evasion - 50)
        return max(1, evasion * self.get_health_ratio())

    # Effective offense with health ratio
    def get_effective_combat_offense(self):
        courage = self.get_effective_stat_level("courage")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        offense = (courage + coordination) / 2
        offense += (military_science / 10)
        if self.has_item("offense implant"):
            offense += 50
        return max(1, offense * self.get_health_ratio())

    # Effective defense with health ratio
    def get_effective_combat_defense(self):
        strength = self.get_effective_stat_level("strength")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        defense = (strength + coordination) / 2
        defense = defense + (military_science / 10)
        if self.has_item("exoskeleton") or self.has_item("powered armor"):
            if self.has_skill("Exoskeleton Systems"):
                defense += self.get_effective_skill_level("Exoskeleton Systems") / 2
        return max(1, defense * self.get_health_ratio())

    # Effective combat melee with health ratio
    def get_effective_combat_melee(self):
        strength = self.get_effective_stat_level("strength")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        evasion = (strength + coordination) / 2
        evasion = evasion + (military_science / 10)
        if self.is_encumbered():
            evasion = max(0, evasion - 50)
        if self.has_item("exoskeleton") or self.has_item("powered armor"):
            if self.has_skill("Exoskeleton Systems"):
                evasion += self.get_effective_skill_level("Exoskeleton Systems") / 4
        strength = self.get_effective_stat_level("strength")
        return max(1, (evasion + strength) * self.get_health_ratio())

    def has_ranged_weapon(self):
        return (self.has_item("laser pistol")
                or self.has_item("pistol")
                or self.has_item("laser rifle")
                or self.has_item("blaster rifle")
                or self.has_item("carbine")
                or self.has_item("launcher")
                )

    def has_melee_weapon(self):
        return self.has_item("slicer")

    def has_item(self, item_name):
        for item in self.equipment:
            if item.name == item_name:
                return True
        return False

    def has_skill(self, skill_name):
        if skill_name is None:
            return False
        if skill_name in self.skills:
              return True
        return False

    def add_item(self, item:Item):
        """Adds an Item object to the character's equipment."""
        if isinstance(item, Item):
            self.equipment.append(item.copy())
        else:
            raise ValueError("Only Item instances can be added to equipment.")

    def remove_item(self, item_name):
        for i, item in enumerate(self.equipment):
            if item.name == item_name:
                del self.equipment[i]
                return

    def remove_random_item(self):
        random_item = random.choice(self.equipment)
        self.remove_item(random_item.name)

    def list_equipment(self):
        """Returns a list of equipment names."""
        return [item.name for item in self.equipment]

    def assign_skills(self, intelligence, willpower):
        # Randomly select 3 to 6 unique skills from the list
        num_skills = random.randint(3, 6)
        if intelligence > 75:
            num_skills += 1
        elif intelligence < 50:
            num_skills -= 1
        if willpower > 75:
            num_skills += 1
        elif willpower < 50:
            num_skills -= 1
        selected_skills = random.sample(self.possible_skills, num_skills)

        # Assign each skill a random proficiency level (1 to 100)
        skills_dict = {skill: self.bell_curve_stat() for skill in selected_skills}
        return skills_dict

    def get_weapon_count(self):
        total = 0
        for item in self.equipment:
            if item.type == "weapon":
                total += 1
        return total

    def get_armor_count(self):
        total = 0
        for item in self.equipment:
            if item.type == "armor":
                total += 1
        return total

    def __repr__(self):
        return f"Character(name={self.name}, stats={self.stats}, vetted={self.vetted}, equipment={self.equipment})"

    # Prefixes and suffixes for sci-fi names
    # List of possible sci-fi skills
    possible_skills = [
        "Piloting", "Hacking", "Negotiation", "Martial Arts", "Sharpshooting", "Stealth", "Medicine",
        "Military Science", "Explosives", "Cybernetics", "Xenobiology", "Survival",
        "Diplomacy", "Navigation", "Interrogation", "Robot Repair", "Social Engineering",
        "Ships Systems", "Espionage", "Fabrication", "Instruction",
        "Energy Weapons", "Physics", "Projectile Weapons", "Artifact Analysis", "Squad Tactics", "Mech Combat",
        "Exoskeleton Systems", "Resource Extraction", "Detection"
    ]
    prefixes = ["Agn", "Abb", "Bann", "Bor", "Cer", "Can", "Dan", "Drax", "Eol", "End", "Fet", "Gal", "Han", "Ill",
                "Jak", "Kalor", "Kor", "Lan",
                "Mer", "Nar", "Nol", "Orr", "Pret", "Quon", "Rev", "Ruxx", "Sor", "Tal", "Tulon", "Uol", "Val", "Wen",
                "Xan", "Xen", "Zar", "Zior"]
    suffixes = ["aa", "aark", "an", "ar", "ear", "en", "ett", "ex", "ian", "ion", "ius", "ith", "ix", "oat", "on", "or",
                "os", "uan", "ul", "un", "ux"]
    occupations = ["pilot", "engineer", "bounty hunter", "cyberneticist", "mechanic", "diplomat", "scientist",
                   "smuggler", "android", "hacker", "ex-pirate", "military officer", "mercenary", "ex-special forces",
                   "artifact hunter"]
    homeworlds = ["Epsilon Prime", "Aurora-7", "Nebulon VI", "Kestrel's Reach", "Galatea Colony", "Seren Station",
                  "Vega-4", "Orbis Ring", "Zypheron", "Mira Core", "Xentari-3", "Theraxis-2", "Unknown", "New Lyra",]
    events = [
        "discovered a hidden alien artifact", "barely escaped a collapsing star",
        "led a rebellion against the Galactic Syndicate", "worked as an ambassador to the Gorin Collective",
        "was stranded on an uncharted moon", "made first contact with an unknown species",
        "escaped an attack from space marauders", "called out an alien attack weeks beforehand",
        "activated an ancient AI", "stumbled upon a secret research facility", "terraformed a small moon",
        "decoded a mysterious alien transmission", "was betrayed by a close ally",
        "disarmed a mutiny aboard the Vigilant Resolve", "extracted pirate intel under deep cover",
        "saved a crew from a reactor meltdown",
    ]
    goals = [
        "find a way to restore peace to their war-torn world",
        "uncover the secrets of an ancient civilization",
        "seek revenge against those who wronged them",
        "bring about peace between aggressive alien species",
        "reclaim their lost honor",
        "find the fabled planet of Exile",
        "bring unity to the star colonies of Epsilon sector",
        "master the art of quantum engineering",
        "construct a superior type of star drive",
        "rescue their abducted sibling",
        "discover the truth behind the galactic council's hidden agendas",
        "become the galaxy's most feared bounty hunter",
        "win the Space Force's highest honors",
        "defeat space pirates everywhere",
        "remove the threat of pirates from the colonies",
        "ensure the safety of the core worlds",
        "prove the existence of a hidden alien empire",
        "establish new standard ai protocols in Core World society",
    ]
    personality_types = [
        "Qualities: aggressive, extrovert",
        "Qualities: aggressive, narcissist",
        "Qualities: calm, introvert",
        "Qualities: analytical, skeptic",
        "Qualities: empathetic, diplomat",
        "Qualities: assertive, leader",
        "Qualities: patient, tolerant",
        "Qualities: loyal, idealist",
        "Qualities: impulsive, adventurer",
        "Qualities: practical, realist",
        "Qualities: reserved, strategist",
        "Qualities: charismatic, visionary",
        "Qualities: skeptical, realist",
        "Qualities: optimistic, motivator",
        "Qualities: meticulous, perfectionist",
        "Qualities: adaptable, explorer",
        "Qualities: direct, pragmatist",
        "Qualities: imaginative, dreamer",
        "Qualities: responsible, caregiver",
        "Qualities: decisive, commander",
    ]

    stat_descriptions = {
        "strength": "Determines physical power and endurance",
        "intelligence": "Indicates analytical and problem-solving abilities",
        "willpower": "Measures mental resilience and focus",
        "coordination": "Represents dexterity and agility",
        "charisma": "Reflects social skills and influence",
        "courage": "Measures bravery and risk-taking capacity",
        "offense": "Calculates attack potential in combat",
        "defense": "Indicates resilience in combat",
        "deception": "Ability to mislead and manipulate",
        "evasion": "Capability to avoid detection and attacks",
        "analyze": "Skill in examining and understanding unknown objects",
        "lifelevel": "Overall health and vitality",
        "movement": "Speed and agility in movement",
        "meleecombat": "Skill in close-quarters combat",
        "surprise": "Capability to catch others off-guard",
        "leadership": "Ability to inspire loyalty and lead others"
    }

    skill_descriptions = {
        "Piloting": "Skill in operating spacecraft and vehicles",
        "Hacking": "Expertise in bypassing computer security and extracting data",
        "Negotiation": "Ability to reach agreements and persuade others",
        "Martial Arts": "Training in hand-to-hand combat techniques",
        "Sharpshooting": "Skill in precise shooting with rifles",
        "Stealth": "Ability to move unseen and avoid detection",
        "Medicine": "Knowledge of medical practices and patient care",
        "Military Science": "Understanding of military tactics and strategies",
        "Explosives": "Knowledge of explosives and their safe handling",
        "Cybernetics": "Expertise in augmenting biology with artificial parts",
        "Xenobiology": "Study of alien biology and lifeforms",
        "Survival": "Skills needed to endure in hostile environments",
        "Diplomacy": "Ability to maintain peace and foster alliances",
        "Navigation": "Skill in plotting courses through space and planetary terrains",
        "Interrogation": "Techniques for extracting information from subjects",
        "Robot Repair": "Knowledge in maintaining and fixing robotic systems",
        "Social Engineering": "Manipulation of social interactions for specific outcomes",
        "Ships Systems": "Expertise in operating and repairing complex systems",
        "Espionage": "Skill in gathering intelligence covertly",
        "Mechanics": "Skill in altering, repairing, and breaching mechanical systems",
        "Fabrication": "Ability to design and manufacture complex items",
        "Instruction": "Proficiency instructing others in known skills",
        "Energy Weapons": "Proficiency with weapons that use energy-based attacks",
        "Sonic Weapons": "Proficiency with blasters and stunners that use sonic attacks",
        "Physics": "Understanding of physical principles and phenomena",
        "Projectile Weapons": "Skill in handling traditional firearms and projectile weapons",
        "Artifact Analysis": "Ability to study and understand ancient alien artifacts",
        "Squad Tactics": "Skill in coordinating and leading small groups in combat",
        "Mech Combat": "Skill in controlling and fighting with or against robots",
        "Exoskeleton Systems": "Skill in the use of powered exoskeletons and armor",
        "Resource Extraction": "Ability to efficiently gather resources from environments",
        "Detection": "Skill in noticing hidden details or signs of danger",
    }

    def draw(self, screen):
        """Draws the character's portrait on the screen."""
        screen.blit(self.portrait, self.rect)

    def move(self, rel):
        self.rect.move_ip(rel)

    def make_name(self):
        return random.choice(self.prefixes) + random.choice(self.suffixes)

    def bell_curve_stat(self):
        value = int(random.gauss(60, 20))  # Mean of 60, standard deviation of 20
        return max(25, min(95, value))  # Clamp between 25 and 95

    def generate_random_stats(self):
        return {
            "strength": self.bell_curve_stat(),
            "intelligence": self.bell_curve_stat(),
            "willpower": self.bell_curve_stat(),
            "coordination": self.bell_curve_stat(),
            "charisma": self.bell_curve_stat(),
            "courage": self.bell_curve_stat(),
        }

    @staticmethod
    def random_skill():
        return random.choice(Character.possible_skills)

    def set_rect(self, character_rect):
        self.rect = character_rect

    def get_rect(self):
        return self.rect

    def get_raw_skills(self):
        return self.skills

    @staticmethod
    def create_assaultbot(index, all_items):
        assaultbot = Character(index, "robot")
        assaultbot.occupation = "assaultbot"
        assaultbot.history = "A robot."
        assaultbot.name = "ASB" + str(index)
        portrait_path = resource_path(f"gadgets/assaultbot.jpg")
        assaultbot.portrait = pygame.image.load(portrait_path)
        assaultbot.portrait = pygame.transform.scale(assaultbot.portrait, (70, 80))
        assaultbot.stats["livelevel"] = all_items["assaultbot"].hp
        assaultbot.max_life = all_items["assaultbot"].hp
        assaultbot.stats["strength"] = 50
        assaultbot.stats["intelligence"] = 30
        assaultbot.stats["willpower"] = 90
        assaultbot.stats["coordination"] = 80
        assaultbot.stats["charisma"] = 10
        assaultbot.stats["courage"] = 95
        assaultbot.stats["offense"] = 75
        assaultbot.stats["defense"] = 75
        assaultbot.stats["evasion"] = 50
        assaultbot.stats["deception"] = 50
        assaultbot.stats["analyze"] = 10
        assaultbot.stats["movement"] = 30
        assaultbot.stats["meleecombat"] = 10
        assaultbot.stats["surprise"] = 175
        assaultbot.stats["leadership"] = 5
        assaultbot.skills = {"Energy Weapons":75, "Mech Combat":50}
        assaultbot.add_item(all_items["laser pistol"])
        assaultbot.add_item(all_items["power shield"])

        return assaultbot

    @staticmethod
    def create_stunbot(index, all_items):
        stunbot = Character(index, "robot")
        stunbot.occupation = "stunbot"
        stunbot.history = "A robot."
        stunbot.name = "STB" + str(index)
        portrait_path = resource_path(f"gadgets/stunbot.jpg")
        stunbot.portrait = pygame.image.load(portrait_path)
        stunbot.portrait = pygame.transform.scale(stunbot.portrait, (70, 80))
        stunbot.stats["livelevel"] = all_items["stunbot"].hp
        stunbot.max_life = all_items["stunbot"].hp
        stunbot.stats["lifelevel"] = stunbot.max_life
        stunbot.stats["strength"] = 50
        stunbot.stats["intelligence"] = 30
        stunbot.stats["willpower"] = 90
        stunbot.stats["coordination"] = 80
        stunbot.stats["charisma"] = 10
        stunbot.stats["courage"] = 95
        stunbot.stats["offense"] = 75
        stunbot.stats["defense"] = 75
        stunbot.stats["evasion"] = 50
        stunbot.stats["deception"] = 50
        stunbot.stats["analyze"] = 10
        stunbot.stats["movement"] = 30
        stunbot.stats["meleecombat"] = 10
        stunbot.stats["surprise"] = 125
        stunbot.stats["leadership"] = 5
        stunbot.skills = {"Energy Weapons": 75, "Mech Combat":50}
        stunbot.add_item(all_items["stunner"])
        stunbot.add_item(all_items["power shield"])
        return stunbot

    @staticmethod
    def create_mechbot(index, all_items):
        mechbot = Character(index, "robot")
        mechbot.occupation = "mechbot"
        mechbot.history = "A robot."
        mechbot.name = "MKB" + str(index)
        portrait_path = resource_path(f"gadgets/mechbot.jpg")
        mechbot.portrait = pygame.image.load(portrait_path)
        mechbot.portrait = pygame.transform.scale(mechbot.portrait, (70, 80))
        mechbot.stats["livelevel"] = all_items["mechbot"].hp
        mechbot.max_life = all_items["mechbot"].hp
        mechbot.stats["lifelevel"] = mechbot.max_life
        mechbot.stats["strength"] = 50
        mechbot.stats["intelligence"] = 30
        mechbot.stats["willpower"] = 90
        mechbot.stats["coordination"] = 80
        mechbot.stats["charisma"] = 10
        mechbot.stats["courage"] = 95
        mechbot.stats["offense"] = 10
        mechbot.stats["defense"] = 10
        mechbot.stats["evasion"] = 30
        mechbot.stats["deception"] = 30
        mechbot.stats["analyze"] = 35
        mechbot.stats["movement"] = 30
        mechbot.stats["meleecombat"] = 5
        mechbot.stats["surprise"] = 20
        mechbot.stats["leadership"] = 5
        mechbot.skills = {"Robot Repair": 65, "Fabrication": 35, "Mechanics": 50}
        mechbot.add_item(all_items["stunner"])
        return mechbot

    @staticmethod
    def create_techbot(i, all_items):
        techbot = Character(i, "robot")
        techbot.occupation = "techbot"
        techbot.history = "A robot."
        techbot.name = "TKB" + str(i)
        portrait_path = resource_path(f"gadgets/techbot.jpg")
        techbot.portrait = pygame.image.load(portrait_path)
        techbot.portrait = pygame.transform.scale(techbot.portrait, (70, 80))
        techbot.stats["livelevel"] = all_items["techbot"].hp
        techbot.max_life = all_items["techbot"].hp
        techbot.stats["strength"] = 50
        techbot.stats["intelligence"] = 30
        techbot.stats["willpower"] = 90
        techbot.stats["coordination"] = 80
        techbot.stats["charisma"] = 10
        techbot.stats["courage"] = 95
        techbot.stats["offense"] = 10
        techbot.stats["defense"] = 10
        techbot.stats["evasion"] = 40
        techbot.stats["deception"] = 30
        techbot.stats["analyze"] = 65
        techbot.stats["movement"] = 30
        techbot.stats["meleecombat"] = 5
        techbot.stats["surprise"] = 20
        techbot.stats["leadership"] = 5
        techbot.skills = {"Robot Repair": 65, "Ships Systems": 55, "Fabrication": 15,
                              "Artifact Analysis": 45, "Hacking": 35}
        techbot.add_item(all_items["stunner"])
        return techbot

    @staticmethod
    def create_hackbot(i, all_items):
        hackbot = Character(i, "robot")
        hackbot.occupation = "hackbot"
        hackbot.history = "A robot."
        hackbot.name = "HKB" + str(i)
        portrait_path = resource_path(f"gadgets/hackbot.jpg")
        hackbot.portrait = pygame.image.load(portrait_path)
        hackbot.portrait = pygame.transform.scale(hackbot.portrait, (70, 80))
        hackbot.stats["livelevel"] = all_items["hackbot"].hp
        hackbot.max_life = all_items["hackbot"].hp
        hackbot.stats["lifelevel"] = hackbot.max_life
        hackbot.stats["strength"] = 50
        hackbot.stats["intelligence"] = 30
        hackbot.stats["willpower"] = 90
        hackbot.stats["coordination"] = 80
        hackbot.stats["charisma"] = 10
        hackbot.stats["courage"] = 95
        hackbot.stats["offense"] = 10
        hackbot.stats["defense"] = 10
        hackbot.stats["evasion"] = 40
        hackbot.stats["deception"] = 30
        hackbot.stats["analyze"] = 45
        hackbot.stats["movement"] = 30
        hackbot.stats["meleecombat"] = 5
        hackbot.stats["surprise"] = 20
        hackbot.stats["leadership"] = 5
        hackbot.skills = {"Robot Repair": 15, "Ships Systems": 45, "Fabrication": 10,
                          "Artifact Analysis": 25, "Hacking": 75}
        hackbot.add_item(all_items["stunner"])
        return hackbot

    @staticmethod
    def create_meleebot(i, all_items):
        meleebot = Character(i, "robot")
        meleebot.occupation = "meleebot"
        meleebot.history = "A robot."
        meleebot.name = "MEB" + str(i)
        portrait_path = resource_path(f"gadgets/meleebot.jpg")
        meleebot.portrait = pygame.image.load(portrait_path)
        meleebot.portrait = pygame.transform.scale(meleebot.portrait, (70, 80))
        meleebot.stats["livelevel"] = all_items["meleebot"].hp
        meleebot.max_life = all_items["meleebot"].hp
        meleebot.stats["strength"] = 50
        meleebot.stats["intelligence"] = 30
        meleebot.stats["willpower"] = 90
        meleebot.stats["coordination"] = 80
        meleebot.stats["charisma"] = 10
        meleebot.stats["courage"] = 95
        meleebot.stats["offense"] = 75
        meleebot.stats["defense"] = 75
        meleebot.stats["evasion"] = 75
        meleebot.stats["deception"] = 40
        meleebot.stats["analyze"] = 5
        meleebot.stats["movement"] = 75
        meleebot.stats["meleecombat"] = 75
        meleebot.stats["surprise"] = 150
        meleebot.stats["leadership"] = 5
        meleebot.skills = {"Martial Arts":75, "Mech Combat":50}
        meleebot.add_item(all_items["slicer"])
        meleebot.add_item(all_items["veer suit"])
        return meleebot

    @staticmethod
    def create_batonbot(i, all_items):
        batonbot = Character(i, "robot")
        batonbot.occupation = "batonbot"
        batonbot.history = "A robot."
        batonbot.name = "BAB" + str(i)
        portrait_path = resource_path(f"gadgets/batonbot.jpg")
        batonbot.portrait = pygame.image.load(portrait_path)
        batonbot.portrait = pygame.transform.scale(batonbot.portrait, (70, 80))
        batonbot.stats["livelevel"] = all_items["batonbot"].hp
        batonbot.max_life = all_items["batonbot"].hp
        batonbot.stats["strength"] = 50
        batonbot.stats["intelligence"] = 30
        batonbot.stats["willpower"] = 90
        batonbot.stats["coordination"] = 80
        batonbot.stats["charisma"] = 10
        batonbot.stats["courage"] = 95
        batonbot.stats["offense"] = 75
        batonbot.stats["defense"] = 75
        batonbot.stats["evasion"] = 50
        batonbot.stats["deception"] = 40
        batonbot.stats["analyze"] = 5
        batonbot.stats["movement"] = 75
        batonbot.stats["meleecombat"] = 75
        batonbot.stats["surprise"] = 150
        batonbot.stats["leadership"] = 5
        batonbot.skills = {"Martial Arts": 75, "Mech Combat":50}
        batonbot.add_item(all_items["stun baton"])
        batonbot.add_item(all_items["veer suit"])
        return batonbot

    @staticmethod
    def create_medibot(i, all_items):
        medibot = Character(i, "robot")
        medibot.occupation = "medibot"
        medibot.history = "A robot."
        medibot.name = "MDB" + str(i)
        portrait_path = resource_path(f"gadgets/medibot.jpg")
        medibot.portrait = pygame.image.load(portrait_path)
        medibot.portrait = pygame.transform.scale(medibot.portrait, (70, 80))
        medibot.stats["livelevel"] = all_items["medibot"].hp
        medibot.max_life = all_items["medibot"].hp
        medibot.stats["strength"] = 50
        medibot.stats["intelligence"] = 30
        medibot.stats["willpower"] = 90
        medibot.stats["coordination"] = 80
        medibot.stats["charisma"] = 10
        medibot.stats["courage"] = 95
        medibot.stats["offense"] = 10
        medibot.stats["defense"] = 10
        medibot.stats["evasion"] = 30
        medibot.stats["deception"] = 40
        medibot.stats["analyze"] = 15
        medibot.stats["movement"] = 30
        medibot.stats["meleecombat"] = 5
        medibot.stats["surprise"] = 20
        medibot.stats["leadership"] = 5
        medibot.skills = {"Medicine": 75, "Xenobiology": 50}
        medibot.add_item(all_items["stun baton"])
        medibot.add_item(all_items["medikit"])
        return medibot

    @staticmethod
    def create_mulebot(i, all_items):
        mulebot = Character(i, "robot")
        mulebot.occupation = "mulebot"
        mulebot.history = "A robot."
        mulebot.name = "MUB" + str(i)
        portrait_path = resource_path(f"gadgets/mulebot.jpg")
        mulebot.portrait = pygame.image.load(portrait_path)
        mulebot.portrait = pygame.transform.scale(mulebot.portrait, (70, 80))
        mulebot.stats["livelevel"] = all_items["mulebot"].hp
        mulebot.max_life = all_items["mulebot"].hp
        mulebot.stats["strength"] = 50
        mulebot.stats["intelligence"] = 30
        mulebot.stats["willpower"] = 90
        mulebot.stats["coordination"] = 80
        mulebot.stats["charisma"] = 10
        mulebot.stats["courage"] = 95
        mulebot.stats["offense"] = 10
        mulebot.stats["defense"] = 10
        mulebot.stats["evasion"] = 30
        mulebot.stats["deception"] = 30
        mulebot.stats["analyze"] = 15
        mulebot.stats["movement"] = 30
        mulebot.stats["meleecombat"] = 5
        mulebot.stats["surprise"] = 20
        mulebot.stats["leadership"] = 5
        mulebot.skills = {}
        mulebot.add_item(all_items["stun baton"])
        return mulebot

    @staticmethod
    def create_scoutbot(i, all_items):
        scoutbot = Character(i, "robot")
        scoutbot.occupation = "scoutbot"
        scoutbot.history = "A robot."
        scoutbot.name = "SCB" + str(i)
        portrait_path = resource_path(f"gadgets/scoutbot.jpg")
        scoutbot.portrait = pygame.image.load(portrait_path)
        scoutbot.portrait = pygame.transform.scale(scoutbot.portrait, (70, 80))
        scoutbot.stats["livelevel"] = all_items["scoutbot"].hp
        scoutbot.max_life = all_items["scoutbot"].hp
        scoutbot.stats["strength"] = 30
        scoutbot.stats["intelligence"] = 50
        scoutbot.stats["willpower"] = 90
        scoutbot.stats["coordination"] = 80
        scoutbot.stats["charisma"] = 10
        scoutbot.stats["courage"] = 95
        scoutbot.stats["offense"] = 10
        scoutbot.stats["defense"] = 60
        scoutbot.stats["evasion"] = 85
        scoutbot.stats["deception"] = 50
        scoutbot.stats["analyze"] = 15
        scoutbot.stats["movement"] = 125
        scoutbot.stats["meleecombat"] = 5
        scoutbot.stats["surprise"] = 150
        scoutbot.stats["leadership"] = 5
        scoutbot.skills = {"Stealth": 50, "Espionage":50, "Detection":75}
        scoutbot.add_item(all_items["stunner"])
        scoutbot.add_item(all_items["scanner"])
        return scoutbot

    def to_dict(self):
        """Converts the character to a dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "index": self.index,
            "stats": self.stats,
            "occupation": self.occupation,
            "homeworld": self.homeworld,
            "event": self.event,
            "goal": self.goal,
            "history": self.history,
            "skills": self.skills,
            "mission": self.mission,
            "mission points": self.mission_points,
            "vetted": self.vetted,
            "psychotic": self.psychotic,
            "traitor": self.traitor,
            "morale": self.morale,
            # Store each item in equipment as a serializable dictionary without the 'icon' pygame surface
            # Store equipment as a list of dictionaries (Item's `__dict__`).
            "equipment": [item.to_dict() for item in self.equipment]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        """Creates a Character instance from a dictionary."""
        character = cls(data["index"], data["type"])
        character.name = data["name"]
        character.type = data["type"]
        character.stats = data["stats"]
        character.occupation = data["occupation"]
        character.homeworld = data["homeworld"]
        character.event = data["event"]
        character.goal = data["goal"]
        character.history = data["history"]
        character.skills = data["skills"]
        character.vetted = data["vetted"]
        character.psychotic = data["psychotic"]
        character.traitor = data["traitor"]
        character.morale = data["morale"]
        if "mission" in data:
            character.mission = data["mission"]
        if "mission points" in data:
            character.mission_points = data["mission points"]
        character.equipment = [Item.from_dict(item_data) for item_data in data["equipment"]]  # Recreate items

        if data["type"] == "robot":
            portrait_path = resource_path(f"gadgets/{character.occupation}.jpg")
            try:
                character.portrait = pygame.image.load(portrait_path)
                character.portrait = pygame.transform.scale(character.portrait, (70, 80))
            except pygame.error:
                print(f"Failed to load robot portrait: {portrait_path}")

        return character