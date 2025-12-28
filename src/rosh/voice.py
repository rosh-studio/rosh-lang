"""
Rosh Voice Normalizer

Normalizes speech-to-text input into canonical Rosh commands.
Uses the voice specification for corrections and transformations.

WARNING: Rosh is experimental. This implementation may change.
"""

import re
from typing import Optional, Tuple, List

# Try to load voice spec
_voice_spec = None
_corrections_cache = {}


def _load_voice_spec():
    """Load the voice specification."""
    global _voice_spec, _corrections_cache
    if _voice_spec is not None:
        return _voice_spec

    try:
        from .spec.loader import SpecLoader
        loader = SpecLoader()
        _voice_spec = loader.load('voice')

        # Build corrections cache for fast lookup
        corrections = _voice_spec.get('corrections', {})
        for category, items in corrections.items():
            # Skip contextual corrections - these need special handling
            # (e.g., 'to' should NOT become '2' in 'set x to 5')
            if category == 'numbers_contextual':
                continue
            if isinstance(items, dict):
                for typo, correct in items.items():
                    _corrections_cache[typo.lower()] = correct

        # Add spellings
        spellings = _voice_spec.get('spellings', {})
        for british, american in spellings.items():
            _corrections_cache[british.lower()] = american

        return _voice_spec
    except Exception:
        return {}


def normalize_word(word: str) -> Tuple[str, Optional[str]]:
    """Normalize a single word.

    Args:
        word: The word to normalize

    Returns:
        Tuple of (normalized_word, correction_message or None)
    """
    _load_voice_spec()

    word_lower = word.lower()

    # Check corrections cache
    if word_lower in _corrections_cache:
        corrected = _corrections_cache[word_lower]
        return corrected, f"[corrected: {word}→{corrected}]"

    return word, None


def normalize_line(line: str, quiet: bool = False) -> Tuple[str, List[str]]:
    """Normalize a line of input.

    Args:
        line: The input line
        quiet: If True, suppress correction messages

    Returns:
        Tuple of (normalized_line, list of correction messages)
    """
    _load_voice_spec()

    words = line.split()
    normalized_words = []
    messages = []

    for word in words:
        # Preserve punctuation at end
        punct = ""
        clean_word = word
        if word and word[-1] in '.,!?;:':
            punct = word[-1]
            clean_word = word[:-1]

        normalized, msg = normalize_word(clean_word)
        normalized_words.append(normalized + punct)

        if msg and not quiet:
            messages.append(msg)

    return ' '.join(normalized_words), messages


