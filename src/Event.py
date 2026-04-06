import pygame
import random
import time

from Battle import *
from TypeText import *
from Character import *

enemies_present_statements = [
    "Enemies are present! A battle breaks out.",
    "Enemies are present, weapons drawn!",
    "An alarm blares, and enemy forces rush into the room from a far door!",
    "The team encounters hostiles!",
    "Enemies block the team's path!",
    "Combat commences!"
    "A fight erupts!",
    "The team finds themselves face-to-face with a group of hostiles!"
]

def team_evades_notice(team):
    """Rolls to see if the team avoids being detected before combat.
    Returns True if the team slips by unnoticed."""
    if not team:
        return False
    avg_evasion = sum(m.get_effective_combat_evasion() for m in team) / len(team)
    roll = random.randint(1, 100)
    evaded = roll < avg_evasion
    print(f"Stealth check: roll={roll}, avg_evasion={avg_evasion:.1f}, evaded={evaded}")
    return evaded

def mission_failure(screen, font):
    global mission_failed
    type_out_text(screen, "The mission has failed.", font)
    mission_failed = True

def team_status(team, screen, font):
    deaths = 0
    for member in team:
        if member.stats["lifelevel"] * 100 // member.max_lifelevel() <= 0:
            deaths += 1

    for member in team:
        member.demoralize(5 * deaths)

    for member in team:
        percent = member.stats["lifelevel"] * 100 // member.max_lifelevel()
        morale = member.morale // 100
        color = GREEN
        if percent <= 50:
            color = RED
        if percent > 0:
            emit_character_image_at_text_offset(member, screen)
            type_out_text(screen, f"{member.name} health is {percent}%.\n ", font, color)
            type_out_text(screen, f"{member.name} morale is {morale}%.\n ", font, color)
        else:
            emit_character_image_at_text_offset(member, screen)
            type_out_text(screen, f"{member.name} is dead.\n ", font, RED)

    reset_x_offset()

def team_repairs_robots(team, screen, font):
    # Check if any robot item hp is below normal
    repair_needed = False
    robots = [m for m in team if m.type == "robot"]
    for robot in robots:
        if robot.type == "robot":
          if 0 < robot.stats["lifelevel"] < .75 * robot.max_life:
            type_out_text(screen, f"{robot.name} needs repair.", font)
            repair_needed = True

    if not repair_needed:
        type_out_text(screen, "No robot repairs needed.", font)
        return

    # Perform skill check for "Robot Repair"
    repair_successful = team_skill_check(team, "Robot Repair", 0)
    if repair_successful:
        type_out_text(screen, "Repair skills and equipment improved the results.", font)
        base_repair = 40
    else:
        base_repair = 10

    for robot in robots:
        if robot.type == "robot":
          robot.stats["lifelevel"] = min(robot.max_life, robot.stats["lifelevel"] + base_repair)

    return

