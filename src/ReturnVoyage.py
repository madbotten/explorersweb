import pygame
import os
import random
import pickle
import time
import sys

from Character import Character
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
BASE_TEXT_X_OFFSET = 50

no_suitable_statements = [
    "However, no one on the team is a suitable instructor.",
    "No one has any valuable skills to share.",
    "The team doesn't really know what they are doing.",
    "The team lacks someone capable of effective instruction.",
    "There isn't anyone with the expertise needed to guide others.",
    "No one on the team possesses the necessary teaching skills.",
    "The team is missing a member who can effectively pass on knowledge.",
    "None of the team members are experienced enough to instruct.",
    "There’s no one on the team who feels confident enough to teach.",
    "No one here has the ability to instruct others properly.",
    "The team doesn't have someone with skills to share on this subject.",
    "None of the members are equipped to share their expertise."
]

teaches_statements = [
    "shares many valuable insights with the team.",
    "provides excellent instruction.",
    "is able to help everyone master some concepts.",
    "delivers practical knowledge to the group.",
    "breaks down complex topics into simple concepts for the team.",
    "helps teammates overcome obstacles with clear guidance.",
    "instills confidence in the group through effective teaching.",
    "shares a wealth of experience to support everyone's growth.",
    "leads the team with clear and concise instruction.",
    "bridges knowledge gaps with insightful explanations.",
    "demonstrates a clear understanding of the material.",
    "guides everyone through difficult tasks step by step.",
    "empowers the team with actionable knowledge.",
]

teacher_responds_statements = [
    "responds by offering to train teammates:",
    "steps up to show some pointers:",
    "convinces everyone to listen up and learn something:",
    "offers to walk everyone through the process:",
    "decides to take the lead in teaching some key points:",
    "steps forward to share knowledge with the team:",
    "volunteers to provide a learning session:",
    "proposes a quick training to get everyone on the same page:",
    "initiates a hands-on learning session for the group:",
    "takes it upon themselves to demonstrate the right approach:",
    "actively engages with the team to pass on their expertise:",
    "encourages the team to follow along and learn something new:",
    "gets the team together for an impromptu training session:",
]

train_fail_statements = [
    "tries to teach the team, but only confuses them.",
    "provides instruction, but little of it gets through.",
    "fails to keep everyone's focus during the session.",
    "ends up leaving the team more confused than before.",
    "fails to clarify the topic effectively for everyone.",
    "tries to explain, but the message gets lost in translation.",
    "provides unclear examples that confuse the team further.",
    "cannot maintain the team’s attention long enough to teach.",
    "loses the group’s interest halfway through the session.",
    "ends up creating more questions than answers.",
    "struggles to deliver the content in a way that sticks.",
    "cannot simplify the concepts enough for everyone to follow.",
    "tries hard but fails to make the material understandable.",
]

no_suitable_team_member_statements = [
  "No suitable team members found to address the event.",
  "No one has the skill to prevent the fire from spreading in the area.",
  "No one responds in time.",
]

global locations

def update_screen(surface, background, day, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"DAY {day}", True, CYAN)
    surface.blit(day_text, (40, 10))
    ship_text = font.render("The voyage of Knacknarpia to mission point", True, CYAN)
    surface.blit(ship_text, (140, 10))
    reset_text_offsets()

def calculate_outcome_training(team, stat_name, skill_name, screen, font):
    # Determine the best team member(s) to handle the event
    member = determine_best_team_member(team, stat_name, skill_name)
    if member:
        type_out_text(screen, f"{member.name} {random.choice(teacher_responds_statements)}", font)
    else:
        type_out_text(screen, random.choice(no_suitable_statements), font)
        return

    # Simulate a skill check
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.skill_check(roll, skill_name, 0)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, skill_name, stat_name, 0), font, color)

    if skill_check:
        result_text = f"{member.name} {random.choice(teaches_statements)}\n(Mission points + 1)"
        member.mission_points += 1
        for member in team:
          member.increase_skill(skill_name, 2)
    else:
        result_text = f"{member.name} {random.choice(train_fail_statements)}\n "

    type_out_text(screen, result_text, font, WHITE)

