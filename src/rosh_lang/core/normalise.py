"""
Rosh language normaliser.

Converts natural-language variations into canonical Rosh before the parser
sees them. This runs on every line before dispatch, so any Rosh runtime
(terminal, browser, API) gets forgiving input handling for free.

Design rules:
- Input: one line of text (may produce multiple output lines for compound forms)
- Output: one or more canonical Rosh lines joined by newline
- Never raises — if nothing matches, returns the original line unchanged
- No runtime state, no side effects, pure text transformation
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Colour vocabulary
# ---------------------------------------------------------------------------

NAMED_COLORS: frozenset[str] = frozenset({
    "red", "green", "blue", "yellow", "cyan", "magenta",
    "white", "black", "orange", "purple", "pink", "gray", "grey",
    "gold", "silver", "brown", "lime", "navy", "teal", "coral",
    "crimson", "violet", "indigo", "maroon", "olive", "aqua", "rainbow",
})

# Nouns/adjectives that imply a colour when no direct colour word is present
COLOR_SEMANTICS: dict[str, str] = {
    "obsidian": "black", "void": "black", "darkness": "black",
    "shadow": "black", "night": "black", "coal": "black",
    "ash": "gray", "smoke": "gray", "thunder": "gray",
    "storm": "gray", "fog": "gray", "concrete": "gray",
    "granite": "gray", "stone": "gray", "rock": "gray",
    "steel": "gray", "iron": "gray",
    "mercury": "silver", "chrome": "silver",
    "permafrost": "white", "frost": "white", "ice": "white",
    "snow": "white", "glacier": "white", "cloud": "white",
    "foam": "white", "bone": "white", "plasma": "white", "lightning": "white",
    "lava": "orange", "magma": "orange", "flame": "orange", "fire": "orange",
    "ember": "orange", "rust": "orange", "copper": "orange",
    "autumn": "orange", "fall": "orange", "sunset": "orange",
    "wood": "brown", "oak": "brown", "bark": "brown", "earth": "brown",
    "soil": "brown", "mud": "brown", "dirt": "brown",
    "root": "brown", "roots": "brown", "log": "brown",
    "grass": "green", "leaf": "green", "leaves": "green",
    "moss": "green", "ivy": "green", "jungle": "green",
    "forest": "green", "pine": "green", "emerald": "green",
    "ocean": "blue", "sea": "blue", "water": "blue",
    "sky": "blue", "sapphire": "blue", "lake": "blue",
    "blood": "red", "ruby": "red", "cherry": "red", "rose": "red",
    "sand": "yellow", "desert": "yellow", "hay": "yellow",
    "sun": "yellow", "sunlight": "yellow",
    "amethyst": "purple", "lavender": "purple",
    "coral_noun": "pink", "salmon": "pink",
    "rainbow": "rainbow",
    "thunderstorm": "gray", "golden": "gold", "straw": "yellow",
}

_ARTICLES: frozenset[str] = frozenset({"a", "an", "the"})

_CREATE_VERBS: frozenset[str] = frozenset({
    "create", "make", "add", "spawn", "build", "put", "place",
})

_DESTROY_VERBS: frozenset[str] = frozenset({
    "delete", "remove", "destroy",
})

_COLOUR_VERBS: frozenset[str] = frozenset({
    "colour", "color", "paint", "recolour", "recolor",
})

_OPACITY_WORDS: dict[str, str] = {
    "invisible": "0", "hidden": "0",
    "transparent": "0.3",
    "visible": "1", "opaque": "1",
}


def fuzzy_color(text: str) -> Optional[str]:
    """Extract the best colour name from a natural-language description.

    Tries in order: exact named-colour word, semantic noun mapping,
    substring scan of compound words. Returns None if nothing found.
    """
    words = re.sub(r"[^a-z\s]", "", text.lower()).split()
    # Direct named colour
    for w in words:
        if w in NAMED_COLORS:
            return w
    # Semantic mapping
    for w in words:
        if w in COLOR_SEMANTICS:
            return COLOR_SEMANTICS[w]
    # Substring scan for compound forms ("darkgreen", "lightblue")
    joined = "".join(words)
    for col in sorted(NAMED_COLORS, key=len, reverse=True):
        if col in joined:
            return col
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalise(line: str) -> str:
    """Normalise one line of natural-language Rosh into canonical form.

    Returns one or more canonical lines joined by newline.
    Returns the original line unchanged if no rewrite applies.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return line

    tokens = stripped.split()
    head = tokens[0].lower()

    # -- destroy aliases: delete/remove -> destroy -------------------------
    if head in _DESTROY_VERBS and head != "destroy":
        rest = stripped[len(head):].strip()
        return f"destroy {rest}" if rest else stripped

    # -- colour verb: colour/paint X <description> -------------------------
    if head in _COLOUR_VERBS:
        rest = [t for t in tokens[1:] if t.lower() not in _ARTICLES]
        if len(rest) >= 2:
            obj = rest[0]
            desc = " ".join(rest[1:])
            col = fuzzy_color(desc)
            if col:
                lines = [f"set {obj}.color to {col}"]
                if desc.strip().lower() != col:
                    lines.append(f"set {obj}.color_desc to {desc.strip()}")
                return "\n".join(lines)

    # -- change X colour to <description> ----------------------------------
    if head == "change":
        m = re.match(
            r"change\s+(?:the\s+)?(\S+)\s+colou?r\s+to\s+(.+)",
            stripped, flags=re.IGNORECASE,
        )
        if m:
            obj, desc = m.group(1), m.group(2).strip()
            col = fuzzy_color(desc) or desc.split()[0].lower()
            lines = [f"set {obj}.color to {col}"]
            if desc.lower() != col:
                lines.append(f"set {obj}.color_desc to {desc}")
            return "\n".join(lines)

    # -- turn X <colour|invisible|into Y> ----------------------------------
    if head == "turn":
        rest = [t for t in tokens[1:] if t.lower() not in _ARTICLES]
        if len(rest) >= 2:
            obj = rest[0]
            last = rest[-1].lower()
            # "turn X into <material>" — last word is the material noun
            if len(rest) >= 3 and rest[1].lower() == "into":
                material_words = rest[2:]
                material = material_words[-1].lower()
                lines = [f"set {obj}.material to {material}"]
                if len(material_words) > 1:
                    lines.append(f"set {obj}.material_desc to {' '.join(material_words)}")
                return "\n".join(lines)
            # "turn X invisible/transparent/visible"
            if last in _OPACITY_WORDS:
                return f"set {obj}.opacity to {_OPACITY_WORDS[last]}"
            # "turn X <colour description>"
            desc = " ".join(r.lower() for r in rest[1:])
            col = fuzzy_color(desc)
            if col:
                lines = [f"set {obj}.color to {col}"]
                if desc != col:
                    lines.append(f"set {obj}.color_desc to {desc}")
                return "\n".join(lines)

    # -- set X.color to <description> — fuzzy parse the value --------------
    if head == "set":
        m = re.match(
            r"set\s+(\S+)\.(colou?r)\s+to\s+(.+)",
            stripped, flags=re.IGNORECASE,
        )
        if m:
            obj, _, desc = m.group(1), m.group(2), m.group(3).strip()
            col = fuzzy_color(desc)
            if col and desc.lower() != col:
                lines = [f"set {obj}.color to {col}",
                         f"set {obj}.color_desc to {desc}"]
                return "\n".join(lines)

        # set X.material to <description> — preserve if complex
        m2 = re.match(
            r"set\s+(\S+)\.(material)\s+to\s+(.+)",
            stripped, flags=re.IGNORECASE,
        )
        if m2:
            obj, _, desc = m2.group(1), m2.group(2), m2.group(3).strip()
            words = desc.split()
            if len(words) > 1:
                # Last word is the material noun; earlier words are adjectives
                return (
                    f"set {obj}.material to {words[-1].lower()}\n"
                    f"set {obj}.material_desc to {desc}"
                )

    # -- create aliases: build/put/place -> create -------------------------
    if head in _CREATE_VERBS and head != "create":
        rest = stripped[len(head):].strip()
        # Only rewrite if it doesn't already look like a strict create
        if not rest.lower().startswith("object "):
            return f"create {rest}"

    return stripped


def normalise_programme(text: str) -> str:
    """Normalise a multi-line Rosh programme, expanding rewrites line by line."""
    out: list[str] = []
    for raw in text.splitlines():
        out.append(normalise(raw))
    return "\n".join(out)
