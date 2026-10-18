import pygame
import textwrap

from Utils import *

LOCATION_WIDTH = 350
LOCATION_HEIGHT = 350
LOCATION_LEFT = SCREEN_WIDTH - 370
LOCATION_TOP = 100
LOCATION_RECT = pygame.Rect(LOCATION_LEFT, LOCATION_TOP, 175, 175)
LOCATION_SOUTH = (LOCATION_LEFT + LOCATION_WIDTH/2, LOCATION_TOP + LOCATION_HEIGHT)
LOCATION_NORTH = (LOCATION_LEFT + LOCATION_WIDTH/2, LOCATION_TOP)
LOCATION_WEST = (LOCATION_LEFT, LOCATION_TOP + LOCATION_HEIGHT/2)
LOCATION_EAST = (LOCATION_LEFT + LOCATION_WIDTH, LOCATION_TOP + LOCATION_HEIGHT/2)

# use different locations and stuffs for mission
PIRATE_LOCATION_ATTRIBUTES = {
    "ai core": ("Interface room for an advanced AI core.", {"south": True}, ("goal",)),
    "armory": ("A workroom filled with weapons, armor and ammo.", {"south": True}, ("supply",)),
    "artifact analysis": ("A room equipped to scan unknown objects.", {"south": True}, ("tech",)),
    "barracks": ("An area with bunks and equipment lockers for soldiers.", {"south": True}, ("combat",)),
    "bioaugmentation": ("An area with bunks and equipment lockers for\nsoldiers.", {"south": True}, ("medical",)),
    "canteen": ("A colorful room for drinking and recreation.", {"south": True}, ("corridor",)),
    "cargo lift": ("A fuel and energy storage depot.", {"south": True}, ("corridor",)),
    "checkpoint": ("A security checkpoint.", {"south": True}, ("combat",)),
    "corridor": ("A clean, narrow corridor.", {"south": True}, ("corridor",)),
    "depot": ("A fuel and energy storage depot.", {"south": True}, ("supply",)),
    "drone launch": ("A room with an opening for drone egress.", {"south": True}, ("combat",)),
    "entrance": ("The entrance to a pirate stronghold.\nNo enemies are visible.", {"south": True}, ("entrance",)),
    "environmental control": ("A fuel and energy storage depot.", {"south": True}, ("tech",)),
    "fabrication": ("A fuel and energy storage depot.", {"south": True}, ("supply",)),
    "game room": ("A colorful entertainment center.", {"south": True}, ("corridor",)),
    "guard room": ("A simple guard room.", {"south": True}, ("combat",)),
    "implant room": ("A room filled with complex medical equipment.", {"south": True}, ("medical",)),
    "medical bay": ("A bloodstained medical facility.", {"south": True}, ("medical",)),
    "new chamber": ("A new room carved from the mountainside, yet to be\ncompleted.", {"south": True}, ("corridor",)),
    "officer's quarters": ("A group of four quarters with common area", {"south": True}, ("goal",)),
    "parts bay": ("A bay for parts storage and fabrication.", {"south": True}, ("supply",)),
    "prison": ("A grim space pirate prison.", {"south": True}, ("goal",)),
    "radar tower": ("A room filled with observation displays.", {"south": True}, ("tech",)),
    "smuggler's den": ("A comfortable room for relaxing and socializing.", {"south": True}, ("corridor",)),
    "storage": ("A clutter-filled storage room.", {"south": True}, ("supply",)),
    "training room": ("A large combat training center.", {"south": True}, ("combat",)),
    "vault": ("A heavily armored vault room.", {"south": True}, ("goal",)),
    "vehicle bay": ("A bay for vehicle storage and repair.", {"south": True}, ("supply",)),
    "war room": ("A large planning room.", {"south": True}, ("tech",)),
    "well": ("A water extraction and storage room.", {"south": True}, ("corridor",)),
    "workshop": ("A cluttered mechanical workshop.", {"south": True}, ("supply",)),
}