def add_implied_to(line: str) -> Tuple[str, Optional[str]]:
    """Add implied 'to' in set/move commands.

    Examples:
        "set x 100" → "set x to 100"
        "set box x 100" → "set box x to 100"
        "set color red" → "set color to red"
        "move ball 50 100" → "move ball to 50 100"

    Args:
        line: The command line

    Returns:
        Tuple of (modified_line, message or None)
    """
    # Skip if already has 'to'
    if ' to ' in line.lower():
        return line, None

    # Pattern 1: set <object> <property> <value> (3+ tokens after set)
    # e.g., "set box x 100" → "set box x to 100"
    # Must check this BEFORE the short pattern
    set_long_pattern = r'^(set\s+\w+\s+\w+)\s+(\S.*)$'
    match = re.match(set_long_pattern, line, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        value = match.group(2)
        if not value.lower().startswith('to '):
            return f"{prefix} to {value}", "[implied: to]"

    # Pattern 2: set <property> <value> (2 tokens after set)
    # e.g., "set x 100" → "set x to 100"
    set_short_pattern = r'^(set\s+\w+)\s+(\S.*)$'
    match = re.match(set_short_pattern, line, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        value = match.group(2)
        # Check it's not already "set x to ..."
        if not value.lower().startswith('to '):
            return f"{prefix} to {value}", "[implied: to]"

    # Pattern 3: move <object> <x> <y> (missing 'to')
    move_pattern = r'^(move\s+\w+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(.*)$'
    match = re.match(move_pattern, line, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        x = match.group(2)
        y = match.group(3)
        rest = match.group(4)
        return f"{prefix} to {x} {y}{rest}", "[implied: to]"

    return line, None


def infer_property_from_value(line: str) -> Tuple[str, Optional[str]]:
    """Infer property name when value is unambiguous.

    Examples:
        "set box red" → "set box color to red"
        "set box to red" → "set box color to red" (after implied to)

    Args:
        line: The command line

    Returns:
        Tuple of (modified_line, message or None)
    """
    _load_voice_spec()

    # Get color names from voice spec
    color_names = set()
    try:
        voice = _voice_spec or {}
        inference = voice.get('inference', {})
        color_from_name = inference.get('color_from_name', {})
        color_names = set(n.lower() for n in color_from_name.get('color_names', []))
    except Exception:
        # Fallback colors
        color_names = {
            'red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
            'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey'
        }

    color_pattern = '|'.join(color_names)

    # Pattern 1: set <object> <color_name>
    # Should become: set <object> color to <color_name>
    pattern1 = r'^set\s+(\w+)\s+(' + color_pattern + r')$'
    match = re.match(pattern1, line, re.IGNORECASE)
    if match:
        obj = match.group(1)
        color = match.group(2)
        return f"set {obj} color to {color}", "[inferred: color]"

    # Pattern 2: set <object> to <color_name> (after implied to was added)
    # Should become: set <object> color to <color_name>
    pattern2 = r'^set\s+(\w+)\s+to\s+(' + color_pattern + r')$'
    match = re.match(pattern2, line, re.IGNORECASE)
    if match:
        obj = match.group(1)
        color = match.group(2)
        return f"set {obj} color to {color}", "[inferred: color]"

    return line, None


def strip_articles(line: str) -> str:
    """Remove articles (a, an, the) from command.

    Examples:
        "create a box" → "create box"
        "delete the ball" → "delete ball"
    """
    # Only strip in specific contexts
    patterns = [
        (r'\bcreate\s+a\s+', 'create '),
        (r'\bcreate\s+an\s+', 'create '),
        (r'\bdelete\s+the\s+', 'delete '),
        (r'\bclone\s+the\s+', 'clone '),
        (r'\bmove\s+the\s+', 'move '),
        (r'\bhide\s+the\s+', 'hide '),
        (r'\bshow\s+the\s+', 'show '),
        (r'\blook\s+at\s+the\s+', 'look '),
    ]

    result = line
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def strip_politeness(line: str) -> str:
    """Remove politeness phrases.

    Examples:
        "please create a box" → "create a box"
        "can you delete the ball" → "delete the ball"
    """
    patterns = [
        r'^please\s+',
        r'^can\s+you\s+',
        r'^could\s+you\s+',
        r'^would\s+you\s+',
    ]

    result = line
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)

    return result


def normalize_input(line: str, quiet: bool = False) -> Tuple[str, List[str]]:
    """Full normalization pipeline for voice input.

    Args:
        line: Raw input line
        quiet: If True, suppress correction messages

    Returns:
        Tuple of (normalized_line, list of messages)
    """
    messages = []

    # Step 1: Strip politeness
    line = strip_politeness(line)

    # Step 2: Strip articles
    line = strip_articles(line)

    # Step 3: Normalize words (typos, spellings)
    line, word_messages = normalize_line(line, quiet)
    messages.extend(word_messages)

    # Step 4: Add implied 'to'
    line, to_msg = add_implied_to(line)
    if to_msg and not quiet:
        messages.append(to_msg)

    # Step 5: Infer properties from values
    line, infer_msg = infer_property_from_value(line)
    if infer_msg and not quiet:
        messages.append(infer_msg)

    return line, messages


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    # Test cases
    test_cases = [
        "creat box",
        "set box x 100",
        "set ball red",
        "please create a box",
        "delte the ball",
        "colour blue",
        "raush help",
        "move player 50 100",
    ]

    print("Rosh Voice Normalizer Test")
    print("=" * 60)
    print()

    for test in test_cases:
        normalized, messages = normalize_input(test)
        print(f"Input:  {test}")
        print(f"Output: {normalized}")
        if messages:
            print(f"Notes:  {' '.join(messages)}")
        print()
