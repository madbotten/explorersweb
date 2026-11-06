from itertools import filterfalse
from typing import Any

import pygame
import random
import os
from typing import Any
from constants import DEBUG
from Utils import *


# ---------------------------------------------------------------------------
# Interaction type constants
# ---------------------------------------------------------------------------
class InteractionType:
    FLATTER  = "FLATTER"
    BRAG     = "BRAG"
    PERSUADE = "PERSUADE"
    THREATEN = "THREATEN"
    DEMAND   = "DEMAND"
    INFORM   = "INFORM"
    REQUEST  = "REQUEST"
    JOKE     = "JOKE"

    ALL = [FLATTER, BRAG, PERSUADE, THREATEN, DEMAND, INFORM, REQUEST, JOKE]

# Thresholds for personality labels
INTERACTION_LOVE_THRESHOLD =  90
INTERACTION_HATE_THRESHOLD = -90

# Human-readable labels used in the personality summary line
# (action the character DOES → label  |  action done TO character → label)
_DOES_LABELS = {
    InteractionType.FLATTER:  "Flatterer",
    InteractionType.BRAG:     "Braggart",
    InteractionType.PERSUADE: "Persuader",
    InteractionType.THREATEN: "Intimidator",
    InteractionType.DEMAND:   "Demander",
    InteractionType.INFORM:   "Informer",
    InteractionType.REQUEST:  "Requester",
    InteractionType.JOKE:     "Jokester",
}
_LIKED_BY_LABELS = {
    InteractionType.FLATTER:  "Egomaniac",
    InteractionType.BRAG:     "Fan",
    InteractionType.PERSUADE: "Persuadable",
    InteractionType.THREATEN: "Pushover",
    InteractionType.DEMAND:   "Obedient",
    InteractionType.INFORM:   "Scholar",
    InteractionType.REQUEST:  "Cooperative",
    InteractionType.JOKE:     "Cheerful",
}

# Base directory for all portraits; each character type lives in its own subdirectory
portraits_dir = "portraits/"
TOP_EDGE = 30
CHARACTER_BOX_WIDTH = 90
CHARACTER_BOX_HEIGHT = 100

