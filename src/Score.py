import pygame
import os
import random
import pickle
import time
import sys
import asyncio

from pygame.sprite import collide_rect
from Character import Character
from Utils import *
from TypeText import *
from MissionOrders import get_theatre_for_loop, get_mission_goals_for_theatre
from constants import TOP_BAR_Y, DEBUG

# Screen settings
TEXT_AREA_WIDTH    = SCREEN_WIDTH - 100
TEXT_AREA_HEIGHT   = SCREEN_HEIGHT * 0.8
CREDITS_BAR_HEIGHT = SCREEN_HEIGHT // 20
ITEM_PANEL_WIDTH   = int(SCREEN_WIDTH * 0.3) - 6
TEAM_PANEL_WIDTH   = int(SCREEN_WIDTH * 0.7)
BASE_TEXT_X_OFFSET = 50

# Portrait size — small enough that 6 members fit vertically with room to spare
PORTRAIT_W = 60
PORTRAIT_H = 68
ROW_GAP    = 5    # gap between member rows

TOPMOST = 10
TOP_EDGE = TOP_BAR_Y
INSTRUCTIONS_TOP  = 80   # pushed down to clear top border art
INSTRUCTIONS_LEFT = PORTRAIT_W + 70   # text starts to the right of portrait

PROCEED_RECT = pygame.Rect(1130, TOP_BAR_Y, 105, 25)
EXIT_RECT    = pygame.Rect(1330, TOP_BAR_Y, 105, 25)

ROW_H = PORTRAIT_H + ROW_GAP   # height of one member row

# Hover popup panel dimensions
POPUP_W   = 380
POPUP_PAD = 12
POPUP_BG  = (8, 18, 35, 230)    # RGBA — semi-transparent dark
POPUP_BORDER = (0, 180, 200)


