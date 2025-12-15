// Auto-generated from Rosh code
// Transpiled with Rosh Phaser Transpiler v0.1.7

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.eventHandlers = {};
    }

    create() {
        // Logo object
        this.logo = this.add.text(400, 280, 'rosh', { fontFamily: 'Arial', fontSize: '8px', color: 'cyan', align: 'center' });
        this.logo.setOrigin(0.5, 0.5);
        this.logo.textContent = 'rosh';
        this.logo.font_size = 8;

        // Tagline object
        this.tagline = this.add.text(400, 350, 'happy coding', { fontFamily: 'Arial', fontSize: '1px', color: 'gray', align: 'center' });
        this.tagline.setOrigin(0.5, 0.5);
        this.tagline.setVisible(false);
        this.tagline.textContent = 'happy coding';
        this.tagline.font_size = 1;

        // Dot object
        this.dot = this.add.rectangle(400, 450, 8, 8, 0xffff);
        this.dot.setVisible(false);

        // State object
        this.state = this.add.rectangle(100, 100, 50, 50, 0xffff00);
        this.state.phase = 1;
        this.state.logo_done = false;
        this.state.tagline_done = false;


        // Event handler registrations
        this.registerEventHandler('update', (params) => {
            if ((this.state.phase === 1)) {
                if ((this.logo.font_size < 96)) {
                    { const _fs = (this.logo.font_size + 2); this.logo.font_size = _fs; this.logo.setFontSize(_fs); }
                } else {
                    this.state.phase = 2;
                    this.tagline.setVisible(true);
                    this.dot.setVisible(true);
                }
            }
            if ((this.state.phase === 2)) {
                if ((this.tagline.font_size < 24)) {
                    { const _fs = (this.tagline.font_size + 1); this.tagline.font_size = _fs; this.tagline.setFontSize(_fs); }
                } else {
                    this.state.phase = 3;
                }
            }
            if ((this.state.phase === 3)) {
                if ((this.dot.width < 12)) {
                    this.dot.width = (this.dot.width + 1);
                    this.dot.height = (this.dot.height + 1);
                } else {
                    this.dot.width = 8;
                    this.dot.height = 8;
                }
            }
        });

    }

    update() {
        this.triggerEvent('update', null);

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