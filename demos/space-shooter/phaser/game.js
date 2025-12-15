// Auto-generated from Rosh code
// Transpiled with Rosh Phaser Transpiler v0.1.10

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.eventHandlers = {};
    }

    preload() {
        // Load sprite for player
        this.load.image('player_sprite', 'assets/player.png');
        // Load sprite for bullet1
        this.load.image('bullet1_sprite', 'assets/laserGreen.png');
        // Load sprite for bullet2
        this.load.image('bullet2_sprite', 'assets/laserGreen.png');
        // Load sprite for bullet3
        this.load.image('bullet3_sprite', 'assets/laserGreen.png');
        // Load sprite for bullet4
        this.load.image('bullet4_sprite', 'assets/laserGreen.png');
        // Load sprite for bullet5
        this.load.image('bullet5_sprite', 'assets/laserGreen.png');
        // Load sprite for enemy1
        this.load.image('enemy1_sprite', 'assets/enemyShip.png');
        // Load sprite for enemy2
        this.load.image('enemy2_sprite', 'assets/enemyShip.png');
        // Load sprite for enemy3
        this.load.image('enemy3_sprite', 'assets/enemyShip.png');
        // Load sprite for enemy4
        this.load.image('enemy4_sprite', 'assets/enemyShip.png');
        // Load sound: laser1.ogg
        this.load.audio('laser1_ogg', 'assets/laser1.ogg');
        // Load sound: lose1.ogg
        this.load.audio('lose1_ogg', 'assets/lose1.ogg');
        // Load sound: lose3.ogg
        this.load.audio('lose3_ogg', 'assets/lose3.ogg');
    }

    create() {
        // Keyboard setup
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = {
            space: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE),
            r: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.R)
        };

        // Title object
        this.title = this.add.text(400, 150, 'Space Shooter', { fontFamily: 'Arial', fontSize: '48px', color: 'cyan', align: 'center' });
        this.title.setOrigin(0.5, 0.5);
        this.title.textContent = 'Space Shooter';
        this.title.font_size = 48;

        // Instructions object
        this.instructions = this.add.text(400, 270, 'Arrow keys to move, SPACE to fire', { fontFamily: 'Arial', fontSize: '18px', color: 'white', align: 'center' });
        this.instructions.setOrigin(0.5, 0.5);
        this.instructions.textContent = 'Arrow keys to move, SPACE to fire';
        this.instructions.font_size = 18;

        // Start_text object
        this.start_text = this.add.text(400, 420, 'Press SPACE to start', { fontFamily: 'Arial', fontSize: '20px', color: 'yellow', align: 'center' });
        this.start_text.setOrigin(0.5, 0.5);
        this.start_text.textContent = 'Press SPACE to start';
        this.start_text.font_size = 20;

        // Player object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('player_sprite')) {
            this.player = this.add.image(400, 540, 'player_sprite');
            this.player.setDisplaySize(50, 50);
        } else {
            console.warn('Sprite not found: player.png, using colored rectangle');
            this.player = this.add.rectangle(400, 540, 50, 50, 0xff00);
        }
        this.player.speed = 8;
        this.player.setVisible(false);

        // Bullet1 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('bullet1_sprite')) {
            this.bullet1 = this.add.image(0, 0, 'bullet1_sprite');
            this.bullet1.setDisplaySize(9, 33);
        } else {
            console.warn('Sprite not found: laserGreen.png, using colored rectangle');
            this.bullet1 = this.add.rectangle(0, 0, 9, 33, 0xff00);
        }
        this.bullet1.active = 0;
        this.bullet1.setVisible(false);

        // Bullet2 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('bullet2_sprite')) {
            this.bullet2 = this.add.image(0, 0, 'bullet2_sprite');
            this.bullet2.setDisplaySize(9, 33);
        } else {
            console.warn('Sprite not found: laserGreen.png, using colored rectangle');
            this.bullet2 = this.add.rectangle(0, 0, 9, 33, 0xff00);
        }
        this.bullet2.active = 0;
        this.bullet2.setVisible(false);

        // Bullet3 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('bullet3_sprite')) {
            this.bullet3 = this.add.image(0, 0, 'bullet3_sprite');
            this.bullet3.setDisplaySize(9, 33);
        } else {
            console.warn('Sprite not found: laserGreen.png, using colored rectangle');
            this.bullet3 = this.add.rectangle(0, 0, 9, 33, 0xff00);
        }
        this.bullet3.active = 0;
        this.bullet3.setVisible(false);

        // Bullet4 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('bullet4_sprite')) {
            this.bullet4 = this.add.image(0, 0, 'bullet4_sprite');
            this.bullet4.setDisplaySize(9, 33);
        } else {
            console.warn('Sprite not found: laserGreen.png, using colored rectangle');
            this.bullet4 = this.add.rectangle(0, 0, 9, 33, 0xff00);
        }
        this.bullet4.active = 0;
        this.bullet4.setVisible(false);

        // Bullet5 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('bullet5_sprite')) {
            this.bullet5 = this.add.image(0, 0, 'bullet5_sprite');
            this.bullet5.setDisplaySize(9, 33);
        } else {
            console.warn('Sprite not found: laserGreen.png, using colored rectangle');
            this.bullet5 = this.add.rectangle(0, 0, 9, 33, 0xff00);
        }
        this.bullet5.active = 0;
        this.bullet5.setVisible(false);

        // Enemy1 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('enemy1_sprite')) {
            this.enemy1 = this.add.image(100, -50, 'enemy1_sprite');
            this.enemy1.setDisplaySize(40, 40);
        } else {
            console.warn('Sprite not found: enemyShip.png, using colored rectangle');
            this.enemy1 = this.add.rectangle(100, -50, 40, 40, 0xff0000);
        }
        this.enemy1.active = 0;
        this.enemy1.speed = 2;
        this.enemy1.setVisible(false);

        // Enemy2 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('enemy2_sprite')) {
            this.enemy2 = this.add.image(300, -50, 'enemy2_sprite');
            this.enemy2.setDisplaySize(40, 40);
        } else {
            console.warn('Sprite not found: enemyShip.png, using colored rectangle');
            this.enemy2 = this.add.rectangle(300, -50, 40, 40, 0xff0000);
        }
        this.enemy2.active = 0;
        this.enemy2.speed = 2;
        this.enemy2.setVisible(false);

        // Enemy3 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('enemy3_sprite')) {
            this.enemy3 = this.add.image(500, -50, 'enemy3_sprite');
            this.enemy3.setDisplaySize(40, 40);
        } else {
            console.warn('Sprite not found: enemyShip.png, using colored rectangle');
            this.enemy3 = this.add.rectangle(500, -50, 40, 40, 0xff0000);
        }
        this.enemy3.active = 0;
        this.enemy3.speed = 2;
        this.enemy3.setVisible(false);

        // Enemy4 object
        // Try to load sprite, fallback to rectangle if missing
        if (this.textures.exists('enemy4_sprite')) {
            this.enemy4 = this.add.image(700, -50, 'enemy4_sprite');
            this.enemy4.setDisplaySize(40, 40);
        } else {
            console.warn('Sprite not found: enemyShip.png, using colored rectangle');
            this.enemy4 = this.add.rectangle(700, -50, 40, 40, 0xff0000);
        }
        this.enemy4.active = 0;
        this.enemy4.speed = 2;
        this.enemy4.setVisible(false);

        // Score_text object
        this.score_text = this.add.text(70, 30, 'Score: 0', { fontFamily: 'Arial', fontSize: '20px', color: 'white', align: 'center' });
        this.score_text.setOrigin(0.5, 0.5);
        this.score_text.setVisible(false);
        this.score_text.textContent = 'Score: 0';
        this.score_text.font_size = 20;

        // Lives_text object
        this.lives_text = this.add.text(730, 30, 'Lives: 3', { fontFamily: 'Arial', fontSize: '20px', color: 'green', align: 'center' });
        this.lives_text.setOrigin(0.5, 0.5);
        this.lives_text.setVisible(false);
        this.lives_text.textContent = 'Lives: 3';
        this.lives_text.font_size = 20;

        // Game_over_text object
        this.game_over_text = this.add.text(400, 270, 'GAME OVER', { fontFamily: 'Arial', fontSize: '48px', color: 'red', align: 'center' });
        this.game_over_text.setOrigin(0.5, 0.5);
        this.game_over_text.setVisible(false);
        this.game_over_text.textContent = 'GAME OVER';
        this.game_over_text.font_size = 48;

        // Final_score_text object
        this.final_score_text = this.add.text(400, 360, 'Final Score: 0', { fontFamily: 'Arial', fontSize: '24px', color: 'white', align: 'center' });
        this.final_score_text.setOrigin(0.5, 0.5);
        this.final_score_text.setVisible(false);
        this.final_score_text.textContent = 'Final Score: 0';
        this.final_score_text.font_size = 24;

        // Restart_text object
        this.restart_text = this.add.text(400, 450, 'Press R to restart', { fontFamily: 'Arial', fontSize: '20px', color: 'yellow', align: 'center' });
        this.restart_text.setOrigin(0.5, 0.5);
        this.restart_text.setVisible(false);
        this.restart_text.textContent = 'Press R to restart';
        this.restart_text.font_size = 20;

        // State object
        this.state = this.add.rectangle(0, 0, 1, 1, 0xff0000);
        this.state.level = 0;
        this.state.score = 0;
        this.state.lives = 3;
        this.state.spawn_timer = 0;
        this.state.next_bullet = 1;
        this.state.setVisible(false);


        // Event handler registrations
        this.registerEventHandler('space_pressed', (params) => {
            if ((this.state.level === 0)) {
                this.start_game();
            }
            if ((this.state.level > 0)) {
                this.fire_bullet();
            }
        });

        this.registerEventHandler('while_key_left', (params) => {
            if ((this.state.level > 0)) {
                if ((this.player.x > 30)) {
                    this.player.x = (this.player.x - 5);
                }
            }
        });

        this.registerEventHandler('while_key_right', (params) => {
            if ((this.state.level > 0)) {
                if ((this.player.x < 770)) {
                    this.player.x = (this.player.x + 5);
                }
            }
        });

        this.registerEventHandler('key_r', (params) => {
            if ((this.state.level === 0)) {
                if ((this.game_over_text.visible === true)) {
                    this.restart_game();
                }
            }
        });

        this.registerEventHandler('update', (params) => {
            if ((this.state.level > 0)) {
                if ((this.bullet1.active === 1)) {
                    this.bullet1.y = (this.bullet1.y - 10);
                    if ((this.bullet1.y < 0)) {
                        this.bullet1.active = 0;
                        this.bullet1.setVisible(false);
                    }
                }
                if ((this.bullet2.active === 1)) {
                    this.bullet2.y = (this.bullet2.y - 10);
                    if ((this.bullet2.y < 0)) {
                        this.bullet2.active = 0;
                        this.bullet2.setVisible(false);
                    }
                }
                if ((this.bullet3.active === 1)) {
                    this.bullet3.y = (this.bullet3.y - 10);
                    if ((this.bullet3.y < 0)) {
                        this.bullet3.active = 0;
                        this.bullet3.setVisible(false);
                    }
                }
                if ((this.bullet4.active === 1)) {
                    this.bullet4.y = (this.bullet4.y - 10);
                    if ((this.bullet4.y < 0)) {
                        this.bullet4.active = 0;
                        this.bullet4.setVisible(false);
                    }
                }
                if ((this.bullet5.active === 1)) {
                    this.bullet5.y = (this.bullet5.y - 10);
                    if ((this.bullet5.y < 0)) {
                        this.bullet5.active = 0;
                        this.bullet5.setVisible(false);
                    }
                }
                if ((this.enemy1.active === 1)) {
                    this.enemy1.y = (this.enemy1.y + 2);
                    if ((this.enemy1.y > 650)) {
                        this.enemy1.y = (-50);
                    }
                }
                if ((this.enemy2.active === 1)) {
                    this.enemy2.y = (this.enemy2.y + 2);
                    if ((this.enemy2.y > 650)) {
                        this.enemy2.y = (-50);
                    }
                }
                if ((this.enemy3.active === 1)) {
                    this.enemy3.y = (this.enemy3.y + 2);
                    if ((this.enemy3.y > 650)) {
                        this.enemy3.y = (-50);
                    }
                }
                if ((this.enemy4.active === 1)) {
                    this.enemy4.y = (this.enemy4.y + 2);
                    if ((this.enemy4.y > 650)) {
                        this.enemy4.y = (-50);
                    }
                }
                if ((this.bullet1.active === 1)) {
                    if ((this.enemy1.active === 1)) {
                        if ((this.bullet1.x > (this.enemy1.x - 20))) {
                            if ((this.bullet1.x < (this.enemy1.x + 20))) {
                                if ((this.bullet1.y > (this.enemy1.y - 20))) {
                                    if ((this.bullet1.y < (this.enemy1.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy1.y = (-50);
                                        this.bullet1.active = 0;
                                        this.bullet1.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy2.active === 1)) {
                        if ((this.bullet1.x > (this.enemy2.x - 20))) {
                            if ((this.bullet1.x < (this.enemy2.x + 20))) {
                                if ((this.bullet1.y > (this.enemy2.y - 20))) {
                                    if ((this.bullet1.y < (this.enemy2.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy2.y = (-50);
                                        this.bullet1.active = 0;
                                        this.bullet1.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy3.active === 1)) {
                        if ((this.bullet1.x > (this.enemy3.x - 20))) {
                            if ((this.bullet1.x < (this.enemy3.x + 20))) {
                                if ((this.bullet1.y > (this.enemy3.y - 20))) {
                                    if ((this.bullet1.y < (this.enemy3.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy3.y = (-50);
                                        this.bullet1.active = 0;
                                        this.bullet1.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy4.active === 1)) {
                        if ((this.bullet1.x > (this.enemy4.x - 20))) {
                            if ((this.bullet1.x < (this.enemy4.x + 20))) {
                                if ((this.bullet1.y > (this.enemy4.y - 20))) {
                                    if ((this.bullet1.y < (this.enemy4.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy4.y = (-50);
                                        this.bullet1.active = 0;
                                        this.bullet1.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                }
                if ((this.bullet2.active === 1)) {
                    if ((this.enemy1.active === 1)) {
                        if ((this.bullet2.x > (this.enemy1.x - 20))) {
                            if ((this.bullet2.x < (this.enemy1.x + 20))) {
                                if ((this.bullet2.y > (this.enemy1.y - 20))) {
                                    if ((this.bullet2.y < (this.enemy1.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy1.y = (-50);
                                        this.bullet2.active = 0;
                                        this.bullet2.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy2.active === 1)) {
                        if ((this.bullet2.x > (this.enemy2.x - 20))) {
                            if ((this.bullet2.x < (this.enemy2.x + 20))) {
                                if ((this.bullet2.y > (this.enemy2.y - 20))) {
                                    if ((this.bullet2.y < (this.enemy2.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy2.y = (-50);
                                        this.bullet2.active = 0;
                                        this.bullet2.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy3.active === 1)) {
                        if ((this.bullet2.x > (this.enemy3.x - 20))) {
                            if ((this.bullet2.x < (this.enemy3.x + 20))) {
                                if ((this.bullet2.y > (this.enemy3.y - 20))) {
                                    if ((this.bullet2.y < (this.enemy3.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy3.y = (-50);
                                        this.bullet2.active = 0;
                                        this.bullet2.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy4.active === 1)) {
                        if ((this.bullet2.x > (this.enemy4.x - 20))) {
                            if ((this.bullet2.x < (this.enemy4.x + 20))) {
                                if ((this.bullet2.y > (this.enemy4.y - 20))) {
                                    if ((this.bullet2.y < (this.enemy4.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy4.y = (-50);
                                        this.bullet2.active = 0;
                                        this.bullet2.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                }
                if ((this.bullet3.active === 1)) {
                    if ((this.enemy1.active === 1)) {
                        if ((this.bullet3.x > (this.enemy1.x - 20))) {
                            if ((this.bullet3.x < (this.enemy1.x + 20))) {
                                if ((this.bullet3.y > (this.enemy1.y - 20))) {
                                    if ((this.bullet3.y < (this.enemy1.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy1.y = (-50);
                                        this.bullet3.active = 0;
                                        this.bullet3.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy2.active === 1)) {
                        if ((this.bullet3.x > (this.enemy2.x - 20))) {
                            if ((this.bullet3.x < (this.enemy2.x + 20))) {
                                if ((this.bullet3.y > (this.enemy2.y - 20))) {
                                    if ((this.bullet3.y < (this.enemy2.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy2.y = (-50);
                                        this.bullet3.active = 0;
                                        this.bullet3.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy3.active === 1)) {
                        if ((this.bullet3.x > (this.enemy3.x - 20))) {
                            if ((this.bullet3.x < (this.enemy3.x + 20))) {
                                if ((this.bullet3.y > (this.enemy3.y - 20))) {
                                    if ((this.bullet3.y < (this.enemy3.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy3.y = (-50);
                                        this.bullet3.active = 0;
                                        this.bullet3.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy4.active === 1)) {
                        if ((this.bullet3.x > (this.enemy4.x - 20))) {
                            if ((this.bullet3.x < (this.enemy4.x + 20))) {
                                if ((this.bullet3.y > (this.enemy4.y - 20))) {
                                    if ((this.bullet3.y < (this.enemy4.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy4.y = (-50);
                                        this.bullet3.active = 0;
                                        this.bullet3.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                }
                if ((this.bullet4.active === 1)) {
                    if ((this.enemy1.active === 1)) {
                        if ((this.bullet4.x > (this.enemy1.x - 20))) {
                            if ((this.bullet4.x < (this.enemy1.x + 20))) {
                                if ((this.bullet4.y > (this.enemy1.y - 20))) {
                                    if ((this.bullet4.y < (this.enemy1.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy1.y = (-50);
                                        this.bullet4.active = 0;
                                        this.bullet4.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy2.active === 1)) {
                        if ((this.bullet4.x > (this.enemy2.x - 20))) {
                            if ((this.bullet4.x < (this.enemy2.x + 20))) {
                                if ((this.bullet4.y > (this.enemy2.y - 20))) {
                                    if ((this.bullet4.y < (this.enemy2.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy2.y = (-50);
                                        this.bullet4.active = 0;
                                        this.bullet4.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy3.active === 1)) {
                        if ((this.bullet4.x > (this.enemy3.x - 20))) {
                            if ((this.bullet4.x < (this.enemy3.x + 20))) {
                                if ((this.bullet4.y > (this.enemy3.y - 20))) {
                                    if ((this.bullet4.y < (this.enemy3.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy3.y = (-50);
                                        this.bullet4.active = 0;
                                        this.bullet4.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy4.active === 1)) {
                        if ((this.bullet4.x > (this.enemy4.x - 20))) {
                            if ((this.bullet4.x < (this.enemy4.x + 20))) {
                                if ((this.bullet4.y > (this.enemy4.y - 20))) {
                                    if ((this.bullet4.y < (this.enemy4.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy4.y = (-50);
                                        this.bullet4.active = 0;
                                        this.bullet4.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                }
                if ((this.bullet5.active === 1)) {
                    if ((this.enemy1.active === 1)) {
                        if ((this.bullet5.x > (this.enemy1.x - 20))) {
                            if ((this.bullet5.x < (this.enemy1.x + 20))) {
                                if ((this.bullet5.y > (this.enemy1.y - 20))) {
                                    if ((this.bullet5.y < (this.enemy1.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy1.y = (-50);
                                        this.bullet5.active = 0;
                                        this.bullet5.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy2.active === 1)) {
                        if ((this.bullet5.x > (this.enemy2.x - 20))) {
                            if ((this.bullet5.x < (this.enemy2.x + 20))) {
                                if ((this.bullet5.y > (this.enemy2.y - 20))) {
                                    if ((this.bullet5.y < (this.enemy2.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy2.y = (-50);
                                        this.bullet5.active = 0;
                                        this.bullet5.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy3.active === 1)) {
                        if ((this.bullet5.x > (this.enemy3.x - 20))) {
                            if ((this.bullet5.x < (this.enemy3.x + 20))) {
                                if ((this.bullet5.y > (this.enemy3.y - 20))) {
                                    if ((this.bullet5.y < (this.enemy3.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy3.y = (-50);
                                        this.bullet5.active = 0;
                                        this.bullet5.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                    if ((this.enemy4.active === 1)) {
                        if ((this.bullet5.x > (this.enemy4.x - 20))) {
                            if ((this.bullet5.x < (this.enemy4.x + 20))) {
                                if ((this.bullet5.y > (this.enemy4.y - 20))) {
                                    if ((this.bullet5.y < (this.enemy4.y + 20))) {
                                        this.sound.play('lose1_ogg');
                                        this.enemy4.y = (-50);
                                        this.bullet5.active = 0;
                                        this.bullet5.setVisible(false);
                                        this.state.score = (this.state.score + 10);
                                        this.update_score();
                                    }
                                }
                            }
                        }
                    }
                }
                if ((this.enemy1.active === 1)) {
                    if ((this.enemy1.y > (this.player.y - 25))) {
                        if ((this.enemy1.y < (this.player.y + 25))) {
                            if ((this.enemy1.x > (this.player.x - 30))) {
                                if ((this.enemy1.x < (this.player.x + 30))) {
                                    this.sound.play('lose3_ogg');
                                    this.enemy1.y = (-50);
                                    this.state.lives = (this.state.lives - 1);
                                    this.update_lives();
                                }
                            }
                        }
                    }
                }
                if ((this.enemy2.active === 1)) {
                    if ((this.enemy2.y > (this.player.y - 25))) {
                        if ((this.enemy2.y < (this.player.y + 25))) {
                            if ((this.enemy2.x > (this.player.x - 30))) {
                                if ((this.enemy2.x < (this.player.x + 30))) {
                                    this.sound.play('lose3_ogg');
                                    this.enemy2.y = (-50);
                                    this.state.lives = (this.state.lives - 1);
                                    this.update_lives();
                                }
                            }
                        }
                    }
                }
                if ((this.enemy3.active === 1)) {
                    if ((this.enemy3.y > (this.player.y - 25))) {
                        if ((this.enemy3.y < (this.player.y + 25))) {
                            if ((this.enemy3.x > (this.player.x - 30))) {
                                if ((this.enemy3.x < (this.player.x + 30))) {
                                    this.sound.play('lose3_ogg');
                                    this.enemy3.y = (-50);
                                    this.state.lives = (this.state.lives - 1);
                                    this.update_lives();
                                }
                            }
                        }
                    }
                }
                if ((this.enemy4.active === 1)) {
                    if ((this.enemy4.y > (this.player.y - 25))) {
                        if ((this.enemy4.y < (this.player.y + 25))) {
                            if ((this.enemy4.x > (this.player.x - 30))) {
                                if ((this.enemy4.x < (this.player.x + 30))) {
                                    this.sound.play('lose3_ogg');
                                    this.enemy4.y = (-50);
                                    this.state.lives = (this.state.lives - 1);
                                    this.update_lives();
                                }
                            }
                        }
                    }
                }
            }
        });

    }

    update() {
        this.triggerEvent('update', null);

        // Keyboard event detection
        if (this.cursors.left.isDown || this.cursors.right.isDown ||
            this.cursors.up.isDown || this.cursors.down.isDown) {
            this.triggerEvent('key_pressed', null);
        }

        if (Phaser.Input.Keyboard.JustDown(this.cursors.left)) {
            this.triggerEvent('key_left', null);
        }
        if (Phaser.Input.Keyboard.JustDown(this.cursors.right)) {
            this.triggerEvent('key_right', null);
        }
        if (Phaser.Input.Keyboard.JustDown(this.cursors.up)) {
            this.triggerEvent('key_up', null);
        }
        if (Phaser.Input.Keyboard.JustDown(this.cursors.down)) {
            this.triggerEvent('key_down', null);
        }

        if (this.cursors.left.isDown) {
            this.triggerEvent('while_key_left', null);
        }
        if (this.cursors.right.isDown) {
            this.triggerEvent('while_key_right', null);
        }
        if (this.cursors.up.isDown) {
            this.triggerEvent('while_key_up', null);
        }
        if (this.cursors.down.isDown) {
            this.triggerEvent('while_key_down', null);
        }

        if (Phaser.Input.Keyboard.JustDown(this.keys.space)) {
            this.triggerEvent('space_pressed', null);
        }
        if (Phaser.Input.Keyboard.JustDown(this.keys.r)) {
            this.triggerEvent('key_r', null);
        }

    }

    // Event system helpers
    registerEventHandler(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }
        this.eventHandlers[eventName].push(handler);
    }

    triggerEvent(eventName, params) {
        if (this.eventHandlers[eventName]) {
            this.eventHandlers[eventName].forEach(handler => handler(params || null));
        }
    }

    start_game() {
        this.title.setVisible(false);
        this.instructions.setVisible(false);
        this.start_text.setVisible(false);
        this.player.setVisible(true);
        this.score_text.setVisible(true);
        this.lives_text.setVisible(true);
        this.state.level = 1;
        this.state.score = 0;
        this.state.lives = 3;
        this.state.spawn_timer = 0;
        this.player.x = 400;
        this.score_text.setText("Score: 0");
        this.lives_text.setText("Lives: 3");
        this.spawn_enemy_wave();
    }

    spawn_enemy_wave() {
        this.enemy1.x = 100;
        this.enemy1.y = (-50);
        this.enemy1.active = 1;
        this.enemy1.setVisible(true);
        this.enemy2.x = 300;
        this.enemy2.y = (-100);
        this.enemy2.active = 1;
        this.enemy2.setVisible(true);
        this.enemy3.x = 500;
        this.enemy3.y = (-150);
        this.enemy3.active = 1;
        this.enemy3.setVisible(true);
        this.enemy4.x = 700;
        this.enemy4.y = (-200);
        this.enemy4.active = 1;
        this.enemy4.setVisible(true);
    }

    fire_bullet() {
        this.sound.play('laser1_ogg');
        if ((this.state.next_bullet === 1)) {
            if ((this.bullet1.active === 0)) {
                this.bullet1.x = this.player.x;
                this.bullet1.y = (this.player.y - 30);
                this.bullet1.active = 1;
                this.bullet1.setVisible(true);
            }
            this.state.next_bullet = 2;
        }
        if ((this.state.next_bullet === 2)) {
            if ((this.bullet2.active === 0)) {
                this.bullet2.x = this.player.x;
                this.bullet2.y = (this.player.y - 30);
                this.bullet2.active = 1;
                this.bullet2.setVisible(true);
            }
            this.state.next_bullet = 3;
        }
        if ((this.state.next_bullet === 3)) {
            if ((this.bullet3.active === 0)) {
                this.bullet3.x = this.player.x;
                this.bullet3.y = (this.player.y - 30);
                this.bullet3.active = 1;
                this.bullet3.setVisible(true);
            }
            this.state.next_bullet = 4;
        }
        if ((this.state.next_bullet === 4)) {
            if ((this.bullet4.active === 0)) {
                this.bullet4.x = this.player.x;
                this.bullet4.y = (this.player.y - 30);
                this.bullet4.active = 1;
                this.bullet4.setVisible(true);
            }
            this.state.next_bullet = 5;
        }
        if ((this.state.next_bullet === 5)) {
            if ((this.bullet5.active === 0)) {
                this.bullet5.x = this.player.x;
                this.bullet5.y = (this.player.y - 30);
                this.bullet5.active = 1;
                this.bullet5.setVisible(true);
            }
            this.state.next_bullet = 1;
        }
    }

    update_score() {
        this.score_text.setText(`Score: ${this.state.score}`);
    }

    update_lives() {
        this.lives_text.setText(`Lives: ${this.state.lives}`);
        if ((this.state.lives === 0)) {
            this.game_over();
        }
    }

    game_over() {
        this.state.level = 0;
        this.player.setVisible(false);
        this.score_text.setVisible(false);
        this.lives_text.setVisible(false);
        this.bullet1.setVisible(false);
        this.bullet2.setVisible(false);
        this.bullet3.setVisible(false);
        this.bullet4.setVisible(false);
        this.bullet5.setVisible(false);
        this.enemy1.setVisible(false);
        this.enemy2.setVisible(false);
        this.enemy3.setVisible(false);
        this.enemy4.setVisible(false);
        this.game_over_text.setVisible(true);
        this.final_score_text.setText(`Final Score: ${this.state.score}`);
        this.final_score_text.setVisible(true);
        this.restart_text.setVisible(true);
    }

    restart_game() {
        this.game_over_text.setVisible(false);
        this.final_score_text.setVisible(false);
        this.restart_text.setVisible(false);
        this.bullet1.active = 0;
        this.bullet2.active = 0;
        this.bullet3.active = 0;
        this.bullet4.active = 0;
        this.bullet5.active = 0;
        this.enemy1.active = 0;
        this.enemy2.active = 0;
        this.enemy3.active = 0;
        this.enemy4.active = 0;
        this.start_game();
    }
}

// Phaser game configuration
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    backgroundColor: '#2d2d2d',
    scene: GameScene
};

// Create and start the game
const game = new Phaser.Game(config);