import pygame
import sys
import asyncio

from Utils import *
from constants import TOP_BAR_Y, DEBUG

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8
BASE_TEXT_X_OFFSET = 50

TOPMOST = 10
TOP_EDGE = TOP_BAR_Y
INSTRUCTIONS_TOP = 50
INSTRUCTIONS_LEFT_EDGE = 180
PROCEED_RECT = pygame.Rect(1130, TOP_BAR_Y, 105, 25)
EXIT_RECT = pygame.Rect(1330, TOP_BAR_Y, 105, 25)

async def introduction3() :
    global text_x_offset
    global text_y_offset
    global max_height
    global locations

    text_x_offset = 50
    text_y_offset = 50
    max_height = SCREEN_HEIGHT - CREDITS_BAR_HEIGHT

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Introduction")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)

    PROCEED_TEXT = DEFAULT_FONT.render("PROCEED", True, CYAN)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Instructions text
    instructions = []
    instructions.append([
        "You are a commander selecting and equipping a team to go on a mission.",
        "Once they depart, you will see what happens but you have no control of their actions.",
        "Use the PROCEED button to skip all instructions.",
        "The game has 6 stages.",
        "Your team is persisted between each stage.",
        "You can resume from the last position in each stage using first loading screen.",
        "You can EXIT from any stage, but you can only resume from between completed stages.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the first stage, you select your team of 6 from 100 candidates.",
        "Use drag n drop (or buttons) to choose your team.",
        "Click PROCEED once you have a full team chosen.",
        "Mouseovers describe stats and skills.",
        "Paying attention to hints in history impacts chances of recruiting traitors, frauds, or psychopaths.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the second stage, you equip your team.",
        "Use drag n drop to purchase and move items.",
        "Up to four robots may be added to the team by dragging them over.",
        "Items on robots may not be moved, sold, or traded between team members.",
        "Click your character to review their stats.",
        "Mouseovers explain item details.",
        "Once you leave this stage, weapons and armor are keyed to their users and cannot be passed around.",
        "Most, but not all, enemy items are similarly keyed to their users and are of no use to the team.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the third stage, the team trains while traveling to the destination.",
        "Various events may affect your team's effectiveness on the mission.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the fourth stage, your team arrives at the mission point and begins their task.",
        "You can only watch as they proceed.",
        "Injuries degrade a team member's ability to use skills and fight.",
        "If they fail, the game ends.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the fifth phase, the team travels back to the home port.",
        "Various events may still affect your mission's success.",
        "Click anywhere to continue..."
    ])
    instructions.append([
        "In the sixth and final phase, your score is displayed."
        "",
        "Good luck.",
        "Click PROCEED to continue."
    ])

    # Split the text into multiple screens
    instruction_screens = [instructions[i] for i in range(0, 7)]

    # Load and play background music
    play_background_music("music/track3.ogg", pygame)

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    pygame.display.flip()

    current_screen = 0
    stage = 0
    running = True

    # EVENT LOOP HERE
    while running:
        # Display the current screen's instructions
        # Draw background first
        screen.blit(background_image, (0, 0))

        y_offset = 60
        for line in instruction_screens[current_screen]:
            text_surface = DEFAULT_FONT.render(line, True, WHITE)
            screen.blit(text_surface, (text_x_offset, y_offset))
            y_offset += 30

        # Display buttons
        screen.blit(PROCEED_TEXT, PROCEED_RECT.topleft)
        screen.blit(EXIT_TEXT, EXIT_RECT.topleft)

        pygame.display.flip()
        await asyncio.sleep(0)

        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False
                elif PROCEED_RECT.collidepoint(event.pos):
                    stage = 1
                    running = False
                else:
                    # Advance to the next screen or exit if at the last screen
                    if current_screen < len(instruction_screens) - 1:
                        current_screen += 1
                    else:
                        stage = 1
                        running = False

    return stage