def empty_outcome(team, stat_name, skill_name, screen, font):
    return

def return_voyage(team_data) :
    global max_height
    global locations

    reset_text_offsets()
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Voyage")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    LOCATION_FONT = pygame.font.Font(font_path, 18)
    SMALL_FONT = pygame.font.Font(font_path, 12)
    EXIT_RECT = pygame.Rect(1330, 8, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team("team_data_stage_5.pkl")
    team = [Character.from_dict(data) for data in team_data]
    for character in team:
        character.team = team

    # Resize portraits to fit into a small area for each character
    for character in team:
        if character.portrait:
            character.portrait = pygame.transform.scale(character.portrait, (70, 80))

    # Load and play background music
    play_background_music("music/track3.mp3", pygame)

    # Load locations and attributes
    locations = load_ship_locations()
    all_items = load_items_battle()

    # pre_description,
    # post_description,
    # num_enemies, stat_name, skill_name,location,
    # calculate_outcome,
    # all_items
    repeatable_events = [
        # Empty outcomes
        Event(
            "The team recuperates in their quarters, pondering what comes next.",
            None,
            0, "intelligence", None, locations["quarters"],
            empty_outcome,
            all_items,
        ),
        Event(
            "The team decides they would like to practice hacking.",
            None,
            0, None, "Hacking", locations["bridge"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team conducts a virtual shooting practice session in the holo room.",
            None,
            0, None, "Projectile Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team tries to manipulate each other to get their favorite food bars.",
            "Eventually everyone accepts their ration.",
            0, None, "Social Engineering", locations["mess"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team is restless and decide to spar in the holo room.",
            "The sparring is over.",
            0, None, "Martial Arts", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team plays hide and seek to pass the time.",
            "The time for games is over.",
            0, None, "Stealth", locations["supply room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "While eating in the mess hall, the team discusses what aliens they might encounter on the mission.",
            "The meal ends.",
            0, None, "Xenobiology", locations["mess"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team plans out how to conduct the mission.",
            None,
            0, None, "Squad Tactics", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team debates what model of combat mech is the most effective.",
            "The debate subsides.",
            0, None, "Mech Combat", locations["robot bay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team simulates flying maneuvers in the holo room.",
            "The training session is over.",
            0, None, "Piloting", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team attempts to bypass a simulated security system.",
            None,
            0, None, "Hacking", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices negotiating resource agreements with an AI facilitator.",
            None,
            0, None, "Negotiation", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team participates in a sharpshooting competition using holographic targets.",
            None,
            0, None, "Sharpshooting", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices infiltrating a simulated enemy facility.",
            None,
            0, None, "Stealth", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team learns advanced first aid techniques.",
            None,
            0, None, "Medicine", locations["sickbay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices with sonic weapons in a virtual environment.",
            None,
            0, None, "Sonic Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team analyzes historical military conflicts in the planning room.",
            None,
            0, None, "Military Science", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team safely defuses a mock explosive device.",
            None,
            0, None, "Explosives", locations["hangar"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team experiments with prosthetic enhancements in the tech lab.",
            None,
            0, None, "Cybernetics", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team studies alien biology specimens in hydroponics.",
            None,
            0, None, "Xenobiology", locations["hydroponics"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices building shelters in a survival simulation.",
            None,
            0, None, "Survival", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team simulates high-stakes diplomatic negotiations with an AI moderator.",
            None,
            0, None, "Diplomacy", locations["communications"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team develops tactical plans for various combat scenarios.",
            None,
            0, None, "Tactics", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices star map navigation.",
            None,
            0, None, "Navigation", locations["bridge"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team interrogates a simulated suspect to uncover vital information.",
            None,
            0, None, "Interrogation", locations["brig"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team repairs malfunctioning droids in the robot bay.",
            None,
            0, None, "Robot Repair", locations["robot bay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team works on repairing the ship's life support systems.",
            None,
            0, None, "Ships Systems", locations["life support"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices gathering intelligence from a simulated enemy base.",
            None,
            0, None, "Espionage", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team fabricates essential mission tools using the onboard fabricator.",
            None,
            0, None, "Fabrication", locations["engineering"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices using high-energy weapons in a controlled environment.",
            None,
            0, None, "Energy Weapons", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team solves complex physics problems to optimize their equipment.",
            None,
            0, None, "Physics", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team analyzes mock artifacts for potential functionality.",
            None,
            0, None, "Artifact Analysis", locations["tech lab"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team runs squad drills in simulated battle conditions.",
            None,
            0, None, "Squad Tactics", locations["mission planning"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team tests exoskeleton systems for improved mobility and strength.",
            None,
            0, None, "Exoskeleton Systems", locations["engineering"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team conducts an advanced medical emergency response drill.",
            None,
            0, None, "Medicine", locations["sickbay"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team learns efficient methods for extracting resources in simulated terrain.",
            None,
            0, None, "Resource Extraction", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
        Event(
            "The team practices detecting anomalies in a simulated operational environment.",
            None,
            0, None, "Detection", locations["holo room"],
            calculate_outcome_training,
            all_items,
        ),
    ]

    optional_singular_events = [
        # Skill check events
        # Empty outcomes
        Event(
            "Situation critical. We have run out of Oreos.",
            "There is no recourse.",
            0, "intelligence", None, locations["mess"],
            empty_outcome,
            all_items,
        ),
    ]

    rando_atmosphere_strings = [
        " the vastness of space overwhelms the crew, causing a combination of awe and anxiety.",
        " the tiny confines of the Knacknarpia press in on the crew, causing them to feel trapped.",
        " the meager selection of food begins to annoy the crew.",
        " the crew plays a virtual Starcraft tournament to pass the time.",
        " the team debates whether or not life is a simulation.",
        " despite the best life support, the air in the ship is stale.",
        " data drops from the frontier become fewer and far between.",
        " the crew hypothesizes about the source of that intermittent creaking sound in the bulkhead.",
        f" {team[random.randint(0, len(team) - 1)].name} regales the crew with tales of past glory.",
        " the Knacknarpia has become home for the team until they reach the mission point.",
        " the team starts to doubt if their mission can be accomplished.",
        f" {team[random.randint(0, len(team) - 1)].name} has a dream they are convinced is an alien warning to turn back.",
    ]

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    stage = 6

    day = 1
    voyage_complete = False
    # Display the day
    day_text = DEFAULT_FONT.render(f"DAY {day}", True, CYAN)
    screen.blit(day_text, (40, 10))
    ship_text = DEFAULT_FONT.render("The voyage of Knacknarpia to home base", True, CYAN)
    screen.blit(ship_text, (140, 10))

    intro_text = "The return voyage to home base begins... click to proceed."
    type_out_text(screen, intro_text, DEFAULT_FONT)

    events_completed = 0
    max_events_in_voyage = random.randint(10, 15)

    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False
                else:
                    waiting = False
                    update_screen(screen, background_image, day, DEFAULT_FONT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        type_out_text(screen, "The voyage continues..." + rando_text, DEFAULT_FONT)
                    else:
                        running = False
                        waiting = True

        # Move to next event
        if not waiting:
            location = locations[random.choice(list(locations.keys()))]
            if events_completed > max_events_in_voyage:
                type_out_text(screen, "You have arrived at the destination!", DEFAULT_FONT)
                voyage_complete = True
            else:
                selector = random.randint(0, 100)
                if selector < 75:
                    event_index = random.randint(0, len(repeatable_events) - 1)
                    event = repeatable_events[event_index]
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, None, None, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                elif optional_singular_events:
                    event_index = random.randint(0, len(optional_singular_events) - 1)
                    event = optional_singular_events.pop(event_index)
                    location = event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    event.run(team, None, None, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    events_completed = max_events_in_voyage
                    day += 1
            waiting = True

        # Update the display
        screen.blit(EXIT_TEXT, EXIT_RECT)
        pygame.display.flip()

    # Save characters upon exit
    if stage < 1000:
        team_data = save_team("team_data_stage_6.pkl", team)

    pygame.quit()

    return stage + 1, team_data

def main():
    print("Starting Stage: Return Voyage")
    team_data = return_voyage(None)

if __name__ == "__main__":
    main()
