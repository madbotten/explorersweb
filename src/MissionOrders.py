import pygame
import sys
import asyncio

from Utils import *
from Character import Character
from constants import TOP_BAR_Y, DEBUG

CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
BRIEFING_OFFSET = 70
METHODS_OFFSET = 190
MEANS_OFFSET = 300
OPTIONS_OFFSET = 450

# description, required item, required people, required kills
# locations: vault, officer's quarters, officer's quarters, ai core, sweep (any)
MISSION_GOALS = [
    ("MISSION: The team must obtain a Trilisk artifact known to be in pirate possession at the mission point.", ["valneeth"], [], []),
    ("MISSION: The team must capture the pirate named Jalorith known to be at the mission point.", [], ["Jalorith"], []),
    ("MISSION: The team must neutralize all pirate officers at the mission point.", [], [], [6]),
    ("MISSION: The team must discover the location of a secret base called Yoria.", ["datachip"], [], []),
    ("MISSION: The team must defeat 20 pirates at the mission point.", [], [], [20]),
]

# Derelict vessel & Klackon goals (even loops: 2, 4, 6...)
# locations: warpchamber, throneroom, biolab, bridge, sweep (any)
DERELICT_MISSION_GOALS = [
    ("MISSION: The team must recover a Xeno-Relic from the warp chamber of the derelict vessel.", ["xeno-relic"], [], []),
    ("MISSION: The team must neutralize the Klackon Broodmother Xylarx in the derelict throne room.", [], ["Xylarx"], []),
    ("MISSION: The team must purge the Klackon bio-nest inside the derelict biolab.", [], [], [6]),
    ("MISSION: The team must extract the black-box flight core from the derelict bridge.", ["flightcore"], [], []),
    ("MISSION: The team must defeat 20 Klackons aboard the derelict vessel.", [], [], [20]),
]

THEATRE_SETTING_LINES = {
    "pirates": "Proceed to pirate base at target coordinates.",
    "derelict": "Intercept alien derelict at target coordinates.",
}

MISSION_RECOMMENDATIONS = [
    "Recommend balanced team with strong technical skills for this mission.",
    "Recommend stealthy or highly combat-capable team for this mission.",
    "Recommend heavy combat team for this mission.",
    "Recommend balanced team with strong technical skills for this mission.",
    "Recommend heavy combat team for this mission.",
]

DERELICT_MISSION_RECOMMENDATIONS = [
    "Recommend balanced team with strong technical skills for this mission.",
    "Recommend stealthy or highly combat-capable team for this mission.",
    "Recommend heavy combat team for this mission.",
    "Recommend balanced team with strong technical skills for this mission.",
    "Recommend heavy combat team for this mission.",
]


def get_theatre_for_loop(loop: int = 1) -> str:
    """Return 'pirates' on odd loops (1, 3, 5...) and 'derelict' on even loops (2, 4, 6...)."""
    return "derelict" if (loop and loop % 2 == 0) else "pirates"


def get_mission_goals_for_theatre(theatre: str = "pirates"):
    """Return the mission goals list for the given theatre ('pirates' or 'derelict')."""
    return DERELICT_MISSION_GOALS if theatre == "derelict" else MISSION_GOALS


def get_mission_briefing_lines(theatre: str = "pirates", mission_index: int = 0) -> tuple[str, str, str]:
    """Return (setting_line, mission_description, recommendation_line) for the theatre and mission index."""
    goals = get_mission_goals_for_theatre(theatre)
    idx = mission_index % len(goals)
    setting_line = THEATRE_SETTING_LINES.get(theatre, THEATRE_SETTING_LINES["pirates"])
    mission_description = goals[idx][0]
    recs = DERELICT_MISSION_RECOMMENDATIONS if theatre == "derelict" else MISSION_RECOMMENDATIONS
    recommendation_line = recs[idx % len(recs)]
    return setting_line, mission_description, recommendation_line


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
                play_positive_click()
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

    theatre = get_theatre_for_loop(loop)
    goals = get_mission_goals_for_theatre(theatre)
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

    existing_mission = team[0].mission if (team and getattr(team[0], "mission", None)) else {}
    if existing_mission.get("loop") == loop and "mission_index" in existing_mission:
        mission_index = existing_mission["mission_index"] % len(goals)
    else:
        mission_index = random.randint(0, len(goals) - 1)

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

    # Mission statement & briefing lines
    mission_description, required_items, required_people, required_kills = goals[mission_index]
    setting_line, mission_description, recommendation_line = get_mission_briefing_lines(
        theatre, mission_index
    )

    stage = 2

    # Checkbox groups
    methods_group = [
    Checkbox("Be stealthy - Avoid all hostile contact where possible except as required to accomplish the mission.", "stealth", 100, METHODS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Be brazen - Neutralize all hostiles you encounter.", "brazen", 100, METHODS_OFFSET + 60, OPTION_FONT, None),
    ]
    for checkbox in methods_group:
        checkbox.group = methods_group
        if existing_mission.get("methods") == checkbox.param:
            checkbox.checked = True

    means_group = [
        Checkbox("Wipe 'em out - Use any and all means necessary to accomplish the mission.", "any", 100, MEANS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Pirates are people too - Avoid unnecessary killing but do whatever you must to accomplish the mission.", "just", 100, MEANS_OFFSET + 60, OPTION_FONT, None),
        Checkbox("We are the good guys - Use only nonlethal force to accomplish the mission.", "pacifist", 100, MEANS_OFFSET + 90, OPTION_FONT, None),
    ]
    for checkbox in means_group:
        checkbox.group = means_group
        if existing_mission.get("means") == checkbox.param:
            checkbox.checked = True

    options_group = [
        Checkbox("Eyes on the prize - Focus only on the mission and don't be distracted by anything else.", "focus", 100, OPTIONS_OFFSET + 30, OPTION_FONT, None),
        Checkbox("Be flexible - Exploit any opportunities that arise.", "flex", 100, OPTIONS_OFFSET + 60, OPTION_FONT, None),
    ]
    for checkbox in options_group:
        checkbox.group = options_group
        if existing_mission.get("options") == checkbox.param:
            checkbox.checked = True

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
                    play_positive_click()
                    running = False
                elif EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False

        # Draw the screen
        screen.blit(background_image, (0, 0))

        # Draw the mission briefing in the main part of the screen
        setting_surface = TITLE_FONT.render(setting_line, True, CYAN)
        screen.blit(setting_surface, (50, BRIEFING_OFFSET))
        title_surface = TITLE_FONT.render(mission_description, True, WHITE)
        screen.blit(title_surface, (50, BRIEFING_OFFSET + 32))
        rec_surface = OPTION_FONT.render(recommendation_line, True, GREEN)
        screen.blit(rec_surface, (50, BRIEFING_OFFSET + 64))

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
    add_team_mission_param(team, "theatre", theatre)
    add_team_mission_param(team, "loop", loop)
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