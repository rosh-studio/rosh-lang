// Auto-generated from Rosh IR
// Emitter: Phaser 3 v0.2.0

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.eventHandlers = {};
    }

    create() {
        this.logo = this.add.text(400.0, 252.0, 'rosh', { fontSize: '8px', fill: '#00ffff' });
        this.logo.setOrigin(0.5, 0.5);
        this.logo.font_size = 8;

        this.tagline = this.add.text(400.0, 378.0, 'happy coding', { fontSize: '1px', fill: '#888888' });
        this.tagline.setOrigin(0.5, 0.5);
        this.tagline.font_size = 1;
        this.tagline.visible = false;

        this.state = this.add.rectangle(400.0, 300.0, 40.0, 30.0, 0x00ff00);
        this.state.phase = 1;
        this.state.logo_done = false;
        this.state.tagline_done = false;
        this.state.visible = false;

        this.registerEvent('update', function() { if (this.state.phase == 1) { if (this.logo.font_size < 128) { this.logo.font_size = (this.logo.font_size + 3); if (this.logo.setFontSize) this.logo.setFontSize(this.logo.font_size); } else { this.state.phase = 2; this.tagline.visible = true; } } if (this.state.phase == 2) { if (this.tagline.font_size < 28) { this.tagline.font_size = (this.tagline.font_size + 1); if (this.tagline.setFontSize) this.tagline.setFontSize(this.tagline.font_size); } else { this.state.phase = 3; } } });

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