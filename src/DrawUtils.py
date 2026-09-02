# DrawUtils.py -- common stuffs and things for drawing
import pygame
import asyncio

from Utils import resource_path

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
DARK_CYAN = (15, 33, 32)

class DrawingContext:
    def __init__(self, screen):
        self.screen = screen

        font_path = resource_path("fonts/Orbitron-Bold.ttf")
        self.fonts = {
            "default": pygame.font.Font(font_path, 16),
            "small": pygame.font.Font(font_path, 12),
            "medium": pygame.font.Font(font_path, 14),
            "large": pygame.font.Font(font_path, 18),
            "location": pygame.font.Font(font_path, 18),
        }

    async def display_message(self,
            text,
            font_selector,
            position,
            color=CYAN,
            erase=False,
            flip=False,
            sleep=False):

        font = self.fonts.get(font_selector)
        action_text_surface = font.render(text, True, color)
        if erase:
            background_surface = pygame.Surface(
                (action_text_surface.get_width() + 150, action_text_surface.get_height() + 5))
            background_surface.fill((0, 0, 0))  # Black background
            self.screen.blit(background_surface, position)
        self.screen.blit(action_text_surface, position)
        if flip:
            pygame.display.flip()
        if sleep:
            await asyncio.sleep(2)

