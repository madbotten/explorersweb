import pygame
from Utils import resource_path

# Store attributes for robots: (cost, mass, rate, effect, effect_type, hp, item_type, description)
# Robots have no quality tiers (C/B/A/S) and are purchased in the Equip Team store's "Robots" tab.
ROBOT_ATTRIBUTES = {
    "assaultbot": (500, 0, 3, 20, "impact", 200, "robot", "A fearless humanoid combat robot that can lead chamber breaches and fight enemies with the team"),
    "techbot":    (350, 0, 1,  1, "impact",  50, "robot", "A tech robot that can repair electronics and small misc items"),
    "hackbot":    (200, 0, 1,  1, "impact",  50, "robot", "A robot that can mesh with electronic interfaces and hack enemy systems"),
    "mechbot":    (250, 0, 1,  5, "impact",  50, "robot", "A repair robot that can repair structural or mechanical systems"),
    "mulebot":    (250, 0, 1,  1, "impact",  50, "robot", "A robot to carry food, ammo, and currently unused items to prevent team members from being encumbered"),
    "scoutbot":   (150, 0, 1,  1, "impact",  20, "robot", "A scout robot that helps prevent the team from being surprised"),
    "meleebot":   (275, 0, 3, 20, "impact", 200, "robot", "A melee robot with short range cutters"),
    "medibot":    (500, 0, 1,  5, "impact",  50, "robot", "A medical robot that provides healing and medical supplies"),
    "stunbot":    (350, 0, 2, 20, "sonic",  200, "robot", "A robot with ranged nonlethal weapons"),
    "batonbot":   (250, 0, 2, 20, "impact", 200, "robot", "A melee robot with nonlethal stun batons"),
}

ROBOT_SPECS = {
    "assaultbot": {
        "prefix": "ASB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 75, "defense": 75,
            "evasion": 50, "deception": 50, "analyze": 10, "movement": 30,
            "meleecombat": 10, "surprise": 175, "leadership": 5, "perception": 30,
        },
        "skills": {"Energy Weapons": 75, "Mech Combat": 50},
        "equipment": ("laser pistol", "power shield"),
    },
    "stunbot": {
        "prefix": "STB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 75, "defense": 75,
            "evasion": 50, "deception": 50, "analyze": 10, "movement": 30,
            "meleecombat": 10, "surprise": 125, "leadership": 5, "perception": 30,
        },
        "skills": {"Sonic Weapons": 75, "Mech Combat": 50},
        "equipment": ("stunner", "power shield"),
    },
    "mechbot": {
        "prefix": "MKB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 10,
            "evasion": 30, "deception": 30, "analyze": 35, "movement": 30,
            "meleecombat": 5, "surprise": 20, "leadership": 5, "perception": 30,
        },
        "skills": {"Robot Repair": 65, "Fabrication": 35, "Mechanics": 50},
        "equipment": ("stunner",),
    },
    "techbot": {
        "prefix": "TKB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 10,
            "evasion": 40, "deception": 30, "analyze": 65, "movement": 30,
            "meleecombat": 5, "surprise": 20, "leadership": 5, "perception": 50,
        },
        "skills": {
            "Robot Repair": 65, "Ships Systems": 55, "Fabrication": 15,
            "Artifact Analysis": 45, "Hacking": 35,
        },
        "equipment": ("stunner",),
    },
    "hackbot": {
        "prefix": "HKB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 10,
            "evasion": 40, "deception": 30, "analyze": 45, "movement": 30,
            "meleecombat": 5, "surprise": 20, "leadership": 5, "perception": 60,
        },
        "skills": {
            "Robot Repair": 15, "Ships Systems": 45, "Fabrication": 10,
            "Artifact Analysis": 25, "Hacking": 75,
        },
        "equipment": ("stunner",),
    },
    "meleebot": {
        "prefix": "MEB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 75, "defense": 75,
            "evasion": 75, "deception": 40, "analyze": 5, "movement": 75,
            "meleecombat": 75, "surprise": 150, "leadership": 5, "perception": 30,
        },
        "skills": {"Martial Arts": 75, "Mech Combat": 50},
        "equipment": ("slicer", "veer suit"),
    },
    "batonbot": {
        "prefix": "BAB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 75, "defense": 75,
            "evasion": 50, "deception": 40, "analyze": 5, "movement": 75,
            "meleecombat": 75, "surprise": 150, "leadership": 5, "perception": 30,
        },
        "skills": {"Martial Arts": 75, "Mech Combat": 50},
        "equipment": ("stun baton", "veer suit"),
    },
    "medibot": {
        "prefix": "MDB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 10,
            "evasion": 30, "deception": 40, "analyze": 15, "movement": 30,
            "meleecombat": 5, "surprise": 20, "leadership": 5, "perception": 40,
        },
        "skills": {"Medicine": 75, "Xenobiology": 50},
        "equipment": ("stun baton", "medikit"),
    },
    "mulebot": {
        "prefix": "MUB",
        "stats": {
            "strength": 50, "intelligence": 30, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 10,
            "evasion": 30, "deception": 30, "analyze": 15, "movement": 30,
            "meleecombat": 5, "surprise": 20, "leadership": 5, "perception": 30,
        },
        "skills": {},
        "equipment": ("stun baton",),
    },
    "scoutbot": {
        "prefix": "SCB",
        "stats": {
            "strength": 30, "intelligence": 50, "willpower": 90, "coordination": 80,
            "charisma": 10, "courage": 95, "offense": 10, "defense": 60,
            "evasion": 85, "deception": 50, "analyze": 15, "movement": 125,
            "meleecombat": 5, "surprise": 150, "leadership": 5, "perception": 75,
        },
        "skills": {"Stealth": 50, "Espionage": 50, "Detection": 75},
        "equipment": ("stunner", "scanner"),
    },
}


