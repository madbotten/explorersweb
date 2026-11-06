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
    "power shield":   (200, 4, 1, 30, "impact",  50, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield C": (200, 4, 1, 30, "impact",  50, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield B": (210, 3, 1, 32, "impact",  53, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield A": (220, 3, 1, 33, "impact",  55, "armor", "A protective item that can absorb some damage from energy attacks"),
    "power shield S": (230, 3, 1, 35, "impact",  58, "armor", "A protective item that can absorb some damage from energy attacks"),
    # ---- veer suit (moderate all-round protection) ----
    "veer suit":   (200, 5, 1, 20, "impact", 100, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit C": (200, 5, 1, 20, "impact", 100, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit B": (210, 4, 1, 21, "impact", 105, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit A": (220, 4, 1, 22, "impact", 110, "armor", "A protective suit that protects against ballistic and melee impacts"),
    "veer suit S": (230, 4, 1, 23, "impact", 115, "armor", "A protective suit that protects against ballistic and melee impacts"),
    # ---- exoskeleton (good vs impact; adds strength) ----
    "exoskeleton":   (350, 1, 2, 25, "impact", 150, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton C": (350, 1, 2, 25, "impact", 150, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton B": (368, 1, 2, 26, "impact", 158, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton A": (385, 1, 2, 28, "impact", 165, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    "exoskeleton S": (403, 1, 2, 29, "impact", 173, "armor", "A powered suit that protects against melee impacts and increases the strength of the wearer"),
    # ---- holofier (effect = miss-chance roll penalty applied to attackers) ----
    "holofier":   (325, 2, 1, 25, "impact", 40, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier C": (325, 2, 1, 25, "impact", 40, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier B": (341, 1, 1, 26, "impact", 42, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier A": (358, 1, 1, 28, "impact", 44, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
    "holofier S": (374, 1, 1, 29, "impact", 46, "armor", "Projects holograms of the wearer, causing some attacks to miss"),
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
    "medikit":   (150, 3, 1, 60, "impact", 40, "misc", "A medical kit that helps team members heal injuries"),
    "medikit C": (150, 3, 1, 60, "impact", 40, "misc", "A medical kit that helps team members heal injuries"),
    "medikit B": (158, 2, 1, 63, "impact", 42, "misc", "A medical kit that helps team members heal injuries"),
    "medikit A": (165, 2, 1, 66, "impact", 44, "misc", "A medical kit that helps team members heal injuries"),
    "medikit S": (173, 2, 1, 69, "impact", 46, "misc", "A medical kit that helps team members heal injuries"),
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
    "bio container":   (75, 2, 1, 10, "impact", 50, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container C": (75, 2, 1, 10, "impact", 50, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container B": (79, 1, 1, 11, "impact", 53, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container A": (83, 1, 1, 11, "impact", 55, "misc", "A rugged container suitable for carrying isolated biological samples"),
    "bio container S": (86, 1, 1, 12, "impact", 58, "misc", "A rugged container suitable for carrying isolated biological samples"),
    # ---- stealth orb ----
    "stealth orb":   (400, 3, 2, 40, "impact", 50, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb C": (400, 3, 2, 40, "impact", 50, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb B": (420, 2, 2, 42, "impact", 53, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb A": (440, 2, 2, 44, "impact", 55, "misc", "Blurs image of the wearer and suppresses noise"),
    "stealth orb S": (460, 2, 2, 46, "impact", 58, "misc", "Blurs image of the wearer and suppresses noise"),
    # ---- pacifier ----
    "pacifier":   (250, 3, 5, 50, "impact", 40, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier C": (250, 3, 5, 50, "impact", 40, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier B": (263, 2, 5, 53, "impact", 42, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier A": (275, 2, 5, 55, "impact", 44, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    "pacifier S": (288, 2, 5, 58, "impact", 46, "misc", "Used to incapacitate a humanoid, useful for capturing mission targets"),
    # ---- offense implant ----
    "offense implant":   (550, 1, 1, 50, "impact", 100, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant C": (550, 1, 1, 50, "impact", 100, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant B": (578, 0, 1, 53, "impact", 105, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant A": (605, 0, 1, 55, "impact", 110, "misc", "Provides superhuman combat efficiency and accuracy"),
    "offense implant S": (633, 0, 1, 58, "impact", 115, "misc", "Provides superhuman combat efficiency and accuracy"),
    # ---- neural trainer ----
    "neural trainer":   (250, 1, 1, 6, "impact", 100, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer C": (250, 1, 1, 7, "impact", 100, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer B": (263, 0, 1, 8, "impact", 105, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer A": (275, 0, 1, 9, "impact", 110, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    "neural trainer S": (288, 0, 1, 10, "impact", 115, "misc", "Temporarily endows recipient with low skill in untrained skills"),
    # ---- magnum ----
    "magnum":   (225, 4, 1, 35, "pierce", 40, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum C": (225, 4, 1, 35, "pierce", 40, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum B": (236, 3, 1, 37, "pierce", 42, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum A": (248, 3, 1, 39, "pierce", 44, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    "magnum S": (259, 3, 1, 40, "pierce", 46, "weapon", "A powerful projectile weapon with low rate of fire and low accuracy"),
    # ---- laser pistol ----
    "laser pistol":   (375, 3, 2, 20, "energy", 40, "weapon", "A precise energy weapon"),
    "laser pistol C": (375, 3, 2, 20, "energy", 40, "weapon", "A precise energy weapon"),
    "laser pistol B": (394, 2, 2, 21, "energy", 42, "weapon", "A precise energy weapon"),
    "laser pistol A": (413, 2, 2, 22, "energy", 44, "weapon", "A precise energy weapon"),
    "laser pistol S": (431, 2, 2, 23, "energy", 46, "weapon", "A precise energy weapon"),
    # ---- pistol ----
    "pistol":   (100, 2, 2, 14, "pierce", 40, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol C": (100, 2, 2, 14, "pierce", 40, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol B": (105, 1, 2, 15, "pierce", 42, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol A": (110, 1, 3, 15, "pierce", 44, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    "pistol S": (115, 1, 4, 16, "pierce", 46, "weapon", "A projectile weapon with high rate of fire and low accuracy"),
    # ---- slicer ----
    "slicer":   (350, 4, 1, 30, "slash", 50, "weapon", "A powered melee weapon"),
    "slicer C": (350, 4, 1, 30, "slash", 50, "weapon", "A powered melee weapon"),
    "slicer B": (368, 3, 1, 32, "slash", 53, "weapon", "A powered melee weapon"),
    "slicer A": (385, 3, 2, 33, "slash", 55, "weapon", "A powered melee weapon"),
    "slicer S": (403, 3, 2, 35, "slash", 58, "weapon", "A powered melee weapon"),
    # ---- stunner ----
    "stunner":   (200, 3, 1, 20, "sonic", 40, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner C": (200, 3, 1, 20, "sonic", 40, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner B": (210, 2, 1, 21, "sonic", 42, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner A": (220, 2, 1, 22, "sonic", 44, "weapon", "A nonlethal weapon that disables humanoids"),
    "stunner S": (230, 2, 2, 23, "sonic", 46, "weapon", "A nonlethal weapon that disables humanoids"),
    # ---- carbine ----
    "carbine":   (400, 6, 3, 18, "pierce", 50, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine C": (400, 6, 3, 18, "pierce", 50, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine B": (420, 5, 3, 19, "pierce", 53, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine A": (440, 5, 5, 20, "pierce", 55, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    "carbine S": (460, 5, 5, 21, "pierce", 58, "weapon", "A projectile weapon with very high rate of fire and medium accuracy"),
    # ---- laser rifle ----
    "laser rifle":   (700, 8, 1, 50, "energy", 40, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle C": (700, 8, 1, 50, "energy", 40, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle B": (735, 7, 1, 53, "energy", 42, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle A": (770, 7, 1, 55, "energy", 44, "weapon", "A powerful, heavy, expensive laser weapon"),
    "laser rifle S": (805, 6, 1, 58, "energy", 46, "weapon", "A powerful, heavy, expensive laser weapon"),
    # ---- blaster rifle ----
    "blaster rifle":   (500, 8, 1, 50, "sonic", 40, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle C": (500, 8, 1, 50, "sonic", 40, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle B": (525, 7, 1, 53, "sonic", 42, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle A": (550, 7, 1, 55, "sonic", 44, "weapon", "A powerful sonic rifle, but useless against robots"),
    "blaster rifle S": (575, 6, 1, 58, "sonic", 46, "weapon", "A powerful sonic rifle, but useless against robots"),
    # ---- stun baton ----
    "stun baton":   (175, 3, 1, 20, "sonic", 200, "weapon", "A nonlethal melee weapon"),
    "stun baton C": (175, 3, 1, 20, "sonic", 200, "weapon", "A nonlethal melee weapon"),
    "stun baton B": (184, 2, 1, 21, "sonic", 210, "weapon", "A nonlethal melee weapon"),
    "stun baton A": (193, 2, 1, 22, "sonic", 220, "weapon", "A nonlethal melee weapon"),
    "stun baton S": (201, 2, 2, 23, "sonic", 230, "weapon", "A nonlethal melee weapon"),
    # ---- grenade rifle (ranged impact rifle) ----
    "grenade rifle":   (650, 8, 1, 45, "impact", 50, "weapon", "A heavy rifle that fires high-velocity impact grenades"),
    "grenade rifle C": (650, 8, 1, 45, "impact", 50, "weapon", "A heavy rifle that fires high-velocity impact grenades"),
    "grenade rifle B": (683, 7, 1, 47, "impact", 53, "weapon", "A heavy rifle that fires high-velocity impact grenades"),
    "grenade rifle A": (715, 7, 2, 50, "impact", 55, "weapon", "A heavy rifle that fires high-velocity impact grenades"),
    "grenade rifle S": (748, 6, 2, 52, "impact", 58, "weapon", "A heavy rifle that fires high-velocity impact grenades"),
    # ---- power mace (melee impact weapon) ----
    "power mace":   (325, 5, 1, 32, "impact", 80, "weapon", "A high-tech powered mace that crushes armor on impact"),
    "power mace C": (325, 5, 1, 32, "impact", 80, "weapon", "A high-tech powered mace that crushes armor on impact"),
    "power mace B": (341, 4, 1, 34, "impact", 84, "weapon", "A high-tech powered mace that crushes armor on impact"),
    "power mace A": (358, 4, 2, 35, "impact", 88, "weapon", "A high-tech powered mace that crushes armor on impact"),
    "power mace S": (374, 4, 2, 37, "impact", 92, "weapon", "A high-tech powered mace that crushes armor on impact"),
    # ---- flechette pistol (ranged slash weapon) ----
    "flechette pistol":   (250, 2, 3, 14, "slash", 40, "weapon", "Fires bursts of razor-sharp micro-flechettes that shred lightly armored targets"),
    "flechette pistol C": (250, 2, 3, 14, "slash", 40, "weapon", "Fires bursts of razor-sharp micro-flechettes that shred lightly armored targets"),
    "flechette pistol B": (263, 1, 3, 15, "slash", 42, "weapon", "Fires bursts of razor-sharp micro-flechettes that shred lightly armored targets"),
    "flechette pistol A": (275, 1, 4, 15, "slash", 44, "weapon", "Fires bursts of razor-sharp micro-flechettes that shred lightly armored targets"),
    "flechette pistol S": (288, 1, 4, 16, "slash", 46, "weapon", "Fires bursts of razor-sharp micro-flechettes that shred lightly armored targets"),
    # ---- mono spear (melee pierce weapon) ----
    "mono spear":   (375, 4, 1, 35, "pierce", 60, "weapon", "A monomolecular-tipped combat spear that punches through heavy armor"),
    "mono spear C": (375, 4, 1, 35, "pierce", 60, "weapon", "A monomolecular-tipped combat spear that punches through heavy armor"),
    "mono spear B": (394, 3, 1, 37, "pierce", 63, "weapon", "A monomolecular-tipped combat spear that punches through heavy armor"),
    "mono spear A": (413, 3, 2, 39, "pierce", 66, "weapon", "A monomolecular-tipped combat spear that punches through heavy armor"),
    "mono spear S": (431, 3, 2, 40, "pierce", 69, "weapon", "A monomolecular-tipped combat spear that punches through heavy armor"),
    # ---- launcher (ranged concussion weapon) ----
    "launcher":   (650, 9, 1, 55, "concussion", 50, "weapon", "A heavy concussion grenade launcher that batters armored targets"),
    "launcher C": (650, 9, 1, 55, "concussion", 50, "weapon", "A heavy concussion grenade launcher that batters armored targets"),
    "launcher B": (683, 8, 1, 58, "concussion", 53, "weapon", "A heavy concussion grenade launcher that batters armored targets"),
    "launcher A": (715, 8, 1, 61, "concussion", 55, "weapon", "A heavy concussion grenade launcher that batters armored targets"),
    "launcher S": (748, 7, 2, 63, "concussion", 58, "weapon", "A heavy concussion grenade launcher that batters armored targets"),
    # ---- grav hammer (melee concussion weapon) ----
    "grav hammer":   (450, 7, 1, 45, "concussion", 80, "weapon", "A heavy melee warhammer that releases a concussive shockwave on impact"),
    "grav hammer C": (450, 7, 1, 45, "concussion", 80, "weapon", "A heavy melee warhammer that releases a concussive shockwave on impact"),
    "grav hammer B": (473, 6, 1, 47, "concussion", 84, "weapon", "A heavy melee warhammer that releases a concussive shockwave on impact"),
    "grav hammer A": (495, 6, 1, 50, "concussion", 88, "weapon", "A heavy melee warhammer that releases a concussive shockwave on impact"),
    "grav hammer S": (518, 5, 2, 52, "concussion", 92, "weapon", "A heavy melee warhammer that releases a concussive shockwave on impact"),
    # ---- arc thrower (ranged electric weapon) ----
    "arc thrower":   (450, 6, 2, 25, "electric", 45, "weapon", "Projects lethal high-voltage electrical arcs, devastating against robots"),
    "arc thrower C": (450, 6, 2, 25, "electric", 45, "weapon", "Projects lethal high-voltage electrical arcs, devastating against robots"),
    "arc thrower B": (473, 5, 2, 26, "electric", 47, "weapon", "Projects lethal high-voltage electrical arcs, devastating against robots"),
    "arc thrower A": (495, 5, 2, 28, "electric", 50, "weapon", "Projects lethal high-voltage electrical arcs, devastating against robots"),
    "arc thrower S": (518, 5, 3, 29, "electric", 52, "weapon", "Projects lethal high-voltage electrical arcs, devastating against robots"),
    # ---- shock prod (melee electric nonlethal weapon) ----
    "shock prod":   (225, 3, 2, 18, "electric", 80, "weapon", "An electrified close-combat prod that incapacitates humanoids and overloads robots"),
    "shock prod C": (225, 3, 2, 18, "electric", 80, "weapon", "An electrified close-combat prod that incapacitates humanoids and overloads robots"),
    "shock prod B": (236, 2, 2, 19, "electric", 84, "weapon", "An electrified close-combat prod that incapacitates humanoids and overloads robots"),
    "shock prod A": (248, 2, 2, 20, "electric", 88, "weapon", "An electrified close-combat prod that incapacitates humanoids and overloads robots"),
    "shock prod S": (259, 2, 3, 21, "electric", 92, "weapon", "An electrified close-combat prod that incapacitates humanoids and overloads robots"),
    # ---- sonic helmet (helmet; strong vs sonic, boosts Detection) ----
    "sonic helmet":   (150, 2, 1, 25, "sonic", 60, "armor", "A sound-dampening helmet that protects against sonic attacks and aids detection"),
    "sonic helmet C": (150, 2, 1, 25, "sonic", 60, "armor", "A sound-dampening helmet that protects against sonic attacks and aids detection"),
    "sonic helmet B": (158, 1, 1, 26, "sonic", 63, "armor", "A sound-dampening helmet that protects against sonic attacks and aids detection"),
    "sonic helmet A": (165, 1, 1, 28, "sonic", 66, "armor", "A sound-dampening helmet that protects against sonic attacks and aids detection"),
    "sonic helmet S": (173, 1, 1, 29, "sonic", 69, "armor", "A sound-dampening helmet that protects against sonic attacks and aids detection"),
    # ---- targeting helmet (helmet; boosts ranged accuracy and perception) ----
    "targeting helmet":   (250, 2, 1, 15, "impact", 50, "armor", "A HUD helmet that improves ranged accuracy and sharpens perception"),
    "targeting helmet C": (250, 2, 1, 15, "impact", 50, "armor", "A HUD helmet that improves ranged accuracy and sharpens perception"),
    "targeting helmet B": (263, 1, 1, 16, "impact", 53, "armor", "A HUD helmet that improves ranged accuracy and sharpens perception"),
    "targeting helmet A": (275, 1, 1, 17, "impact", 55, "armor", "A HUD helmet that improves ranged accuracy and sharpens perception"),
    "targeting helmet S": (288, 1, 1, 17, "impact", 58, "armor", "A HUD helmet that improves ranged accuracy and sharpens perception"),
    # ---- command helmet (helmet; boosts leadership, squad tactics, and morale) ----
    "command helmet":   (225, 2, 1, 15, "impact", 60, "armor", "A tactical comms helmet that boosts leadership, squad coordination, and morale resistance"),
    "command helmet C": (225, 2, 1, 15, "impact", 60, "armor", "A tactical comms helmet that boosts leadership, squad coordination, and morale resistance"),
    "command helmet B": (236, 1, 1, 16, "impact", 63, "armor", "A tactical comms helmet that boosts leadership, squad coordination, and morale resistance"),
    "command helmet A": (248, 1, 1, 17, "impact", 66, "armor", "A tactical comms helmet that boosts leadership, squad coordination, and morale resistance"),
    "command helmet S": (259, 1, 1, 17, "impact", 69, "armor", "A tactical comms helmet that boosts leadership, squad coordination, and morale resistance"),
    # ---- flak vest (body armor; strong vs concussion, slash, and impact) ----
    "flak vest":   (150, 4, 1, 25, "impact", 90, "armor", "Layered ballistic vest that absorbs shrapnel, slashes, and concussive blasts"),
    "flak vest C": (150, 4, 1, 25, "impact", 90, "armor", "Layered ballistic vest that absorbs shrapnel, slashes, and concussive blasts"),
    "flak vest B": (158, 3, 1, 26, "impact", 95, "armor", "Layered ballistic vest that absorbs shrapnel, slashes, and concussive blasts"),
    "flak vest A": (165, 3, 1, 28, "impact", 99, "armor", "Layered ballistic vest that absorbs shrapnel, slashes, and concussive blasts"),
    "flak vest S": (173, 3, 1, 29, "impact", 104, "armor", "Layered ballistic vest that absorbs shrapnel, slashes, and concussive blasts"),
    # ---- insulated suit (body armor; strong vs electric and energy) ----
    "insulated suit":   (225, 4, 1, 28, "electric", 90, "armor", "Grounded hazard suit that insulates against electrical and energy attacks"),
    "insulated suit C": (225, 4, 1, 28, "electric", 90, "armor", "Grounded hazard suit that insulates against electrical and energy attacks"),
    "insulated suit B": (236, 3, 1, 29, "electric", 95, "armor", "Grounded hazard suit that insulates against electrical and energy attacks"),
    "insulated suit A": (248, 3, 1, 31, "electric", 99, "armor", "Grounded hazard suit that insulates against electrical and energy attacks"),
    "insulated suit S": (259, 3, 1, 32, "electric", 104, "armor", "Grounded hazard suit that insulates against electrical and energy attacks"),
    # ---- chitin carapace (body armor; strong vs slash, pierce, and impact) ----
    "chitin carapace":   (425, 5, 1, 35, "impact", 140, "armor", "Bio-composite alien carapace plating that excels against blades, projectiles, and acid"),
    "chitin carapace C": (425, 5, 1, 35, "impact", 140, "armor", "Bio-composite alien carapace plating that excels against blades, projectiles, and acid"),
    "chitin carapace B": (446, 4, 1, 37, "impact", 147, "armor", "Bio-composite alien carapace plating that excels against blades, projectiles, and acid"),
    "chitin carapace A": (468, 4, 1, 39, "impact", 154, "armor", "Bio-composite alien carapace plating that excels against blades, projectiles, and acid"),
    "chitin carapace S": (489, 4, 1, 40, "impact", 161, "armor", "Bio-composite alien carapace plating that excels against blades, projectiles, and acid"),
}

# Armor protection multipliers per effect_type:
#   (energy, sonic, impact, slash, pierce, concussion, electric)
# Protection applied = round(armor.effect * multiplier)
ARMOR_ATTRIBUTES = {
    "power shield":     (1.0, 0.0, 0.05, 0.05, 0.05, 0.10, 0.50),  # excellent vs energy; near-zero vs physical
    "veer suit":        (0.3, 0.3, 0.50, 0.50, 0.50, 0.40, 0.30),  # moderate all-round
    "exoskeleton":      (0.2, 0.2, 0.60, 0.50, 0.40, 0.50, 0.30),  # strong vs impact/concussion
    "holofier":         (0.0, 0.0, 0.00, 0.00, 0.00, 0.00, 0.00),  # miss-chance only; no flat reduction
    "powered armor":    (0.5, 0.5, 1.00, 0.80, 0.70, 0.80, 0.50),  # elite: full impact, strong elsewhere
    "sonic helmet":     (0.1, 1.0, 0.20, 0.10, 0.10, 0.40, 0.10),  # specialized sonic/concussion helmet
    "targeting helmet": (0.2, 0.2, 0.20, 0.20, 0.20, 0.20, 0.20),  # light protection; accuracy/perception bonus
    "command helmet":   (0.1, 0.4, 0.30, 0.20, 0.20, 0.30, 0.20),  # light protection; command/morale bonus
    "flak vest":        (0.1, 0.1, 0.60, 0.70, 0.50, 0.80, 0.10),  # strong vs concussion, slash, and impact
    "insulated suit":   (0.6, 0.4, 0.30, 0.30, 0.20, 0.40, 1.00),  # immune/strong vs electric and energy
    "chitin carapace":  (0.3, 0.1, 0.70, 0.90, 0.80, 0.50, 0.20),  # strong vs slash, pierce, and impact
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

    _RIFLE_BASES      = {"blaster rifle", "laser rifle", "grenade rifle"}
    _RANGED_BASES     = {"blaster rifle", "laser rifle", "laser pistol",
                         "carbine", "magnum", "pistol", "stunner",
                         "grenade rifle", "flechette pistol", "launcher", "arc thrower"}
    _MELEE_BASES      = {"slicer", "stun baton", "power mace", "mono spear", "grav hammer", "shock prod"}
    _ENERGY_BASES     = {"laser rifle", "laser pistol", "arc thrower"}
    _SONIC_BASES      = {"blaster rifle", "stunner", "stun baton"}
    _PROJECTILE_BASES = {"carbine", "magnum", "pistol", "grenade rifle", "flechette pistol"}
    _EXPLOSIVE_BASES  = {"launcher"}
    _NONLETHAL_BASES  = {"stunner", "stun baton", "shock prod"}
    _HELMET_BASES     = {"sonic helmet", "targeting helmet", "command helmet"}
    _BODY_ARMOR_BASES = {"power shield", "veer suit", "exoskeleton", "holofier",
                         "powered armor", "flak vest", "insulated suit", "chitin carapace"}

    def is_rifle(self) -> bool:
        """True for blaster rifle, laser rifle, and grenade rifle (benefits from Sharpshooting)."""
        return item_base_name(self.name) in self._RIFLE_BASES

    def is_ranged_weapon(self) -> bool:
        """True for any weapon that fires at range."""
        return self.type == "weapon" and item_base_name(self.name) in self._RANGED_BASES

    def is_melee_weapon(self) -> bool:
        """True for any weapon used in close combat."""
        return self.type == "weapon" and item_base_name(self.name) in self._MELEE_BASES

    def is_energy_weapon(self) -> bool:
        """True for weapons using Energy Weapons skill (laser rifle, laser pistol, arc thrower)."""
        return self.type == "weapon" and item_base_name(self.name) in self._ENERGY_BASES

    def is_sonic_weapon(self) -> bool:
        """True for weapons with sonic effect type (blaster rifle, stunner, stun baton)."""
        return self.type == "weapon" and item_base_name(self.name) in self._SONIC_BASES

    def is_projectile_weapon(self) -> bool:
        """True for projectile/ballistic weapons (carbine, magnum, pistol, grenade rifle, flechette pistol)."""
        return self.type == "weapon" and item_base_name(self.name) in self._PROJECTILE_BASES

    def is_explosive_weapon(self) -> bool:
        """True for heavy explosive/ordnance weapons (launcher)."""
        return self.type == "weapon" and item_base_name(self.name) in self._EXPLOSIVE_BASES

    def is_lethal(self) -> bool:
        """True for weapons that can kill. Stunner, stun baton, and shock prod are non-lethal."""
        return self.type == "weapon" and item_base_name(self.name) not in self._NONLETHAL_BASES

    def is_helmet(self) -> bool:
        """True for helmet armor items (at most 1 helmet per character)."""
        return self.type == "armor" and item_base_name(self.name) in self._HELMET_BASES

    def is_body_armor(self) -> bool:
        """True for non-helmet body armor items (at most 1 body armor per character)."""
        return self.type == "armor" and item_base_name(self.name) not in self._HELMET_BASES


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
        icon_path = _resolve_gadget_icon_path(base)
        try:
            icon = pygame.image.load(icon_path)
            return pygame.transform.scale(icon, size)
        except pygame.error:
            print(f"Failed to load icon for '{item_name}' (tried '{icon_path}').")
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


def _resolve_gadget_icon_path(base_name: str) -> str:
    """Resolve gadget icon path, checking spaced filename first and falling back to no-space filename."""
    spaced_path = resource_path(f"gadgets/{base_name}.jpg")
    if os.path.exists(spaced_path):
        return spaced_path
    nospace_path = resource_path(f"gadgets/{base_name.replace(' ', '')}.jpg")
    if os.path.exists(nospace_path):
        return nospace_path
    return spaced_path


def _build_items(icon_size: tuple) -> dict:
    items = {}
    _icon_cache: dict = {}

    def get_icon(base_name: str):
        if base_name not in _icon_cache:
            path = _resolve_gadget_icon_path(base_name)
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

