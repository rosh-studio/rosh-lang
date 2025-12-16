// Auto-generated from Rosh code
// Transpiled with Rosh Phaser Transpiler v0.1.10

class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
    }

    create() {
        // Logo object
        this.logo = this.add.text(400, 300, 'rosh', { fontFamily: 'Arial', fontSize: '72px', color: 'cyan', align: 'center' });
        this.logo.setOrigin(0.5, 0.5);
        this.logo.textContent = 'rosh';
        this.logo.font_size = 72;

        // Tagline object
        this.tagline = this.add.text(400, 380, 'one language. many worlds.', { fontFamily: 'Arial', fontSize: '18px', color: 'gray', align: 'center' });
        this.tagline.setOrigin(0.5, 0.5);
        this.tagline.textContent = 'one language. many worlds.';
        this.tagline.font_size = 18;

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