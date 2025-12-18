// Auto-generated from Rosh IR
// Emitter: Phaser 3 v0.2.0

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.eventHandlers = {};
        this.currentScene = null;
        this.currentLevel = 1;
    }

    preload() {
        this.load.image('player_png', 'assets/player.png');
    }

    create() {
        this.cursors = this.input.keyboard.createCursorKeys();
        this.keys = this.input.keyboard.addKeys('W,A,S,D,SPACE,R');

        this.title = this.add.text(400.0, 150.0, 'Block Pusher', { fontSize: '48px', fill: '#ffffff' });
        this.title.setOrigin(0.5, 0.5);
        this.title.font_size = 48;

        this.subtitle = this.add.text(400.0, 228.0, 'A Sokoban Puzzle Game', { fontSize: '24px', fill: '#888888' });
        this.subtitle.setOrigin(0.5, 0.5);
        this.subtitle.font_size = 24;

        this.instructions = this.add.text(400.0, 330.0, 'Push all boxes onto the circles', { fontSize: '18px', fill: '#00ffff' });
        this.instructions.setOrigin(0.5, 0.5);
        this.instructions.font_size = 18;

        this.start_text = this.add.text(400.0, 480.0, 'Press SPACE to start', { fontSize: '20px', fill: '#ffff00' });
        this.start_text.setOrigin(0.5, 0.5);
        this.start_text.font_size = 20;

        this.player = this.add.sprite(275.0, 275.0, 'player_png');
        this.player.setDisplaySize(40.0, 40.0);
        this.player.visible = false;

        this.box1 = this.add.rectangle(375.0, 275.0, 40.0, 40.0, 0x00ff00);
        this.box1.visible = false;

        this.goal1 = this.add.rectangle(475.0, 275.0, 44.0, 44.0, 0x0000ff);
        this.goal1.shape = 'circle';
        this.goal1.visible = false;

        this.wall1 = this.add.rectangle(475.0, 325.0, 40.0, 40.0, 0xff0000);
        this.wall1.visible = false;

        this.level_text = this.add.text(400.0, 48.0, 'Level 1', { fontSize: '24px', fill: '#ffffff' });
        this.level_text.setOrigin(0.5, 0.5);
        this.level_text.font_size = 24;
        this.level_text.visible = false;

        this.moves_text = this.add.text(400.0, 552.0, 'Moves: 0', { fontSize: '16px', fill: '#888888' });
        this.moves_text.setOrigin(0.5, 0.5);
        this.moves_text.font_size = 16;
        this.moves_text.visible = false;

        this.win_text = this.add.text(400.0, 300.0, 'You Win!', { fontSize: '64px', fill: '#ffd700' });
        this.win_text.setOrigin(0.5, 0.5);
        this.win_text.font_size = 64;
        this.win_text.visible = false;

        this.next_level_text = this.add.text(400.0, 390.0, 'Press SPACE for next level', { fontSize: '20px', fill: '#ffff00' });
        this.next_level_text.setOrigin(0.5, 0.5);
        this.next_level_text.font_size = 20;
        this.next_level_text.visible = false;

        this.state = this.add.rectangle(0.0, 0.0, 1.0, 1.0, 0xffff00);
        this.state.moves = 0;
        this.state.can_move = 1;
        this.state.visible = false;

        this.input.keyboard.on('keydown-SPACE', () => { if (this.state.level == 0) { this.title.visible = false; this.subtitle.visible = false; this.instructions.visible = false; this.start_text.visible = false; this.player.visible = true; this.box1.visible = true; this.goal1.visible = true; this.level_text.visible = true; this.moves_text.visible = true; this.start_level_1(); } });
        this.input.keyboard.on('keydown-SPACE', () => { if (this.state.level == 1) { if (this.win_text.visible == true) { this.start_level_2(); } } });
        this.input.keyboard.on('keydown-LEFT', () => { if (this.state.level > 0) { if (this.state.level < 3) { if (this.win_text.visible == false) { if (this.player.x > 250) { this.state.can_move = 1; if ((this.player.x - 50) == this.wall1.x) { if (this.player.y == this.wall1.y) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.player.x == (this.box1.x + 50)) { if (this.player.y == this.box1.y) { this.state.can_move = 1; if ((this.box1.x - 50) == this.wall1.x) { if (this.box1.y == this.wall1.y) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.box1.x > 250) { this.box1.x = (this.box1.x - 50); this.player.x = (this.player.x - 50); this.state.moves = (this.state.moves + 1); } } } else { this.player.x = (this.player.x - 50); this.state.moves = (this.state.moves + 1); } } else { this.player.x = (this.player.x - 50); this.state.moves = (this.state.moves + 1); } } } } } } });
        this.input.keyboard.on('keydown-RIGHT', () => { if (this.state.level > 0) { if (this.state.level < 3) { if (this.win_text.visible == false) { if (this.player.x < 550) { this.state.can_move = 1; if ((this.player.x + 50) == this.wall1.x) { if (this.player.y == this.wall1.y) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.player.x == (this.box1.x - 50)) { if (this.player.y == this.box1.y) { this.state.can_move = 1; if ((this.box1.x + 50) == this.wall1.x) { if (this.box1.y == this.wall1.y) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.box1.x < 550) { this.box1.x = (this.box1.x + 50); this.player.x = (this.player.x + 50); this.state.moves = (this.state.moves + 1); } } } else { this.player.x = (this.player.x + 50); this.state.moves = (this.state.moves + 1); } } else { this.player.x = (this.player.x + 50); this.state.moves = (this.state.moves + 1); } } } } } } });
        this.input.keyboard.on('keydown-UP', () => { if (this.state.level > 0) { if (this.state.level < 3) { if (this.win_text.visible == false) { if (this.player.y > 200) { this.state.can_move = 1; if ((this.player.y - 50) == this.wall1.y) { if (this.player.x == this.wall1.x) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.player.y == (this.box1.y + 50)) { if (this.player.x == this.box1.x) { this.state.can_move = 1; if ((this.box1.y - 50) == this.wall1.y) { if (this.box1.x == this.wall1.x) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.box1.y > 200) { this.box1.y = (this.box1.y - 50); this.player.y = (this.player.y - 50); this.state.moves = (this.state.moves + 1); } } } else { this.player.y = (this.player.y - 50); this.state.moves = (this.state.moves + 1); } } else { this.player.y = (this.player.y - 50); this.state.moves = (this.state.moves + 1); } } } } } } });
        this.input.keyboard.on('keydown-DOWN', () => { if (this.state.level > 0) { if (this.state.level < 3) { if (this.win_text.visible == false) { if (this.player.y < 400) { this.state.can_move = 1; if ((this.player.y + 50) == this.wall1.y) { if (this.player.x == this.wall1.x) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.player.y == (this.box1.y - 50)) { if (this.player.x == this.box1.x) { this.state.can_move = 1; if ((this.box1.y + 50) == this.wall1.y) { if (this.box1.x == this.wall1.x) { this.state.can_move = 0; } } if (this.state.can_move == 1) { if (this.box1.y < 400) { this.box1.y = (this.box1.y + 50); this.player.y = (this.player.y + 50); this.state.moves = (this.state.moves + 1); } } } else { this.player.y = (this.player.y + 50); this.state.moves = (this.state.moves + 1); } } else { this.player.y = (this.player.y + 50); this.state.moves = (this.state.moves + 1); } } } } } } });
        this.input.keyboard.on('keydown-LEFT', () => { this.check_win(); this.update_display(); });
        this.input.keyboard.on('keydown-RIGHT', () => { this.check_win(); this.update_display(); });
        this.input.keyboard.on('keydown-UP', () => { this.check_win(); this.update_display(); });
        this.input.keyboard.on('keydown-DOWN', () => { this.check_win(); this.update_display(); });
        this.input.keyboard.on('keydown-R', () => { this.restart_level(); });


        // Set initial scene/level visibility
        this.updateSceneVisibility();
    }

    update() {
        this.triggerEvent('update');
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

    updateSceneVisibility() {
        // Roshonic "Dimensions, Not Modes" - scene/level as coordinates
        if (this.state) this.state.visible = (this.currentLevel === 0);
    }

    start_level_1() {
        this.player.x = 275.0;
        this.player.y = 275.0;
        this.box1.x = 375.0;
        this.box1.y = 275.0;
        this.goal1.x = 475.0;
        this.goal1.y = 275.0;
        this.wall1.visible = false;
        this.level_text.text = `Level 1`;
        this.state.level = 1;
        this.state.moves = 0;
        this.moves_text.text = `Moves: 0`;
    }

    start_level_2() {
        this.player.x = 275.0;
        this.player.y = 325.0;
        this.box1.x = 375.0;
        this.box1.y = 325.0;
        this.wall1.x = 475.0;
        this.wall1.y = 325.0;
        this.wall1.visible = true;
        this.goal1.x = 525.0;
        this.goal1.y = 225.0;
        this.level_text.text = `Level 2`;
        this.state.level = 2;
        this.state.moves = 0;
        this.moves_text.text = `Moves: 0`;
        this.win_text.visible = false;
        this.next_level_text.visible = false;
    }

    show_victory() {
        this.win_text.text = `You Win!`;
        this.win_text.visible = true;
        this.next_level_text.text = `Press R to play again`;
        this.next_level_text.visible = true;
        this.state.level = 3;
    }

    restart_level() {
        this.win_text.visible = false;
        this.next_level_text.visible = false;
        if (this.state.level == 1) { this.start_level_1(); }
        if (this.state.level == 2) { this.start_level_2(); }
        if (this.state.level == 3) { this.start_level_1(); }
    }

    check_win() {
        if (this.box1.x == this.goal1.x) { if (this.box1.y == this.goal1.y) { if (this.state.level == 1) { this.win_text.text = `Level Complete!`; this.win_text.visible = true; this.next_level_text.visible = true; } if (this.state.level == 2) { this.show_victory(); } } }
    }

    update_display() {
        this.moves_text.text = `Moves: ${this.state.moves}`;
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