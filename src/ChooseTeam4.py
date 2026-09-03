import os
import pickle
import pygame
import sys
import textwrap
import random
import asyncio

from Character import Character
from Utils import *
from constants import TOP_BAR_Y, DEBUG

# Generate 100 characters and load their images
candidates = []
rejects = []
names = []
for i in range(1, 101):  # Assuming filenames start from character1.jpg to character100.jpg
    candidate = Character(i, "team")
    while candidate.name in names:
        candidate = Character(i, "team")
    names.append(candidate.name)
    candidates.append(candidate)

# Screen dimensions
TOPMOST = 4
TOP_EDGE = 29
STATS_EDGE = 180
CHARACTER_BOX_WIDTH = 90
CHARACTER_BOX_HEIGHT = 100
BOX_GAP = 10  # Space between boxes

# Create six boxes for "Selected Team"
x_position = 330
y_position = TOP_EDGE
TEAM_BOX_0 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
x_position += CHARACTER_BOX_WIDTH + BOX_GAP
TEAM_BOX_1 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
x_position += CHARACTER_BOX_WIDTH + BOX_GAP
TEAM_BOX_2 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
x_position += CHARACTER_BOX_WIDTH + BOX_GAP
TEAM_BOX_3 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
x_position += CHARACTER_BOX_WIDTH + BOX_GAP
TEAM_BOX_4 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
x_position += CHARACTER_BOX_WIDTH + BOX_GAP
TEAM_BOX_5 = pygame.Rect(x_position, y_position, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
team_boxes = [TEAM_BOX_0, TEAM_BOX_1, TEAM_BOX_2, TEAM_BOX_3, TEAM_BOX_4, TEAM_BOX_5]

# Set next and previous button rects
NEXT_BUTTON_RECT = pygame.Rect(140, TOP_EDGE + 12, 105, 25)
PREV_BUTTON_RECT = pygame.Rect(140, TOP_EDGE + 35, 105, 25)
REJECT_BUTTON_RECT = pygame.Rect(140, TOP_EDGE + 58, 105, 25)
CANDIDATE_LABEL_RECT = pygame.Rect(22, TOPMOST, 105, 25)
LEADER_LABEL_RECT = pygame.Rect(330, TOPMOST, 105, 25)
TEAM_LABEL_RECT = pygame.Rect(640, TOPMOST, 105, 25)
REJECTED_LABEL_RECT = pygame.Rect(1363, TOPMOST, 105, 25)
STATS_LABEL_RECT = pygame.Rect(130, STATS_EDGE, 105, 25)
DERIVED_LABEL_RECT = pygame.Rect(75, STATS_EDGE + 160, 105, 25)
SKILLS_LABEL_RECT = pygame.Rect(700, STATS_EDGE, 105, 25)
BACKGROUND_LABEL_RECT = pygame.Rect(1285, STATS_EDGE, 105, 25)
PROCEED_RECT = pygame.Rect(1150, TOP_EDGE + 35, 105, 25)
EXIT_RECT = pygame.Rect(1150, TOP_BAR_Y, 105, 25)

NAME_Y_TOP = 129
CANDIDATE_NAME_LOC = (40, NAME_Y_TOP)
LEADER_NAME_LOC = (340, NAME_Y_TOP)
TEAM_ONE_NAME_LOC = (340 + 1 * (CHARACTER_BOX_WIDTH + BOX_GAP), NAME_Y_TOP)
TEAM_TWO_NAME_LOC = (340 + 2 * (CHARACTER_BOX_WIDTH + BOX_GAP), NAME_Y_TOP)
TEAM_THREE_NAME_LOC = (340 + 3 * (CHARACTER_BOX_WIDTH + BOX_GAP), NAME_Y_TOP)
TEAM_FOUR_NAME_LOC = (340 + 4 * (CHARACTER_BOX_WIDTH + BOX_GAP), NAME_Y_TOP)
TEAM_FIVE_NAME_LOC = (340 + 5 * (CHARACTER_BOX_WIDTH + BOX_GAP), NAME_Y_TOP)

CANDIDATE_RECT = pygame.Rect(22, TOP_EDGE, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)
REJECTED_BOX = box_rect = pygame.Rect(1375, TOP_EDGE, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT)

async def _prompt_team_name(screen):
    """
    Show a text-entry overlay on the current screen and return the entered team name.
    Accepts alphanumeric characters and spaces (max 20 chars).
    Enter confirms; Backspace deletes. Returns "My Team" if nothing is entered.
    """
    font_path   = resource_path("fonts/Orbitron-Bold.ttf")
    title_font  = pygame.font.Font(font_path, 22)
    input_font  = pygame.font.Font(font_path, 28)
    hint_font   = pygame.font.Font(font_path, 13)

    entered = ""
    MAX_LEN = 20

    # Overlay panel
    panel_w, panel_h = 520, 180
    panel_x = (SCREEN_WIDTH  - panel_w) // 2
    panel_y = (SCREEN_HEIGHT - panel_h) // 2

    clock = pygame.time.Clock()
    done  = False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    done = True
                elif event.key == pygame.K_BACKSPACE:
                    entered = entered[:-1]
                else:
                    ch = event.unicode
                    # Allow letters, digits, spaces
                    if ch and (ch.isalnum() or ch == " ") and len(entered) < MAX_LEN:
                        entered += ch

        # Draw semi-transparent overlay
        overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        overlay.fill((10, 20, 40, 220))
        screen.blit(overlay, (panel_x, panel_y))
        pygame.draw.rect(screen, (0, 180, 200),
                         (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

        # Title
        title = title_font.render("Name your team:", True, (0, 255, 255))
        screen.blit(title, title.get_rect(centerx=panel_x + panel_w // 2,
                                          y=panel_y + 20))

        # Input box
        box_rect = pygame.Rect(panel_x + 30, panel_y + 70, panel_w - 60, 50)
        pygame.draw.rect(screen, (0, 40, 60), box_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 180, 200), box_rect, 2, border_radius=6)
        display_text = entered if entered else ""
        input_surf = input_font.render(display_text + "_", True, (255, 255, 255))
        screen.blit(input_surf, input_surf.get_rect(
            midleft=(box_rect.x + 12, box_rect.centery)))

        # Hint
        hint = hint_font.render("Press Enter to confirm", True, (100, 140, 160))
        screen.blit(hint, hint.get_rect(centerx=panel_x + panel_w // 2,
                                        y=panel_y + 140))

        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

    result = entered.strip() or "My Team"
    return result


async def choose_team(team_data, team_name="Debug Team", loop=1):
    # If this is the first mission, team starts empty.
    # team = [None, None, None, None, None, None]
    # Otherwise, this is an opportunity to replace team members or add ones to replace dead ones
    # This would be better if team is just a list, but the choose team logic has boxes for each one
    # and treats empty boxes as None

    # 1. Initialize the team from data, or start with 6 Nones
    if team_data:
        team = [Character.from_dict(data) for data in team_data]
    else:
        team = [None] * 6

    # 2. Ensure the list is exactly 6 entries long (padding with None if shorter)
    while len(team) < 6:
        team.append(None)

    # 3. Clean up the team: replace dead characters with None
    # This syntax creates a new list based on your "alive" logic
    team = [member if (member and member.is_alive()) else None for member in team]

    # Index of the current candidate on left
    current_candidate_index = 0

    # Index of the current selected character
    current_selected_character = candidates[0]

    def box_empty(box, team):
        for character in team:
            if character is not None:
                if box == character.get_rect():
                    return False
        return True

    def character_in_team_box(box):
        for character in team:
            if character is not None:
                if box == character.get_rect():
                    return character
        return None

    def remove_from_team(candidate):
        for i in range(len(team)):
            if team[i] == candidate:
                team[i] = None

    def team_full(team):
        for i in range(6):
            if team[i] is None:
                return False
        return True

    def swap_on_team(character_present, character_moved):
        present_index = 0
        moved_index = 0
        for i in range(len(team)):
            if team[i] == character_present:
                present_index = i
            if team[i] == character_moved:
                moved_index = i
        team[present_index] = character_moved
        character_moved.get_rect().center = team_boxes[present_index].center
        team[moved_index] = character_present
        character_present.get_rect().center = team_boxes[moved_index].center

    def add_character_to_team_box(character, box, index):
        character.get_rect().center = box.center
        if not character in team:
            team[index] = character
        if character in candidates:
            candidates.remove(character)
        if character in rejects:
            rejects.remove(character)

    def add_character_to_candidates(character, current_selected_character):
        if not character in candidates:
            candidates.append(character)
        if character in team:
            remove_from_team(current_selected_character)
        if character in rejects:
            rejects.remove(character)
        character.set_rect(pygame.Rect(20, TOP_EDGE, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT))

    def add_character_to_rejects(character):
        character.get_rect().center = REJECTED_BOX.center
        if not character in rejects:
            rejects.append(character)
        if character in team:
            remove_from_team(current_selected_character)
        if character in candidates:
            candidates.remove(character)

    def select_next_candidate():
        nonlocal current_candidate_index
        nonlocal current_selected_character
        if len(candidates) > 0:
            if current_candidate_index >= len(candidates):
                current_candidate_index = 0
            current_selected_character = candidates[current_candidate_index]

    def clicked_character(position, current_candidate_index):
        blah = current_selected_character
        if current_selected_character.get_rect().collidepoint(position):
            return current_selected_character
        for character in team:
            if character is not None:
                if character.get_rect().collidepoint(position):
                    return character
        if CANDIDATE_RECT.collidepoint(position) and len(candidates) > 0:
            return candidates[current_candidate_index]
        if REJECTED_BOX.collidepoint(position) and len(rejects) > 0:
            return rejects[len(rejects) - 1]
        return None

    def blit_text3(surface, text, pos, font, color=GREEN, max_width=500):
        lines = text.splitlines()
        y = pos[1]
        for line in lines:
            wrapped_lines = textwrap.wrap(line, width=int(max_width / font.size(" ")[0]))
            for wrapped_line in wrapped_lines:
                text_surface = font.render(wrapped_line, True, color)
                surface.blit(text_surface, (pos[0], y))
                y += font.get_linesize()
            y += font.get_linesize()

    # Position each stat on the screen as Rects for mouseover detection
    def create_stat_rects(stats, start_x, start_y, font):
        stat_rects = {}
        y_offset = start_y
        for stat in stats:
            text_surface = font.render(f"{stat}: {stats[stat]}", True, WHITE)
            rect = text_surface.get_rect(topleft=(start_x, y_offset))
            stat_rects[stat] = rect
            if stat == "courage":
                y_offset += 50
            y_offset += 20
        return stat_rects

    # Display stat descriptions on mouseover
    def blit_stats_with_hover(surface, stats, stat_rects, font, mouse_pos):
        for stat, value in stats.items():
            # Check for mouse hover
            if stat_rects[stat].collidepoint(mouse_pos):
                # Render and display description if hovered
                description = Character.stat_descriptions[stat]
                description_surface = font.render(description, True, WHITE)
                background_surface = pygame.Surface(
                    (description_surface.get_width() + 10, description_surface.get_height() + 10))
                background_surface.fill((0, 0, 0))  # Black background
                background_position = (stat_rects[stat].left + 10, stat_rects[stat].bottom + 10)
                surface.blit(background_surface, background_position)
                surface.blit(description_surface, (background_position[0] + 5, background_position[1] + 5))


    # Position each skill on the screen as Rects for mouseover detection
    def create_skill_rects(skills, start_x, start_y, font):
        stat_rects = {}
        y_offset = start_y
        for skill in skills:
            text_surface = font.render(f"{skill}: {skills[skill]}", True, WHITE)
            rect = text_surface.get_rect(topleft=(start_x, y_offset))
            stat_rects[skill] = rect
            y_offset += 20
        return stat_rects

    def blit_skills(surface, candidate, font):
        descent = 211
        for skill_name, skill_value in candidate.get_raw_skills().items():
            color = color_for_skill(skill_value)
            skill_text = f"{skill_name}: {skill_value}"
            blit_text3(surface, str(skill_text), (500, descent), font, color, 185)
            descent += 20

    def blit_stats(surface, candidate, font):
        descent = 205
        blit_text3(surface, "STRENGTH", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("strength")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "INTELLIGENCE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("intelligence")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "WILLPOWER", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("willpower")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "COORDINATION", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("coordination")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "CHARISMA", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("charisma")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "COURAGE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("courage")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 65
        blit_text3(surface, "OFFENSE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("offense")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "DEFENSE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("defense")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "DECEPTION", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("deception")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "EVASION", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("evasion")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "ANALYSIS", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("analyze")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "LIFE LEVEL", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("max_health")
        color = color_for_stat(round(value / 2))
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "MOVEMENT", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("movement")
        color = color_for_stat(round(value / 3))
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "MELEE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("meleecombat")
        color = color_for_stat(round(value / 2))
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "SURPRISE", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("surprise")
        color = color_for_stat(round(value / 2))
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "LEADERSHIP", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("leadership")
        color = color_for_stat(round(value / 3))
        blit_text3(surface, str(value), (240, descent), font, color, 185)
        descent += 20
        blit_text3(surface, "PERCEPTION", (60, descent), font, CYAN, 185)
        value = candidate.stats.get("perception")
        color = color_for_stat(value)
        blit_text3(surface, str(value), (240, descent), font, color, 185)

    # Display skill descriptions on mouseover
    def blit_skills_with_hover(surface, skills, skill_rects, font, mouse_pos):
        for skill, value in skills.items():
            # Check for mouse hover
            if skill_rects[skill].collidepoint(mouse_pos):
                # Render and display description if hovered
                description = Character.skill_descriptions[skill]
                description_surface = font.render(description, True, WHITE)
                background_surface = pygame.Surface(
                    (description_surface.get_width() + 10, description_surface.get_height() + 10))
                background_surface.fill((0, 0, 0))  # Black background
                background_position = (skill_rects[skill].left + 10, skill_rects[skill].bottom + 10)
                surface.blit(background_surface, background_position)
                surface.blit(description_surface, (background_position[0] + 5, background_position[1] + 5))

    def blit_history(surface, candidate, font):
        label = candidate.history
        blit_text3(surface, label, (SCREEN_WIDTH - 340, 210), font, GREEN, 175)

    def blit_name(surface, location, candidate, font):
        blit_text3(surface, candidate.name, location, font, GREEN, 180)

    def blit_button(surface, location, text, font):
        blit_text3(surface, text, location, font, CYAN, 180)


    # Initialize PyGame
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()

    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    STAT_FONT = pygame.font.Font(font_path, 16)
    MOUSEOVER_FONT = pygame.font.Font(font_path, 16)
    HISTORY_FONT = pygame.font.Font(font_path, 16)
    SKILL_FONT = pygame.font.Font(font_path, 16)
    CHARNAME_FONT = pygame.font.Font(font_path, 14)
    BUTTON_FONT = pygame.font.Font(font_path, 18)

    PROCEED_TEXT = BUTTON_FONT.render("PROCEED", True, CYAN)
    CANDIDATE_TEXT = BUTTON_FONT.render("CANDIDATE", True, CYAN)
    LEADER_TEXT = BUTTON_FONT.render("LEADER", True, CYAN)
    TEAM_TEXT = BUTTON_FONT.render("TEAM", True, CYAN)
    REJECTS_TEXT = BUTTON_FONT.render("REJECTED", True, RED)
    DERIVED_LABEL_TEXT = BUTTON_FONT.render("DERIVED STATS", True, CYAN)
    REJECT_BUTTON_TEXT = BUTTON_FONT.render("REJECT", True, RED)
    NEXT_BUTTON_TEXT = BUTTON_FONT.render(">> NEXT", True, CYAN)
    PREVIOUS_BUTTON_TEXT = BUTTON_FONT.render("<< PREVIOUS", True, CYAN)
    STATS_LABEL_TEXT = BUTTON_FONT.render("STATS", True, CYAN)
    SKILLS_LABEL_TEXT = BUTTON_FONT.render("SKILLS", True, CYAN)
    BACKGROUND_LABEL_TEXT = BUTTON_FONT.render("BACKGROUND", True, CYAN)
    EXIT_TEXT = BUTTON_FONT.render("EXIT", True, RED)

    # Create stat rects
    stat_rects = create_stat_rects(current_selected_character.stats, start_x=50, start_y=210, font=MOUSEOVER_FONT)

    # Load and play background music
    play_background_music("music/track1.mp3", pygame)

    # Set up the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Choose Your Team")

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage1.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Variables to track dragging and current character
    dragging = False

    # Main game loop
    stage = 1
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Start dragging if the mouse is over the portrait
                next_selected = clicked_character(event.pos, current_candidate_index)
                if next_selected:
                    current_selected_character = next_selected
                    dragging = True
                elif NEXT_BUTTON_RECT.collidepoint(event.pos):
                    current_candidate_index += 1
                    if current_candidate_index >= len(candidates):
                        current_candidate_index = 0
                    current_selected_character = candidates[current_candidate_index]
                elif PREV_BUTTON_RECT.collidepoint(event.pos):
                    current_candidate_index -= 1
                    if current_candidate_index < 0:
                        current_candidate_index = len(candidates) - 1
                    current_selected_character = candidates[current_candidate_index]
                elif REJECT_BUTTON_RECT.collidepoint(event.pos):
                    add_character_to_rejects(current_selected_character)
                    select_next_candidate()
                elif PROCEED_RECT.collidepoint(event.pos):
                    if team_full(team):
                        running = False
                elif EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False

            elif event.type == pygame.MOUSEBUTTONUP:
                # Stop dragging and check for drop onto a box
                if dragging:
                    dragging = False
                    # Check if character is being re-added to candidates
                    if current_selected_character.get_rect().colliderect(CANDIDATE_RECT):
                        current_selected_character.get_rect().center = CANDIDATE_RECT.center
                        if current_selected_character in team:
                            remove_from_team(current_selected_character)
                        if current_selected_character in rejects:
                            rejects.remove(current_selected_character)
                        if not current_selected_character in candidates:
                            candidates.append(current_selected_character)

                    # Check if character is dropped onto any of the boxes
                    box_index = 0
                    for box in team_boxes:
                        # Dropped character onto an empty box
                        if box.collidepoint(event.pos) and box_empty(box, team):
                            remove_from_team(current_selected_character)
                            add_character_to_team_box(current_selected_character, box, box_index)
                            select_next_candidate()
                            break
                        # Dropped character onto a taken team box
                        elif box.collidepoint(event.pos):
                            in_team_box = character_in_team_box(box)
                            if in_team_box and in_team_box != current_selected_character:
                                if current_selected_character in team:
                                    swap_on_team(in_team_box, current_selected_character)
                                else:
                                    add_character_to_candidates(in_team_box, current_selected_character)
                                    remove_from_team(in_team_box)
                                    add_character_to_team_box(current_selected_character, box, box_index)
                            select_next_candidate()
                            break
                        box_index += 1

                    if current_selected_character.get_rect().colliderect(REJECTED_BOX):
                        # Snap the character into the box center if dropped
                        add_character_to_rejects(current_selected_character)
                        select_next_candidate()

            elif event.type == pygame.MOUSEMOTION:
                # Update position while dragging
                if dragging:
                    current_selected_character.move(event.rel)

        # Drawing
        screen.blit(background_image, (0, 0))

        # Draw the selected team images
        for character in team:
            if character is not None:
                character.draw(screen)

        # Draw the most recent rejected portrait
        if len(rejects) > 0:
            screen.blit(rejects[len(rejects)-1].portrait, REJECTED_BOX)

        # Draw candidate pool image
        if len(candidates) > 0:
            screen.blit(candidates[current_candidate_index].portrait, candidates[current_candidate_index].get_rect())

        # Draw the current character portrait last
        screen.blit(current_selected_character.portrait, CANDIDATE_RECT)

        # Draw the candidate history
        blit_history(screen, current_selected_character, HISTORY_FONT)
        # Draw the candidate stats
        blit_stats(screen, current_selected_character, STAT_FONT)
        # Draw the candidate skills
        blit_skills(screen, current_selected_character, SKILL_FONT)

        # Draw the buttons
        screen.blit(PROCEED_TEXT, PROCEED_RECT)
        screen.blit(EXIT_TEXT, EXIT_RECT)
        screen.blit(REJECT_BUTTON_TEXT, REJECT_BUTTON_RECT)
        screen.blit(NEXT_BUTTON_TEXT, NEXT_BUTTON_RECT)
        screen.blit(PREVIOUS_BUTTON_TEXT, PREV_BUTTON_RECT)

        # Draw the labels
        screen.blit(CANDIDATE_TEXT, CANDIDATE_LABEL_RECT)
        screen.blit(LEADER_TEXT, LEADER_LABEL_RECT)
        screen.blit(TEAM_TEXT, TEAM_LABEL_RECT)
        screen.blit(REJECTS_TEXT, REJECTED_LABEL_RECT)
        screen.blit(STATS_LABEL_TEXT, STATS_LABEL_RECT)
        screen.blit(DERIVED_LABEL_TEXT, DERIVED_LABEL_RECT)
        screen.blit(SKILLS_LABEL_TEXT, SKILLS_LABEL_RECT)
        screen.blit(BACKGROUND_LABEL_TEXT, BACKGROUND_LABEL_RECT)

        # Draw the candidate name
        blit_name(screen, CANDIDATE_NAME_LOC, current_selected_character, CHARNAME_FONT)
        if team[0] is not None:
            blit_name(screen, LEADER_NAME_LOC, team[0], CHARNAME_FONT)
        if team[1] is not None:
            blit_name(screen, TEAM_ONE_NAME_LOC, team[1], CHARNAME_FONT)
        if team[2] is not None:
            blit_name(screen, TEAM_TWO_NAME_LOC, team[2], CHARNAME_FONT)
        if team[3] is not None:
            blit_name(screen, TEAM_THREE_NAME_LOC, team[3], CHARNAME_FONT)
        if team[4] is not None:
            blit_name(screen, TEAM_FOUR_NAME_LOC, team[4], CHARNAME_FONT)
        if team[5] is not None:
            blit_name(screen, TEAM_FIVE_NAME_LOC, team[5], CHARNAME_FONT)

        # Draw descriptions on hover
        blit_stats_with_hover(screen, current_selected_character.stats, stat_rects, STAT_FONT, mouse_pos)
        skill_rects = create_skill_rects(current_selected_character.skills, start_x=450, start_y=210, font=MOUSEOVER_FONT)
        blit_skills_with_hover(screen, current_selected_character.skills, skill_rects, SKILL_FONT, mouse_pos)

        # Draw boxes for team selection
        for box in team_boxes:
            pygame.draw.rect(screen, (255, 255, 255), box, 2)  # Draw box border
        pygame.draw.rect(screen, (255, 0, 0), REJECTED_BOX, 2)
        pygame.draw.rect(screen, (255, 255, 255), CANDIDATE_RECT, 2)

        # Update the display
        pygame.display.flip()
        await asyncio.sleep(0)

    # ---- Team naming prompt (loop 1 only) ----
    if stage < 1000 and loop == 1:
        team_name = await _prompt_team_name(screen)

    # store the resulting team
    if stage < 1000:
        add_team_mission_param(team, "team_name", team_name)
        team_data = save_team_named(team_name, loop, 1, team)
    else:
        team_data = None

    # Quit PyGame
    pygame.quit()

    return stage + 1, team_data, team_name

async def main():
    print("Starting Stage: Choose Team")
    team_data = choose_team()

if __name__ == "__main__":
    main()

