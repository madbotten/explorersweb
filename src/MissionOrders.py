import pygame
import sys
import asyncio

from Utils import *
from Character import Character
from constants import TOP_BAR_Y, DEBUG

CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
METHODS_OFFSET = 60
MEANS_OFFSET = 170
OPTIONS_OFFSET = 320

# Checkbox class
class Checkbox:
    def __init__(self, text, param, x, y, font, group, color=WHITE):
        self.text = text
        self.x = x
        self.y = y
        self.font = font
        self.color = color
        self.rect = pygame.Rect(x, y, 20, 20)
        self.checked = False
        self.param = param
        self.group = group

    def draw(self, screen):
        # Draw checkbox
        if self.checked:
            color = GREEN
        else: color = self.color
        pygame.draw.rect(screen, color, self.rect, 2)
        text_surface = self.font.render(self.text, True, color)
        screen.blit(text_surface, (self.x + 30, self.y))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                # Uncheck all checkboxes in the group
                for checkbox in self.group:
                    checkbox.checked = False
                # Check this checkbox
                self.checked = True

async def draw_team(team, screen, font):
    for i, character in enumerate(team):
        character_rect = pygame.Rect(SCREEN_WIDTH - 370, CREDITS_BAR_HEIGHT + i * 120, 50, 50)

        # Display character's name
        name_text = font.render(character.name, True, GREEN)
        screen.blit(name_text, (character_rect.x + 10, character_rect.y + 3))

        # Display character portrait to the left within the equipment area
        if character.portrait:
            portrait_x = character_rect.x + 10
            portrait_y = character_rect.y + 20
            screen.blit(character.portrait, (portrait_x, portrait_y))

# Game screen function
async def mission_orders(team_data, team_name="Debug Team", loop=1):
    # Initialize Pygame
    pygame.init()
    pygame.font.init()
    pygame.mixer.init()

    # Fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    TITLE_FONT = pygame.font.Font(font_path, 18)
    OPTION_FONT = pygame.font.Font(font_path, 16)
    EXIT_RECT = pygame.Rect(1350, TOP_BAR_Y, 105, 25)
    EXIT_TEXT = TITLE_FONT.render("EXIT", True, RED)
    PROCEED_RECT = pygame.Rect(1200, TOP_BAR_Y, 105, 20)
    PROCEED_TEXT = TITLE_FONT.render("PROCEED", True, CYAN)

    mission_index = random.randint(0, len(MISSION_GOALS) - 1)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mission Briefing")

    # Load and play background music
    play_background_music("music/track4.mp3", pygame)

    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 1)
    team = [Character.from_dict(data) for data in team_data]

    # if not vetted, chance their skills are exaggerated
    for member in team:
        if not member.vetted and random.randint(1, 100) < 15:
            print(f"{member.name} exaggerated their skills")
            for skill_name, skill_value in member.get_raw_skills().items():
                if skill_value > 75:
                    member.skills[skill_name] = max(0, skill_value - 25)
                if skill_value > 50:
                    member.skills[skill_name] = max(0, skill_value - 15)
                # prevent further drop in later missions
                member.vetted = True

    # Mission statement
    mission_description, required_items, required_people, required_kills = MISSION_GOALS[mission_index]

    stage = 2

    # Checkbox groups
    methods_group = [
    Checkbox("Be stealthy - Avoid all hostile contact where possible except as required to accomplish the mission.", "stealth", 100, METHODS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Be brazen - Neutralize all hostiles you encounter.", "brazen", 100, METHODS_OFFSET + 60, OPTION_FONT, None),
    ]
    for checkbox in methods_group:
        checkbox.group = methods_group

    means_group = [
        Checkbox("Wipe 'em out - Use any and all means necessary to accomplish the mission.", "any", 100, MEANS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Pirates are people too - Avoid unnecessary killing but do whatever you must to accomplish the mission.", "just", 100, MEANS_OFFSET + 60, OPTION_FONT, None),
        Checkbox("We are the good guys - Use only nonlethal force to accomplish the mission.", "pacifist", 100, MEANS_OFFSET + 90, OPTION_FONT, None),
    ]
    for checkbox in means_group:
        checkbox.group = means_group

    options_group = [
        Checkbox("Eyes on the prize - Focus only on the mission and don't be distracted by anything else.", "focus", 100, OPTIONS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Be flexible - Exploit any opportunities that arise.", "flex", 100, OPTIONS_OFFSET + 60, OPTION_FONT, None),
    ]
    for checkbox in options_group:
        checkbox.group = options_group

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            # Handle checkbox events
            for checkbox in methods_group:
                checkbox.handle_event(event)
            for checkbox in means_group:
                checkbox.handle_event(event)
            for checkbox in options_group:
                checkbox.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if PROCEED_RECT.collidepoint(event.pos):
                    running = False
                elif EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False

        # Draw the screen
        screen.blit(background_image, (0, 0))

        # Draw the mission statement
        title_surface = TITLE_FONT.render(mission_description, True, WHITE)
        screen.blit(title_surface, (50, 5))
        # Draw group titles
        methods_surface = TITLE_FONT.render("Methods", True, WHITE)
        screen.blit(methods_surface, (50, METHODS_OFFSET))
        methods_surface = TITLE_FONT.render("Means", True, WHITE)
        screen.blit(methods_surface, (50, MEANS_OFFSET))
        methods_surface = TITLE_FONT.render("Options", True, WHITE)
        screen.blit(methods_surface, (50, OPTIONS_OFFSET))

        screen.blit(PROCEED_TEXT, PROCEED_RECT)
        screen.blit(EXIT_TEXT, EXIT_RECT)

        await draw_team(team, screen, OPTION_FONT)

        # Draw checkboxes
        for checkbox in methods_group:
            checkbox.draw(screen)
        for checkbox in means_group:
            checkbox.draw(screen)
        for checkbox in options_group:
            checkbox.draw(screen)

        pygame.display.flip()
        await asyncio.sleep(0)

    # save characters upon exit
    add_team_mission_param(team, "mission_index", mission_index)
    for checkbox in methods_group:
        if checkbox.checked:
            add_team_mission_param(team, "methods", checkbox.param)
    for checkbox in means_group:
        if checkbox.checked:
            add_team_mission_param(team, "means", checkbox.param)
    for checkbox in options_group:
        if checkbox.checked:
            add_team_mission_param(team, "options", checkbox.param)

    if stage < 1000:
        team_data = save_team_named(team_name, loop, 2, team)
    else:
        team_data = None

    pygame.quit()

    return stage + 1, team_data

# Test the mission screen
if __name__ == "__main__":
    print("Starting Stage: Orders")
    team_data = mission_orders(None)