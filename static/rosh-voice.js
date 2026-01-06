/**
 * Rosh Voice Module - Speech recognition corrections and normalization
 *
 * Handles common voice input mishearings and provides text normalization.
 *
 * Usage:
 *   const result = RoshVoice.correct('make read cube');
 *   // result = { text: 'make red cube', changes: ['read → red'] }
 *
 * Version: 0.1.0
 */

const RoshVoice = (function() {
  'use strict';

  // Voice corrections table - common speech recognition mishearings
  // Format: 'misheard': 'correct'
  const CORRECTIONS = {
    // Brand name
    'rush': 'rosh',
    'rash': 'rosh',
    'ross': 'rosh',
    'roush': 'rosh',
    'raush': 'rosh',
    'rawsh': 'rosh',

    // Colors
    'read': 'red',
    'reed': 'red',
    'grey': 'gray',
    'blew': 'blue',
    'blow': 'blue',
    'wait': 'white',
    'weight': 'white',
    'wet': 'white',
    'lack': 'black',
    'block': 'black',
    'screen': 'green',
    'grain': 'green',
    'fellow': 'yellow',
    'yell': 'yellow',
    'science': 'cyan',
    'sign': 'cyan',
    'arrange': 'orange',
    'ping': 'pink',
    'perple': 'purple',
    'people': 'purple',

    // Properties
    'collar': 'color',
    'colour': 'color',
    'cooler': 'color',
    'fund': 'font',
    'front': 'font',
    'funt': 'font',
    'with': 'width',
    'whith': 'width',
    'hight': 'height',
    'fizzy ball': 'visible',
    'skill': 'scale',
    'polls': 'pulse',
    'pulls': 'pulse',
    'pals': 'pulse',

    // Coordinates
    'ex': 'x',
    'eggs': 'x',
    'why': 'y',
    'wie': 'y',
    'see': 'z',
    'zee': 'z',
    'zed': 'z',

    // Font names
    'enter': 'Inter',
    'inter': 'Inter',
    'inner': 'Inter',
    'aerial': 'Arial',
    'arial': 'Arial',
    'area': 'Arial',

    // Common objects
    'logo': 'logo',
    'lego': 'logo',
    'local': 'logo',

    // British spellings (normalize to American)
    'centre': 'center',
    'visibility': 'visible'
  };

  /**
   * Apply voice corrections to text
   * @param {string} text - Input text (possibly from speech recognition)
   * @returns {object} { text: correctedText, changes: ['wrong → right', ...] }
   */
  function correct(text) {
    if (!text) return { text: '', changes: [] };

    let corrected = text;
    const changes = [];

    for (const [wrong, right] of Object.entries(CORRECTIONS)) {
      const regex = new RegExp('\\b' + wrong + '\\b', 'gi');
      if (regex.test(corrected)) {
        corrected = corrected.replace(regex, right);
        changes.push(wrong + ' → ' + right);
      }
    }

    return { text: corrected, changes: changes };
  }

  /**
   * Simple correction (returns only the corrected text)
   * @param {string} text - Input text
   * @returns {string} Corrected text
   */
  function correctSimple(text) {
    return correct(text).text;
  }

  /**
   * Normalize text for comparison (lowercase, trim, normalize spaces)
   * @param {string} text - Input text
   * @returns {string} Normalized text
   */
  function normalize(text) {
    if (!text) return '';
    return text.toLowerCase().trim().replace(/\s+/g, ' ');
  }

  /**
   * Add a custom correction
   * @param {string} wrong - Misheard word
   * @param {string} right - Correct word
   */
  function addCorrection(wrong, right) {
    CORRECTIONS[wrong.toLowerCase()] = right;
  }

  /**
   * Get all corrections (for debugging/display)
   * @returns {object} Copy of corrections map
   */
  function getCorrections() {
    return Object.assign({}, CORRECTIONS);
  }

  // Public API
  return {
    correct: correct,
    correctSimple: correctSimple,
    normalize: normalize,
    addCorrection: addCorrection,
    getCorrections: getCorrections,
    // Direct access for adapters
    CORRECTIONS: CORRECTIONS
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshVoice;
}
