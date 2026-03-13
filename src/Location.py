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
    "ai core": ("Interface room for an advanced AI core.", {"south":True}),
    "armory": ("A workroom filled with weapons, armor and ammo.", {"south":True}),
    "artifact analysis": ("A room equipped to scan unknown objects.", {"south":True}),
    "barracks": ("An area with bunks and equipment lockers for soldiers.", {"south":True}),
    "bioaugmentation": ("An area with bunks and equipment lockers for\nsoldiers.", {"south":True}),
    "canteen": ("A colorful room for drinking and recreation.", {"south":True}),
    "cargo lift": ("A fuel and energy storage depot.", {"south":True}),
    "checkpoint": ("A security checkpoint.", {"south":True}),
    "corridor": ("A clean, narrow corridor.", {"south":True}),
    "depot": ("A fuel and energy storage depot.", {"south": True}),
    "drone launch": ("A room with an opening for drone egress.", {"south":True}),
    "entrance": ("The entrance to a pirate stronghold.\nNo enemies are visible.", {"south": True}),
    "environmental control": ("A fuel and energy storage depot.", {"south": True}),
    "fabrication": ("A fuel and energy storage depot.", {"south": True}),
    "game room": ("A colorful entertainment center.", {"south": True}),
    "guard room": ("A simple guard room.", {"south": True}),
    "implant room": ("A room filled with complex medical equipment.", {"south": True}),
    "medical bay": ("A bloodstained medical facility.", {"south": True}),
    "new chamber": ("A new room carved from the mountainside, yet to be\ncompleted.", {"south": True}),
    "officer's quarters": ("A group of four quarters with common area", {"south": True}),
    "parts bay": ("A bay for parts storage and fabrication.", {"south": True}),
    "prison": ("A grim space pirate prison.", {"south": True}),
    "radar tower": ("A room filled with observation displays.", {"south": True}),
    "smuggler's den": ("A comfortable room for relaxing and socializing.", {"south": True}),
    "storage": ("A clutter-filled storage room.", {"south": True}),
    "training room": ("A large combat training center.", {"south": True}),
    "vault": ("A heavily armored vault room.", {"south": True}),
    "vehicle bay": ("A bay for vehicle storage and repair.", {"south": True}),
    "war room": ("A large planning room.", {"south": True}),
    "well": ("A water extraction and storage room.", {"south": True}),
    "workshop": ("A cluttered mechanical workshop.", {"south": True}),
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

GOAL_LOCATION_NAMES = ("ai core", "officer's quarters", "vault")

def get_goal_location(locations, mission_index):
    if mission_index == 0:
        return locations["vault"]
    if mission_index == 1:
        return locations["officer's quarters"]
    if mission_index == 2:
        return locations["officer's quarters"]
    if mission_index == 3:
        return locations["ai core"]

def get_next_mission_location(locations, last_location):
    spot = locations["vault"]
    while spot.name in GOAL_LOCATION_NAMES or spot.name == last_location.name:
        spot = locations[random.choice(list(locations.keys()))]
    return spot

class Location:
    def __init__(self, icon, rect, name, description, connections):
        self.icon = icon
        self.rect = rect
        self.name = name
        self.description = description
        self.connections = connections

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
        return f"Location(name={self.name}, connections={self.connections})"

def load_ship_locations():
    locations = {}
    location_dir = resource_path("locations/knacknarpia/")
    for file_name in os.listdir(location_dir):
        if file_name.endswith(".jpg"):
            location_surface = pygame.image.load(resource_path("locations/knacknarpia/" + file_name))
            item_surface = pygame.transform.scale(location_surface, (LOCATION_WIDTH, LOCATION_HEIGHT))
            name = file_name.split(".")[0]
            description, connections = KNAKNARPIA_LOCATION_ATTRIBUTES[name]
            locations[name] = Location(item_surface, pygame.Rect(LOCATION_RECT).copy(), name, description, connections)
    return locations

def load_pirate_locations():
    locations = {}
    location_dir = resource_path("locations/pirates/")
    for file_name in os.listdir(location_dir):
        if file_name.endswith(".jpg"):
            location_surface = pygame.image.load(resource_path("locations/pirates/" + file_name))
            item_surface = pygame.transform.scale(location_surface, (LOCATION_WIDTH, LOCATION_HEIGHT))
            name = file_name.split(".")[0]
            description, connections = PIRATE_LOCATION_ATTRIBUTES[name]
            locations[name] = Location(item_surface, pygame.Rect(LOCATION_RECT).copy(), name, description, connections)
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
