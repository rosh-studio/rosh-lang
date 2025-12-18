# Auto-generated from Rosh IR
# Emitter: Pygame v0.2.0

import pygame
import sys
import os

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption('Rosh Game')
        self.clock = pygame.time.Clock()
        self.running = True
        self.font = pygame.font.Font(None, 24)
        self.current_scene = None
        self.current_level = 1

        # Load sprites
        self.sprites = {}
        self.sprites['player_png'] = pygame.image.load(os.path.join('assets', 'player.png'))

        # Create objects
        self.title = pygame.Rect(380, 135, 40, 30)
        self.title_text = 'Block Pusher'
        self.title_color = (255, 255, 255)
        self.title_font_size = 48
        self.subtitle = pygame.Rect(380, 213, 40, 30)
        self.subtitle_text = 'A Sokoban Puzzle Game'
        self.subtitle_color = (136, 136, 136)
        self.subtitle_font_size = 24
        self.instructions = pygame.Rect(380, 315, 40, 30)
        self.instructions_text = 'Push all boxes onto the circles'
        self.instructions_color = (0, 255, 255)
        self.instructions_font_size = 18
        self.start_text = pygame.Rect(380, 465, 40, 30)
        self.start_text_text = 'Press SPACE to start'
        self.start_text_color = (255, 255, 0)
        self.start_text_font_size = 20
        self.player = pygame.Rect(255, 255, 40, 40)
        self.player_visible = False
        self.player_color = (0, 255, 0)
        self.player_sprite = 'player_png'
        self.box1 = pygame.Rect(355, 255, 40, 40)
        self.box1_visible = False
        self.box1_color = (0, 0, 255)
        self.goal1 = pygame.Rect(453, 253, 44, 44)
        self.goal1_shape = 'circle'
        self.goal1_visible = False
        self.goal1_color = (255, 0, 0)
        self.wall1 = pygame.Rect(455, 305, 40, 40)
        self.wall1_visible = False
        self.wall1_color = (255, 255, 0)
        self.level_text = pygame.Rect(380, 33, 40, 30)
        self.level_text_text = 'Level 1'
        self.level_text_color = (255, 255, 255)
        self.level_text_font_size = 24
        self.level_text_visible = False
        self.moves_text = pygame.Rect(380, 537, 40, 30)
        self.moves_text_text = 'Moves: 0'
        self.moves_text_color = (136, 136, 136)
        self.moves_text_font_size = 16
        self.moves_text_visible = False
        self.win_text = pygame.Rect(380, 285, 40, 30)
        self.win_text_text = 'You Win!'
        self.win_text_color = (255, 215, 0)
        self.win_text_font_size = 64
        self.win_text_visible = False
        self.next_level_text = pygame.Rect(380, 375, 40, 30)
        self.next_level_text_text = 'Press SPACE for next level'
        self.next_level_text_color = (255, 255, 0)
        self.next_level_text_font_size = 20
        self.next_level_text_visible = False
        self.state = pygame.Rect(0, 0, 1, 1)
        self.state_moves = 0
        self.state_can_move = 1
        self.state_visible = False
        self.state_color = (255, 0, 255)
        self.state_level = 0

        # Set initial scene/level visibility
        self.update_scene_visibility()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.state_level == 0:
                        self.title_visible = False
                        self.subtitle_visible = False
                        self.instructions_visible = False
                        self.start_text_visible = False
                        self.player_visible = True
                        self.box1_visible = True
                        self.goal1_visible = True
                        self.level_text_visible = True
                        self.moves_text_visible = True
                        self.start_level_1()
                    if self.state_level == 1:
                        if self.win_text_visible == True:
                            self.start_level_2()
                if event.key == pygame.K_LEFT:
                    if self.state_level > 0:
                        if self.state_level < 3:
                            if self.win_text_visible == False:
                                if self.player.centerx > 250:
                                    self.state_can_move = 1
                                    if (self.player.centerx - 50) == self.wall1.centerx:
                                        if self.player.centery == self.wall1.centery:
                                            self.state_can_move = 0
                                    if self.state_can_move == 1:
                                        if self.player.centerx == (self.box1.centerx + 50):
                                            if self.player.centery == self.box1.centery:
                                                self.state_can_move = 1
                                                if (self.box1.centerx - 50) == self.wall1.centerx:
                                                    if self.box1.centery == self.wall1.centery:
                                                        self.state_can_move = 0
                                                if self.state_can_move == 1:
                                                    if self.box1.centerx > 250:
                                                        self.box1.centerx = (self.box1.centerx - 50)
                                                        self.player.centerx = (self.player.centerx - 50)
                                                        self.state_moves = (self.state_moves + 1)
                                            else:
                                                self.player.centerx = (self.player.centerx - 50)
                                                self.state_moves = (self.state_moves + 1)
                                        else:
                                            self.player.centerx = (self.player.centerx - 50)
                                            self.state_moves = (self.state_moves + 1)
                    self.check_win()
                    self.update_display()
                if event.key == pygame.K_RIGHT:
                    if self.state_level > 0:
                        if self.state_level < 3:
                            if self.win_text_visible == False:
                                if self.player.centerx < 550:
                                    self.state_can_move = 1
                                    if (self.player.centerx + 50) == self.wall1.centerx:
                                        if self.player.centery == self.wall1.centery:
                                            self.state_can_move = 0
                                    if self.state_can_move == 1:
                                        if self.player.centerx == (self.box1.centerx - 50):
                                            if self.player.centery == self.box1.centery:
                                                self.state_can_move = 1
                                                if (self.box1.centerx + 50) == self.wall1.centerx:
                                                    if self.box1.centery == self.wall1.centery:
                                                        self.state_can_move = 0
                                                if self.state_can_move == 1:
                                                    if self.box1.centerx < 550:
                                                        self.box1.centerx = (self.box1.centerx + 50)
                                                        self.player.centerx = (self.player.centerx + 50)
                                                        self.state_moves = (self.state_moves + 1)
                                            else:
                                                self.player.centerx = (self.player.centerx + 50)
                                                self.state_moves = (self.state_moves + 1)
                                        else:
                                            self.player.centerx = (self.player.centerx + 50)
                                            self.state_moves = (self.state_moves + 1)
                    self.check_win()
                    self.update_display()
                if event.key == pygame.K_UP:
                    if self.state_level > 0:
                        if self.state_level < 3:
                            if self.win_text_visible == False:
                                if self.player.centery > 200:
                                    self.state_can_move = 1
                                    if (self.player.centery - 50) == self.wall1.centery:
                                        if self.player.centerx == self.wall1.centerx:
                                            self.state_can_move = 0
                                    if self.state_can_move == 1:
                                        if self.player.centery == (self.box1.centery + 50):
                                            if self.player.centerx == self.box1.centerx:
                                                self.state_can_move = 1
                                                if (self.box1.centery - 50) == self.wall1.centery:
                                                    if self.box1.centerx == self.wall1.centerx:
                                                        self.state_can_move = 0
                                                if self.state_can_move == 1:
                                                    if self.box1.centery > 200:
                                                        self.box1.centery = (self.box1.centery - 50)
                                                        self.player.centery = (self.player.centery - 50)
                                                        self.state_moves = (self.state_moves + 1)
                                            else:
                                                self.player.centery = (self.player.centery - 50)
                                                self.state_moves = (self.state_moves + 1)
                                        else:
                                            self.player.centery = (self.player.centery - 50)
                                            self.state_moves = (self.state_moves + 1)
                    self.check_win()
                    self.update_display()
                if event.key == pygame.K_DOWN:
                    if self.state_level > 0:
                        if self.state_level < 3:
                            if self.win_text_visible == False:
                                if self.player.centery < 400:
                                    self.state_can_move = 1
                                    if (self.player.centery + 50) == self.wall1.centery:
                                        if self.player.centerx == self.wall1.centerx:
                                            self.state_can_move = 0
                                    if self.state_can_move == 1:
                                        if self.player.centery == (self.box1.centery - 50):
                                            if self.player.centerx == self.box1.centerx:
                                                self.state_can_move = 1
                                                if (self.box1.centery + 50) == self.wall1.centery:
                                                    if self.box1.centerx == self.wall1.centerx:
                                                        self.state_can_move = 0
                                                if self.state_can_move == 1:
                                                    if self.box1.centery < 400:
                                                        self.box1.centery = (self.box1.centery + 50)
                                                        self.player.centery = (self.player.centery + 50)
                                                        self.state_moves = (self.state_moves + 1)
                                            else:
                                                self.player.centery = (self.player.centery + 50)
                                                self.state_moves = (self.state_moves + 1)
                                        else:
                                            self.player.centery = (self.player.centery + 50)
                                            self.state_moves = (self.state_moves + 1)
                    self.check_win()
                    self.update_display()
                if event.key == pygame.K_r:
                    self.restart_level()

    def update(self):
        keys = pygame.key.get_pressed()
        speed = getattr(self, 'player_speed', 5)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.x += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.y -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.y += speed

    def draw(self):
        self.screen.fill((26, 26, 46))

        # Draw objects
        if getattr(self, 'title_visible', True):
            _font = pygame.font.Font(None, self.title_font_size)
            _text_surf = _font.render(self.title_text, True, self.title_color)
            _text_rect = _text_surf.get_rect(center=(self.title.centerx, self.title.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'subtitle_visible', True):
            _font = pygame.font.Font(None, self.subtitle_font_size)
            _text_surf = _font.render(self.subtitle_text, True, self.subtitle_color)
            _text_rect = _text_surf.get_rect(center=(self.subtitle.centerx, self.subtitle.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'instructions_visible', True):
            _font = pygame.font.Font(None, self.instructions_font_size)
            _text_surf = _font.render(self.instructions_text, True, self.instructions_color)
            _text_rect = _text_surf.get_rect(center=(self.instructions.centerx, self.instructions.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'start_text_visible', True):
            _font = pygame.font.Font(None, self.start_text_font_size)
            _text_surf = _font.render(self.start_text_text, True, self.start_text_color)
            _text_rect = _text_surf.get_rect(center=(self.start_text.centerx, self.start_text.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'player_visible', True):
            _sprite = pygame.transform.scale(self.sprites['player_png'], (self.player.width, self.player.height))
            self.screen.blit(_sprite, self.player)
        if getattr(self, 'box1_visible', True):
            pygame.draw.rect(self.screen, self.box1_color, self.box1)
        if getattr(self, 'goal1_visible', True):
            pygame.draw.rect(self.screen, self.goal1_color, self.goal1)
        if getattr(self, 'wall1_visible', True):
            pygame.draw.rect(self.screen, self.wall1_color, self.wall1)
        if getattr(self, 'level_text_visible', True):
            _font = pygame.font.Font(None, self.level_text_font_size)
            _text_surf = _font.render(self.level_text_text, True, self.level_text_color)
            _text_rect = _text_surf.get_rect(center=(self.level_text.centerx, self.level_text.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'moves_text_visible', True):
            _font = pygame.font.Font(None, self.moves_text_font_size)
            _text_surf = _font.render(self.moves_text_text, True, self.moves_text_color)
            _text_rect = _text_surf.get_rect(center=(self.moves_text.centerx, self.moves_text.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'win_text_visible', True):
            _font = pygame.font.Font(None, self.win_text_font_size)
            _text_surf = _font.render(self.win_text_text, True, self.win_text_color)
            _text_rect = _text_surf.get_rect(center=(self.win_text.centerx, self.win_text.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'next_level_text_visible', True):
            _font = pygame.font.Font(None, self.next_level_text_font_size)
            _text_surf = _font.render(self.next_level_text_text, True, self.next_level_text_color)
            _text_rect = _text_surf.get_rect(center=(self.next_level_text.centerx, self.next_level_text.centery))
            self.screen.blit(_text_surf, _text_rect)
        if getattr(self, 'state_visible', True):
            pygame.draw.rect(self.screen, self.state_color, self.state)

        pygame.display.flip()

    def update_scene_visibility(self):
        # Roshonic "Dimensions, Not Modes" - scene/level as coordinates
        self.state_visible = (self.current_level == 0)

    def start_level_1(self):
        self.player.centerx = 275.0
        self.player.centery = 275.0
        self.box1.centerx = 375.0
        self.box1.centery = 275.0
        self.goal1.centerx = 475.0
        self.goal1.centery = 275.0
        self.wall1_visible = False
        self.level_text_text = f'Level 1'
        self.state_level = 1
        self.state_moves = 0
        self.moves_text_text = f'Moves: 0'

    def start_level_2(self):
        self.player.centerx = 275.0
        self.player.centery = 325.0
        self.box1.centerx = 375.0
        self.box1.centery = 325.0
        self.wall1.centerx = 475.0
        self.wall1.centery = 325.0
        self.wall1_visible = True
        self.goal1.centerx = 525.0
        self.goal1.centery = 225.0
        self.level_text_text = f'Level 2'
        self.state_level = 2
        self.state_moves = 0
        self.moves_text_text = f'Moves: 0'
        self.win_text_visible = False
        self.next_level_text_visible = False

    def show_victory(self):
        self.win_text_text = f'You Win!'
        self.win_text_visible = True
        self.next_level_text_text = f'Press R to play again'
        self.next_level_text_visible = True
        self.state_level = 3

    def restart_level(self):
        self.win_text_visible = False
        self.next_level_text_visible = False
        if self.state_level == 1:
            self.start_level_1()
        if self.state_level == 2:
            self.start_level_2()
        if self.state_level == 3:
            self.start_level_1()

    def check_win(self):
        if self.box1.centerx == self.goal1.centerx:
            if self.box1.centery == self.goal1.centery:
                if self.state_level == 1:
                    self.win_text_text = f'Level Complete!'
                    self.win_text_visible = True
                    self.next_level_text_visible = True
                if self.state_level == 2:
                    self.show_victory()

    def update_display(self):
        self.moves_text_text = f'Moves: {self.state_moves}'


if __name__ == '__main__':
    game = Game()
    game.run()