DERELICT_LOCATION_ATTRIBUTES = {
    "analysisbay": ("An alien specimen and artifact analysis bay.", {"south": True}, ("tech",)),
    "armory": ("A derelict weapons locker lined with chitin-encrusted racks.", {"south": True}, ("supply",)),
    "barracks1": ("A deserted crew barracks strewn with shattered carapaces.", {"south": True}, ("combat",)),
    "barracks2": ("A secondary troop berth converted into a Klackon nesting den.", {"south": True}, ("combat",)),
    "biolab": ("A bio-research laboratory overgrown with pulsing alien resin.", {"south": True}, ("goal",)),
    "bridge": ("The dark, silent command bridge of the derelict vessel.", {"south": True}, ("goal",)),
    "captainquarters": ("The former captain's quarters, ransacked and eerie.", {"south": True}, ("tech",)),
    "corridor": ("A scarred ship corridor flickering with emergency lighting.", {"south": True}, ("corridor",)),
    "empty": ("A stripped, depressurized hull compartment.", {"south": True}, ("corridor",)),
    "engineering": ("Main engineering, where damaged conduits hiss with plasma.", {"south": True}, ("tech",)),
    "fabrication": ("An automated fabrication bay covered in alien webbing.", {"south": True}, ("supply",)),
    "generator": ("A cavernous auxiliary power generator chamber.", {"south": True}, ("tech",)),
    "implant": ("A cybernetic surgical bay with flickering diagnostic screens.", {"south": True}, ("medical",)),
    "medbay": ("An abandoned sickbay with overturned stasis beds.", {"south": True}, ("medical",)),
    "navigation": ("A stellar navigation dome displaying dead star charts.", {"south": True}, ("tech",)),
    "orechamber": ("A raw ore processing chamber hollowed out by mandibles.", {"south": True}, ("supply",)),
    "parts": ("A spare-parts warehouse stacked with salvaged hull plating.", {"south": True}, ("supply",)),
    "quarters1": ("Abandoned crew quarters smelling of ozone and chitin.", {"south": True}, ("corridor",)),
    "quarters2": ("Dimly lit officer berths with claw marks across the bulkheads.", {"south": True}, ("corridor",)),
    "robotshop": ("A robotics maintenance shop littered with dismantled chassis.", {"south": True}, ("supply",)),
    "s-corridor": ("A curved service corridor winding through the hull.", {"south": True}, ("corridor",)),
    "shipsweapons": ("A heavy weapons battery deck patrolled by Klackon warriors.", {"south": True}, ("combat",)),
    "shuttlebay": ("A cavernous shuttle bay where the boarding craft docked.", {"south": True}, ("corridor",)),
    "suitroom": ("An EVA suit locker room with rows of vacuum-sealed armor.", {"south": True}, ("supply",)),
    "throneroom": ("A monumental hive-throne chamber at the heart of the derelict.", {"south": True}, ("goal",)),
    "warpchamber": ("The unstable warp core chamber humming with dimensional energy.", {"south": True}, ("goal",)),
}

# name: description, items (items can be picked up)
KNAKNARPIA_LOCATION_ATTRIBUTES = {
    "atrium": ("An open intersection between wings of the complex", {"south":True}),
    "bridge": ("A main command and control room", {"south":True}),
    "brig": ("A compact, hi-tech brig with four holding rooms", {"south":True}),
    "communications": ("A room filled with sophisticated communications\nand ECM consoles", {"south":True}),
    "corridor": ("A clean, narrow corridor", {"south":True}),
    "crew quarters": ("A group of crew quarters", {"south":True}),
    "decontamination center": ("A space used to clean personnel and items", {"south":True}),
    "engineering": ("A complex room filled with industrial sized machines", {"south":True}),
    "hangar": ("A cargo bay specialized for landing craft", {"south":True}),
    "holo room": ("A training room equipped with holographic projection\nequipment", {"south":True}),
    "hydroponics": ("An advanced food production farm", {"south":True}),
    "life support": ("A room filled with heavy equipment for maintaining\nthe ship's environment", {"south":True}),
    "mess": ("A large automated cafeteria", {"south":True}),
    "mission planning": ("A room equipped with simulation gear for\nplanning conflicts", {"south":True}),
    "officer's quarters": ("A well-equipped common room and 4 personal\nquarters", {"south":True}),
    "quarters": ("A small single-person quarters", {"south":True}),
    "rec room": ("A large room with many recreational configurations", {"south":True}),
    "robot storage": ("A storage room filled with spare robots and parts", {"south":True}),
    "robot bay": ("A robot maintenance and programming bay with\nseveral deactivated robots awaiting work.", {"south":True}),
    "ship's vault": ("A medical center with trauma control equipment", {"south":True}),
    "sickbay": ("A medical center with trauma control equipment", {"south":True}),
    "stasis vault": ("A room with stasis projectors for storing volatile\nitems safely", {"south":True}),
    "supply room": ("A room filled with a myriad of mundane supplies", {"south":True}),
    "tech lab": ("A sophisticated lab for simulating and repairing high\ntech items", {"south":True}),
}

GOAL_LOCATION_NAMES = ("ai core", "officer's quarters", "vault", "throneroom", "warpchamber", "biolab", "bridge")

def get_goal_location(locations, mission_index):
    if mission_index == 0:
        return locations.get("vault") or locations.get("warpchamber")
    if mission_index == 1:
        return locations.get("officer's quarters") or locations.get("throneroom")
    if mission_index == 2:
        return locations.get("officer's quarters") or locations.get("biolab")
    if mission_index == 3:
        return locations.get("ai core") or locations.get("bridge")