def draw_team_and_scores(team, screen, font):
    """Draw each member's portrait and mission-point line. Returns list of portrait rects."""
    rects = []
    y = INSTRUCTIONS_TOP
    for member in team:
        portrait = pygame.transform.scale(member.portrait, (PORTRAIT_W, PORTRAIT_H))
        screen.blit(portrait, (50, y))
        line = f"{member.name} contributed {member.mission_points} mission points."
        text_surface = font.render(line, True, GREEN)
        screen.blit(text_surface, (INSTRUCTIONS_LEFT, y + (PORTRAIT_H - font.get_height()) // 2))
        rects.append(pygame.Rect(50, y, PORTRAIT_W, PORTRAIT_H))
        y += ROW_H
    return rects


def _popup_lines(member):
    """
    Build a list of (label, value, colour) tuples describing the member,
    suitable for rendering in the hover popup.
    """
    CYAN2  = (0, 255, 255)
    WHITE2 = (220, 220, 220)
    GREEN2 = (80, 220, 80)
    GREY   = (150, 170, 190)

    lines = []

    is_robot = getattr(member, "type", "") == "robot"

    # --- Header ---
    lines.append((member.name, "", CYAN2))

    if is_robot:
        lines.append(("Type",   getattr(member, "occupation", member.type), WHITE2))
        hp_max = member.max_life if member.max_life > 0 else "?"
        lines.append(("Health", f"{member.current_health} / {hp_max}", GREEN2))
        # Robot stats
        lines.append(("--- Stats ---", "", GREY))
        for stat, val in member.stats.items():
            lines.append((stat.capitalize(), str(val), WHITE2))
    else:
        lines.append(("Occupation", member.occupation, WHITE2))
        hp_max = member.stats.get("max_health", "?")
        lines.append(("Health",  f"{member.current_health} / {hp_max}", GREEN2))
        lines.append(("Morale",  str(getattr(member, "morale", "?")),  GREEN2))

        # Stats
        primary = ["strength", "coordination", "intelligence", "willpower", "courage", "charisma"]
        lines.append(("--- Stats ---", "", GREY))
        for stat in primary:
            if stat in member.stats:
                lines.append((stat.capitalize(), str(member.stats[stat]), WHITE2))

        # Skills
        skills = getattr(member, "skills", {})
        if skills:
            lines.append(("--- Skills ---", "", GREY))
            for skill, val in skills.items():
                lines.append((skill.replace("_", " ").capitalize(), str(val), WHITE2))

        # Equipment
        equipment = getattr(member, "equipment", [])
        if equipment:
            lines.append(("--- Items ---", "", GREY))
            for item in equipment:
                name = getattr(item, "name", str(item))
                lines.append((name, "", WHITE2))

    return lines


def draw_hover_popup(member, screen, mouse_pos, popup_font, header_font):
    """Draw a popup panel to the right of the portrait area when hovering."""
    lines = _popup_lines(member)

    line_h   = popup_font.get_height() + 3
    n_lines  = len(lines)
    popup_h  = POPUP_PAD * 2 + line_h * n_lines + 6  # +6 for header extra space

    # Position: to the right of the team area, vertically centred on mouse
    px = INSTRUCTIONS_LEFT + 400
    py = max(10, min(mouse_pos[1] - popup_h // 2, SCREEN_HEIGHT - popup_h - 10))

    # Clamp to screen
    if px + POPUP_W > SCREEN_WIDTH - 10:
        px = SCREEN_WIDTH - POPUP_W - 10

    # Semi-transparent background surface
    surf = pygame.Surface((POPUP_W, popup_h), pygame.SRCALPHA)
    surf.fill(POPUP_BG)
    screen.blit(surf, (px, py))
    pygame.draw.rect(screen, POPUP_BORDER, (px, py, POPUP_W, popup_h), 2, border_radius=6)

    # Render lines
    ty = py + POPUP_PAD
    for i, (label, value, colour) in enumerate(lines):
        if value == "":
            # Section header or single-line entry
            font_to_use = header_font if i == 0 else popup_font
            surf_t = font_to_use.render(label, True, colour)
            screen.blit(surf_t, (px + POPUP_PAD, ty))
        else:
            label_surf = popup_font.render(f"{label}:", True, colour)
            val_surf   = popup_font.render(value, True, (220, 220, 220))
            screen.blit(label_surf, (px + POPUP_PAD, ty))
            screen.blit(val_surf,   (px + POPUP_PAD + 160, ty))
        ty += line_h


def liquidate_surviving_robots(team):
    """Convert any surviving robots into credits and return (surviving_humanoids, robot_refund)."""
    from Robot import get_robot_cost

    robot_refund = sum(
        get_robot_cost(getattr(m, "occupation", ""))
        for m in team
        if m is not None and m.is_robot() and m.is_alive()
    )
    humanoid_team = [
        m for m in team
        if m is not None and not m.is_robot() and m.is_alive()
    ]
    for member in humanoid_team:
        member.team = humanoid_team
    return humanoid_team, robot_refund


async def score(team_data, team_name="Debug Team", loop=1):
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

    font_path    = resource_path("fonts/Orbitron-Bold.ttf")
    DEFAULT_FONT = pygame.font.Font(font_path, 16)
    SMALL_FONT   = pygame.font.Font(font_path, 13)
    POPUP_FONT   = pygame.font.Font(font_path, 11)
    POPUP_HEADER = pygame.font.Font(font_path, 14)

    PROCEED_TEXT = DEFAULT_FONT.render("PROCEED", True, CYAN)
    EXIT_TEXT    = DEFAULT_FONT.render("EXIT",    True, RED)

    # Load team if not passed in by StageController
    if not team_data:
        team_data = load_team_named(team_name, loop, 7)
    team = [Character.from_dict(data) for data in team_data]

    # ---- Credit calculation (including converting surviving robots to credits) ----
    total_score      = sum(m.mission_points for m in team)
    credits_earned   = total_score // 10
    humanoid_team, robot_refund = liquidate_surviving_robots(team)
    existing_credits = team[0].mission.get("credits", 0) if team else 0
    new_credits      = existing_credits + credits_earned + robot_refund

    # Load and play background music
    play_background_music("music/track3.mp3", pygame)

    # Load and scale background image
    background_image = pygame.image.load(resource_path("backgrounds/backgroundstage3.jpg"))
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    stage   = 9
    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()

        screen.blit(background_image, (0, 0))

        # Buttons
        screen.blit(PROCEED_TEXT, PROCEED_RECT.topleft)
        screen.blit(EXIT_TEXT,    EXIT_RECT.topleft)

        # Team scores — returns portrait rects for hover detection
        portrait_rects = draw_team_and_scores(team, screen, DEFAULT_FONT)

        # Credits summary — below the team list
        credits_y    = INSTRUCTIONS_TOP + len(team) * ROW_H + 12
        total_line   = SMALL_FONT.render(f"Total mission score: {total_score}", True, WHITE)
        if robot_refund > 0:
            credits_line = SMALL_FONT.render(
                f"Credits earned: {credits_earned}   |   Robot refund: {robot_refund}   |   Team balance: {new_credits}",
                True, CYAN)
        else:
            credits_line = SMALL_FONT.render(
                f"Credits earned: {credits_earned}   |   Team balance: {new_credits}", True, CYAN)
        screen.blit(total_line,   (50, credits_y))
        screen.blit(credits_line, (50, credits_y + 22))

        # Hint
        hint = SMALL_FONT.render("Click PROCEED to continue  |  EXIT to quit", True, (100, 140, 160))
        screen.blit(hint, (50, SCREEN_HEIGHT - 41))

        # Hover popup
        for i, rect in enumerate(portrait_rects):
            if rect.collidepoint(mouse_pos):
                draw_hover_popup(team[i], screen, mouse_pos, POPUP_FONT, POPUP_HEADER)
                break

        pygame.display.flip()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stage = 1000
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if EXIT_RECT.collidepoint(event.pos):
                    play_negative_click()
                    stage = 1000
                    running = False
                elif PROCEED_RECT.collidepoint(event.pos):
                    play_positive_click()
                    stage = 1   # loop back to stage 1
                    running = False

    # ---- Save surviving humanoid team with incremented loop and updated credits ----
    next_loop = loop + 1
    next_theatre = get_theatre_for_loop(next_loop)
    next_goals = get_mission_goals_for_theatre(next_theatre)
    next_mission_index = random.randint(0, len(next_goals) - 1)
    add_team_mission_param(humanoid_team, "loop",          next_loop)
    add_team_mission_param(humanoid_team, "credits",       new_credits)
    add_team_mission_param(humanoid_team, "theatre",       next_theatre)
    add_team_mission_param(humanoid_team, "mission_index", next_mission_index)
    add_team_mission_param(humanoid_team, "enemies_defeated", 0)
    team_data = save_team_named(team_name, next_loop, 1, humanoid_team)

    pygame.quit()
    return stage, team_data


async def main():
    print("Starting Stage: Score")
    score(None)

if __name__ == "__main__":
    main()
