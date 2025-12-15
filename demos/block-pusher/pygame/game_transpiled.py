#!/usr/bin/env python3
# Auto-generated from Rosh code
# Transpiled with Rosh Pygame Transpiler v0.1.8

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
title = TextObject(400, 150, "Block Pusher", (255, 255, 255), 48)

subtitle = TextObject(400, 228, "A Sokoban Puzzle Game", (128, 128, 128), 24)

instructions = TextObject(400, 330, "Push all boxes onto the circles", (0, 255, 255), 18)

start_text = TextObject(400, 480, "Press SPACE to start", (255, 255, 0), 20)

player = GameObject(275, 275, 40, 40, (255, 0, 255), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'player.png'
    player.sprite = pygame.image.load(str(_sprite_path))
    player.sprite = pygame.transform.scale(player.sprite, (40, 40))
except:
    print(f'Warning: Could not load sprite player.png, using colored shape')
player.visible = False

box1 = GameObject(375, 275, 40, 40, (0, 255, 255), 'rectangle')
box1.visible = False

goal1 = GameObject(475, 275, 44, 44, (255, 136, 0), 'circle')
goal1.visible = False

wall1 = GameObject(475, 325, 40, 40, (136, 0, 255), 'rectangle')
wall1.visible = False

level_text = TextObject(400, 48, "Level 1", (255, 255, 255), 24)
level_text.visible = False

moves_text = TextObject(400, 552, "Moves: 0", (128, 128, 128), 16)
moves_text.visible = False

win_text = TextObject(400, 300, "You Win!", (255, 215, 0), 64)
win_text.visible = False

next_level_text = TextObject(400, 390, "Press SPACE for next level", (255, 255, 0), 20)
next_level_text.visible = False

state = GameObject(0, 0, 1, 1, (255, 0, 255), 'rectangle')
state.visible = False
state.level = 0
state.moves = 0
state.can_move = 1


# User-defined functions
def start_level_1():
    player.x = 275
    player.y = 275
    box1.x = 375
    box1.y = 275
    goal1.x = 475
    goal1.y = 275
    wall1.visible = False
    level_text.set_text("Level 1")
    state.level = 1
    state.moves = 0
    moves_text.set_text("Moves: 0")

def start_level_2():
    player.x = 275
    player.y = 325
    box1.x = 375
    box1.y = 325
    wall1.x = 475
    wall1.y = 325
    wall1.visible = True
    goal1.x = 525
    goal1.y = 225
    level_text.set_text("Level 2")
    state.level = 2
    state.moves = 0
    moves_text.set_text("Moves: 0")
    win_text.visible = False
    next_level_text.visible = False

def show_victory():
    win_text.set_text("You Win!")
    win_text.visible = True
    next_level_text.set_text("Press R to play again")
    next_level_text.visible = True
    state.level = 3

def restart_level():
    win_text.visible = False
    next_level_text.visible = False
    if (state.level == 1):
        start_level_1()
    if (state.level == 2):
        start_level_2()
    if (state.level == 3):
        start_level_1()

def check_win():
    if (box1.x == goal1.x):
        if (box1.y == goal1.y):
            if (state.level == 1):
                win_text.set_text("Level Complete!")
                win_text.visible = True
                next_level_text.visible = True
            if (state.level == 2):
                show_victory()

def update_display():
    moves_text.set_text(f"Moves: {state.moves}")


# Event handlers
def handle_space_pressed():
    if (state.level == 0):
        title.visible = False
        subtitle.visible = False
        instructions.visible = False
        start_text.visible = False
        player.visible = True
        box1.visible = True
        goal1.visible = True
        level_text.visible = True
        moves_text.visible = True
        start_level_1()
    if (state.level == 1):
        if (win_text.visible == True):
            start_level_2()

def handle_key_left():
    if (state.level > 0):
        if (state.level < 3):
            if (player.x > 250):
                state.can_move = 1
                if ((player.x - 50) == wall1.x):
                    if (player.y == wall1.y):
                        state.can_move = 0
                if (state.can_move == 1):
                    if (player.x == (box1.x + 50)):
                        if (player.y == box1.y):
                            state.can_move = 1
                            if ((box1.x - 50) == wall1.x):
                                if (box1.y == wall1.y):
                                    state.can_move = 0
                            if (state.can_move == 1):
                                if (box1.x > 250):
                                    box1.x = (box1.x - 50)
                                    player.x = (player.x - 50)
                                    state.moves = (state.moves + 1)
                        else:
                            player.x = (player.x - 50)
                            state.moves = (state.moves + 1)
                    else:
                        player.x = (player.x - 50)
                        state.moves = (state.moves + 1)
    check_win()
    update_display()

def handle_key_right():
    if (state.level > 0):
        if (state.level < 3):
            if (player.x < 550):
                state.can_move = 1
                if ((player.x + 50) == wall1.x):
                    if (player.y == wall1.y):
                        state.can_move = 0
                if (state.can_move == 1):
                    if (player.x == (box1.x - 50)):
                        if (player.y == box1.y):
                            state.can_move = 1
                            if ((box1.x + 50) == wall1.x):
                                if (box1.y == wall1.y):
                                    state.can_move = 0
                            if (state.can_move == 1):
                                if (box1.x < 550):
                                    box1.x = (box1.x + 50)
                                    player.x = (player.x + 50)
                                    state.moves = (state.moves + 1)
                        else:
                            player.x = (player.x + 50)
                            state.moves = (state.moves + 1)
                    else:
                        player.x = (player.x + 50)
                        state.moves = (state.moves + 1)
    check_win()
    update_display()

def handle_key_up():
    if (state.level > 0):
        if (state.level < 3):
            if (player.y > 200):
                state.can_move = 1
                if ((player.y - 50) == wall1.y):
                    if (player.x == wall1.x):
                        state.can_move = 0
                if (state.can_move == 1):
                    if (player.y == (box1.y + 50)):
                        if (player.x == box1.x):
                            state.can_move = 1
                            if ((box1.y - 50) == wall1.y):
                                if (box1.x == wall1.x):
                                    state.can_move = 0
                            if (state.can_move == 1):
                                if (box1.y > 200):
                                    box1.y = (box1.y - 50)
                                    player.y = (player.y - 50)
                                    state.moves = (state.moves + 1)
                        else:
                            player.y = (player.y - 50)
                            state.moves = (state.moves + 1)
                    else:
                        player.y = (player.y - 50)
                        state.moves = (state.moves + 1)
    check_win()
    update_display()

def handle_key_down():
    if (state.level > 0):
        if (state.level < 3):
            if (player.y < 400):
                state.can_move = 1
                if ((player.y + 50) == wall1.y):
                    if (player.x == wall1.x):
                        state.can_move = 0
                if (state.can_move == 1):
                    if (player.y == (box1.y - 50)):
                        if (player.x == box1.x):
                            state.can_move = 1
                            if ((box1.y + 50) == wall1.y):
                                if (box1.x == wall1.x):
                                    state.can_move = 0
                            if (state.can_move == 1):
                                if (box1.y < 400):
                                    box1.y = (box1.y + 50)
                                    player.y = (player.y + 50)
                                    state.moves = (state.moves + 1)
                        else:
                            player.y = (player.y + 50)
                            state.moves = (state.moves + 1)
                    else:
                        player.y = (player.y + 50)
                        state.moves = (state.moves + 1)
    check_win()
    update_display()

def handle_key_r():
    restart_level()

# Main game loop
running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                handle_key_left()
            elif event.key == pygame.K_RIGHT:
                handle_key_right()
            elif event.key == pygame.K_UP:
                handle_key_up()
            elif event.key == pygame.K_DOWN:
                handle_key_down()
            elif event.key == pygame.K_SPACE:
                handle_space_pressed()
            elif event.key == pygame.K_r:
                handle_key_r()

    # Clear screen
    screen.fill((45, 45, 45))

    # Draw all objects
    title.draw(screen)
    subtitle.draw(screen)
    instructions.draw(screen)
    start_text.draw(screen)
    player.draw(screen)
    box1.draw(screen)
    goal1.draw(screen)
    wall1.draw(screen)
    level_text.draw(screen)
    moves_text.draw(screen)
    win_text.draw(screen)
    next_level_text.draw(screen)
    state.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()