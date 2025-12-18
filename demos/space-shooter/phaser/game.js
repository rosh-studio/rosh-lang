// Auto-generated from Rosh IR
// Emitter: Phaser 3 v0.2.0

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.eventHandlers = {};
    }

    preload() {
        this.load.image('enemyShip_png', 'assets/enemyShip.png');
        this.load.image('laserGreen_png', 'assets/laserGreen.png');
        this.load.image('player_png', 'assets/player.png');
        this.load.audio('laser1_ogg', 'assets/laser1.ogg');
        this.load.audio('lose1_ogg', 'assets/lose1.ogg');
        this.load.audio('lose3_ogg', 'assets/lose3.ogg');
    }

    create() {
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = this.input.keyboard.addKeys('W,A,S,D,SPACE,R');

        this.title = this.add.text(400.0, 150.0, 'Space Shooter', { fontSize: '48px', fill: '#00ffff' });
        this.title.setOrigin(0.5, 0.5);
        this.title.font_size = 48;

        this.instructions = this.add.text(400.0, 270.0, 'Arrow keys to move, SPACE to fire', { fontSize: '18px', fill: '#ffffff' });
        this.instructions.setOrigin(0.5, 0.5);
        this.instructions.font_size = 18;

        this.start_text = this.add.text(400.0, 420.0, 'Press SPACE to start', { fontSize: '20px', fill: '#ffff00' });
        this.start_text.setOrigin(0.5, 0.5);
        this.start_text.font_size = 20;

        this.player = this.add.sprite(400.0, 540.0, 'player_png');
        this.player.setDisplaySize(50.0, 50.0);
        this.player.visible = false;
        this.player.speed = 8;

        this.bullet1 = this.add.sprite(0.0, 0.0, 'laserGreen_png');
        this.bullet1.setDisplaySize(9.0, 33.0);
        this.bullet1.visible = false;
        this.bullet1.active = 0;

        this.bullet2 = this.add.sprite(0.0, 0.0, 'laserGreen_png');
        this.bullet2.setDisplaySize(9.0, 33.0);
        this.bullet2.visible = false;
        this.bullet2.active = 0;

        this.bullet3 = this.add.sprite(0.0, 0.0, 'laserGreen_png');
        this.bullet3.setDisplaySize(9.0, 33.0);
        this.bullet3.visible = false;
        this.bullet3.active = 0;

        this.bullet4 = this.add.sprite(0.0, 0.0, 'laserGreen_png');
        this.bullet4.setDisplaySize(9.0, 33.0);
        this.bullet4.visible = false;
        this.bullet4.active = 0;

        this.bullet5 = this.add.sprite(0.0, 0.0, 'laserGreen_png');
        this.bullet5.setDisplaySize(9.0, 33.0);
        this.bullet5.visible = false;
        this.bullet5.active = 0;

        this.enemy1 = this.add.sprite(100.0, 300.0, 'enemyShip_png');
        this.enemy1.setDisplaySize(40.0, 40.0);
        this.enemy1.visible = false;
        this.enemy1.active = 0;
        this.enemy1.speed = 2;

        this.enemy2 = this.add.sprite(300.0, 300.0, 'enemyShip_png');
        this.enemy2.setDisplaySize(40.0, 40.0);
        this.enemy2.visible = false;
        this.enemy2.active = 0;
        this.enemy2.speed = 2;

        this.enemy3 = this.add.sprite(500.0, 300.0, 'enemyShip_png');
        this.enemy3.setDisplaySize(40.0, 40.0);
        this.enemy3.visible = false;
        this.enemy3.active = 0;
        this.enemy3.speed = 2;

        this.enemy4 = this.add.sprite(700.0, 300.0, 'enemyShip_png');
        this.enemy4.setDisplaySize(40.0, 40.0);
        this.enemy4.visible = false;
        this.enemy4.active = 0;
        this.enemy4.speed = 2;

        this.score_text = this.add.text(70.0, 30.0, 'Score: 0', { fontSize: '20px', fill: '#ffffff' });
        this.score_text.setOrigin(0.5, 0.5);
        this.score_text.font_size = 20;
        this.score_text.visible = false;

        this.lives_text = this.add.text(730.0, 30.0, 'Lives: 3', { fontSize: '20px', fill: '#00ff00' });
        this.lives_text.setOrigin(0.5, 0.5);
        this.lives_text.font_size = 20;
        this.lives_text.visible = false;

        this.game_over_text = this.add.text(400.0, 270.0, 'GAME OVER', { fontSize: '48px', fill: '#ff0000' });
        this.game_over_text.setOrigin(0.5, 0.5);
        this.game_over_text.font_size = 48;
        this.game_over_text.visible = false;

        this.final_score_text = this.add.text(400.0, 360.0, 'Final Score: 0', { fontSize: '24px', fill: '#ffffff' });
        this.final_score_text.setOrigin(0.5, 0.5);
        this.final_score_text.font_size = 24;
        this.final_score_text.visible = false;

        this.restart_text = this.add.text(400.0, 450.0, 'Press R to restart', { fontSize: '20px', fill: '#ffff00' });
        this.restart_text.setOrigin(0.5, 0.5);
        this.restart_text.font_size = 20;
        this.restart_text.visible = false;

        this.state = this.add.rectangle(0.0, 0.0, 1.0, 1.0, 0x00ff00);
        this.state.visible = false;
        this.state.level = 0;
        this.state.score = 0;
        this.state.lives = 3;
        this.state.spawn_timer = 0;
        this.state.next_bullet = 1;

        this.input.keyboard.on('keydown-SPACE', () => { if (this.state.level == 0) { this.start_game(); } if (this.state.level > 0) { this.fire_bullet(); } });
        this.input.keyboard.on('keydown-R', () => { if (this.state.level == 0) { if (this.game_over_text.visible == true) { this.restart_game(); } } });
        this.registerEvent('update', function() { if (this.state.level > 0) { if (this.bullet1.active == 1) { this.bullet1.y = (this.bullet1.y - 10); if (this.bullet1.y < 0) { this.bullet1.active = 0; this.bullet1.visible = false; } } if (this.bullet2.active == 1) { this.bullet2.y = (this.bullet2.y - 10); if (this.bullet2.y < 0) { this.bullet2.active = 0; this.bullet2.visible = false; } } if (this.bullet3.active == 1) { this.bullet3.y = (this.bullet3.y - 10); if (this.bullet3.y < 0) { this.bullet3.active = 0; this.bullet3.visible = false; } } if (this.bullet4.active == 1) { this.bullet4.y = (this.bullet4.y - 10); if (this.bullet4.y < 0) { this.bullet4.active = 0; this.bullet4.visible = false; } } if (this.bullet5.active == 1) { this.bullet5.y = (this.bullet5.y - 10); if (this.bullet5.y < 0) { this.bullet5.active = 0; this.bullet5.visible = false; } } if (this.enemy1.active == 1) { this.enemy1.y = (this.enemy1.y + 2); if (this.enemy1.y > 650) { this.enemy1.y = -50; } } if (this.enemy2.active == 1) { this.enemy2.y = (this.enemy2.y + 2); if (this.enemy2.y > 650) { this.enemy2.y = -50; } } if (this.enemy3.active == 1) { this.enemy3.y = (this.enemy3.y + 2); if (this.enemy3.y > 650) { this.enemy3.y = -50; } } if (this.enemy4.active == 1) { this.enemy4.y = (this.enemy4.y + 2); if (this.enemy4.y > 650) { this.enemy4.y = -50; } } if (this.bullet1.active == 1) { if (this.enemy1.active == 1) { if (this.bullet1.x > (this.enemy1.x - 20)) { if (this.bullet1.x < (this.enemy1.x + 20)) { if (this.bullet1.y > (this.enemy1.y - 20)) { if (this.bullet1.y < (this.enemy1.y + 20)) { this.sound.play('lose1_ogg'); this.enemy1.y = -50; this.bullet1.active = 0; this.bullet1.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy2.active == 1) { if (this.bullet1.x > (this.enemy2.x - 20)) { if (this.bullet1.x < (this.enemy2.x + 20)) { if (this.bullet1.y > (this.enemy2.y - 20)) { if (this.bullet1.y < (this.enemy2.y + 20)) { this.sound.play('lose1_ogg'); this.enemy2.y = -50; this.bullet1.active = 0; this.bullet1.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy3.active == 1) { if (this.bullet1.x > (this.enemy3.x - 20)) { if (this.bullet1.x < (this.enemy3.x + 20)) { if (this.bullet1.y > (this.enemy3.y - 20)) { if (this.bullet1.y < (this.enemy3.y + 20)) { this.sound.play('lose1_ogg'); this.enemy3.y = -50; this.bullet1.active = 0; this.bullet1.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy4.active == 1) { if (this.bullet1.x > (this.enemy4.x - 20)) { if (this.bullet1.x < (this.enemy4.x + 20)) { if (this.bullet1.y > (this.enemy4.y - 20)) { if (this.bullet1.y < (this.enemy4.y + 20)) { this.sound.play('lose1_ogg'); this.enemy4.y = -50; this.bullet1.active = 0; this.bullet1.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } } if (this.bullet2.active == 1) { if (this.enemy1.active == 1) { if (this.bullet2.x > (this.enemy1.x - 20)) { if (this.bullet2.x < (this.enemy1.x + 20)) { if (this.bullet2.y > (this.enemy1.y - 20)) { if (this.bullet2.y < (this.enemy1.y + 20)) { this.sound.play('lose1_ogg'); this.enemy1.y = -50; this.bullet2.active = 0; this.bullet2.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy2.active == 1) { if (this.bullet2.x > (this.enemy2.x - 20)) { if (this.bullet2.x < (this.enemy2.x + 20)) { if (this.bullet2.y > (this.enemy2.y - 20)) { if (this.bullet2.y < (this.enemy2.y + 20)) { this.sound.play('lose1_ogg'); this.enemy2.y = -50; this.bullet2.active = 0; this.bullet2.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy3.active == 1) { if (this.bullet2.x > (this.enemy3.x - 20)) { if (this.bullet2.x < (this.enemy3.x + 20)) { if (this.bullet2.y > (this.enemy3.y - 20)) { if (this.bullet2.y < (this.enemy3.y + 20)) { this.sound.play('lose1_ogg'); this.enemy3.y = -50; this.bullet2.active = 0; this.bullet2.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy4.active == 1) { if (this.bullet2.x > (this.enemy4.x - 20)) { if (this.bullet2.x < (this.enemy4.x + 20)) { if (this.bullet2.y > (this.enemy4.y - 20)) { if (this.bullet2.y < (this.enemy4.y + 20)) { this.sound.play('lose1_ogg'); this.enemy4.y = -50; this.bullet2.active = 0; this.bullet2.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } } if (this.bullet3.active == 1) { if (this.enemy1.active == 1) { if (this.bullet3.x > (this.enemy1.x - 20)) { if (this.bullet3.x < (this.enemy1.x + 20)) { if (this.bullet3.y > (this.enemy1.y - 20)) { if (this.bullet3.y < (this.enemy1.y + 20)) { this.sound.play('lose1_ogg'); this.enemy1.y = -50; this.bullet3.active = 0; this.bullet3.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy2.active == 1) { if (this.bullet3.x > (this.enemy2.x - 20)) { if (this.bullet3.x < (this.enemy2.x + 20)) { if (this.bullet3.y > (this.enemy2.y - 20)) { if (this.bullet3.y < (this.enemy2.y + 20)) { this.sound.play('lose1_ogg'); this.enemy2.y = -50; this.bullet3.active = 0; this.bullet3.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy3.active == 1) { if (this.bullet3.x > (this.enemy3.x - 20)) { if (this.bullet3.x < (this.enemy3.x + 20)) { if (this.bullet3.y > (this.enemy3.y - 20)) { if (this.bullet3.y < (this.enemy3.y + 20)) { this.sound.play('lose1_ogg'); this.enemy3.y = -50; this.bullet3.active = 0; this.bullet3.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy4.active == 1) { if (this.bullet3.x > (this.enemy4.x - 20)) { if (this.bullet3.x < (this.enemy4.x + 20)) { if (this.bullet3.y > (this.enemy4.y - 20)) { if (this.bullet3.y < (this.enemy4.y + 20)) { this.sound.play('lose1_ogg'); this.enemy4.y = -50; this.bullet3.active = 0; this.bullet3.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } } if (this.bullet4.active == 1) { if (this.enemy1.active == 1) { if (this.bullet4.x > (this.enemy1.x - 20)) { if (this.bullet4.x < (this.enemy1.x + 20)) { if (this.bullet4.y > (this.enemy1.y - 20)) { if (this.bullet4.y < (this.enemy1.y + 20)) { this.sound.play('lose1_ogg'); this.enemy1.y = -50; this.bullet4.active = 0; this.bullet4.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy2.active == 1) { if (this.bullet4.x > (this.enemy2.x - 20)) { if (this.bullet4.x < (this.enemy2.x + 20)) { if (this.bullet4.y > (this.enemy2.y - 20)) { if (this.bullet4.y < (this.enemy2.y + 20)) { this.sound.play('lose1_ogg'); this.enemy2.y = -50; this.bullet4.active = 0; this.bullet4.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy3.active == 1) { if (this.bullet4.x > (this.enemy3.x - 20)) { if (this.bullet4.x < (this.enemy3.x + 20)) { if (this.bullet4.y > (this.enemy3.y - 20)) { if (this.bullet4.y < (this.enemy3.y + 20)) { this.sound.play('lose1_ogg'); this.enemy3.y = -50; this.bullet4.active = 0; this.bullet4.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy4.active == 1) { if (this.bullet4.x > (this.enemy4.x - 20)) { if (this.bullet4.x < (this.enemy4.x + 20)) { if (this.bullet4.y > (this.enemy4.y - 20)) { if (this.bullet4.y < (this.enemy4.y + 20)) { this.sound.play('lose1_ogg'); this.enemy4.y = -50; this.bullet4.active = 0; this.bullet4.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } } if (this.bullet5.active == 1) { if (this.enemy1.active == 1) { if (this.bullet5.x > (this.enemy1.x - 20)) { if (this.bullet5.x < (this.enemy1.x + 20)) { if (this.bullet5.y > (this.enemy1.y - 20)) { if (this.bullet5.y < (this.enemy1.y + 20)) { this.sound.play('lose1_ogg'); this.enemy1.y = -50; this.bullet5.active = 0; this.bullet5.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy2.active == 1) { if (this.bullet5.x > (this.enemy2.x - 20)) { if (this.bullet5.x < (this.enemy2.x + 20)) { if (this.bullet5.y > (this.enemy2.y - 20)) { if (this.bullet5.y < (this.enemy2.y + 20)) { this.sound.play('lose1_ogg'); this.enemy2.y = -50; this.bullet5.active = 0; this.bullet5.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy3.active == 1) { if (this.bullet5.x > (this.enemy3.x - 20)) { if (this.bullet5.x < (this.enemy3.x + 20)) { if (this.bullet5.y > (this.enemy3.y - 20)) { if (this.bullet5.y < (this.enemy3.y + 20)) { this.sound.play('lose1_ogg'); this.enemy3.y = -50; this.bullet5.active = 0; this.bullet5.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } if (this.enemy4.active == 1) { if (this.bullet5.x > (this.enemy4.x - 20)) { if (this.bullet5.x < (this.enemy4.x + 20)) { if (this.bullet5.y > (this.enemy4.y - 20)) { if (this.bullet5.y < (this.enemy4.y + 20)) { this.sound.play('lose1_ogg'); this.enemy4.y = -50; this.bullet5.active = 0; this.bullet5.visible = false; this.state.score = (this.state.score + 10); this.update_score(); } } } } } } if (this.enemy1.active == 1) { if (this.enemy1.y > (this.player.y - 25)) { if (this.enemy1.y < (this.player.y + 25)) { if (this.enemy1.x > (this.player.x - 30)) { if (this.enemy1.x < (this.player.x + 30)) { this.sound.play('lose3_ogg'); this.enemy1.y = -50; this.state.lives = (this.state.lives - 1); this.update_lives(); } } } } } if (this.enemy2.active == 1) { if (this.enemy2.y > (this.player.y - 25)) { if (this.enemy2.y < (this.player.y + 25)) { if (this.enemy2.x > (this.player.x - 30)) { if (this.enemy2.x < (this.player.x + 30)) { this.sound.play('lose3_ogg'); this.enemy2.y = -50; this.state.lives = (this.state.lives - 1); this.update_lives(); } } } } } if (this.enemy3.active == 1) { if (this.enemy3.y > (this.player.y - 25)) { if (this.enemy3.y < (this.player.y + 25)) { if (this.enemy3.x > (this.player.x - 30)) { if (this.enemy3.x < (this.player.x + 30)) { this.sound.play('lose3_ogg'); this.enemy3.y = -50; this.state.lives = (this.state.lives - 1); this.update_lives(); } } } } } if (this.enemy4.active == 1) { if (this.enemy4.y > (this.player.y - 25)) { if (this.enemy4.y < (this.player.y + 25)) { if (this.enemy4.x > (this.player.x - 30)) { if (this.enemy4.x < (this.player.x + 30)) { this.sound.play('lose3_ogg'); this.enemy4.y = -50; this.state.lives = (this.state.lives - 1); this.update_lives(); } } } } } } });

    }

    update() {
        this.triggerEvent('update');

        // Continuous key handlers
        if (this.cursors.left.isDown) { if (this.state.level > 0) { if (this.player.x > 30) { this.player.x = (this.player.x - 5); } } }
        if (this.cursors.right.isDown) { if (this.state.level > 0) { if (this.player.x < 770) { this.player.x = (this.player.x + 5); } } }
    }

    registerEvent(name, handler) {
        if (!this.eventHandlers[name]) {
            this.eventHandlers[name] = [];
        }
        this.eventHandlers[name].push(handler);
    }

    triggerEvent(name, ...args) {
        if (this.eventHandlers[name]) {
            for (const handler of this.eventHandlers[name]) {
                handler.call(this, ...args);
            }
        }
    }

    start_game() {
        this.title.visible = false;
        this.instructions.visible = false;
        this.start_text.visible = false;
        this.player.visible = true;
        this.score_text.visible = true;
        this.lives_text.visible = true;
        this.state.level = 1;
        this.state.score = 0;
        this.state.lives = 3;
        this.state.spawn_timer = 0;
        this.player.x = 400.0;
        this.score_text.text = `Score: 0`;
        this.lives_text.text = `Lives: 3`;
        this.spawn_enemy_wave();
    }

    spawn_enemy_wave() {
        this.enemy1.x = 100.0;
        this.enemy1.y = -50;
        this.enemy1.active = 1;
        this.enemy1.visible = true;
        this.enemy2.x = 300.0;
        this.enemy2.y = -100;
        this.enemy2.active = 1;
        this.enemy2.visible = true;
        this.enemy3.x = 500.0;
        this.enemy3.y = -150;
        this.enemy3.active = 1;
        this.enemy3.visible = true;
        this.enemy4.x = 700.0;
        this.enemy4.y = -200;
        this.enemy4.active = 1;
        this.enemy4.visible = true;
    }

    fire_bullet() {
        this.sound.play('laser1_ogg');
        if (this.state.next_bullet == 1) { if (this.bullet1.active == 0) { this.bullet1.x = this.player.x; this.bullet1.y = (this.player.y - 30); this.bullet1.active = 1; this.bullet1.visible = true; } this.state.next_bullet = 2; }
        if (this.state.next_bullet == 2) { if (this.bullet2.active == 0) { this.bullet2.x = this.player.x; this.bullet2.y = (this.player.y - 30); this.bullet2.active = 1; this.bullet2.visible = true; } this.state.next_bullet = 3; }
        if (this.state.next_bullet == 3) { if (this.bullet3.active == 0) { this.bullet3.x = this.player.x; this.bullet3.y = (this.player.y - 30); this.bullet3.active = 1; this.bullet3.visible = true; } this.state.next_bullet = 4; }
        if (this.state.next_bullet == 4) { if (this.bullet4.active == 0) { this.bullet4.x = this.player.x; this.bullet4.y = (this.player.y - 30); this.bullet4.active = 1; this.bullet4.visible = true; } this.state.next_bullet = 5; }
        if (this.state.next_bullet == 5) { if (this.bullet5.active == 0) { this.bullet5.x = this.player.x; this.bullet5.y = (this.player.y - 30); this.bullet5.active = 1; this.bullet5.visible = true; } this.state.next_bullet = 1; }
    }

    update_score() {
        this.score_text.text = `Score: ${this.state.score}`;
    }

    update_lives() {
        this.lives_text.text = `Lives: ${this.state.lives}`;
        if (this.state.lives == 0) { this.game_over(); }
    }

    game_over() {
        this.state.level = 0;
        this.player.visible = false;
        this.score_text.visible = false;
        this.lives_text.visible = false;
        this.bullet1.visible = false;
        this.bullet2.visible = false;
        this.bullet3.visible = false;
        this.bullet4.visible = false;
        this.bullet5.visible = false;
        this.enemy1.visible = false;
        this.enemy2.visible = false;
        this.enemy3.visible = false;
        this.enemy4.visible = false;
        this.game_over_text.visible = true;
        this.final_score_text.text = `Final Score: ${this.state.score}`;
        this.final_score_text.visible = true;
        this.restart_text.visible = true;
    }

    restart_game() {
        this.game_over_text.visible = false;
        this.final_score_text.visible = false;
        this.restart_text.visible = false;
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

const config = {
    type: Phaser.AUTO,
    parent: 'game-container',
    width: 800,
    height: 600,
    backgroundColor: '#1a1a2e',
    scene: GameScene
};

const game = new Phaser.Game(config);