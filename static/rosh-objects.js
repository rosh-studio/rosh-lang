/**
 * Rosh Known Objects Registry
 *
 * Shared object definitions for all Rosh targets.
 * Generated from known_objects.toml
 *
 * Each target uses the appropriate properties:
 *   - 2D (Phaser, Pygame): color, shape, width, height, scale, sprite
 *   - 3D (Three.js): shape, color (hex), scaleX/Y/Z, model
 */

'use strict';

const RoshObjects = (function() {

  // 2D properties for Phaser/Pygame
  const KNOWN_OBJECTS_2D = {
    // FOOD
    banana: { color: 'yellow', shape: 'ellipse', width: 0.6, height: 1.0 },
    apple: { color: 'red', shape: 'circle' },
    orange: { color: 'orange', shape: 'circle' },
    lemon: { color: 'yellow', shape: 'ellipse' },
    grape: { color: 'purple', shape: 'circle', scale: 0.5 },
    cherry: { color: 'red', shape: 'circle', scale: 0.4 },
    watermelon: { color: 'green', shape: 'ellipse', scale: 2.0 },

    // NATURE
    tree: { color: 'green', shape: 'triangle', height: 2.0, sprite: 'sprites/tree.png' },
    rock: { color: 'gray', shape: 'rectangle', height: 0.6 },
    flower: { color: 'pink', shape: 'circle', scale: 0.5 },
    bush: { color: 'green', shape: 'circle' },
    mushroom: { color: 'red', shape: 'circle', scale: 0.5 },

    // COLLECTIBLES
    coin: { color: 'gold', shape: 'circle', scale: 0.5 },
    gem: { color: 'cyan', shape: 'diamond', scale: 0.6 },
    star: { color: 'yellow', shape: 'star' },
    heart: { color: 'pink', shape: 'heart' },
    key: { color: 'gold', shape: 'rectangle', width: 0.3, height: 0.8 },
    treasure: { color: 'brown', shape: 'rectangle' },

    // CHARACTERS
    player: { color: 'blue', shape: 'rectangle', height: 1.5 },
    enemy: { color: 'red', shape: 'rectangle', height: 1.3 },
    npc: { color: 'green', shape: 'rectangle', height: 1.4 },
    ghost: { color: 'white', shape: 'circle', opacity: 0.6 },
    monster: { color: 'purple', shape: 'rectangle', height: 1.8 },
    orc: { color: 'green', shape: 'rectangle', height: 1.6, sprite: 'sprites/orc.png' },

    // SHAPES (primitives)
    ball: { color: 'red', shape: 'circle' },
    football: { color: 'white', shape: 'circle' },
    cube: { color: 'blue', shape: 'rectangle' },
    cylinder: { color: 'green', shape: 'rectangle', height: 1.5 },
    sphere: { color: 'white', shape: 'circle' },
    box: { color: 'gray', shape: 'rectangle' },
    square: { color: 'gray', shape: 'rectangle' },  // 3D square -> 2D rectangle

    // STRUCTURES
    wall: { color: 'brown', shape: 'rectangle', width: 0.3, height: 2.0 },
    platform: { color: 'brown', shape: 'rectangle', width: 2.0, height: 0.3 },
    door: { color: 'brown', shape: 'rectangle', width: 0.8, height: 1.8 },
    crate: { color: 'brown', shape: 'rectangle' },
    barrel: { color: 'brown', shape: 'circle' },
    castle: { color: 'gray', shape: 'rectangle', width: 2.0, height: 1.5 },

    // VEHICLES
    car: { color: 'red', shape: 'rectangle', width: 1.5, height: 0.8 },
    ship: { color: 'brown', shape: 'triangle', width: 1.2, height: 1.5 },
    rocket: { color: 'silver', shape: 'triangle', height: 2.0 },

    // EFFECTS
    explosion: { color: 'orange', shape: 'circle', scale: 1.5 },
    spark: { color: 'yellow', shape: 'circle', scale: 0.2 },
    cloud: { color: 'white', shape: 'ellipse', width: 2.0, height: 0.8 },

    // HERITAGE (Scottish)
    lewis_chess_king: { color: 'white', shape: 'rectangle', width: 0.8, height: 1.4 },
    lewis_chess_queen: { color: 'white', shape: 'rectangle', width: 0.8, height: 1.3 },
    invereen_stone: { color: 'gray', shape: 'rectangle', width: 0.6, height: 1.5 },
    cutty_sark_cat: { color: 'gold', shape: 'ellipse', width: 0.8, height: 1.0 },
    dolly_the_sheep: { color: 'white', shape: 'ellipse', width: 1.2, height: 0.8 },
    hunterston_brooch: { color: 'silver', shape: 'circle' },
    linen_bank: { color: 'gray', shape: 'rectangle', width: 2.0, height: 1.5 },
    joanna_baillie_monument: { color: 'gray', shape: 'rectangle', width: 1.0, height: 2.0 }
  };

  // 3D properties for Three.js
  const KNOWN_OBJECTS_3D = {
    // FOOD
    banana: { shape: 'cylinder', color: 0xffe135, scaleX: 0.3, scaleY: 1.2, scaleZ: 0.3, model: 'assets/3d_glb/banana.glb' },
    apple: { shape: 'sphere', color: 0xff0000, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/apple.glb' },
    orange: { shape: 'sphere', color: 0xff8800, scaleX: 1, scaleY: 1, scaleZ: 1 },
    lemon: { shape: 'sphere', color: 0xffff00, scaleX: 1, scaleY: 1.2, scaleZ: 1 },
    grape: { shape: 'sphere', color: 0x800080, scaleX: 0.5, scaleY: 0.5, scaleZ: 0.5 },
    cherry: { shape: 'sphere', color: 0xdc143c, scaleX: 0.4, scaleY: 0.4, scaleZ: 0.4 },
    watermelon: { shape: 'sphere', color: 0x228b22, scaleX: 1.5, scaleY: 1.0, scaleZ: 1.2 },

    // NATURE
    tree: { shape: 'cylinder', color: 0x228b22, scaleX: 1, scaleY: 2.0, scaleZ: 1, model: 'assets/3d_glb/pine_tree.glb' },
    rock: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 0.6, scaleZ: 1 },
    flower: { shape: 'sphere', color: 0xff69b4, scaleX: 0.5, scaleY: 0.8, scaleZ: 0.5 },
    bush: { shape: 'sphere', color: 0x228b22, scaleX: 1, scaleY: 0.7, scaleZ: 1 },
    mushroom: { shape: 'sphere', color: 0xff0000, scaleX: 0.6, scaleY: 0.5, scaleZ: 0.6 },

    // COLLECTIBLES
    coin: { shape: 'cylinder', color: 0xffd700, scaleX: 1.0, scaleY: 0.1, scaleZ: 1.0 },
    gem: { shape: 'sphere', color: 0x00ffff, scaleX: 0.5, scaleY: 0.7, scaleZ: 0.5 },
    star: { shape: 'sphere', color: 0xffff00, scaleX: 0.8, scaleY: 0.8, scaleZ: 0.8 },
    heart: { shape: 'sphere', color: 0xff69b4, scaleX: 1, scaleY: 1, scaleZ: 1 },
    key: { shape: 'box', color: 0xffd700, scaleX: 0.2, scaleY: 0.8, scaleZ: 0.1 },
    treasure: { shape: 'box', color: 0x8b4513, scaleX: 1, scaleY: 0.7, scaleZ: 1 },

    // CHARACTERS
    player: { shape: 'box', color: 0x4169e1, scaleX: 1, scaleY: 1.8, scaleZ: 1 },
    enemy: { shape: 'box', color: 0xff4500, scaleX: 1, scaleY: 1.5, scaleZ: 1 },
    npc: { shape: 'box', color: 0x32cd32, scaleX: 1, scaleY: 1.6, scaleZ: 1 },
    ghost: { shape: 'sphere', color: 0xffffff, scaleX: 1, scaleY: 1, scaleZ: 1, opacity: 0.6 },
    monster: { shape: 'box', color: 0x800080, scaleX: 1.3, scaleY: 1.8, scaleZ: 1.3 },
    orc: { shape: 'box', color: 0x228b22, scaleX: 2.5, scaleY: 2.5, scaleZ: 2.5, model: 'assets/3d_glb/orc_warrior.glb' },

    // SHAPES
    ball: { shape: 'sphere', color: 0xff0000, scaleX: 1, scaleY: 1, scaleZ: 1 },
    football: { shape: 'sphere', color: 0xffffff, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/cheap_soccer_ball.glb' },
    cube: { shape: 'box', color: 0x0000ff, scaleX: 1, scaleY: 1, scaleZ: 1 },
    cylinder: { shape: 'cylinder', color: 0x00ff00, scaleX: 1, scaleY: 1, scaleZ: 1 },
    sphere: { shape: 'sphere', color: 0xffffff, scaleX: 1, scaleY: 1, scaleZ: 1 },
    box: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 1, scaleZ: 1 },
    square: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 0.1, scaleZ: 1 },  // flat square

    // STRUCTURES
    wall: { shape: 'box', color: 0x8b4513, scaleX: 0.2, scaleY: 2.0, scaleZ: 1.0 },
    platform: { shape: 'box', color: 0x8b4513, scaleX: 2.0, scaleY: 0.2, scaleZ: 2.0 },
    door: { shape: 'box', color: 0x8b4513, scaleX: 0.8, scaleY: 1.8, scaleZ: 0.1 },
    crate: { shape: 'box', color: 0xdeb887, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/crate_box.glb' },
    barrel: { shape: 'cylinder', color: 0x8b4513, scaleX: 1, scaleY: 1.2, scaleZ: 1, model: 'assets/3d_glb/stylized_low_poly_wooden_barrell.glb' },
    castle: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/castle.glb' },

    // VEHICLES
    car: { shape: 'box', color: 0xff0000, scaleX: 1.5, scaleY: 0.6, scaleZ: 0.8 },
    ship: { shape: 'box', color: 0x8b4513, scaleX: 0.8, scaleY: 1.0, scaleZ: 2.0 },
    rocket: { shape: 'cylinder', color: 0xc0c0c0, scaleX: 0.4, scaleY: 2.0, scaleZ: 0.4 },

    // EFFECTS
    explosion: { shape: 'sphere', color: 0xff4500, scaleX: 1.5, scaleY: 1.5, scaleZ: 1.5 },
    spark: { shape: 'sphere', color: 0xffff00, scaleX: 0.2, scaleY: 0.2, scaleZ: 0.2 },
    cloud: { shape: 'sphere', color: 0xffffff, scaleX: 2.0, scaleY: 0.8, scaleZ: 1.5, opacity: 0.8 },

    // HERITAGE
    lewis_chess_king: { shape: 'box', color: 0xf5f5dc, scaleX: 1, scaleY: 1.4, scaleZ: 1, model: 'assets/3d_glb/lewis_chess_king.glb' },
    lewis_chess_queen: { shape: 'box', color: 0xf5f5dc, scaleX: 1, scaleY: 1.3, scaleZ: 1, model: 'assets/3d_glb/lewis_chess_queen.glb' },
    invereen_stone: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 1.5, scaleZ: 1, model: 'assets/3d_glb/invereen_stone.glb' },
    cutty_sark_cat: { shape: 'sphere', color: 0xffd700, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/cutty_sark_cat.glb' },
    dolly_the_sheep: { shape: 'sphere', color: 0xf5f5f5, scaleX: 1.2, scaleY: 0.8, scaleZ: 0.8, model: 'assets/3d_glb/dolly_the_sheep.glb' },
    hunterston_brooch: { shape: 'cylinder', color: 0xc0c0c0, scaleX: 1, scaleY: 0.1, scaleZ: 1 },
    linen_bank: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/linen_bank.glb' },
    joanna_baillie_monument: { shape: 'box', color: 0x808080, scaleX: 1, scaleY: 1, scaleZ: 1, model: 'assets/3d_glb/joanna_baillie_monument.glb' }
  };

  // Object descriptions (for "look" command)
  const KNOWN_OBJECTS_TEXT = {
    banana: 'A bright yellow banana, slightly curved',
    apple: 'A shiny red apple',
    orange: 'A round orange fruit',
    orc: 'A fierce green orc warrior',
    tree: 'A tall green tree',
    rock: 'A gray boulder',
    coin: 'A shiny gold coin',
    gem: 'A sparkling cyan gem',
    player: 'The player character',
    enemy: 'A hostile enemy',
    ball: 'A red ball',
    cube: 'A blue cube',
    sphere: 'A white sphere',
    square: 'A flat square shape',
    box: 'A gray box',
    castle: 'A stone castle with towers and walls',
    lewis_chess_king: 'A king from the Lewis Chessmen, 12th century Norse-Gaelic walrus ivory chess piece',
    dolly_the_sheep: 'Dolly the Sheep (1996-2003), the first mammal cloned from an adult cell'
  };

  return {
    // 2D object definitions
    KNOWN_OBJECTS_2D: KNOWN_OBJECTS_2D,

    // 3D object definitions
    KNOWN_OBJECTS_3D: KNOWN_OBJECTS_3D,

    // Text descriptions
    KNOWN_OBJECTS_TEXT: KNOWN_OBJECTS_TEXT,

    // Get 2D properties for an object type
    get2D: function(typeName) {
      return KNOWN_OBJECTS_2D[typeName] || null;
    },

    // Get 3D properties for an object type
    get3D: function(typeName) {
      return KNOWN_OBJECTS_3D[typeName] || null;
    },

    // Get description for an object type
    getDescription: function(typeName) {
      return KNOWN_OBJECTS_TEXT[typeName] || null;
    },

    // Check if a type is known
    isKnown: function(typeName) {
      return typeName in KNOWN_OBJECTS_2D || typeName in KNOWN_OBJECTS_3D;
    },

    // Get all known type names
    getTypeNames: function() {
      const names2d = Object.keys(KNOWN_OBJECTS_2D);
      const names3d = Object.keys(KNOWN_OBJECTS_3D);
      return [...new Set([...names2d, ...names3d])].sort();
    }
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshObjects;
}
