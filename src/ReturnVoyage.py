import pygame
import os
import random
import pickle
import asyncio
import sys

from Character import Character
from Location import *
from Utils import *
from Event import *
from TypeText import *
from Interaction import Interaction, PRIVATE, PUBLIC, PERSONAL, PROFESSIONAL
from ShipEvents import *
from ShipEvents import _run_interaction, _interaction_reaction_string
from constants import TOP_BAR_Y, DEBUG

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8  # Adjust for 8 characters, reserving space for credits
BASE_TEXT_X_OFFSET = 50

global locations


async def update_screen(surface, background, day, font):
    surface.blit(background, (0, 0))
    day_text = font.render(f"DAY {day}", True, CYAN)
    surface.blit(day_text, (40, TOP_BAR_Y))
    ship_text = font.render("The voyage of Knacknarpia to home base", True, CYAN)
    surface.blit(ship_text, (140, TOP_BAR_Y))
    reset_text_offsets()


async def return_voyage(team_data, team_name="Debug Team", loop=1):
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
    EXIT_RECT = pygame.Rect(1330, TOP_BAR_Y, 105, 25)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 6)
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

    repeatable_events, optional_singular_events, required_singular_events = build_return_voyage_event_sets(
        locations, all_items, team
    )
    rando_atmosphere_strings = build_rando_atmosphere_strings(team)

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    stage = 7

    day = 1
    voyage_complete = False
    # Display the day
    day_text = DEFAULT_FONT.render(f"DAY {day}", True, CYAN)
    screen.blit(day_text, (40, TOP_BAR_Y))
    ship_text = DEFAULT_FONT.render("The voyage of Knacknarpia to home base", True, CYAN)
    screen.blit(ship_text, (140, TOP_BAR_Y))

    intro_text = "The return voyage to home base begins... click to proceed."
    await type_out_text(screen, intro_text, DEFAULT_FONT)

    events_completed = 0
    max_events_in_voyage = random.randint(10, 15)
    speech_done = False
    last_repeatable_event_name = None

    # Pre-schedule trigger points for required events (not at step 0 or the last step)
    _req_count = len(required_singular_events)
    _available = list(range(2, max_events_in_voyage))  # steps 2..max-1
    _req_triggers = set(
        random.sample(_available, min(_req_count, len(_available)))
    )

    # Event Loop
    running = True
    waiting = True
    while running:
        for event in pygame.event.get():
            if team_dead(team):
                await mission_failure(screen, DEFAULT_FONT)
                running = False
                stage = 999  # sentinel: return to load screen
                break

            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False
                else:
                    play_positive_click()
                    waiting = False
                    await update_screen(screen, background_image, day, DEFAULT_FONT)
                    if not voyage_complete:
                        rando_text = ""
                        if rando_atmosphere_strings and random.randint(0, 100) < 30:
                            rando_index = random.randint(0, len(rando_atmosphere_strings) - 1)
                            rando_text = rando_atmosphere_strings.pop(rando_index)
                        await type_out_text(screen, "The voyage continues..." + rando_text, DEFAULT_FONT)
                    else:
                        running = False
                        waiting = True

        # Move to next event
        if not waiting:
            location = locations[random.choice(list(locations.keys()))]
            if not speech_done:
                # Always-first event: inspirational speech
                speech_done = True
                draw_location(locations["mess"], screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                await calculate_outcome_inspirational_speech(
                    team, None, None, screen, DEFAULT_FONT, context_phrase="before the return voyage"
                )
                await type_out_text(screen, "Click to proceed.", DEFAULT_FONT)
                events_completed += 1
                day += 1
            elif events_completed > max_events_in_voyage:
                # Force any remaining required events before declaring arrival
                if required_singular_events:
                    req_event = required_singular_events.pop(0)
                    location = req_event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    await req_event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    await type_out_text(screen, "You have arrived at the destination!", DEFAULT_FONT)
                    voyage_complete = True
            else:
                # Fire a scheduled required event if this step is a trigger point
                if required_singular_events and events_completed in _req_triggers:
                    req_event = required_singular_events.pop(0)
                    location = req_event.context.location
                    draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                    await req_event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                    events_completed += 1
                    day += 1
                else:
                    selector = random.randint(0, 99)
                    if selector < 55:
                        event = build_procedural_training_event(team, locations, all_items, calculate_outcome_training)
                        if event.name == last_repeatable_event_name:
                            event = build_procedural_training_event(team, locations, all_items, calculate_outcome_training)
                        last_repeatable_event_name = event.name
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        events_completed += 1
                        day += 1
                    elif selector < 80:
                        available = repeatable_events if len(repeatable_events) == 1 else \
                            [e for e in repeatable_events if e.name != last_repeatable_event_name]
                        event = random.choice(available)
                        last_repeatable_event_name = event.name
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        events_completed += 1
                        day += 1
                    elif optional_singular_events:
                        event_index = random.randint(0, len(optional_singular_events) - 1)
                        event = optional_singular_events.pop(event_index)
                        location = event.context.location
                        draw_location(location, screen, LOCATION_LEFT, LOCATION_TOP, LOCATION_FONT, SMALL_FONT)
                        await event.run(team, screen, DEFAULT_FONT, background_image, LOCATION_FONT)
                        events_completed += 1
                        day += 1
                    else:
                        events_completed = max_events_in_voyage
                        day += 1
            waiting = True

        # Update the display
        screen.blit(EXIT_TEXT, EXIT_RECT)
        pygame.display.flip()
        await asyncio.sleep(0)

    # Save characters upon exit (only on clean exit, not team death/quit)
    if stage not in (999, 1000):
        team_data = save_team_named(team_name, loop, 7, team)

    pygame.quit()

    return stage + 1, team_data


async def main():
    print("Starting Stage: Return Voyage")
    team_data = return_voyage(None)


if __name__ == "__main__":
    main()
