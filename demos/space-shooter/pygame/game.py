#!/usr/bin/env python3
# Auto-generated from Rosh code
# Transpiled with Rosh Pygame Transpiler v0.1.10

import pygame
import sys
from pathlib import Path

# Asset path resolution (relative to script)
SCRIPT_DIR = Path(__file__).parent
ASSETS_DIR = SCRIPT_DIR / 'assets'

# Initialize Pygame
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Rosh Game')
clock = pygame.time.Clock()

# Sound cache and helper
_sounds = {}

def play_sound(filename):
    """Play a sound effect with caching"""
    if filename not in _sounds:
        try:
            _sounds[filename] = pygame.mixer.Sound(str(ASSETS_DIR / filename))
        except Exception as e:
            print(f'Warning: Could not load sound {filename}: {e}')
            return
    _sounds[filename].play()

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
title = TextObject(400, 150, "Space Shooter", (0, 255, 255), 48)

instructions = TextObject(400, 270, "Arrow keys to move, SPACE to fire", (255, 255, 255), 18)

start_text = TextObject(400, 420, "Press SPACE to start", (255, 255, 0), 20)

player = GameObject(400, 540, 50, 50, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'player.png'
    player.sprite = pygame.image.load(str(_sprite_path))
    player.sprite = pygame.transform.scale(player.sprite, (50, 50))
except:
    print(f'Warning: Could not load sprite player.png, using colored shape')
player.visible = False
player.speed = 8

bullet1 = GameObject(0, 0, 9, 33, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'laserGreen.png'
    bullet1.sprite = pygame.image.load(str(_sprite_path))
    bullet1.sprite = pygame.transform.scale(bullet1.sprite, (9, 33))
except:
    print(f'Warning: Could not load sprite laserGreen.png, using colored shape')
bullet1.visible = False
bullet1.active = 0

bullet2 = GameObject(0, 0, 9, 33, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'laserGreen.png'
    bullet2.sprite = pygame.image.load(str(_sprite_path))
    bullet2.sprite = pygame.transform.scale(bullet2.sprite, (9, 33))
except:
    print(f'Warning: Could not load sprite laserGreen.png, using colored shape')
bullet2.visible = False
bullet2.active = 0

bullet3 = GameObject(0, 0, 9, 33, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'laserGreen.png'
    bullet3.sprite = pygame.image.load(str(_sprite_path))
    bullet3.sprite = pygame.transform.scale(bullet3.sprite, (9, 33))
except:
    print(f'Warning: Could not load sprite laserGreen.png, using colored shape')
bullet3.visible = False
bullet3.active = 0

bullet4 = GameObject(0, 0, 9, 33, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'laserGreen.png'
    bullet4.sprite = pygame.image.load(str(_sprite_path))
    bullet4.sprite = pygame.transform.scale(bullet4.sprite, (9, 33))
except:
    print(f'Warning: Could not load sprite laserGreen.png, using colored shape')
bullet4.visible = False
bullet4.active = 0

bullet5 = GameObject(0, 0, 9, 33, (0, 255, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'laserGreen.png'
    bullet5.sprite = pygame.image.load(str(_sprite_path))
    bullet5.sprite = pygame.transform.scale(bullet5.sprite, (9, 33))
except:
    print(f'Warning: Could not load sprite laserGreen.png, using colored shape')
bullet5.visible = False
bullet5.active = 0

enemy1 = GameObject(100, -50, 40, 40, (255, 0, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'enemyShip.png'
    enemy1.sprite = pygame.image.load(str(_sprite_path))
    enemy1.sprite = pygame.transform.scale(enemy1.sprite, (40, 40))
except:
    print(f'Warning: Could not load sprite enemyShip.png, using colored shape')
enemy1.visible = False
enemy1.active = 0
enemy1.speed = 2

enemy2 = GameObject(300, -50, 40, 40, (255, 0, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'enemyShip.png'
    enemy2.sprite = pygame.image.load(str(_sprite_path))
    enemy2.sprite = pygame.transform.scale(enemy2.sprite, (40, 40))
except:
    print(f'Warning: Could not load sprite enemyShip.png, using colored shape')
enemy2.visible = False
enemy2.active = 0
enemy2.speed = 2

enemy3 = GameObject(500, -50, 40, 40, (255, 0, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'enemyShip.png'
    enemy3.sprite = pygame.image.load(str(_sprite_path))
    enemy3.sprite = pygame.transform.scale(enemy3.sprite, (40, 40))
except:
    print(f'Warning: Could not load sprite enemyShip.png, using colored shape')
enemy3.visible = False
enemy3.active = 0
enemy3.speed = 2

enemy4 = GameObject(700, -50, 40, 40, (255, 0, 0), 'rectangle')
try:
    _sprite_path = ASSETS_DIR / 'enemyShip.png'
    enemy4.sprite = pygame.image.load(str(_sprite_path))
    enemy4.sprite = pygame.transform.scale(enemy4.sprite, (40, 40))
except:
    print(f'Warning: Could not load sprite enemyShip.png, using colored shape')
enemy4.visible = False
enemy4.active = 0
enemy4.speed = 2

score_text = TextObject(70, 30, "Score: 0", (255, 255, 255), 20)
score_text.visible = False

lives_text = TextObject(730, 30, "Lives: 3", (0, 255, 0), 20)
lives_text.visible = False

game_over_text = TextObject(400, 270, "GAME OVER", (255, 0, 0), 48)
game_over_text.visible = False

final_score_text = TextObject(400, 360, "Final Score: 0", (255, 255, 255), 24)
final_score_text.visible = False

restart_text = TextObject(400, 450, "Press R to restart", (255, 255, 0), 20)
restart_text.visible = False

state = GameObject(0, 0, 1, 1, (255, 0, 0), 'rectangle')
state.visible = False
state.level = 0
state.score = 0
state.lives = 3
state.spawn_timer = 0
state.next_bullet = 1


# User-defined functions
def start_game():
    title.visible = False
    instructions.visible = False
    start_text.visible = False
    player.visible = True
    score_text.visible = True
    lives_text.visible = True
    state.level = 1
    state.score = 0
    state.lives = 3
    state.spawn_timer = 0
    player.x = 400
    score_text.set_text("Score: 0")
    lives_text.set_text("Lives: 3")
    spawn_enemy_wave()

def spawn_enemy_wave():
    enemy1.x = 100
    enemy1.y = (-50)
    enemy1.active = 1
    enemy1.visible = True
    enemy2.x = 300
    enemy2.y = (-100)
    enemy2.active = 1
    enemy2.visible = True
    enemy3.x = 500
    enemy3.y = (-150)
    enemy3.active = 1
    enemy3.visible = True
    enemy4.x = 700
    enemy4.y = (-200)
    enemy4.active = 1
    enemy4.visible = True

def fire_bullet():
    play_sound("laser1.ogg")
    if (state.next_bullet == 1):
        if (bullet1.active == 0):
            bullet1.x = player.x
            bullet1.y = (player.y - 30)
            bullet1.active = 1
            bullet1.visible = True
        state.next_bullet = 2
    if (state.next_bullet == 2):
        if (bullet2.active == 0):
            bullet2.x = player.x
            bullet2.y = (player.y - 30)
            bullet2.active = 1
            bullet2.visible = True
        state.next_bullet = 3
    if (state.next_bullet == 3):
        if (bullet3.active == 0):
            bullet3.x = player.x
            bullet3.y = (player.y - 30)
            bullet3.active = 1
            bullet3.visible = True
        state.next_bullet = 4
    if (state.next_bullet == 4):
        if (bullet4.active == 0):
            bullet4.x = player.x
            bullet4.y = (player.y - 30)
            bullet4.active = 1
            bullet4.visible = True
        state.next_bullet = 5
    if (state.next_bullet == 5):
        if (bullet5.active == 0):
            bullet5.x = player.x
            bullet5.y = (player.y - 30)
            bullet5.active = 1
            bullet5.visible = True
        state.next_bullet = 1

def update_score():
    score_text.set_text(f"Score: {state.score}")

def update_lives():
    lives_text.set_text(f"Lives: {state.lives}")
    if (state.lives == 0):
        game_over()

def game_over():
    state.level = 0
    player.visible = False
    score_text.visible = False
    lives_text.visible = False
    bullet1.visible = False
    bullet2.visible = False
    bullet3.visible = False
    bullet4.visible = False
    bullet5.visible = False
    enemy1.visible = False
    enemy2.visible = False
    enemy3.visible = False
    enemy4.visible = False
    game_over_text.visible = True
    final_score_text.set_text(f"Final Score: {state.score}")
    final_score_text.visible = True
    restart_text.visible = True

def restart_game():
    game_over_text.visible = False
    final_score_text.visible = False
    restart_text.visible = False
    bullet1.active = 0
    bullet2.active = 0
    bullet3.active = 0
    bullet4.active = 0
    bullet5.active = 0
    enemy1.active = 0
    enemy2.active = 0
    enemy3.active = 0
    enemy4.active = 0
    start_game()


# Event handlers
def handle_space_pressed():
    if (state.level == 0):
        start_game()
    if (state.level > 0):
        fire_bullet()

def handle_while_key_left():
    if (state.level > 0):
        if (player.x > 30):
            player.x = (player.x - 5)

def handle_while_key_right():
    if (state.level > 0):
        if (player.x < 770):
            player.x = (player.x + 5)

def handle_key_r():
    if (state.level == 0):
        if (game_over_text.visible == True):
            restart_game()

def handle_update():
    if (state.level > 0):
        if (bullet1.active == 1):
            bullet1.y = (bullet1.y - 10)
            if (bullet1.y < 0):
                bullet1.active = 0
                bullet1.visible = False
        if (bullet2.active == 1):
            bullet2.y = (bullet2.y - 10)
            if (bullet2.y < 0):
                bullet2.active = 0
                bullet2.visible = False
        if (bullet3.active == 1):
            bullet3.y = (bullet3.y - 10)
            if (bullet3.y < 0):
                bullet3.active = 0
                bullet3.visible = False
        if (bullet4.active == 1):
            bullet4.y = (bullet4.y - 10)
            if (bullet4.y < 0):
                bullet4.active = 0
                bullet4.visible = False
        if (bullet5.active == 1):
            bullet5.y = (bullet5.y - 10)
            if (bullet5.y < 0):
                bullet5.active = 0
                bullet5.visible = False
        if (enemy1.active == 1):
            enemy1.y = (enemy1.y + 2)
            if (enemy1.y > 650):
                enemy1.y = (-50)
        if (enemy2.active == 1):
            enemy2.y = (enemy2.y + 2)
            if (enemy2.y > 650):
                enemy2.y = (-50)
        if (enemy3.active == 1):
            enemy3.y = (enemy3.y + 2)
            if (enemy3.y > 650):
                enemy3.y = (-50)
        if (enemy4.active == 1):
            enemy4.y = (enemy4.y + 2)
            if (enemy4.y > 650):
                enemy4.y = (-50)
        if (bullet1.active == 1):
            if (enemy1.active == 1):
                if (bullet1.x > (enemy1.x - 20)):
                    if (bullet1.x < (enemy1.x + 20)):
                        if (bullet1.y > (enemy1.y - 20)):
                            if (bullet1.y < (enemy1.y + 20)):
                                play_sound("lose1.ogg")
                                enemy1.y = (-50)
                                bullet1.active = 0
                                bullet1.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy2.active == 1):
                if (bullet1.x > (enemy2.x - 20)):
                    if (bullet1.x < (enemy2.x + 20)):
                        if (bullet1.y > (enemy2.y - 20)):
                            if (bullet1.y < (enemy2.y + 20)):
                                play_sound("lose1.ogg")
                                enemy2.y = (-50)
                                bullet1.active = 0
                                bullet1.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy3.active == 1):
                if (bullet1.x > (enemy3.x - 20)):
                    if (bullet1.x < (enemy3.x + 20)):
                        if (bullet1.y > (enemy3.y - 20)):
                            if (bullet1.y < (enemy3.y + 20)):
                                play_sound("lose1.ogg")
                                enemy3.y = (-50)
                                bullet1.active = 0
                                bullet1.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy4.active == 1):
                if (bullet1.x > (enemy4.x - 20)):
                    if (bullet1.x < (enemy4.x + 20)):
                        if (bullet1.y > (enemy4.y - 20)):
                            if (bullet1.y < (enemy4.y + 20)):
                                play_sound("lose1.ogg")
                                enemy4.y = (-50)
                                bullet1.active = 0
                                bullet1.visible = False
                                state.score = (state.score + 10)
                                update_score()
        if (bullet2.active == 1):
            if (enemy1.active == 1):
                if (bullet2.x > (enemy1.x - 20)):
                    if (bullet2.x < (enemy1.x + 20)):
                        if (bullet2.y > (enemy1.y - 20)):
                            if (bullet2.y < (enemy1.y + 20)):
                                play_sound("lose1.ogg")
                                enemy1.y = (-50)
                                bullet2.active = 0
                                bullet2.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy2.active == 1):
                if (bullet2.x > (enemy2.x - 20)):
                    if (bullet2.x < (enemy2.x + 20)):
                        if (bullet2.y > (enemy2.y - 20)):
                            if (bullet2.y < (enemy2.y + 20)):
                                play_sound("lose1.ogg")
                                enemy2.y = (-50)
                                bullet2.active = 0
                                bullet2.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy3.active == 1):
                if (bullet2.x > (enemy3.x - 20)):
                    if (bullet2.x < (enemy3.x + 20)):
                        if (bullet2.y > (enemy3.y - 20)):
                            if (bullet2.y < (enemy3.y + 20)):
                                play_sound("lose1.ogg")
                                enemy3.y = (-50)
                                bullet2.active = 0
                                bullet2.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy4.active == 1):
                if (bullet2.x > (enemy4.x - 20)):
                    if (bullet2.x < (enemy4.x + 20)):
                        if (bullet2.y > (enemy4.y - 20)):
                            if (bullet2.y < (enemy4.y + 20)):
                                play_sound("lose1.ogg")
                                enemy4.y = (-50)
                                bullet2.active = 0
                                bullet2.visible = False
                                state.score = (state.score + 10)
                                update_score()
        if (bullet3.active == 1):
            if (enemy1.active == 1):
                if (bullet3.x > (enemy1.x - 20)):
                    if (bullet3.x < (enemy1.x + 20)):
                        if (bullet3.y > (enemy1.y - 20)):
                            if (bullet3.y < (enemy1.y + 20)):
                                play_sound("lose1.ogg")
                                enemy1.y = (-50)
                                bullet3.active = 0
                                bullet3.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy2.active == 1):
                if (bullet3.x > (enemy2.x - 20)):
                    if (bullet3.x < (enemy2.x + 20)):
                        if (bullet3.y > (enemy2.y - 20)):
                            if (bullet3.y < (enemy2.y + 20)):
                                play_sound("lose1.ogg")
                                enemy2.y = (-50)
                                bullet3.active = 0
                                bullet3.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy3.active == 1):
                if (bullet3.x > (enemy3.x - 20)):
                    if (bullet3.x < (enemy3.x + 20)):
                        if (bullet3.y > (enemy3.y - 20)):
                            if (bullet3.y < (enemy3.y + 20)):
                                play_sound("lose1.ogg")
                                enemy3.y = (-50)
                                bullet3.active = 0
                                bullet3.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy4.active == 1):
                if (bullet3.x > (enemy4.x - 20)):
                    if (bullet3.x < (enemy4.x + 20)):
                        if (bullet3.y > (enemy4.y - 20)):
                            if (bullet3.y < (enemy4.y + 20)):
                                play_sound("lose1.ogg")
                                enemy4.y = (-50)
                                bullet3.active = 0
                                bullet3.visible = False
                                state.score = (state.score + 10)
                                update_score()
        if (bullet4.active == 1):
            if (enemy1.active == 1):
                if (bullet4.x > (enemy1.x - 20)):
                    if (bullet4.x < (enemy1.x + 20)):
                        if (bullet4.y > (enemy1.y - 20)):
                            if (bullet4.y < (enemy1.y + 20)):
                                play_sound("lose1.ogg")
                                enemy1.y = (-50)
                                bullet4.active = 0
                                bullet4.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy2.active == 1):
                if (bullet4.x > (enemy2.x - 20)):
                    if (bullet4.x < (enemy2.x + 20)):
                        if (bullet4.y > (enemy2.y - 20)):
                            if (bullet4.y < (enemy2.y + 20)):
                                play_sound("lose1.ogg")
                                enemy2.y = (-50)
                                bullet4.active = 0
                                bullet4.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy3.active == 1):
                if (bullet4.x > (enemy3.x - 20)):
                    if (bullet4.x < (enemy3.x + 20)):
                        if (bullet4.y > (enemy3.y - 20)):
                            if (bullet4.y < (enemy3.y + 20)):
                                play_sound("lose1.ogg")
                                enemy3.y = (-50)
                                bullet4.active = 0
                                bullet4.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy4.active == 1):
                if (bullet4.x > (enemy4.x - 20)):
                    if (bullet4.x < (enemy4.x + 20)):
                        if (bullet4.y > (enemy4.y - 20)):
                            if (bullet4.y < (enemy4.y + 20)):
                                play_sound("lose1.ogg")
                                enemy4.y = (-50)
                                bullet4.active = 0
                                bullet4.visible = False
                                state.score = (state.score + 10)
                                update_score()
        if (bullet5.active == 1):
            if (enemy1.active == 1):
                if (bullet5.x > (enemy1.x - 20)):
                    if (bullet5.x < (enemy1.x + 20)):
                        if (bullet5.y > (enemy1.y - 20)):
                            if (bullet5.y < (enemy1.y + 20)):
                                play_sound("lose1.ogg")
                                enemy1.y = (-50)
                                bullet5.active = 0
                                bullet5.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy2.active == 1):
                if (bullet5.x > (enemy2.x - 20)):
                    if (bullet5.x < (enemy2.x + 20)):
                        if (bullet5.y > (enemy2.y - 20)):
                            if (bullet5.y < (enemy2.y + 20)):
                                play_sound("lose1.ogg")
                                enemy2.y = (-50)
                                bullet5.active = 0
                                bullet5.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy3.active == 1):
                if (bullet5.x > (enemy3.x - 20)):
                    if (bullet5.x < (enemy3.x + 20)):
                        if (bullet5.y > (enemy3.y - 20)):
                            if (bullet5.y < (enemy3.y + 20)):
                                play_sound("lose1.ogg")
                                enemy3.y = (-50)
                                bullet5.active = 0
                                bullet5.visible = False
                                state.score = (state.score + 10)
                                update_score()
            if (enemy4.active == 1):
                if (bullet5.x > (enemy4.x - 20)):
                    if (bullet5.x < (enemy4.x + 20)):
                        if (bullet5.y > (enemy4.y - 20)):
                            if (bullet5.y < (enemy4.y + 20)):
                                play_sound("lose1.ogg")
                                enemy4.y = (-50)
                                bullet5.active = 0
                                bullet5.visible = False
                                state.score = (state.score + 10)
                                update_score()
        if (enemy1.active == 1):
            if (enemy1.y > (player.y - 25)):
                if (enemy1.y < (player.y + 25)):
                    if (enemy1.x > (player.x - 30)):
                        if (enemy1.x < (player.x + 30)):
                            play_sound("lose3.ogg")
                            enemy1.y = (-50)
                            state.lives = (state.lives - 1)
                            update_lives()
        if (enemy2.active == 1):
            if (enemy2.y > (player.y - 25)):
                if (enemy2.y < (player.y + 25)):
                    if (enemy2.x > (player.x - 30)):
                        if (enemy2.x < (player.x + 30)):
                            play_sound("lose3.ogg")
                            enemy2.y = (-50)
                            state.lives = (state.lives - 1)
                            update_lives()
        if (enemy3.active == 1):
            if (enemy3.y > (player.y - 25)):
                if (enemy3.y < (player.y + 25)):
                    if (enemy3.x > (player.x - 30)):
                        if (enemy3.x < (player.x + 30)):
                            play_sound("lose3.ogg")
                            enemy3.y = (-50)
                            state.lives = (state.lives - 1)
                            update_lives()
        if (enemy4.active == 1):
            if (enemy4.y > (player.y - 25)):
                if (enemy4.y < (player.y + 25)):
                    if (enemy4.x > (player.x - 30)):
                        if (enemy4.x < (player.x + 30)):
                            play_sound("lose3.ogg")
                            enemy4.y = (-50)
                            state.lives = (state.lives - 1)
                            update_lives()

# Main game loop
running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                handle_space_pressed()
            elif event.key == pygame.K_r:
                handle_key_r()

    # Check held keys for smooth movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        handle_while_key_left()
    if keys[pygame.K_RIGHT]:
        handle_while_key_right()

    # Per-frame game update
    handle_update()

    # Clear screen
    screen.fill((45, 45, 45))

    # Draw all objects
    title.draw(screen)
    instructions.draw(screen)
    start_text.draw(screen)
    player.draw(screen)
    bullet1.draw(screen)
    bullet2.draw(screen)
    bullet3.draw(screen)
    bullet4.draw(screen)
    bullet5.draw(screen)
    enemy1.draw(screen)
    enemy2.draw(screen)
    enemy3.draw(screen)
    enemy4.draw(screen)
    score_text.draw(screen)
    lives_text.draw(screen)
    game_over_text.draw(screen)
    final_score_text.draw(screen)
    restart_text.draw(screen)
    state.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()