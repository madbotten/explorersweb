import pygame
import random

from Utils import *

ITEM_CLASSES = ["C", "B", "A", "S"]

def item_base_name(item_name: str) -> str:
    parts = item_name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1] in ITEM_CLASSES:
        return parts[0]
    return item_name

def item_class(item_name: str) -> str | None:
    parts = item_name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1] in ITEM_CLASSES:
        return parts[1]
    return None

# Next-class map: bare/None items without a suffix are treated as pre-C (upgrade to B)
_NEXT_CLASS = {None: "B", "C": "B", "B": "A", "A": "S", "S": None}

def upgrade_item_class(item, all_items: dict):
    """Return the next-tier Item for *item* (C→B→A→S), or None if already S or unknown.

    Looks up the upgraded name in *all_items* first; falls back to ALL_ATTRIBUTES.
    all_items is a dict of name -> Item (e.g. from load_items()).
    """
    next_cls = _NEXT_CLASS.get(item_class(item.name))
    if next_cls is None:
        return None
    upgraded_name = f"{item_base_name(item.name)} {next_cls}"
    if upgraded_name in all_items:
        return all_items[upgraded_name]
    # Lazy fallback: build directly from the attribute table
    if upgraded_name in ALL_ATTRIBUTES:
        return Item.from_data(upgraded_name, ALL_ATTRIBUTES[upgraded_name])
    return None

def replace_item_in_inventory(member, old_item, new_item) -> bool:
    """Swap *old_item* for *new_item* in *member*.equipment in-place.
    Returns True if the swap was performed.
    """
    for i, it in enumerate(member.equipment):
        if it is old_item:
            member.equipment[i] = new_item
            return True
    return False

