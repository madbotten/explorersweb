
import pygame
import os
import sys

from Character import *
from Item import *
from Location import *
from Utils import *
from Event import *
from TypeText import *

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8  # Adjust for 8 characters, reserving space for credits

no_suitable_statements = [
    "However, no one on the team is trained to handle this.",
    "No one has any skills or items to apply to the task.",
    "The team isn't equipped to handle this problem effectively.",
    "There isn't anyone with the necessary expertise.",
    "No one on the team possesses the necessary skills.",
]

global locations
global mission_failed
global rooms_to_goal

def update_screen(surface, background, hour, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"HOUR {hour}", True, CYAN)
    surface.blit(day_text, (40, 10))
    ship_text = font.render("Searching the mission point", True, CYAN)
    surface.blit(ship_text, (120, 10))
    reset_text_offsets()

def calculate_outcome_sickbay(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} grabs a spare medikit from the corner.", font)
    return

def calculate_outcome_locked_portal(team, stat_name, skill_name, screen, font):
    global rooms_to_goal

    # try using cutter
    if team_has_item(team, "cutter"):
        type_out_text(screen, "The team uses the cutter to breach the portal.", font, WHITE)
        return None

    # try hacking
    member = determine_best_team_member(team, None, "Hacking")
    type_out_text(screen, f"{member.name} tries to hack the controller:", font)

    check_passed = standard_skill_check(member, screen, None, "Hacking", font, 0)

    if check_passed:
        result_text = f"{member.name} gets access and opens the portal.\nTheir skill has been strengthened."
        type_out_text(screen, result_text, font, WHITE)
        member.mission_points += 5
        member.increase_skill("Hacking", 1)
        return
    else:
        result_text = f"{member.name} could not break in."
        type_out_text(screen, result_text, font, WHITE)

    # try rerouting the portal control
    member = determine_best_team_member(team, None, "Ships Systems")
    type_out_text(screen, f"{member.name} tries to route around the portal controller:", font)
    check_passed = standard_skill_check(member, screen, None, "Ships Systems", font, 0)

    if check_passed:
        result_text = f"{member.name} gets opens the portal.\nTheir skill has been strengthened."
        type_out_text(screen, result_text, font, WHITE)
        member.mission_points += 5
        member.increase_skill("Ships Systems", 1)
        return
    else:
        result_text = f"{member.name} could not reroute the control."
        type_out_text(screen, result_text, font, WHITE)

    # try to blow up the lock
    member = determine_best_team_member(team, None, "Explosives")
    type_out_text(screen, f"{member.name} prepares a small charge to blow out the lock:", font)
    check_passed = standard_skill_check(member, screen, None, "Explosives", font, 0)

    if check_passed:
        result_text = f"{member.name} gets the portal open.\nTheir skill has been strengthened."
        type_out_text(screen, result_text, font, WHITE)
        member.mission_points += 5
        member.increase_skill("Explosives", 1)
        return
    else:
        result_text = f"{member.name} could not blow out the lock."
        type_out_text(screen, result_text, font, WHITE)

    rooms_to_goal += 5
    type_out_text(screen, "The portal remains locked, the team must take another route", font, WHITE)
    reset_x_offset()
    return

