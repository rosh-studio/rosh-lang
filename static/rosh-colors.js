/**
 * Rosh Colors Module - Shared color mappings and utilities
 *
 * Provides consistent color handling across all Rosh targets.
 *
 * Usage:
 *   const hex = RoshColors.parse('red');        // 0xff0000
 *   const name = RoshColors.getName(0xff0000); // 'red'
 *   const isColor = RoshColors.isColorName('blue'); // true
 *
 * Version: 0.1.0
 */

const RoshColors = (function() {
  'use strict';

  // Name -> Hex mapping
  const COLOR_MAP = {
    red: 0xff0000,
    green: 0x00ff00,
    blue: 0x0000ff,
    yellow: 0xffff00,
    cyan: 0x00ffff,
    magenta: 0xff00ff,
    white: 0xffffff,
    black: 0x111111,  // Not pure black for visibility
    orange: 0xff8800,
    purple: 0x8800ff,
    pink: 0xff88ff,
    gray: 0x888888,
    grey: 0x888888,   // British spelling alias
    gold: 0xffd700,
    silver: 0xc0c0c0,
    brown: 0x8b4513,
    navy: 0x000080,
    teal: 0x008080,
    lime: 0x32cd32,
    coral: 0xff7f50
  };

  // Hex -> Name mapping (for reverse lookup)
  const HEX_TO_COLOR = {
    0xff0000: 'red',
    0x00ff00: 'green',
    0x0000ff: 'blue',
    0xffff00: 'yellow',
    0x00ffff: 'cyan',
    0xff00ff: 'magenta',
    0xffffff: 'white',
    0x000000: 'black',
    0x111111: 'black',
    0xff8800: 'orange',
    0x8800ff: 'purple',
    0xff88ff: 'pink',
    0x888888: 'gray',
    0xffd700: 'gold',
    0xc0c0c0: 'silver',
    0x8b4513: 'brown',
    0x000080: 'navy',
    0x008080: 'teal',
    0x32cd32: 'lime',
    0xff7f50: 'coral'
  };

  // All color names (for validation)
  const COLOR_NAMES = Object.keys(COLOR_MAP);

  /**
   * Parse a color string or number to hex
   * @param {string|number} str - Color name, hex string (#ff0000), or number
   * @returns {number|null} Hex color value or null if invalid
   */
  function parse(str) {
    if (typeof str === 'number') return str;
    if (!str) return null;
    const lower = str.toLowerCase().trim();
    if (COLOR_MAP[lower] !== undefined) return COLOR_MAP[lower];
    if (lower.startsWith('#')) return parseInt(lower.slice(1), 16);
    if (lower.startsWith('0x')) return parseInt(lower, 16);
    return null;
  }

  /**
   * Get color name from hex value
   * @param {number} hex - Hex color value
   * @returns {string|null} Color name or null if not a named color
   */
  function getName(hex) {
    return HEX_TO_COLOR[hex] || null;
  }

  /**
   * Check if a string is a valid color name
   * @param {string} str - String to check
   * @returns {boolean} True if valid color name
   */
  function isColorName(str) {
    if (!str) return false;
    return COLOR_MAP[str.toLowerCase()] !== undefined;
  }

  /**
   * Get hex string representation (#rrggbb)
   * @param {number} hex - Hex color value
   * @returns {string} Hex string with # prefix
   */
  function toHexString(hex) {
    return '#' + hex.toString(16).padStart(6, '0');
  }

  /**
   * Get all available color names
   * @returns {string[]} Array of color names
   */
  function getNames() {
    return COLOR_NAMES.slice();
  }

  // Public API
  return {
    parse: parse,
    getName: getName,
    isColorName: isColorName,
    toHexString: toHexString,
    getNames: getNames,
    // Direct access to maps (for adapters that need them)
    COLOR_MAP: COLOR_MAP,
    HEX_TO_COLOR: HEX_TO_COLOR
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshColors;
}