# Item attributes: cost, mass, rate, effect, effect_type, hp, item_type, description
# Stats scale per tier: cost +5%, mass -5% (floor, min 0), effect +5%, hp +5%.
# Robots are in ROBOT_ATTRIBUTES and have no quality tiers.
ITEM_ATTRIBUTES = {
    # ---- power shield (effect = base protection; strong vs energy) ----
    "power shield":   (200, 15, 1, 30, "impact",  50, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield C": (200, 15, 1, 30, "impact",  50, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield B": (210, 14, 1, 32, "impact",  53, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield A": (220, 13, 1, 33, "impact",  55, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield S": (230, 12, 1, 35, "impact",  58, "armor", "A protective item that can absorb some damage from energy attacks"),
    # ---- veer suit (moderate all-round protection) ----
    "veer suit":   (200, 7, 1, 20, "impact", 100, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit C": (200, 7, 1, 20, "impact", 100, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit B": (210, 6, 1, 21, "impact", 105, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit A": (220, 6, 1, 22, "impact", 110, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit S": (230, 5, 1, 23, "impact", 115, "armor", "A protective suit that protects against ballistic and melee impacts"),
    # ---- exoskeleton (good vs impact; adds strength) ----
    "exoskeleton":   (250, 1, 2, 25, "impact", 150, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton C": (250, 1, 2, 25, "impact", 150, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton B": (263, 1, 2, 26, "impact", 158, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton A": (275, 1, 2, 28, "impact", 165, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton S": (288, 1, 2, 29, "impact", 173, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    # ---- holofier (effect = miss-chance roll penalty applied to attackers) ----
    "holofier":   (400, 10, 1, 25, "impact", 40, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier C": (400, 10, 1, 25, "impact", 40, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier B": (420,  9, 1, 26, "impact", 42, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier A": (440,  9, 1, 28, "impact", 44, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier S": (460,  8, 1, 29, "impact", 46, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    # ---- powered armor (elite; full impact coverage) ----
    "powered armor":   (750, 0, 1, 40, "impact", 200, "armor", "Elite shock troop armor that eliminates encumbrance"),
    "powered armor C": (750, 0, 1, 40, "impact", 200, "armor", "Elite shock troop armor that eliminates encumbrance"),
    "powered armor B": (788, 0, 1, 42, "impact", 210, "armor", "Elite shock troop armor that eliminates encumbrance"),
    "powered armor A": (825, 0, 1, 44, "impact", 220, "armor", "Elite shock troop armor that eliminates encumbrance"),
    "powered armor S": (863, 0, 1, 46, "impact", 230, "armor", "Elite shock troop armor that eliminates encumbrance"),
    # ---- scanner ----
    "scanner":   (100, 4, 1, 20, "impact", 30, "misc", "An item that helps identify unknown objects"),
    "scanner C": (100, 4, 1, 20, "impact", 30, "misc", "An item that helps identify unknown objects"),
    "scanner B": (105, 3, 1, 21, "impact", 32, "misc", "An item that helps identify unknown objects"),
    "scanner A": (110, 3, 1, 22, "impact", 33, "misc", "An item that helps identify unknown objects"),
    "scanner S": (115, 3, 1, 23, "impact", 35, "misc", "An item that helps identify unknown objects"),
    # ---- medikit (effect = healing power) ----
    "medikit":   (150, 5, 1, 60, "impact", 40, "misc", "A medical kit that helps team members heal injuries"),
    "medikit C": (150, 5, 1, 60, "impact", 40, "misc", "A medical kit that helps team members heal injuries"),
    "medikit B": (158, 4, 1, 63, "impact", 42, "misc", "A medical kit that helps team members heal injuries"),
    "medikit A": (165, 4, 1, 66, "impact", 44, "misc", "A medical kit that helps team members heal injuries"),
    "medikit S": (173, 4, 1, 69, "impact", 46, "misc", "A medical kit that helps team members heal injuries"),
    # ---- stimulant ----
    "stimulant":   (100, 1, 1, 25, "impact", 10, "misc", "A powerful stimulant that allows for overhealing beyond base life level"),
    "stimulant C": (100, 1, 1, 25, "impact", 10, "misc", "A powerful stimulant that allows for overhealing beyond base life level"),
    "stimulant B": (105, 0, 1, 26, "impact", 11, "misc", "A powerful stimulant that allows for overhealing beyond base life level"),
    "stimulant A": (110, 0, 1, 28, "impact", 11, "misc", "A powerful stimulant that allows for overhealing beyond base life level"),
    "stimulant S": (115, 0, 1, 29, "impact", 12, "misc", "A powerful stimulant that allows for overhealing beyond base life level"),
    # ---- cutter ----
    "cutter":   (125, 8, 1, 30, "impact", 50, "misc", "A tool used to cut through bulkheads and locked portals"),
    "cutter C": (125, 8, 1, 30, "impact", 50, "misc", "A tool used to cut through bulkheads and locked portals"),
    "cutter B": (131, 7, 1, 32, "impact", 53, "misc", "A tool used to cut through bulkheads and locked portals"),
    "cutter A": (138, 7, 1, 33, "impact", 55, "misc", "A tool used to cut through bulkheads and locked portals"),
    "cutter S": (144, 6, 1, 35, "impact", 58, "misc", "A tool used to cut through bulkheads and locked portals"),
    # ---- bio container ----
    "bio container":   (75, 3, 1, 10, "impact", 50, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container C": (75, 3, 1, 10, "impact", 50, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container B": (79, 2, 1, 11, "impact", 53, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container A": (83, 2, 1, 11, "impact", 55, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container S": (86, 2, 1, 12, "impact", 58, "misc", "A rugged container suitable for carrying isolated biological samples"),
    # ---- stealth orb ----
    "stealth orb":   (400, 10, 2, 40, "impact", 50, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb C": (400, 10, 2, 40, "impact", 50, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb B": (420,  9, 2, 42, "impact", 53, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb A": (440,  9, 2, 44, "impact", 55, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb S": (460,  8, 2, 46, "impact", 58, "misc", "Blurs image of the wearer and suppresses noise"),
    # ---- pacifier ----
    "pacifier":   (650, 10, 5, 50, "impact", 40, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier C": (650, 10, 5, 50, "impact", 40, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier B": (683,  9, 5, 53, "impact", 42, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier A": (715,  9, 5, 55, "impact", 44, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier S": (748,  8, 5, 58, "impact", 46, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    # ---- offense implant ----
    "offense implant":   (650, 1, 1, 50, "impact", 100, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant C": (650, 1, 1, 50, "impact", 100, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant B": (683, 0, 1, 53, "impact", 105, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant A": (715, 0, 1, 55, "impact", 110, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant S": (748, 0, 1, 58, "impact", 115, "misc", "Provides superhuman combat efficiency and accuracy"),
    # ---- neural trainer ----
    "neural trainer":   (650, 1, 1, 6, "impact", 100, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer C": (650, 1, 1, 7, "impact", 100, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer B": (683, 0, 1, 8, "impact", 105, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer A": (715, 0, 1, 9, "impact", 110, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer S": (748, 0, 1, 10, "impact", 115, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    # ---- magnum ----
    "magnum":   (300, 4, 1, 30, "impact", 40, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum C": (300, 4, 1, 30, "impact", 40, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum B": (315, 3, 1, 32, "impact", 42, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum A": (330, 3, 1, 33, "impact", 44, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum S": (345, 3, 1, 35, "impact", 46, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    # ---- laser pistol ----
    "laser pistol":   (500, 3, 2, 20, "energy", 40, "weapon", "A precise energy weapon"),
    "laser pistol C": (500, 3, 2, 20, "energy", 40, "weapon", "A precise energy weapon"),
    "laser pistol B": (525, 2, 2, 21, "energy", 42, "weapon", "A precise energy weapon"),
    "laser pistol A": (550, 2, 2, 22, "energy", 44, "weapon", "A precise energy weapon"),
    "laser pistol S": (575, 2, 2, 23, "energy", 46, "weapon", "A precise energy weapon"),
    # ---- pistol ----
    "pistol":   (100, 2, 2, 10, "impact", 40, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol C": (100, 2, 2, 10, "impact", 40, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol B": (105, 1, 2, 11, "impact", 42, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol A": (110, 1, 3, 11, "impact", 44, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol S": (115, 1, 4, 12, "impact", 46, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    # ---- slicer ----
    "slicer":   (350, 6, 1, 30, "impact", 50, "weapon", "A powered melee weapon"),
    "slicer C": (350, 6, 1, 30, "impact", 50, "weapon", "A powered melee weapon"),
    "slicer B": (368, 5, 1, 32, "impact", 53, "weapon", "A powered melee weapon"),
    "slicer A": (385, 5, 2, 33, "impact", 55, "weapon", "A powered melee weapon"),
    "slicer S": (403, 5, 2, 35, "impact", 58, "weapon", "A powered melee weapon"),
    # ---- stunner ----
    "stunner":   (200, 3, 1, 20, "sonic", 40, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner C": (200, 3, 1, 20, "sonic", 40, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner B": (210, 2, 1, 21, "sonic", 42, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner A": (220, 2, 1, 22, "sonic", 44, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner S": (230, 2, 2, 23, "sonic", 46, "weapon", "A nonlethal weapon that disables humanoids"),
    # ---- carbine ----
    "carbine":   (550, 10, 3, 10, "impact", 50, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine C": (550, 10, 3, 10, "impact", 50, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine B": (578,  9, 3, 11, "impact", 53, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine A": (605,  9, 5, 11, "impact", 55, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine S": (633,  8, 5, 12, "impact", 58, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    # ---- laser rifle ----
    "laser rifle":   (700, 10, 1, 50, "energy", 40, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle C": (700, 10, 1, 50, "energy", 40, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle B": (735,  9, 1, 53, "energy", 42, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle A": (770,  9, 1, 55, "energy", 44, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle S": (805,  8, 1, 58, "energy", 46, "weapon", "A powerful, heavy, expensive laser weapon"),
    # ---- blaster rifle ----
    "blaster rifle":   (500, 10, 1, 50, "sonic", 40, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle C": (500, 10, 1, 50, "sonic", 40, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle B": (525,  9, 1, 53, "sonic", 42, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle A": (550,  9, 1, 55, "sonic", 44, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle S": (575,  8, 1, 58, "sonic", 46, "weapon", "A powerful sonic rifle, but useless against robots"),
    # ---- stun baton ----
    "stun baton":   (250, 4, 1, 20, "sonic", 200, "weapon", "A nonlethal melee weapon"),
    "stun baton C": (250, 4, 1, 20, "sonic", 200, "weapon", "A nonlethal melee weapon"),
    "stun baton B": (263, 3, 1, 21, "sonic", 210, "weapon", "A nonlethal melee weapon"),
    "stun baton A": (275, 3, 1, 22, "sonic", 220, "weapon", "A nonlethal melee weapon"),
    "stun baton S": (288, 3, 2, 23, "sonic", 230, "weapon", "A nonlethal melee weapon"),
}

# Armor protection multipliers per effect_type:
#   (energy, sonic, impact, slash, pierce, concussion, electric)
# Protection applied = round(armor.effect * multiplier)
ARMOR_ATTRIBUTES = {
    "power shield":  (1.0, 0.0, 0.05, 0.05, 0.05, 0.10, 0.50),  # excellent vs energy; near-zero vs physical
    "veer suit":     (0.3, 0.3, 0.50, 0.50, 0.50, 0.40, 0.30),  # moderate all-round
    "exoskeleton":   (0.2, 0.2, 0.60, 0.50, 0.40, 0.50, 0.30),  # strong vs impact/concussion
    "holofier":      (0.0, 0.0, 0.00, 0.00, 0.00, 0.00, 0.00),  # miss-chance only; no flat reduction
    "powered armor": (0.5, 0.5, 1.00, 0.80, 0.70, 0.80, 0.50),  # elite: full impact, strong elsewhere
}

TABS = ["weapons", "armor", "robots", "misc"]


class Item:
    def __init__(self, name, item_type, cost, mass, rate, effect, effect_type, hp, description, icon=None, rect=None):
        self.name = name
        self.type = item_type
        self.cost = cost
        self.mass = mass
        self.rate = rate
        self.effect = effect
        self.effect_type = effect_type
        self.hp = hp
        self.description = description
        self.icon = icon
        self.rect = rect if rect else pygame.Rect(0, 0, 50, 50)

    def __repr__(self):
        return f"Item(name={self.name}, type={self.type}, cost={self.cost}, mass={self.mass}, rate={self.rate}, effect={self.effect}, hp={self.hp})"

    def set_rect(self, rect):
        self.rect = rect

    def get_rect(self):
        return self.rect

    # ------------------------------------------------------------------
    # Semantic predicates — all use item_base_name() so classed items
    # ("laser rifle B", "carbine S", etc.) resolve correctly.
    # ------------------------------------------------------------------

    _RIFLE_BASES      = {"blaster rifle", "laser rifle"}
    _RANGED_BASES     = {"blaster rifle", "laser rifle", "laser pistol",
                         "carbine", "magnum", "pistol", "stunner"}
    _MELEE_BASES      = {"slicer", "stun baton"}
    _ENERGY_BASES     = {"laser rifle", "laser pistol"}
    _SONIC_BASES      = {"blaster rifle", "stunner", "stun baton"}
    _PROJECTILE_BASES = {"carbine", "magnum", "pistol"}
    _NONLETHAL_BASES  = {"stunner", "stun baton"}

    def is_rifle(self) -> bool:
        """True for blaster rifle and laser rifle (benefits from Sharpshooting)."""
        return item_base_name(self.name) in self._RIFLE_BASES

    def is_ranged_weapon(self) -> bool:
        """True for any weapon that fires at range."""
        return self.type == "weapon" and item_base_name(self.name) in self._RANGED_BASES

    def is_melee_weapon(self) -> bool:
        """True for any weapon used in close combat."""
        return self.type == "weapon" and item_base_name(self.name) in self._MELEE_BASES

    def is_energy_weapon(self) -> bool:
        """True for weapons with energy effect type (laser rifle, laser pistol)."""
        return self.type == "weapon" and item_base_name(self.name) in self._ENERGY_BASES

    def is_sonic_weapon(self) -> bool:
        """True for weapons with sonic effect type (blaster rifle, stunner, stun baton)."""
        return self.type == "weapon" and item_base_name(self.name) in self._SONIC_BASES

    def is_projectile_weapon(self) -> bool:
        """True for weapons with impact/projectile effect type (carbine, magnum, pistol)."""
        return self.type == "weapon" and item_base_name(self.name) in self._PROJECTILE_BASES

    def is_lethal(self) -> bool:
        """True for weapons that can kill. Stunner and stun baton are non-lethal."""
        return self.type == "weapon" and item_base_name(self.name) not in self._NONLETHAL_BASES


    @classmethod
    def from_data(cls, name, attributes, icon=None):
        cost, mass, rate, effect, effect_type, hp, item_type, description = attributes
        rect = pygame.Rect(0, 0, 50, 50)
        return cls(name, item_type, cost, mass, rate, effect, effect_type, hp, description, icon, rect)

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "cost": self.cost,
            "mass": self.mass,
            "rate": self.rate,
            "effect": self.effect,
            "effect_type": self.effect_type,
            "hp": self.hp,
            "description": self.description,
        }

    @classmethod
    def load_icon(cls, item_name, size=(50, 50)):
        """Load icon, stripping any class suffix before building the filename."""
        base = item_base_name(item_name)
        icon_path = resource_path(f"gadgets/{base}.jpg")
        try:
            icon = pygame.image.load(icon_path)
            return pygame.transform.scale(icon, size)
        except pygame.error:
            print(f"Failed to load icon for '{item_name}' (tried '{base}.jpg').")
            return None

    @classmethod
    def from_dict(cls, data):
        icon = cls.load_icon(data["name"])
        # Support saves that used the old 'damage'/'damage_type' keys
        effect = data.get("effect", data.get("damage", 1))
        effect_type = data.get("effect_type", data.get("damage_type", "impact"))
        return cls(
            name=data["name"],
            item_type=data["type"],
            cost=data["cost"],
            mass=data["mass"],
            rate=data["rate"],
            effect=effect,
            effect_type=effect_type,
            hp=data["hp"],
            description=data["description"],
            icon=icon,
        )

    def copy(self):
        return Item(
            self.name, self.type, self.cost, self.mass, self.rate,
            self.effect, self.effect_type, self.hp, self.description,
            self.icon, self.rect.copy() if self.rect else None,
        )


from Robot import ROBOT_ATTRIBUTES

ALL_ATTRIBUTES = {**ITEM_ATTRIBUTES, **ROBOT_ATTRIBUTES}


def _build_items(icon_size: tuple) -> dict:
    items = {}
    _icon_cache: dict = {}

    def get_icon(base_name: str):
        if base_name not in _icon_cache:
            path = resource_path(f"gadgets/{base_name}.jpg")
            try:
                img = pygame.image.load(path)
                _icon_cache[base_name] = pygame.transform.scale(img, icon_size)
            except pygame.error:
                print(f"Warning: no icon image for '{base_name}'.")
                _icon_cache[base_name] = None
        return _icon_cache[base_name]

    for name, attrs in ITEM_ATTRIBUTES.items():
        items[name] = Item.from_data(name, attrs, get_icon(item_base_name(name)))

    for name, attrs in ROBOT_ATTRIBUTES.items():
        items[name] = Item.from_data(name, attrs, get_icon(name))

    return items


def load_items() -> dict:
    return _build_items((50, 50))


def load_items_battle() -> dict:
    return _build_items((40, 40))


def load_item_tabs() -> dict:
    """Return store items grouped by tab. Only class-C non-robot items are shown."""
    items_by_tab = {tab: [] for tab in TABS}
    for name, item in load_items().items():
        if item.type == "robot":
            items_by_tab["robots"].append(item)
        elif item_class(name) == "C":
            if item.type == "weapon":
                items_by_tab["weapons"].append(item)
            elif item.type == "armor":
                items_by_tab["armor"].append(item)
            else:
                items_by_tab["misc"].append(item)
    return items_by_tab


# Abstract fallback melee weapon for characters with no weapons equipped (never added to inventory)
DEFAULT_KNIFE_WEAPON = Item(
    "knife", "weapon", 0, 0, 1, 10, "impact", 10,
    "A basic combat knife used when no other weapon is equipped",
)