def get_next_mission_location(locations, last_location):
    spot = next(iter(locations.values()))
    while spot.name in GOAL_LOCATION_NAMES or spot.name == last_location.name:
        spot = locations[random.choice(list(locations.keys()))]
    return spot

class Location:
    def __init__(self, icon, rect, name, description, connections, tags=()):
        self.icon = icon
        self.rect = rect
        self.name = name
        self.description = description
        self.connections = connections
        self.tags = tuple(tags) if isinstance(tags, (list, tuple, set)) else (tags,)

    def connect(self, direction, location):
        if direction in self.connections:
            self.connections[direction] = location
            # Add the reverse connection
            reverse_directions = {"north": "south", "south": "north", "east": "west", "west": "east"}
            if location:
                location.connections[reverse_directions[direction]] = self

    def get_connection(self, direction):
        return self.connections.get(direction, None)

    def __repr__(self):
        return f"Location(name={self.name}, connections={self.connections}, tags={self.tags})"

def load_ship_locations():
    locations = {}
    location_dir = resource_path("locations/knacknarpia/")
    for file_name in os.listdir(location_dir):
        if file_name.endswith(".jpg"):
            location_surface = pygame.image.load(resource_path("locations/knacknarpia/" + file_name))
            item_surface = pygame.transform.scale(location_surface, (LOCATION_WIDTH, LOCATION_HEIGHT))
            name = file_name.split(".")[0]
            entry = KNAKNARPIA_LOCATION_ATTRIBUTES[name]
            description, connections = entry[0], entry[1]
            tags = entry[2] if len(entry) > 2 else ()
            locations[name] = Location(item_surface, pygame.Rect(LOCATION_RECT).copy(), name, description, connections, tags=tags)
    return locations

def load_pirate_locations():
    locations = {}
    location_dir = resource_path("locations/pirates/")
    for file_name in os.listdir(location_dir):
        if file_name.endswith(".jpg"):
            location_surface = pygame.image.load(resource_path("locations/pirates/" + file_name))
            item_surface = pygame.transform.scale(location_surface, (LOCATION_WIDTH, LOCATION_HEIGHT))
            name = file_name.split(".")[0]
            entry = PIRATE_LOCATION_ATTRIBUTES[name]
            description, connections = entry[0], entry[1]
            tags = entry[2] if len(entry) > 2 else ()
            locations[name] = Location(item_surface, pygame.Rect(LOCATION_RECT).copy(), name, description, connections, tags=tags)
    return locations

def load_derelict_locations():
    locations = {}
    location_dir = resource_path("locations/derelict/")
    for file_name in os.listdir(location_dir):
        if file_name.endswith(".jpg"):
            location_surface = pygame.image.load(resource_path("locations/derelict/" + file_name))
            item_surface = pygame.transform.scale(location_surface, (LOCATION_WIDTH, LOCATION_HEIGHT))
            name = file_name.split(".")[0]
            entry = DERELICT_LOCATION_ATTRIBUTES[name]
            description, connections = entry[0], entry[1]
            tags = entry[2] if len(entry) > 2 else ()
            locations[name] = Location(item_surface, pygame.Rect(LOCATION_RECT).copy(), name, description, connections, tags=tags)
    return locations

def draw_location(location, screen, left, top, font, small_font):
    loc_text = font.render("Location: " + location.name, True, WHITE)
    screen.blit(loc_text, (left, top - 25))
    screen.blit(location.icon, (left, top))
    blit_location_description(screen, location.description, (LOCATION_LEFT, LOCATION_TOP + LOCATION_HEIGHT + 10), small_font)

def blit_location_description(surface, text, pos, font, color=GREEN, max_width=500):
    lines = text.splitlines()
    y = pos[1]
    for line in lines:
        wrapped_lines = textwrap.wrap(line, width=int(max_width / font.size(" ")[0]))
        for wrapped_line in wrapped_lines:
            text_surface = font.render(wrapped_line, True, color)
            surface.blit(text_surface, (pos[0], y))
            y += font.get_linesize()
        y += 10


