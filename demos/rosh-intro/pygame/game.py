#!/usr/bin/env python3
# Auto-generated from Rosh code
# Transpiled with Rosh Pygame Transpiler v0.1.9

import pygame
import sys
from pathlib import Path

# Asset path resolution (relative to script)
SCRIPT_DIR = Path(__file__).parent
ASSETS_DIR = SCRIPT_DIR / 'assets'

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Rosh Game')
clock = pygame.time.Clock()

# Disable key repeat (input parity with Phaser JustDown)
pygame.key.set_repeat(0)

class GameObject:
    """Basic game object with position, size, color, and visibility"""

    def __init__(self, x, y, width, height, color, shape='rectangle'):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.shape = shape
        self.visible = True
        self.sprite = None

    def draw(self, surface):
        if not self.visible:
            return
        if self.sprite:
            surface.blit(self.sprite, (self.x - self.width // 2, self.y - self.height // 2))
        elif self.shape == 'circle':
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.width // 2)
        else:
            rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
            pygame.draw.rect(surface, self.color, rect)

class TextObject:
    """Text display object with font rendering"""

    def __init__(self, x, y, text, color=(255, 255, 255), font_size=16):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.font_size = font_size
        self.visible = True
        self.font = None
        try:
            self.font = pygame.font.SysFont('Arial', font_size)
        except Exception as e:
            print(f'Warning: Font init failed: {e}')

    def set_text(self, text):
        self.text = text

    def set_font_size(self, size):
        self.font_size = size
        try:
            self.font = pygame.font.SysFont('Arial', int(size))
        except Exception as e:
            print(f'Warning: Font resize failed: {e}')

    def draw(self, surface):
        if not self.visible:
            return
        if self.font:
            rendered = self.font.render(str(self.text), True, self.color)
            rect = rendered.get_rect(center=(self.x, self.y))
            surface.blit(rendered, rect)
        else:
            # Fallback: draw text position marker if font unavailable
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 5)

class GameState:
    """Container for custom game state properties"""
    pass

# Create game objects
logo = TextObject(400, 280, "rosh", (0, 255, 255), 8)

tagline = TextObject(400, 350, "happy coding", (128, 128, 128), 1)
tagline.visible = False

dot = GameObject(400, 450, 8, 8, (0, 255, 255), 'rectangle')
dot.visible = False

state = GameObject(100, 100, 50, 50, (255, 255, 0), 'rectangle')
state.phase = 1
state.logo_done = False
state.tagline_done = False


# Event handlers
def handle_update():
    if (state.phase == 1):
        if (logo.font_size < 96):
            logo.set_font_size((logo.font_size + 2))
        else:
            state.phase = 2
            tagline.visible = True
            dot.visible = True
    if (state.phase == 2):
        if (tagline.font_size < 24):
            tagline.set_font_size((tagline.font_size + 1))
        else:
            state.phase = 3
    if (state.phase == 3):
        if (dot.width < 12):
            dot.width = (dot.width + 1)
            dot.height = (dot.height + 1)
        else:
            dot.width = 8
            dot.height = 8

# Main game loop
running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Per-frame game update
    handle_update()

    # Clear screen
    screen.fill((45, 45, 45))

    # Draw all objects
    logo.draw(screen)
    tagline.draw(screen)
    dot.draw(screen)
    state.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()