import pygame
import os
import random
import pickle
import time
import sys

from pygame.sprite import collide_rect
from Character import Character
from Utils import *
from TypeText import *

# Screen settings
TEXT_AREA_WIDTH = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH = int(SCREEN_WIDTH * 0.7)
TEAM_BOX_HEIGHT = (SCREEN_HEIGHT - CREDITS_BAR_HEIGHT) // 8  # Adjust for 8 characters, reserving space for credits
BASE_TEXT_X_OFFSET = 50
CHARACTER_BOX_WIDTH = 90
CHARACTER_BOX_HEIGHT = 100

TOPMOST = 10
TOP_EDGE = 8
INSTRUCTIONS_TOP = 50
INSTRUCTIONS_LEFT_EDGE = 180
PROCEED_RECT = pygame.Rect(1130, TOP_EDGE, 105, 25)
EXIT_RECT = pygame.Rect(1330, TOP_EDGE, 105, 25)

def draw_team_and_scores(team, screen, font):
    vertical_offset = INSTRUCTIONS_TOP
    for member in team:
        screen.blit(member.portrait, pygame.Rect(50, vertical_offset, CHARACTER_BOX_WIDTH, CHARACTER_BOX_HEIGHT))
        line = f"{member.name} contributed {member.mission_points} mission points."
        text_surface = font.render(line, True, GREEN)
        screen.blit(text_surface, (INSTRUCTIONS_LEFT_EDGE, vertical_offset))
        vertical_offset += CHARACTER_BOX_HEIGHT + 10

def score(team_data) :
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
    pygame.display.set_caption("Score")
    # fonts
    font_path = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)

    PROCEED_TEXT = DEFAULT_FONT.render("PROCEED", True, CYAN)
    EXIT_TEXT = DEFAULT_FONT.render("EXIT", True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team("team_data_stage_6.pkl")
    team = [Character.from_dict(data) for data in team_data]

    # Load and play background music
    play_background_music("music/track3.mp3", pygame)

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(background_image, (0, 0))
    pygame.display.flip()

    # Display a "Click to continue" message
    click_to_continue = "Click anywhere to continue..."

    current_screen = 0
    stage = 8
    running = True

    # Display "Click to continue"
    y_offset = 800
    click_surface = DEFAULT_FONT.render(click_to_continue, True, CYAN)
    screen.blit(click_surface, (text_x_offset, SCREEN_HEIGHT - 40))

    # Display buttons
    screen.blit(PROCEED_TEXT, PROCEED_RECT.topleft)
    screen.blit(EXIT_TEXT, EXIT_RECT.topleft)

    # Display the team and their scores
    reset_text_offsets()
    draw_team_and_scores(team, screen, DEFAULT_FONT)

    # EVENT LOOP HERE
    while running:

        pygame.display.flip()

        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("exited due to QUIT")
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    stage = 1000
                    running = False
                elif PROCEED_RECT.collidepoint(event.pos):
                    print("exited due to proceed button")
                    stage = 1000
                    running = False

    pygame.quit()

    return stage + 1, team_data

def main():
    print("Starting Stage: Score")
    team_data = score(None)

if __name__ == "__main__":
    main()
