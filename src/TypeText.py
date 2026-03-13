import pygame
import random
import time

from Utils import *

BASE_TEXT_X_OFFSET = 45

global text_x_offset
global text_y_offset

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
def standard_skill_check(member, screen, stat_name, skill_name, font, modifier):
    emit_character_image_at_text_offset(member, screen)
    roll = random.randint(1, 100)
    skill_check = member.stat_and_skill_check(roll, stat_name, skill_name, modifier)
    if skill_check:
        color = GREEN
    else:
        color = RED
    type_out_text(screen, roll_string(roll, skill_name, stat_name, modifier), font, color)
    return skill_check

def emit_character_image_at_text_offset(character, screen):
    global text_x_offset
    global text_y_offset
    screen.blit(character.portrait, (50, text_y_offset + 30))
    text_x_offset = BASE_TEXT_X_OFFSET + 80

def type_out_text(surface, text, font, color=WHITE, line_spacing=5, delay=0.010):
    global text_x_offset
    global text_y_offset

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
            time.sleep(delay)

def clear_screen(surface, background):
    global text_x_offset
    global text_y_offset
    surface.blit(background, (0, 0))
    text_x_offset = BASE_TEXT_X_OFFSET
    text_y_offset = 30