TRAINING_SCENARIOS = {
    "Hacking": [
        ("bridge", "The team decides they would like to practice hacking.", None),
        ("tech lab", "The team attempts to bypass a simulated security system.", None),
    ],
    "Projectile Weapons": [
        ("holo room", "The team conducts a virtual shooting practice session in the holo room.", None),
    ],
    "Social Engineering": [
        ("mess", "The team tries to manipulate each other to get their favorite food bars.", "Eventually everyone accepts their ration."),
    ],
    "Martial Arts": [
        ("holo room", "The team is restless and decide to spar in the holo room.", "The sparring is over."),
    ],
    "Stealth": [
        ("supply room", "The team plays hide and seek to pass the time.", "The time for games is over."),
        ("mission planning", "The team practices infiltrating a simulated enemy facility.", None),
    ],
    "Xenobiology": [
        ("mess", "While eating in the mess hall, the team discusses what aliens they might encounter on the mission.", "The meal ends."),
        ("hydroponics", "The team studies alien biology specimens in hydroponics.", None),
    ],
    "Squad Tactics": [
        ("mission planning", "The team plans out how to conduct themselves on the mission.", None),
        ("mission planning", "The team runs squad drills in simulated battle conditions.", None),
    ],
    "Mech Combat": [
        ("robot bay", "The team debates what model of combat mech is the most effective.", "The debate subsides."),
    ],
    "Piloting": [
        ("holo room", "The team simulates flying maneuvers in the holo room.", "The training session is over."),
    ],
    "Negotiation": [
        ("mission planning", "The team practices negotiating resource agreements with an AI facilitator.", None),
    ],
    "Sharpshooting": [
        ("holo room", "The team participates in a sharpshooting competition using holographic targets.", None),
    ],
    "Medicine": [
        ("sickbay", "The team learns advanced first aid techniques.", None),
        ("sickbay", "The team conducts an advanced medical emergency response drill.", None),
    ],
    "Sonic Weapons": [
        ("holo room", "The team practices using sonic weapons.", None),
    ],
    "Military Science": [
        ("mission planning", "The team analyzes historical military conflicts in the planning room.", None),
    ],
    "Explosives": [
        ("hangar", "The team safely defuses a mock explosive device.", None),
    ],
    "Cybernetics": [
        ("tech lab", "The team experiments with prosthetic enhancements in the tech lab.", None),
    ],
    "Survival": [
        ("holo room", "The team practices building shelters in a survival simulation.", None),
    ],
    "Diplomacy": [
        ("communications", "The team simulates high-stakes diplomatic negotiations with an AI moderator.", None),
    ],
    "Navigation": [
        ("bridge", "The team practices star map navigation.", None),
    ],
    "Interrogation": [
        ("brig", "The team interrogates a simulated suspect to uncover vital information.", None),
    ],
    "Robot Repair": [
        ("robot bay", "The team repairs malfunctioning droids in the robot bay.", None),
    ],
    "Ships Systems": [
        ("life support", "The team works on repairing the ship's life support systems.", None),
    ],
    "Espionage": [
        ("mission planning", "The team practices gathering intelligence from a simulated enemy base.", None),
    ],
    "Fabrication": [
        ("engineering", "The team fabricates essential mission tools using the onboard fabricator.", None),
    ],
    "Energy Weapons": [
        ("holo room", "The team practices using high-energy weapons in a controlled environment.", None),
    ],
    "Physics": [
        ("tech lab", "The team solves complex physics problems to optimize their equipment.", None),
    ],
    "Artifact Analysis": [
        ("tech lab", "The team analyzes mock artifacts for potential functionality.", None),
    ],
    "Exoskeleton Systems": [
        ("engineering", "The team tests exoskeleton systems for improved mobility and strength.", None),
    ],
    "Resource Extraction": [
        ("holo room", "The team learns efficient methods for extracting resources in simulated terrain.", None),
    ],
    "Detection": [
        ("holo room", "The team practices detecting anomalies in a simulated operational environment.", None),
    ],
}


def build_procedural_training_event(team, locations, all_items, outcome_fn=None):
    """Build a voyage training Event dynamically, weighted toward skills known by the crew.

    - 70% of the time picks a skill from TRAINING_SCENARIOS that at least one living
      non-robot crew member has at proficiency >= 50 (if any exist).
    - 30% of the time picks any skill from TRAINING_SCENARIOS at random.
    """
    from Event import Event
    if outcome_fn is None:
        from Voyage import calculate_outcome_training
        outcome_fn = calculate_outcome_training

    team_skills = [
        skill_name
        for skill_name in TRAINING_SCENARIOS
        if any(
            m is not None
            and not m.is_robot()
            and m.is_alive()
            and m.skills.get(skill_name, 0) >= 50
            for m in (team or [])
        )
    ]

    if team_skills and random.random() < 0.70:
        chosen_skill = random.choice(team_skills)
    else:
        chosen_skill = random.choice(list(TRAINING_SCENARIOS.keys()))

    loc_key, pre_desc, post_desc = random.choice(TRAINING_SCENARIOS[chosen_skill])
    location = locations.get(loc_key) if isinstance(locations, dict) else None

    return Event(
        pre_desc,
        post_desc,
        0,
        None,
        chosen_skill,
        location,
        outcome_fn,
        all_items,
        name=f"training_{chosen_skill.lower().replace(' ', '_')}",
    )