def team_heals(team, screen, font):
    # take out your dead
    for member in team[:]:
        if member.stats["lifelevel"] <= 0:
            type_out_text(screen, f"{member.name} is dead.", font, RED)
            team.remove(member)
    # Refresh each survivor's team reference so mulebot checks stay accurate
    for member in team:
        member.team = team

    healing_needed = team_needs_heal(team)
    if not healing_needed:
        type_out_text(screen, "No healing is needed.", font)
        return  # No healing needed

    type_out_text(screen, "The team pauses to heal.", font)

    # Perform skill checks for "Medicine" with difficulty_modifier=0
    # It's okay to skill check against dead members, b/c that check always returns False
    healing_successful = team_skill_check(team, "Medicine", 0)

    # Find the best medikit carried by any team member
    best_medikit = None
    for member in team:
        for item in member.equipment:
            if item_base_name(item.name) == "medikit":
                if best_medikit is None or item.effect > best_medikit.effect:
                    best_medikit = item

    # Determine base healing amounts
    if healing_successful:
        type_out_text(screen, "Medical skills improved the results.", font)
        base_heal = 50
        medikit_heal = best_medikit.effect if best_medikit else 0
    else:
        base_heal = 25
        medikit_heal = (best_medikit.effect // 2) if best_medikit else 0

    # Check if a medikit is available
    has_medikit = best_medikit is not None or team_has_item(team, "medibot")

    # Remove one medikit if available
    if has_medikit:
        type_out_text(screen, "A medikit had to be consumed to patch everyone up.", font)
        for member in team:
            for item in member.equipment:
                if item_base_name(item.name) == "medikit":
                    member.equipment.remove(item)
                    break
            else:
                continue
            break

    # Heal all ALIVE team members
    heal_amount = base_heal + (medikit_heal if has_medikit else 0)
    heal_team_by(team, heal_amount)

    team_status(team, screen, font)

def pirate_enemies(num_pirates, items):
    pirates = []

    # Filter weapons from items where type is "wep"
    weapon_items = [item for item in items.values() if item.type == "weapon"]
    armor_items = [item for item in items.values() if item.type == "armor"]
    non_weapon_items = [item for item in items.values() if (item.type != "weapon" and item.type != "armor")]

    for i in range(num_pirates):
        pirates.append(pirate_enemy(i, weapon_items, armor_items, non_weapon_items, items))

    return pirates

def jalorith(items):
    pirate = Character(20, "pirate")
    pirate.occupation = "pirate"  # Override occupation to "pirate"
    pirate.name = "Jalorith"

    # Assign a random weapon
    pirate.add_item(items["laser rifle A"])
    pirate.add_item(items["powered armor A"])
    pirate.add_item(items["offense implant C"])
    pirate.add_item(items["slicer S"])
    return pirate

def pirate_enemy(i, weapon_items, armor_items, non_weapon_items, all_items):
    index = random.randint(1, 24)
    pirate = Character(index, "pirate", 60, 70)
    pirate.index = i

    # Assign a random weapon
    if weapon_items:
        weapon = random.choice(weapon_items)
        pirate.add_item(weapon)
        #pirate.add_item(all_items["pistol"])
    if armor_items:
        armor = random.choice(armor_items)
        pirate.add_item(armor)

    # Assign 1-3 random additional items
    num_additional_items = random.randint(1, 3)
    additional_items = random.sample(non_weapon_items, k=min(num_additional_items, len(non_weapon_items)))

    for item in additional_items:
        pirate.add_item(item)
    return pirate

def pause_to_clear_screen(screen, background, font):
    paused = True
    type_out_text(screen, "Click to continue.", font)
    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                paused = False
    clear_screen(screen, background)

class Event:
    def __init__(self, pre_description, post_description, num_enemies, stat_name, skill_name, location, calculate_outcome, all_items):
        self.context = EventContext(pre_description, post_description, num_enemies, stat_name, skill_name, location, calculate_outcome, all_items)

    def run(self, team, screen, font, background, location_font):
        self.context.add_run_params(team, screen, font, background, location_font)
        if self.context.num_enemies == 0:
            self.context.enemies = None
        else:
            self.context.enemies = pirate_enemies(self.context.num_enemies, self.context.all_items)

        if self.context.num_enemies == 6 and self.context.location["name"] == "officer's quarters":
            self.context.enemies = pirate_enemies(5, self.context.all_items).append(jalorith(self.context.all_items))

        # Display the pre-battle description
        type_out_text(screen, self.context.pre_description, font)

        # Run the battle, if any
        if self.context.enemies:
            self.run_battle()

        # Calculate the outcome of the event
        next_event = self.context.calculate_outcome(team, self.context.stat_name, self.context.skill_name, screen, font)
        compound_event = False
        # Handle compound events
        while(next_event) is not None:
            compound_event = True
            next_event = next_event.run(team, screen, font, background, location_font)

        # Don't ask for click on compound events
        reset_x_offset()
        if not compound_event:
            type_out_text(screen, "Click to proceed.", font)

    def run_battle(self):
        methods = self.context.team[0].mission.get("methods") if self.context.team else None

        # --- Stealth check ---
        if methods == "stealth":
            if team_evades_notice(self.context.team):
                type_out_text(self.context.screen, "The team moves silently past the enemies undetected.", self.context.font)
                return  # skip combat entirely
            else:
                type_out_text(self.context.screen, "The team is spotted! Combat ensues.", self.context.font)
        type_out_text(self.context.screen, random.choice(enemies_present_statements), self.context.font)

        if methods == "brazen":
            self.context.brazen_bonus = 25
            type_out_text(self.context.screen, "The team catches the enemy by surprise!", self.context.font)
        pause_to_clear_screen(self.context.screen, self.context.background, self.context.font)
        event_battle = TeamBattle(self.context)
        event_battle.run_battle()
        pygame.mixer.music.fadeout(2000)
        play_background_music("music/track3.mp3", pygame)
        max_y_offset()

        # If team died, game ends
        if team_dead(self.context.team):
            mission_failure(self.context.screen, self.context.font)
        else:
            pause_to_clear_screen(self.context.screen, self.context.background, self.context.font)
        # Heal if appropriate
        if self.context.enemies:
            team_heals(self.context.team, self.context.screen, self.context.font)
            team_repairs_robots(self.context.team, self.context.screen, self.context.font)

        # Display the post-battle description
        if self.context.post_description is not None:
            type_out_text(self.context.screen, self.context.post_description, self.context.font)