class Character:
    SUB_STAT_MAP = {
        "strength": ("brawn", "stamina", "resilience"),
        "coordination": ("fine_manipulation", "agility", "reflexes"),
        "intelligence": ("logic", "memory", "guile"),
        "willpower": ("focus", "composure", "tenacity"),
        "charisma": ("beauty", "charm", "command"),
        "courage": ("valor", "nerve", "resolve"),
    }

    SKILL_GATE_STATS = {
        "Piloting": ("coordination", "willpower"),
        "Hacking": ("intelligence", "willpower"),
        "Negotiation": ("charisma",),
        "Martial Arts": ("strength", "coordination"),
        "Sharpshooting": ("coordination", "willpower"),
        "Stealth": ("coordination", "intelligence"),
        "Medicine": ("intelligence", "willpower"),
        "Military Science": ("intelligence", "courage"),
        "Explosives": ("intelligence", "courage"),
        "Cybernetics": ("intelligence", "coordination"),
        "Xenobiology": ("intelligence",),
        "Survival": ("strength", "willpower"),
        "Diplomacy": ("charisma", "intelligence"),
        "Navigation": ("intelligence", "willpower"),
        "Interrogation": ("charisma", "willpower"),
        "Robot Repair": ("intelligence", "coordination"),
        "Social Engineering": ("charisma", "intelligence"),
        "Ships Systems": ("intelligence", "coordination"),
        "Espionage": ("intelligence", "courage"),
        "Mechanics": ("coordination", "intelligence"),
        "Fabrication": ("intelligence", "coordination"),
        "Instruction": ("charisma", "intelligence"),
        "Energy Weapons": ("coordination",),
        "Sonic Weapons": ("coordination",),
        "Physics": ("intelligence",),
        "Projectile Weapons": ("coordination", "strength"),
        "Artifact Analysis": ("intelligence", "willpower"),
        "Squad Tactics": ("charisma", "courage"),
        "Mech Combat": ("coordination", "courage"),
        "Exoskeleton Systems": ("strength", "coordination"),
        "Resource Extraction": ("strength",),
        "Detection": ("willpower",),
        "Weaponsmithing": ("coordination", "intelligence"),
        "Armorsmithing": ("strength", "coordination"),
        "Tinkering": ("coordination", "intelligence"),
        "Supply Logistics": ("intelligence", "willpower"),
    }

    def __init__(self, index, type, width=CHARACTER_BOX_WIDTH, height=CHARACTER_BOX_HEIGHT):
        self.type = type
        if type == "pirate":
            self.name = "pirate" + str(index)
            self.occupation = "pirate"
        elif type == "klackon":
            self.name = "Klackon " + str(index)
            self.occupation = "klackon"
        elif type == "team":
            self.name = self.make_name()
            self.occupation = random.choice(self.occupations)
        self.index = index
        self.rect = pygame.Rect(22, TOP_EDGE, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
        self.sub_stats = self.generate_random_sub_stats()
        if type == "klackon":
            for sub_key in ("brawn", "stamina", "resilience", "agility", "reflexes", "valor", "tenacity"):
                self.sub_stats[sub_key] = max(self.sub_stats.get(sub_key, 70), random.randint(72, 92))
        self.stats = {}
        self.recalculate_stats()

        self.homeworld = random.choice(self.homeworlds)
        self.event = random.choice(self.events)
        self.goal = random.choice(self.goals)
        # "mission_index", "methods", "means", "options"
        self.mission = {}
        if type == "klackon":
            self.history = "A chitinous Klackon warrior defending the hive."
        elif type != "robot":
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

        # ---------------------------------------------------------------
        # Interaction preferences  (score −100 … 100)
        # interaction_likes   : what this character likes/hates TO DO
        # interaction_liked_by: what this character likes/hates DONE TO THEM
        # Robots are emotionally neutral (all scores stay 0).
        # ---------------------------------------------------------------
        if type == "robot":
            self.interaction_likes    = {k: 0 for k in InteractionType.ALL}
            self.interaction_liked_by = {k: 0 for k in InteractionType.ALL}
        else:
            self.interaction_likes    = {
                k: self._random_interaction_score() for k in InteractionType.ALL
            }
            self.interaction_liked_by = {
                k: self._random_interaction_score() for k in InteractionType.ALL
            }

        # Relationship scores with other characters, keyed by character name.
        # Initialised to 0 (neutral) when the character is first generated;
        # scores are populated and updated during gameplay.
        # Robots keep all relationships at 0.
        self.relationships: dict[str, int] = {}
        self.current_health = self.stats["max_health"]

        self.vetted    = False
        self.psychotic = random.randint(1, 100) <= 5   # 5% start psychotic
        self.traitor   = random.randint(1, 100) <= 5   # 5% start as traitor

        if type not in ("robot", "klackon"):
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
            elif random.randint(1, 100) < 50:
                self.history += "\nPsych analysis: Indeterminate."
            else:
                self.history += "\nPsych analysis: Failed."
                roll = random.randint(1, 100)
                if roll < 25:
                    self.psychotic = True

            self.history += "\n" + random.choice(self.personality_types)
            personality_line = self._build_personality_string()
            if personality_line:
                self.history += "\n" + personality_line

        # Generate and assign major skills
        self.skills = self.assign_skills(self.stats["intelligence"], self.stats["willpower"])
        if type == "klackon":
            self.skills["Martial Arts"] = max(self.skills.get("Martial Arts", 0), random.randint(65, 90))

        # Learning progress tracker — one entry per possible skill, starts at 0
        self.learning_skills_dict: dict[str, int] = {skill: 0 for skill in self.possible_skills}

        if type != "robot":
          portrait_path = None
          if type == "team":
            portrait_path = resource_path(f"portraits/characters/character{index}.jpg")
          elif type == "pirate":
            portrait_path = resource_path(f"portraits/pirates/pirate{index}.jpg")
          elif type == "klackon":
            klackon_idx = ((index - 1) % 3) + 1 if isinstance(index, int) and index > 0 else random.randint(1, 3)
            portrait_path = resource_path(f"portraits/klackons/klackon{klackon_idx}.jpg")
          try:
            if portrait_path:
              self.portrait = pygame.image.load(portrait_path)  # Load the portrait image
              self.portrait = pygame.transform.scale(self.portrait, (width, height))
          except pygame.error:
            print(f"Failed to load image")

        self.location = (-1, -1)
        self.battle_index = 0
        self.last_action = BattleAction.NONE
        # Persisted command role ("commander", "exec", or None) and movement position
        # ("point_man", "center", "overwatch", "protected", or None)
        self.command_role = None
        self.position = None
        # Transient combat fields — set at the start of each battle, not persisted.
        self.chosen_ranged_weapon = None   # Item | None
        self.chosen_melee_weapon  = None   # Item | None

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    def is_robot(self):
        """Returns True if this character is a robot."""
        return self.type == "robot"

    @staticmethod
    def _random_interaction_score():
        """Bell-curve score clamped to [−100, 100]."""
        return max(-100, min(100, int(random.gauss(0, 40))))

    def _build_personality_string(self):
        """Return 'Personality: Label1, Label2' listing loves and hates, or '' if none."""
        labels = []
        for k in InteractionType.ALL:
            if self.interaction_likes.get(k, 0) >= INTERACTION_LOVE_THRESHOLD:
                labels.append(_DOES_LABELS[k])
            if self.interaction_liked_by.get(k, 0) >= INTERACTION_LOVE_THRESHOLD:
                labels.append(_LIKED_BY_LABELS[k])
            if self.interaction_likes.get(k, 0) <= INTERACTION_HATE_THRESHOLD:
                labels.append(f"Anti-{_DOES_LABELS[k]}")
            if self.interaction_liked_by.get(k, 0) <= INTERACTION_HATE_THRESHOLD:
                labels.append(f"Anti-{_LIKED_BY_LABELS[k]}")
        if not labels:
            return ""
        return "Personality: " + ", ".join(labels)

    def get_relationship(self, other_name: str) -> int:
        """Return the relationship score with *other_name* (0 if not yet set)."""
        return self.relationships.get(other_name, 0)

    def set_relationship(self, other_name: str, score: int):
        """Set the relationship score with *other_name*, clamped to [−100, 100].
        Robots silently ignore this call (they stay neutral)."""
        if self.is_robot():
            return
        self.relationships[other_name] = max(-100, min(100, score))

    def adjust_relationship(self, other_name: str, delta: int):
        """Adjust the relationship score with *other_name* by *delta*.
        Robots silently ignore this call."""
        if self.is_robot():
            return
        current = self.relationships.get(other_name, 0)
        self.set_relationship(other_name, current + delta)

    def initialize_relationships(self, team):
        """Populate the relationships dict with 0 for every team member that is
        not already present. Call this after team assembly. Robots skip this."""
        if self.is_robot():
            return
        for member in team:
            if member is not self and member.name not in self.relationships:
                self.relationships[member.name] = 0

    def is_combative_personality(self):
        if any(sub in self.history for sub in ("narcissist", "aggressive")) or self.psychotic:
            return True

    def is_enemy(self):
        return self.occupation in ("pirate", "klackon") or self.type in ("pirate", "klackon")

    def is_pirate(self):
        return self.is_enemy()

    def get_health_ratio(self):
        """Current HP as a 0.0-1.0 fraction of max HP."""
        if self.is_robot():
            return min(1.0, self.current_health / self.max_life) if self.max_life > 0 else 0.0
        max_hp = self.stats["max_health"]
        return min(1.0, self.current_health / max_hp) if max_hp > 0 else 0.0

    def health_pct(self):
        """Current HP as a 0–100 integer percentage of max HP."""
        return int(self.get_health_ratio() * 100)

    def morale_from_health(self):
        """
        Sync morale upward to match the current health percentage.
        Called after healing or repair — morale can never exceed 100,
        and can be higher than health% if a separate event boosted it,
        but healing raises a floor up to health%.
        For robots morale IS health%, so it is set exactly.
        """
        pct = self.health_pct()
        if self.is_robot():
            self.morale = pct
        else:
            self.morale = min(100, max(self.morale, pct))

    def get_morale_ratio(self):
        return self.morale / 100

    def get_max_health(self):
        """Max HP for this character (including stimulant overheal capacity)."""
        if self.is_robot():
            return self.max_life
        base = self.stats.get("max_health", self.stats["strength"] + self.stats["willpower"])
        stim = self.get_item("stimulant")
        if stim is not None:
            base += stim.effect * 2
        return base

    def get_lifelevel(self):
        """Return current HP (not the max-HP stat)."""
        return self.current_health

    def is_alive(self):
        return self.current_health > 0

    def demoralize(self, amount):
        """Lower morale by amount.
        Robots are immune (their morale tracks HP only).
        Psychotics are immune to mental/social demoralization; they still
        lose morale from physical damage via hurt().
        """
        if self.is_robot() or self.psychotic:
            return
        self.morale = max(0, self.morale - amount)

    def encourage(self, amount):
        """Raise morale by amount. Robots are immune (their morale tracks HP only)."""
        if self.is_robot():
            return
        self.morale = min(100, self.morale + amount)

    # Apply the pain and return True if they died
    def hurt(self, damage, effect_type):
        """
        Apply damage and update morale.

        Robots: morale is set to health% (damage state proxy).
        Humans: morale drops by the damage dealt AND is clamped so it
                cannot exceed the current health percentage — injury
                always pulls morale down at least as far as HP dropped.
        """
        # effect_type → index in ARMOR_ATTRIBUTES multiplier tuple
        # (energy, sonic, impact, slash, pierce, concussion, electric)
        EFFECT_TYPE_INDEX = {
            "energy": 0, "sonic": 1, "impact": 2,
            "slash": 3, "pierce": 4, "concussion": 5, "electric": 6,
        }
        idx = EFFECT_TYPE_INDEX.get(effect_type, -1)

        # Sum protection from all equipped armor items:
        #   protection = round(armor.effect * type_multiplier)
        if idx >= 0:
            for item in self.equipment:
                base = item_base_name(item.name)
                if base in ARMOR_ATTRIBUTES:
                    modifier = ARMOR_ATTRIBUTES[base][idx]
                    damage -= round(item.effect * modifier)

        # always do at least 1 point on hit
        damage = max(1, damage)

        # Apply HP damage to current_health (stats["max_health"] is the max-HP stat, never changes)
        self.current_health = max(0, self.current_health - damage)

        # Update morale based on new health state
        if self.is_robot():
            # Robot morale = exact health ratio (their only morale driver)
            self.morale = self.health_pct()
        else:
            # Morale drop is proportional to damage relative to max health:
            #   15 dmg vs 100 max_health = -15 morale
            #   15 dmg vs 200 max_health = -7.5 -> -8 morale
            # Also clamped so morale can never exceed the current health%.
            max_hp = self.stats["max_health"]
            morale_drop = round(damage / max_hp * 100) if max_hp > 0 else damage
            self.morale = max(0, min(self.morale - morale_drop, self.health_pct()))

        if self.current_health <= 0:
            return True
        return False

    # Make a skill check which degrades with injury
    # positive difficulty modifiers are easier
    def skill_check(self, roll, skill_name, difficulty_modifier):
        if skill_name is None:
            return True
        ability = self.get_effective_skill_level(skill_name)
        morale_modifier = self.get_morale_ratio()
        if roll < (ability * morale_modifier) + difficulty_modifier:
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
        morale_modifier = self.get_morale_ratio()
        if roll < (ability * morale_modifier) + difficulty_modifier:
            return True
        return False

    # positive difficulty modifiers are easier
    def stat_check(self, roll, stat_name, difficulty_modifier):
        if stat_name is None:
            return True
        if DEBUG:
            print("stat check for " + stat_name + " with difficulty " + str(difficulty_modifier))
        if self.current_health < 0:
            self.current_health = 0
        ability = self.get_effective_stat_level(stat_name)
        morale_modifier = self.get_morale_ratio()
        if DEBUG:
            print("Ability is " + str(ability))
            print("Roll is " + str(roll))
        if roll < (ability * morale_modifier) + difficulty_modifier:
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
            self.stats[stat_name] = 15

    # If encumbered and team has no mulebot, evasion will suffer
    def is_encumbered(self):
        if self.has_item("powered armor"):
            return False
        if self.team and any(m.occupation == "mulebot" and m.is_alive() for m in self.team):
            return False
        total_mass = self.get_carried_mass()
        return total_mass > (self.get_effective_stat_level("strength") / 2)

    def get_carried_mass(self):
       total_mass = 0
       for item in self.equipment:
           total_mass += item.mass
       return total_mass

    # Effective stat level without health ratio (applied in skill check).
    # learning=True (the default) records one use in learning_skills_dict and
    # promotes the skill when enough uses have accumulated.
    # Pass learning=False when the call is only for comparison/selection
    # (e.g. determine_best_team_member) and no actual action will be taken.
    def get_skill_gate_bonus(self, skill_name) -> int:
        """Return a bonus in [0, 10] when a skill's gating main stats are green (> 75)."""
        if not skill_name or self.is_robot():
            return 0
        gate_stats = self.SKILL_GATE_STATS.get(skill_name)
        if not gate_stats:
            return 0
        max_per_stat = 10.0 / len(gate_stats)
        bonus = 0.0
        for stat_name in gate_stats:
            val = self.stats.get(stat_name, 0)
            if val > 75:
                stat_bonus = max(1.0, min(max_per_stat, (val - 75) / 20.0 * max_per_stat))
                bonus += stat_bonus
        return min(10, round(bonus))

    def is_skill_allowed(self, skill_name) -> bool:
        """Return True if none of the skill's gating stats are red (< 50)."""
        gate_stats = self.SKILL_GATE_STATS.get(skill_name, ())
        return all(self.stats.get(st, 50) >= 50 for st in gate_stats)

    def get_effective_skill_level(self, skill_name, learning=True):
        if skill_name is None:
            return 1
        total = 0
        if self.has_skill(skill_name):
            total += self.skills[skill_name]
            total += self.get_skill_gate_bonus(skill_name)

        # --- learning system ---
        if learning and not self.is_robot() and skill_name in self.learning_skills_dict:
            learn_step = 2 if self.has_item("neural trainer") else 1
            self.learning_skills_dict[skill_name] += learn_step
            current_level = self.skills.get(skill_name, 0)
            threshold = max(1, current_level // 10)
            if self.learning_skills_dict[skill_name] >= threshold:
                self.learning_skills_dict[skill_name] = 0
                self.skills[skill_name] = current_level + 1
                total += 1  # reflect the just-earned point in this return value

        if self.has_item("neural trainer"):
            trainer = self.get_item("neural trainer")
            floor_val = (trainer.effect * 3) if trainer else 21
            if total < floor_val:
                total = floor_val

        if self.has_item("scanner") and skill_name in ("Detection", "Artifact Analysis", "Xenobiology"):
            scanner = self.get_item("scanner")
            total += scanner.effect if scanner else 20

        if self.has_item("stealth orb") and skill_name == "Stealth":
            orb = self.get_item("stealth orb")
            total += round(orb.effect / 2) if orb else 20

        return total

    # --- Weapon-base classification constants used by the choosers below ---
    _RIFLE_BASES      = {"blaster rifle", "laser rifle", "grenade rifle"}
    _RANGED_BASES     = {"blaster rifle", "laser rifle", "laser pistol",
                         "carbine", "magnum", "pistol", "stunner",
                         "grenade rifle", "flechette pistol", "launcher", "arc thrower"}
    _MELEE_BASES      = {"slicer", "stun baton", "power mace", "mono spear", "grav hammer", "shock prod"}
    _ENERGY_BASES     = {"laser rifle", "laser pistol", "arc thrower"}
    _SONIC_RANGED     = {"blaster rifle", "stunner"}
    _SONIC_MELEE      = {"stun baton"}
    _PROJECTILE_BASES = {"carbine", "magnum", "pistol", "grenade rifle", "flechette pistol"}
    _EXPLOSIVE_BASES  = {"launcher"}

    def choose_ranged_weapon(self) -> "Item | None":
        """Return the best ranged weapon Item this character should use.

        Priority:
        1. Sharpshooting skill > 0  → prefer a rifle (blaster rifle / laser rifle)
        2. Energy Weapons skill > 0 → prefer energy-type ranged weapons
        3. Sonic Weapons skill > 0  → prefer sonic-type ranged weapons
        4. Projectile Weapons > 0   → prefer projectile-type ranged weapons
        5. Fallback: highest effect × rate among all ranged weapons
        If the preferred pool is empty, fall back to the best overall ranged weapon.
        """
        from Item import item_base_name  # avoid circular import at module level

        def _score(item):
            return item.effect * item.rate

        def _best_in(pool):
            return max(pool, key=_score) if pool else None

        ranged = [
            item for item in self.equipment
            if item.type == "weapon" and item_base_name(item.name) in self._RANGED_BASES
        ]
        if not ranged:
            return None

        means = (
            (self.mission.get("means") if getattr(self, "mission", None) else None)
            or (self.team[0].mission.get("means") if getattr(self, "team", None) and getattr(self.team[0], "mission", None) else None)
        )
        if means == "pacifist":
            stunners = [i for i in ranged if item_base_name(i.name) == "stunner"]
            if stunners:
                return _best_in(stunners)

        # 1. Sharpshooting → rifle
        if self.get_effective_skill_level("Sharpshooting", learning=False) > 0:
            rifles = [i for i in ranged if item_base_name(i.name) in self._RIFLE_BASES]
            if rifles:
                return _best_in(rifles)

        # 2. Energy Weapons → energy-type
        if self.get_effective_skill_level("Energy Weapons", learning=False) > 0:
            energy = [i for i in ranged if item_base_name(i.name) in self._ENERGY_BASES]
            if energy:
                return _best_in(energy)

        # 3. Sonic Weapons → sonic-type
        if self.get_effective_skill_level("Sonic Weapons", learning=False) > 0:
            sonic = [i for i in ranged if item_base_name(i.name) in self._SONIC_RANGED]
            if sonic:
                return _best_in(sonic)

        # 4. Projectile Weapons → projectile-type
        if self.get_effective_skill_level("Projectile Weapons", learning=False) > 0:
            proj = [i for i in ranged if item_base_name(i.name) in self._PROJECTILE_BASES]
            if proj:
                return _best_in(proj)

        # 5. Fallback: highest throughput
        return _best_in(ranged)

    def choose_melee_weapon(self) -> "Item | None":
        """Return the best melee weapon Item this character should use.

        Priority:
        0. Pacifist means          → prefer stun baton
        1. Sonic Weapons skill > 0 → prefer stun baton
        2. Martial Arts skill > 0  → prefer slicer
        3. Fallback: highest effect × rate among all melee weapons
        """
        from Item import item_base_name, DEFAULT_KNIFE_WEAPON  # avoid circular import at module level

        def _score(item):
            return item.effect * item.rate

        melee = [
            item for item in self.equipment
            if item.type == "weapon" and item_base_name(item.name) in self._MELEE_BASES
        ]
        if not melee:
            if not self.is_robot() and self.get_weapon_count() == 0:
                return DEFAULT_KNIFE_WEAPON
            return None

        means = (
            (self.mission.get("means") if getattr(self, "mission", None) else None)
            or (self.team[0].mission.get("means") if getattr(self, "team", None) and getattr(self.team[0], "mission", None) else None)
        )
        if means == "pacifist":
            stun_batons = [i for i in melee if item_base_name(i.name) == "stun baton"]
            if stun_batons:
                return max(stun_batons, key=_score)

        # 1. Sonic Weapons → stun baton
        if self.get_effective_skill_level("Sonic Weapons", learning=False) > 0:
            sonic = [i for i in melee if item_base_name(i.name) in self._SONIC_MELEE]
            if sonic:
                return max(sonic, key=_score)

        # 2. Martial Arts → slicer
        if self.get_effective_skill_level("Martial Arts", learning=False) > 0:
            slicers = [i for i in melee if item_base_name(i.name) == "slicer"]
            if slicers:
                return max(slicers, key=_score)

        # 3. Fallback: highest throughput
        return max(melee, key=_score)

    # Effective stat level without health ratio (applied in skill check)
    def get_effective_stat_level(self, stat_name):
        if stat_name is None:
            return 0
        total = self.stats[stat_name]
        if "strength" == stat_name:
            if self.has_item("exoskeleton"):
                exo = self.get_item("exoskeleton")
                total += (exo.effect * 2) if exo else 50
        if "evasion" == stat_name:
            if self.is_encumbered():
                total -= 10
        if "analyze" == stat_name:
            if self.has_item("scanner"):
                scanner = self.get_item("scanner")
                total += (10 + scanner.effect) if scanner else 30
        return total

    # Effective evasion with health ratio
    def get_effective_combat_evasion(self):
        intelligence = self.get_effective_stat_level("intelligence")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        evasion = round((intelligence + coordination) / 2)
        evasion += military_science / 10
        if self.is_encumbered():
            evasion = max(0, evasion - 20)
        if self.has_item("stealth orb"):
            evasion += 30
        return max(1, evasion * self.get_health_ratio())

    # Effective offense with health ratio
    def get_effective_combat_offense(self):
        courage = self.get_effective_stat_level("courage")
        coordination = self.get_effective_stat_level("coordination")
        military_science = self.get_effective_skill_level("military science")
        offense = (courage + coordination) / 2
        offense += (military_science / 10)
        if self.has_item("offense implant"):
            imp = self.get_item("offense implant")
            offense += imp.effect if imp else 50
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
            evasion = max(0, evasion - 20)
        if self.has_item("exoskeleton") or self.has_item("powered armor"):
            if self.has_skill("Exoskeleton Systems"):
                evasion += self.get_effective_skill_level("Exoskeleton Systems") / 4
        strength = self.get_effective_stat_level("strength")
        return max(1, (evasion + strength) * self.get_health_ratio())

    def has_ranged_weapon(self):
        return any(
            item.type == "weapon" and item_base_name(item.name) in self._RANGED_BASES
            for item in self.equipment
        )

    def has_melee_weapon(self):
        return any(
            item.type == "weapon" and item_base_name(item.name) in self._MELEE_BASES
            for item in self.equipment
        )

    def has_helmet(self) -> bool:
        """Return True if the character has a helmet armor item equipped."""
        return any(item.is_helmet() for item in self.equipment)

    def has_body_armor(self) -> bool:
        """Return True if the character has a non-helmet body armor item equipped."""
        return any(item.is_body_armor() for item in self.equipment)

    def can_equip_item(self, item: "Item") -> tuple[bool, str | None]:
        """Return (allowed, error_message) for equipping *item* on this character.
        Enforces max 2 weapons and max 2 armors (at most 1 helmet + 1 body armor).
        """
        if item.type == "weapon" and self.get_weapon_count() >= 2:
            return False, "Max two weapons per character"
        if item.type == "armor":
            if self.get_armor_count() >= 2:
                return False, "Max two armors per character"
            if item.is_helmet() and self.has_helmet():
                return False, "Max one helmet per character"
            if item.is_body_armor() and self.has_body_armor():
                return False, "Max one body armor per character"
        return True, None

    def has_item(self, item_name):
        """Return True if the character carries any item whose base name matches item_name.
        Strips class suffix so callers can use bare names like 'laser pistol' regardless
        of quality tier ('laser pistol C', 'laser pistol B', etc.)."""
        from Item import item_base_name
        for item in self.equipment:
            if item_base_name(item.name) == item_name or item.name == item_name:
                return True
        return False

    def get_item(self, item_name):
        """Return the first equipped Item whose base name matches item_name, or None."""
        from Item import item_base_name
        for item in self.equipment:
            if item_base_name(item.name) == item_name or item.name == item_name:
                return item
        return None

    def has_skill(self, skill_name):
        if skill_name is None:
            return False
        if skill_name in self.skills:
              return True
        return False

    def add_item(self, item: "Item"):
        """Adds an Item object to the character's equipment."""
        if isinstance(item, Item):
            had_stim = self.has_item("stimulant")
            self.equipment.append(item.copy())
            if not self.is_robot() and self.current_health > 0 and item_base_name(item.name) == "stimulant" and not had_stim:
                self.current_health = min(self.get_max_health(), self.current_health + item.effect * 2)
        else:
            raise ValueError("Only Item instances can be added to equipment.")

    def remove_item(self, item_name):
        for i, item in enumerate(self.equipment):
            if item.name == item_name:
                del self.equipment[i]
                if not self.is_robot() and item_base_name(item_name) == "stimulant":
                    self.current_health = min(self.current_health, self.get_max_health())
                return

    def remove_random_item(self):
        random_item = random.choice(self.equipment)
        self.remove_item(random_item.name)

    def list_equipment(self):
        """Returns a list of equipment names."""
        return [item.name for item in self.equipment]

    def assign_skills(self, intelligence, willpower):
        # Randomly select 3 to 6 unique skills from the list, gated by non-red stats
        num_skills = random.randint(3, 6)
        if intelligence > 75:
            num_skills += 1
        elif intelligence < 50:
            num_skills -= 1
        if willpower > 75:
            num_skills += 1
        elif willpower < 50:
            num_skills -= 1
        eligible_skills = [s for s in self.possible_skills if self.is_skill_allowed(s)]
        num_skills = max(0, min(num_skills, len(eligible_skills)))
        selected_skills = random.sample(eligible_skills, num_skills) if num_skills > 0 else []

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
        "Energy Weapons", "Sonic Weapons", "Physics", "Projectile Weapons", "Artifact Analysis", "Squad Tactics", "Mech Combat",
        "Exoskeleton Systems", "Resource Extraction", "Detection",
        "Weaponsmithing", "Armorsmithing", "Tinkering",
        "Supply Logistics"
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
        "brawn": "Raw muscular force and lifting power",
        "stamina": "Physical endurance and sustained exertion",
        "resilience": "Toughness and resistance to physical trauma",
        "fine_manipulation": "Manual dexterity and precision hand control",
        "agility": "Whole-body balance, footwork, and nimbleness",
        "reflexes": "Reaction speed and split-second timing",
        "logic": "Deductive reasoning and analytical problem-solving",
        "memory": "Information recall and technical knowledge retention",
        "guile": "Cunning, tactical misdirection, and street smarts",
        "focus": "Mental concentration and attention under pressure",
        "composure": "Emotional steadiness and calm in crisis",
        "tenacity": "Grit, determination, and refusal to give up",
        "beauty": "Physical presence and striking appearance",
        "charm": "Warmth, likability, and persuasive appeal",
        "command": "Force of personality and natural authority",
        "valor": "Bravery in the face of physical danger",
        "nerve": "Cool-headedness under fire and high stakes",
        "resolve": "Unwavering commitment to the mission",
        "offense": "Calculates attack potential in combat",
        "defense": "Indicates resilience in combat",
        "deception": "Ability to mislead and manipulate",
        "evasion": "Capability to avoid detection and attacks",
        "analyze": "Skill in examining and understanding unknown objects",
        "max_health": "Overall health and vitality",
        "movement": "Speed and agility in movement",
        "meleecombat": "Skill in close-quarters combat",
        "surprise": "Capability to catch others off-guard",
        "leadership": "Ability to inspire loyalty and lead others",
        "perception": "Ability to observe environment and notice threats"
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
        "Weaponsmithing": "Ability to upgrade and improve the quality of weapons",
        "Armorsmithing": "Ability to upgrade and improve the quality of armor",
        "Tinkering": "Ability to upgrade and improve the quality of miscellaneous gear",
        "Supply Logistics": "Skill in managing and planning consumable resources and supplies",
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

    def generate_random_sub_stats(self):
        sub_stats = {}
        bases = {core_stat: self.bell_curve_stat() for core_stat in self.SUB_STAT_MAP}
        # Ensure at least 2 core stat groups are non-red (>= 50) so gated skills are always available
        non_red = [k for k, v in bases.items() if v >= 54]
        if len(non_red) < 2:
            for k in sorted(bases, key=lambda c: bases[c], reverse=True)[:2]:
                bases[k] = max(bases[k], random.randint(55, 68))

        for core_stat, sub_tuple in self.SUB_STAT_MAP.items():
            base = bases[core_stat]
            min_bound = 50 if base >= 54 else 25
            low = max(min_bound, base - 10)
            high = min(95, low + 20)
            low = max(min_bound, high - 20)
            for sub_name in sub_tuple:
                val = int(random.gauss(base, 6))
                sub_stats[sub_name] = max(low, min(high, val))
        return sub_stats

    def recalculate_stats(self):
        """Compute the 6 core attributes and 11 derived stats from the 18 sub-stats."""
        if not hasattr(self, "sub_stats") or not self.sub_stats:
            self.sub_stats = {}
            for core_stat, sub_tuple in self.SUB_STAT_MAP.items():
                base_val = self.stats.get(core_stat, 60) if hasattr(self, "stats") and self.stats else 60
                for sub_name in sub_tuple:
                    self.sub_stats[sub_name] = base_val

        s = self.sub_stats
        strength = round((s["brawn"] + s["stamina"] + s["resilience"]) / 3)
        intelligence = round((s["logic"] + s["memory"] + s["guile"]) / 3)
        willpower = round((s["focus"] + s["composure"] + s["tenacity"]) / 3)
        coordination = round((s["fine_manipulation"] + s["agility"] + s["reflexes"]) / 3)
        charisma = round((s["beauty"] + s["charm"] + s["command"]) / 3)
        courage = round((s["valor"] + s["nerve"] + s["resolve"]) / 3)

        offense = round((s["reflexes"] + s["nerve"] + s["focus"]) / 3)
        defense = round((s["agility"] + s["resilience"] + s["composure"]) / 3)
        deception = round((s["guile"] + s["charm"] + s["nerve"]) / 3)
        evasion = round((s["agility"] + s["reflexes"] + s["guile"]) / 3)
        analyze = round((s["logic"] + s["memory"] + s["focus"]) / 3)
        max_health = round((s["stamina"] + s["resilience"] + s["tenacity"]) * 2 / 3)
        movement = s["brawn"] + s["stamina"] + s["agility"]
        meleecombat = evasion + round((s["brawn"] + s["valor"]) / 2)
        perception = round((s["focus"] + s["reflexes"] + s["memory"]) / 3)
        surprise = evasion + perception
        leadership = s["command"] + s["resolve"] + s["logic"]

        self.stats = {
            "strength": strength,
            "intelligence": intelligence,
            "willpower": willpower,
            "coordination": coordination,
            "charisma": charisma,
            "courage": courage,
            "offense": offense,
            "defense": defense,
            "deception": deception,
            "evasion": evasion,
            "analyze": analyze,
            "max_health": max_health,
            "movement": movement,
            "meleecombat": meleecombat,
            "surprise": surprise,
            "leadership": leadership,
            "perception": perception,
        }
        return self.stats

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

    def to_dict(self):
        """Converts the character to a dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "index": self.index,
            "stats": self.stats,
            "sub_stats": self.sub_stats,
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
            "current_health": self.current_health,
            "max_life": self.max_life,
            # Store each item in equipment as a serializable dictionary without the 'icon' pygame surface
            # Store equipment as a list of dictionaries (Item's `__dict__`).
            "equipment": [item.to_dict() for item in self.equipment],
            # Interaction data
            "interaction_likes":    self.interaction_likes,
            "interaction_liked_by": self.interaction_liked_by,
            "relationships":        self.relationships,
            # Skills learning system
            "learning_skills_dict": self.learning_skills_dict,
            # Command role and formation position
            "command_role": self.command_role,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        """Creates a Character (or Robot) instance from a dictionary."""
        if data.get("type") == "robot" and cls is Character:
            character = _robot_mod.Robot(data["index"])
        else:
            character = cls(data["index"], data["type"])
        character.name = data["name"]
        character.type = data["type"]
        character.stats = data["stats"]
        if "sub_stats" in data and data["sub_stats"]:
            character.sub_stats = dict(data["sub_stats"])
        else:
            character.sub_stats = {}
            for core_stat, sub_tuple in cls.SUB_STAT_MAP.items():
                core_val = character.stats.get(core_stat, 60)
                for sub_name in sub_tuple:
                    character.sub_stats[sub_name] = core_val
        character.occupation = data["occupation"]
        character.homeworld = data["homeworld"]
        character.event = data["event"]
        character.goal = data["goal"]
        character.history = data["history"]
        character.skills = data["skills"]
        character.vetted = data["vetted"]
        character.psychotic = data["psychotic"]
        character.traitor = data["traitor"]
        character.morale         = data["morale"]
        character.max_life       = data.get("max_life", 0)
        character.current_health = data.get("current_health", character.stats.get("max_health", 0))
        if "mission" in data:
            character.mission = data["mission"]
        if "mission points" in data:
            character.mission_points = data["mission points"]
        character.equipment = [Item.from_dict(item_data) for item_data in data["equipment"]]  # Recreate items

        # Interaction data — use defaults if loading an older save that lacks these keys
        _neutral = {k: 0 for k in InteractionType.ALL}
        character.interaction_likes    = data.get("interaction_likes",    _neutral.copy())
        character.interaction_liked_by = data.get("interaction_liked_by", _neutral.copy())
        character.relationships        = data.get("relationships",        {})

        # Skills learning system — fall back to all-zeros for older saves
        _zero_learning = {skill: 0 for skill in cls.possible_skills}
        saved_learning  = data.get("learning_skills_dict", {})
        _zero_learning.update(saved_learning)          # keep any extra skills that may exist in the save
        character.learning_skills_dict = _zero_learning

        character.command_role = data.get("command_role", None)
        character.position     = data.get("position", None)

        if data["type"] == "robot":
            character.portrait = _robot_mod.Robot.load_robot_portrait(character.occupation)

        return character


from Battle import BattleAction
from Item import *
import Robot as _robot_mod

