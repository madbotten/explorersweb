import pygame
import random

from Utils import *

# Item attributes: cost, mass, rate, damage, damage type, hp, type, description
# NOTE: robots are in ROBOT_ATTRIBUTES below to keep them separate for the quality system.
ITEM_ATTRIBUTES = {
    "power shield":   (200, 15, 1, 1,  "impact", 50,  "armor",  "A protective item that can absorb some damage from energy attacks"),
    "veer suit":      (200, 7,  1, 1,  "impact", 100, "armor",  "A protective suit that protects against ballistic and melee impacts"),
    "exoskeleton":    (250, 1,  2, 20, "impact", 150, "armor",  "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "holofier":       (400, 10, 1, 50, "impact", 40,  "armor",  "Projects holograms of the wearer, causing some attacks to miss"),
    "powered armor":  (750, 0,  1, 50, "impact", 200, "armor",  "Elite shock troop armor that eliminates encumbrance"),
    "scanner":        (100, 4,  1, 1,  "impact", 30,  "misc",   "An item that helps identify unknown objects"),
    "medikit":        (150, 5,  1, 1,  "impact", 40,  "misc",   "A medical kit that helps team members heal injuries"),
    "stimulant":      (100, 1,  1, 1,  "impact", 10,  "misc",   "A powerful stimulant that allows for overhealing beyond base life level"),
    "cutter":         (125, 8,  1, 5,  "impact", 50,  "misc",   "A tool used to cut through bulkheads and locked portals"),
    "bio container":  (75,  3,  1, 1,  "impact", 50,  "misc",   "A rugged container suitable for carrying isolated biological samples"),
    "stealth orb":    (400, 10, 2, 50, "impact", 50,  "misc",   "Blurs image of the wearer and suppresses noise"),
    "pacifier":       (650, 10, 5, 50, "impact", 40,  "misc",   "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "offense implant":(650, 1,  1, 50, "impact", 100, "misc",   "Provides superhuman combat efficiency and accuracy"),
    "neural trainer": (650, 1,  1, 50, "impact", 100, "misc",   "Endows recipient with at least 10 in all skills"),
    "magnum":         (300, 4,  1, 30, "impact", 40,  "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "laser pistol":   (500, 3,  2, 20, "energy", 40,  "weapon", "A precise energy weapon"),
    "pistol":         (100, 2,  3, 10, "impact", 40,  "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "slicer":         (350, 6,  2, 30, "impact", 50,  "weapon", "A powered melee weapon"),
    "stunner":        (200, 3,  1, 20, "sonic",  40,  "weapon", "A nonlethal weapon that disables humanoids"),
    "carbine":        (550, 10, 5, 10, "impact", 50,  "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "launcher":       (600, 10, 1, 30, "impact", 40,  "weapon", "Launches missiles in first combat round, damaging targets in an area"),
    "laser rifle":    (700, 10, 1, 50, "energy", 40,  "weapon", "A powerful, heavy, expensive laser weapon"),
    "blaster rifle":  (500, 10, 1, 50, "sonic",  40,  "weapon", "A powerful sonic rifle, but useless against robots"),
    "stun baton":     (250, 4,  2, 20, "sonic",  200, "weapon", "A nonlethal melee weapon"),
}

# Robot attributes: cost, mass, rate, damage, damage type, hp, type, description
ROBOT_ATTRIBUTES = {
    "assaultbot": (500, 0, 3, 20, "impact", 200, "robot", "A fearless humanoid combat robot that can lead chamber breaches and fight enemies with the team"),
    "techbot":    (350, 0, 1, 1,  "impact",  50, "robot", "A tech robot that can repair electronics and small misc items"),
    "hackbot":    (200, 0, 1, 1,  "impact",  50, "robot", "A robot that can mesh with electronic interfaces and hack enemy systems"),
    "mechbot":    (250, 0, 1, 5,  "impact",  50, "robot", "A repair robot that can repair structural or mechanical systems"),
    "mulebot":    (250, 0, 1, 1,  "impact",  50, "robot", "A robot to carry food, ammo, and currently unused items to prevent team members from being encumbered"),
    "scoutbot":   (150, 0, 1, 1,  "impact",  20, "robot", "A scout robot that helps prevent the team from being surprised"),
    "meleebot":   (275, 0, 3, 20, "impact", 200, "robot", "A melee robot with short range cutters"),
    "medibot":    (500, 0, 1, 5,  "impact",  50, "robot", "A medical robot that provides healing and medical supplies"),
    "stunbot":    (350, 0, 2, 20, "sonic",  200, "robot", "A robot with ranged nonlethal weapons"),
    "batonbot":   (250, 0, 2, 20, "impact", 200, "robot", "A melee robot with nonlethal stun batons"),
}

# Combined lookup: items first, then robots.
# Use this anywhere you need to look up any name regardless of category.
ALL_ATTRIBUTES = {**ITEM_ATTRIBUTES, **ROBOT_ATTRIBUTES}

# protection vs energy, sonic, impact, slash, pierce, concussion, electric
ARMOR_ATTRIBUTES = {
    "power shield": (8, 0, 0, 0, 0, 0, 3),
    "veer suit":    (5, 5, 5, 5, 5, 5, 5),
    "exoskeleton":  (3, 3, 3, 3, 3, 5, 5),
    "holofield":    (0, 0, 0, 0, 0, 0, 0),
    "powered armor":(8, 10, 10, 10, 8, 10, 8),
}

# Tab names and types
TABS = ["weapons", "armor", "robots", "misc"]

class Item:
    def __init__(self, name, item_type, cost, mass, rate, damage, damage_type, hp, description, icon=None, rect=None):
        self.name = name
        self.type = item_type
        self.cost = cost
        self.mass = mass
        self.rate = rate
        self.damage = damage
        self.damage_type = damage_type
        self.hp = hp
        self.description = description
        self.icon = icon  # Pygame Surface for the item icon
        self.rect = rect if rect else pygame.Rect(0, 0, 50, 50)

    def __repr__(self):
        return f"Item(name={self.name}, type={self.type}, cost={self.cost}, mass={self.mass}, rate={self.rate}, damage={self.damage}, hp={self.hp})"

    def set_rect(self, rect):
        self.rect = rect

    def get_rect(self):
        return self.rect

    @classmethod
    def from_data(cls, name, attributes, icon=None):
        cost, mass, rate, damage, damage_type, hp, item_type, description = attributes
        rect = pygame.Rect(0, 0, 50, 50)
        return cls(name, item_type, cost, mass, rate, damage, damage_type, hp, description, icon, rect)

    def to_dict(self):
        """Converts the Item to a serializable dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "cost": self.cost,
            "mass": self.mass,
            "rate": self.rate,
            "damage": self.damage,
            "damage_type": self.damage_type,
            "hp": self.hp,
            "description": self.description
            # Exclude 'icon' because it is not serializable
        }

    @classmethod
    def load_icon(cls, item_name):
        icon_path = resource_path(f"gadgets/{item_name}.jpg")
        try:
            icon = pygame.image.load(icon_path)
            icon = pygame.transform.scale(icon, (50, 50))
            return icon
        except pygame.error:
            print(f"Failed to load icon for {item_name}. Using placeholder.")
            return None  # Return None or a default icon if the loading fails

    @classmethod
    def from_dict(cls, data):
        icon = cls.load_icon(data["name"])
        return cls(
            name=data["name"],
            item_type=data["type"],
            cost=data["cost"],
            mass=data["mass"],
            rate=data["rate"],
            damage=data["damage"],
            damage_type=data["damage_type"],
            hp=data["hp"],
            description=data["description"],
            icon = icon
        )

    def copy(self):
        return Item(
            self.name,
            self.type,
            self.cost,
            self.mass,
            self.rate,
            self.damage,
            self.damage_type,
            self.hp,
            self.description,
            self.icon,
            self.rect.copy() if self.rect else None
        )

def load_items():
    items = {}
    tab_dir = resource_path("gadgets/")

    for file_name in os.listdir(tab_dir):
        if file_name.endswith(".jpg"):
            name = file_name.split(".")[0]
            # Check items first, then robots
            attributes = ITEM_ATTRIBUTES.get(name) or ROBOT_ATTRIBUTES.get(name)
            if attributes is None:
                print(f"Warning: no attributes found for '{name}', skipping.")
                continue
            icon_path = resource_path(tab_dir + "/" + file_name)

            try:
                icon = pygame.image.load(icon_path)
                icon = pygame.transform.scale(icon, (50, 50))
            except pygame.error:
                print(f"Failed to load image for {name}")
                icon = None

            items[name] = Item.from_data(name, attributes, icon)

    return items

def load_items_battle():
    items = {}
    tab_dir = resource_path("gadgets/")

    for file_name in os.listdir(tab_dir):
        if file_name.endswith(".jpg"):
            name = file_name.split(".")[0]
            # Check items first, then robots
            attributes = ITEM_ATTRIBUTES.get(name) or ROBOT_ATTRIBUTES.get(name)
            if attributes is None:
                print(f"Warning: no attributes found for '{name}', skipping.")
                continue
            icon_path = resource_path(tab_dir + "/" + file_name)

            try:
                icon = pygame.image.load(icon_path)
                icon = pygame.transform.scale(icon, (40, 40))
            except pygame.error:
                print(f"Failed to load image for {name}")
                icon = None

            items[name] = Item.from_data(name, attributes, icon)

    return items

def load_item_tabs():
    items_by_tab = {tab: [] for tab in TABS}
    all_items = load_items()
    for item in all_items.values():
        if item.type == "weapon":
            items_by_tab["weapons"].append(item)
        elif item.type == "armor":
            items_by_tab["armor"].append(item)
        elif item.type == "robot":
            items_by_tab["robots"].append(item)
        else:
            items_by_tab["misc"].append(item)

    return items_by_tab