def get_robot_cost(robot_type: str) -> int:
    """Return the store purchase/refund cost for *robot_type* (0 if unknown)."""
    return ROBOT_ATTRIBUTES.get(robot_type, (0,))[0]


from Character import Character


class Robot(Character):
    """A robotic team member (type == 'robot')."""

    def __init__(self, index: int, occupation: str | None = None):
        super().__init__(index, "robot")
        if occupation:
            self.occupation = occupation

    @staticmethod
    def load_robot_portrait(occupation: str, size=(70, 80)):
        portrait_path = resource_path(f"gadgets/{occupation}.jpg")
        try:
            img = pygame.image.load(portrait_path)
            return pygame.transform.scale(img, size)
        except pygame.error:
            print(f"Failed to load robot portrait: {portrait_path}")
            return None

    @classmethod
    def create(cls, robot_type: str, index: int, all_items: dict) -> "Robot | None":
        """Create and return a configured Robot instance for *robot_type*, or None if unknown."""
        spec = ROBOT_SPECS.get(robot_type)
        if spec is None:
            return None

        robot = cls(index, occupation=robot_type)
        robot.occupation = robot_type
        robot.history = "A robot."
        robot.name = f"{spec['prefix']}{index}"
        robot.portrait = cls.load_robot_portrait(robot_type)

        if all_items and robot_type in all_items:
            max_life = all_items[robot_type].hp
        else:
            max_life = ROBOT_ATTRIBUTES[robot_type][5]

        robot.max_life = max_life
        robot.stats["max_health"] = max_life
        robot.current_health = max_life
        for stat_name, val in spec["stats"].items():
            robot.stats[stat_name] = val

        robot.skills = dict(spec["skills"])
        if all_items:
            for item_key in spec["equipment"]:
                if item_key in all_items:
                    robot.add_item(all_items[item_key])

        return robot

    @classmethod
    def add_to_team(cls, team: list, robot_type: str, all_items: dict) -> "Robot | None":
        """Create a Robot of *robot_type*, append it to *team*, and sync team references."""
        index = sum(1 for m in team if m is not None)
        robot = cls.create(robot_type, index, all_items)
        if robot is None:
            return None
        robot.team = team
        team.append(robot)
        for member in team:
            if member is not None:
                member.team = team
        return robot


    @classmethod
    def create_assaultbot(cls, index: int, all_items: dict) -> "Robot":
        return cls.create("assaultbot", index, all_items)

    @classmethod
    def create_stunbot(cls, index: int, all_items: dict) -> "Robot":
        return cls.create("stunbot", index, all_items)

    @classmethod
    def create_mechbot(cls, index: int, all_items: dict) -> "Robot":
        return cls.create("mechbot", index, all_items)

    @classmethod
    def create_techbot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("techbot", i, all_items)

    @classmethod
    def create_hackbot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("hackbot", i, all_items)

    @classmethod
    def create_meleebot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("meleebot", i, all_items)

    @classmethod
    def create_batonbot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("batonbot", i, all_items)

    @classmethod
    def create_medibot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("medibot", i, all_items)

    @classmethod
    def create_mulebot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("mulebot", i, all_items)

    @classmethod
    def create_scoutbot(cls, i: int, all_items: dict) -> "Robot":
        return cls.create("scoutbot", i, all_items)


# Attach backward-compatible factory aliases onto Character
Character.create_assaultbot = Robot.create_assaultbot
Character.create_stunbot = Robot.create_stunbot
Character.create_mechbot = Robot.create_mechbot
Character.create_techbot = Robot.create_techbot
Character.create_hackbot = Robot.create_hackbot
Character.create_meleebot = Robot.create_meleebot
Character.create_batonbot = Robot.create_batonbot
Character.create_medibot = Robot.create_medibot
Character.create_mulebot = Robot.create_mulebot
Character.create_scoutbot = Robot.create_scoutbot

