import sys
import pygame
import random
import asyncio

# True when running inside pygbag / browser (WASM); False for local Python
IS_WEB = sys.platform == "emscripten"
# Per-character typing delay: web already spends ~16 ms per asyncio.sleep(0) frame;
# locally we add an explicit pause so the text feels the same speed.
_CHAR_DELAY = 0 if IS_WEB else 0.03

from Utils import *

BASE_TEXT_X_OFFSET = 45

text_x_offset = BASE_TEXT_X_OFFSET
text_y_offset = 30

def reset_text_offsets():
    global text_x_offset
    global text_y_offset
    text_x_offset = BASE_TEXT_X_OFFSET
    text_y_offset = 30

def max_y_offset():
    global text_y_offset
    text_y_offset = 800

def reset_x_offset():
    global text_x_offset
    text_x_offset = BASE_TEXT_X_OFFSET

# negative modifier is harder
async def standard_skill_check(member, screen, stat_name, skill_name, font, modifier):
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, stat_name, skill_name, modifier)
    if skill_check:
        color = GREEN
    else:
        color = RED
    await type_out_text(screen, roll_string(roll, skill_name, stat_name, modifier), font, color)
    return skill_check

def emit_character_image_at_text_offset(character, screen):
    global text_x_offset
    global text_y_offset
    screen.blit(character.portrait, (50, text_y_offset + 30))
    text_x_offset = BASE_TEXT_X_OFFSET + 80

def emit_team_status_portrait(character, screen, size=50):
    global text_x_offset
    global text_y_offset
    if hasattr(character, "portrait") and character.portrait:
        scaled = pygame.transform.scale(character.portrait, (size, size))
        screen.blit(scaled, (50, text_y_offset + 10))
        text_x_offset = BASE_TEXT_X_OFFSET + size + 20
    else:
        text_x_offset = BASE_TEXT_X_OFFSET + size + 20

def advance_text_y(amount=30):
    global text_y_offset
    text_y_offset += amount

async def type_out_text(surface, text, font, color=WHITE, line_spacing=5, delay=None):
    global text_x_offset
    global text_y_offset

    char_delay = _CHAR_DELAY if delay is None else delay

    lines = text.splitlines()

    for line in lines:
        text_y_offset += 30
        rendered_line = ""
        for char in line:
            rendered_line += char
            text_surface = font.render(rendered_line, True, color)
            # Clear previous rendering of the line
            line_rect = pygame.Rect(text_x_offset, text_y_offset, text_surface.get_width(), text_surface.get_height())
            surface.fill((0, 0, 0), line_rect)  # Black background
            surface.blit(text_surface, (text_x_offset, text_y_offset))
            pygame.display.flip()
            await asyncio.sleep(char_delay)  # 0 on web (one WASM frame ≈ 16 ms); explicit delay locally

def clear_screen(surface, background):
    global text_x_offset
    global text_y_offset
    surface.blit(background, (0, 0))
    text_x_offset = BASE_TEXT_X_OFFSET
    text_y_offset = 30