def calculate_goal_outcome_hack(member, screen, font):
    type_out_text(screen, f"{member.name} steps up to hack into the console:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, None, "Hacking", 0)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, "Hacking", None, 0), font, color)

    if skill_check:
        result_text = f"{member.name} gets access and downloads secrets (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Hacking", 5)
        result = True
    else:
        result_text = f"{member.name} could not break in."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_goal_outcome_explosives(member, screen, font):
    type_out_text(screen, f"{member.name} steps up to place explosives at the mechanism:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, None, "Explosives", 0)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, "Explosives", None, 0), font, color)

    if skill_check:
        result_text = f"{member.name} detonates a shaped charge and forces the vault open (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill("Explosives", 5)
        result = True
    else:
        result_text = f"{member.name} detonates a shaped charge but the mechanism remains secured."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_goal_outcome_cutter(member, screen, font):
    type_out_text(screen, f"{member.name} begins to work on the controller with their cutter:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, "coordination", None, 10)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, None, "coordination", 10), font, color)

    if skill_check:
        result_text = f"{member.name} cuts past the controller and forces the portal open (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} detonates a shaped charge but the area remains unbreached."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_goal_outcome_negotiation(member, screen, font):
    type_out_text(screen, f"{member.name} negotiates with the AI", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.skill_check(roll, "Negotiation", None, 10)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, None, "coordination", 10), font, color)

    if skill_check:
        result_text = f"{member.name} cuts past the controller and forces the portal open (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} detonates a shaped charge but the area remains unbreached."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_goal_outcome_diplomacy(member, screen, font):
    type_out_text(screen, f"{member.name} conducts diplomacy with the AI", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, "coordination", None, 10)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, None, "coordination", 10), font, color)

    if skill_check:
        result_text = f"{member.name} cuts past the controller and forces the portal open (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} detonates a shaped charge but the area remains unbreached."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_goal_outcome_espionage(member, screen, font):
    type_out_text(screen, f"{member.name} tries to use their skill in espionage:", font)

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, None, "Espionage", 10)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, "Espionage", None, 10), font, color)

    if skill_check:
        result_text = f"{member.name} succeeds in the operation (+10 mission points)."
        member.mission_points += 10
        result = True
    else:
        result_text = f"{member.name} fails to make any progress."
        result = False

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()
    return result

def calculate_outcome_pirate_vault(team, stat_name, skill_name, screen, font):
    global mission_failed

    print("Trying hacking")
    member = determine_best_team_member(team, None, "Hacking")
    if member:
        mission_failed = not calculate_goal_outcome_hack(member, screen, font)
        print(f"{mission_failed}")

    if mission_failed:
        print("Trying explosives")
        member = determine_best_team_member(team, None, "Explosives",)
        if member:
            mission_failed = not calculate_goal_outcome_explosives(member, screen, font)
            print(f"{mission_failed}")

    if mission_failed:
        print("Trying cutter")
        member = determine_best_team_member(team, None, None)
        if member:
            mission_failed = not calculate_goal_outcome_cutter(member, screen, font)
            print(f"{mission_failed}")

    if mission_failed:
        type_out_text(screen, "The mission has failed!", font)
    else:
        mission_failed = False
        type_out_text(screen, "The Trilisk artifact is retrieved from the breached vault.\n Mission objective has been achieved!", font)

    return

def calculate_outcome_officers_quarters_jalorith(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = False
    type_out_text(screen, "Jalorith has been defeated. The mission objective has been achieved!", font)
    return

def calculate_outcome_officers_quarters_neutralize(team, stat_name, skill_name, screen, font):
    global mission_failed

    mission_failed = False
    type_out_text(screen, "All the pirates have been neutralized. The mission objective has been achieved!", font)
    return

def calculate_outcome_ai_core(team, stat_name, skill_name, screen, font):
    global mission_failed

    member = determine_best_team_member(team, None, "Negotiation")
    if member:
        mission_failed = not calculate_goal_outcome_negotiation(member, screen, font)

    if mission_failed:
        member = determine_best_team_member(team, None, "Espionage")
        if member:
            mission_failed = not calculate_goal_outcome_espionage(member, screen, font)

    if mission_failed:
        member = determine_best_team_member(team, None, "Diplomacy")
        if member:
            mission_failed = not calculate_goal_outcome_diplomacy(member, screen, font)

    if mission_failed:
        type_out_text(screen, "The mission has failed!", font)
    else:
        mission_failed = False
        type_out_text(screen, "The AI core yields the secret information to the team.\nThe mission mission objective has been achieved!", font)

    return

def calculate_outcome_hack_a_console(team, stat_name, skill_name, screen, font):
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} steps up to hack into the console:", font)
    else:
        type_out_text(screen, random.choice(no_suitable_statements), font)
        result_text = "No one can access any data from here."
        type_out_text(screen, result_text, font, WHITE)
        return

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, stat_name, skill_name, 0)
    if skill_check:
        color = GREEN
    else: color = RED
    type_out_text(screen, roll_string(roll, skill_name, stat_name, 0), font, color)

    if skill_check:
        result_text = f"{member.name} gets access and downloads secrets (+10 mission points).\nTheir skill has been strengthened."
        member.mission_points += 10
        member.increase_skill(skill_name, 5)
        member.increase_stat(stat_name, 3)
    else:
        result_text = f"{member.name} could not discover anything useful."

    type_out_text(screen, result_text, font, WHITE)
    reset_x_offset()

def empty_outcome(team, stat_name, skill_name, screen, font):
    return

def go_mission(team_data) :
    global max_height
    global locations
    global mission_failed
    global rooms_to_goal

    mission_failed = False
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT
    reset_text_offsets()

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mission")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    LOCATION_FONT = pygame.font.Font(font_path, 18)
    SMALL_FONT = pygame.font.Font(font_path, 12)
    EXIT_RECT = pygame.Rect(1330, 8, 105, 25)
    stage = 5

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team("team_data_stage_4.pkl")
    team = [Character.from_dict(data) for data in team_data]
    for member in team:
        member.team = team
    # Hacking icon sizes-- redo this
    for member in team:
        member.portrait = pygame.transform.scale(member.portrait, (60, 70))
        for item in member.equipment:
            item.icon = pygame.transform.scale(item.icon, (40, 40))

    # Load sounds
    play_background_music("music/track3.mp3", pygame)

    # Load locations and attributes
    locations = load_pirate_locations()
    all_items = load_items_battle()

    # preevent, postevent, team, rangedbots, meleebots, enemies, stat_name, skill_name, items, locations, outcome, all_items
    goal_event = [
        Event(
            "The team breaches a hatch and discovers a vault room beyond.",
            "The vault must be breached to obtain the mission objective.",
            5, "Intelligence", "Hacking", locations["vault"],
            calculate_outcome_pirate_vault,
            all_items,
        ),
        Event(
            "The team breaches a hatch and discovers the officer's quarters!",
            "Jalorith is neutralized. The mission has been completed!",
            6, None, None, locations["officer's quarters"],
            calculate_outcome_officers_quarters_jalorith,
            all_items,
        ),
        Event(
            "The team breaches a hatch and discovers the officer's quarters!",
            "All pirates have been neutralized. The mission is a success!",
            5, None, None, locations["officer's quarters"],
            calculate_outcome_officers_quarters_neutralize,
            all_items,
        ),
        Event(
            "The team breaches a hatch and discovers the ai core room!",
            "The team must obtain secrets held by the AI core to succeed.",
            5, None, None, locations["ai core"],
            calculate_outcome_ai_core,
            all_items,
        ),
    ]

    # preevent, postevent, team, enemies, stat_name, skill_name, items, locations, outcome, all_items
    repeatable_events = [
        # Empty outcomes
        Event(
            "The team breaches a hatch and enters a barracks.",
            "This room has been cleared.",
            5, None, None, locations["barracks"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team enters a medical bay.",
            "This sickbay has been cleared.",
            1, None, "Medicine", locations["medical bay"],
            calculate_outcome_sickbay,
            all_items,
        ),
        Event(
            "The team passes into an unfinished room.",
            "This room has been cleared.",
            2, None, None, locations["new chamber"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team finds a colorful room with chairs and a bar.",
            "The canteen has been cleared.",
            0, None, None, locations["canteen"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team breaches a hatch and enters a bay.",
            "Bioaugmentation has been cleared.",
            2, None, None, locations["bioaugmentation"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team's path is blocked by a locked portal.",
            "The corridor has been cleared.",
            0, None, None, locations["corridor"],
            calculate_outcome_locked_portal,
            all_items,
        ),
    ]

    # preevent, postevent, team, enemies, stat_name, skill_name, items, location, outcome, all_items
    optional_singular_events = [
        # Skill check events
        Event(
            "The team enters a messy lab undetected.",
            "The team finds a computer access point and attempts to hack into it.",
            0, None, "Hacking", locations["workshop"],
            calculate_outcome_hack_a_console,
            all_items,
        ),
        # Empty outcomes
        Event(
            "Three pirates attempt to ambush the team in a corridor.",
            "The ambush is over.",
            3, None, None, locations["corridor"],
            empty_outcome,
            all_items,
        ),
    ]

    rando_atmosphere_strings = [
        " the scent of oil and burnt metal fills the air, mingling with the faint aroma of alien spices.",
        " dim, flickering lights cast long shadows, making the base feel even more menacing.",
        " the sound of distant shouting and clanking echoes through the corridors.",
        " holographic wanted posters line the walls, some bearing unsettling resemblances to the team.",
        " the constant hum of the reactor below the base creates a faint vibration underfoot.",
        " the team feels a mix of thrill and unease as rowdy pirates share tales of plunder nearby.",
        " the background hum of life support circulating air breaks the tense silence.",
        " the base's patchwork construction gives the impression it could collapse at any moment.",
        f" {team[random.randint(0, len(team) - 1)].name} sees something in the shadows, then determines nothing is there.",
        " the team debates whether the treasure map on the wall is genuine or a trap.",
        " the glow of a failing light bar paints the area in eerie colors.",
        " a distant intercom speaker emits a song of betrayal and revenge, setting everyone on edge.",
        " the distant sound of laughter echoes through an air duct.",
        f" {team[random.randint(0, len(team) - 1)].name} accidentally bumps into something, making too much noise.",
        " the team notices strange graffiti in a language none of them can decipher.",
        " a faint smell of alien flora wafts in from the base’s vent system, oddly calming amidst the chaos.",
        " a gang of pirates loudly debates something in the distance.",
        " the walls of the base are lined with crates of smuggled goods, their origins a mystery.",
        f" {team[random.randint(0, len(team) - 1)].name} hears an unidentifiable language echoing in the distance.",
        " the base’s dim atmosphere is momentarily broken by a sharp alarm, leaving the team on edge.",
    ]

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage4.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))

    hour = 1
    voyage_complete = False
    # Display the hour
    day_text = DEFAULT_FONT.render(f"HOUR {hour}", True, CYAN)
    screen.blit(day_text, (40, 10))
    ship_text = DEFAULT_FONT.render("The team arrives at the mission point", True, CYAN)
    screen.blit(ship_text, (120, 10))
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    intro_text = "The team arrives on planet at the mission point..."
    type_out_text(screen, intro_text, DEFAULT_FONT)

    mission_index = team[0].mission["mission_index"]
    intro_text = MISSION_GOALS[mission_index][0]
    type_out_text(screen, intro_text, DEFAULT_FONT)
    intro_text = "Click to proceed."
    type_out_text(screen, intro_text, DEFAULT_FONT)

    location = locations["entrance"]
    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
    rooms_to_goal = 5 # random.randint(10, 15)

    if team is None:
        print("Team is None")

    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if team_dead(team) or mission_failed:
                running = False
                break

            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False
                else:
                    waiting = False
                    update_screen(screen, background_image, hour, DEFAULT_FONT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        type_out_text(screen, "The team continues..." + rando_text, DEFAULT_FONT)
                    else:
                        running = False
                        waiting = True

        # Move to next event
        if not waiting:
            if rooms_to_goal <= 0:
                # goal event for mission
                event = goal_event[mission_index]
                location = event.context.location
                draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                hour += 1
                voyage_complete = True
                if not mission_failed:
                    team_mission_success(team)
            else:
                selector = random.randint(0, 100)
                if selector > 75 and optional_singular_events:
                    # Singular event
                    event_index = random.randint(0, len(optional_singular_events) - 1)
                    event = optional_singular_events.pop(event_index)
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    rooms_to_goal -= 1
                    hour += 1
                else:
                    # repeatable event
                    event_index = random.randint(0, len(repeatable_events) - 1)
                    event = repeatable_events[event_index]
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    rooms_to_goal -= 1
                    hour += 1
            waiting = True

        # Update the display
        screen.blit(EXIT_TEXT, EXIT_RECT)
        pygame.display.flip()

    # Save characters upon exit
    if stage < 1000:
        team_data = save_team("team_data_stage_5.pkl", team)
    else:
        team_data = None

    pygame.quit()

    return stage + 1, team_data

def main():
    print("Starting Stage: Mission")
    team_data = mission(None)

if __name__ == "__main__":
    main()
