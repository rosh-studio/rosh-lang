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

BASE_COLORS: frozenset[str] = frozenset({
    "red", "green", "blue", "yellow", "cyan", "magenta",
    "white", "black", "orange", "purple", "pink", "gray", "grey",
    "gold", "silver", "brown", "lime", "navy", "teal", "coral",
    "crimson", "violet", "indigo", "maroon", "olive", "aqua", "rainbow",
})

# Words that shade a colour rather than name one. "Dark blue" is what people
# say; "navy" is not. The joined forms are colours in their own right so that
# fuzzy_color() below matches them directly instead of falling through to its
# substring scan, which finds "blue" inside "darkblue" and quietly returns the
# undarkened colour. Kept in step with SHADE_QUALIFIERS in
# rosh-portal/static/js/rosh-colors.js, which turns the joined name into hex.
# "bright" and "vivid" are intensifiers, not shades: bright orange IS orange.
# They are handled on the client (rosh-colors.js resolves "brightorange" to
# orange's own hex) and deliberately left out here, so an intensifier never
# changes the colour name that gets stored.
SHADE_QUALIFIERS: tuple[str, ...] = ("dark", "deep", "light", "pale")

NAMED_COLORS: frozenset[str] = BASE_COLORS | frozenset(
    q + c for q in SHADE_QUALIFIERS for c in BASE_COLORS
)

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

# A definite article refers back to something that already exists; an
# indefinite one introduces something new. That distinction is what tells
# "make the dome purple" (change it) from "make a red ball" (create it).
_DEFINITE: frozenset[str] = frozenset({"the", "this", "that", "my", "our"})

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
    # A qualifier and the colour it shades, written as two words: "dark blue".
    # Without this the single-word scan below matches "blue" and drops the
    # "dark" without saying so.
    #
    # Only when those two words are the whole of it. This function also reads
    # free prose describing a material, where "dark brown oak wood" means an
    # oak-coloured thing and the useful answer is still brown — folding a
    # shade out of a sentence would change what every material description
    # resolves to, which is a much bigger change than this bug calls for.
    if len(words) == 2 and words[0] in SHADE_QUALIFIERS and words[1] in BASE_COLORS:
        return words[0] + words[1]
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

_HEX_LITERAL_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")


def _strip_inline_comment(text: str) -> str:
    """Strip a trailing '# ...' comment that starts outside any quoted string.

    A '#' inside a quoted string (e.g. a hex colour `"#1a1a2e"`) is left
    alone; only an unquoted '#' begins a comment. A bare apostrophe used as
    a contraction or possessive (Rosh's, don't) is not treated as opening a
    quote — only a `'` preceded by whitespace or the start of the line can
    open one, since a real quote is never glued onto the previous word.

    An unquoted hex colour is a value, not a comment. `set ball.color to
    #00ff88` used to be cut down to `set ball.color to`, and the word `to` was
    then stored as the colour — the object turned grey and the world reported
    success. The portal's own help suggests exactly that syntax, so the
    commonest way to write a colour was the one that silently corrupted the
    object.
    """
    in_quote: str = ""
    for i, ch in enumerate(text):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
        elif ch == '"':
            in_quote = ch
        elif ch == "'" and (i == 0 or text[i - 1].isspace()):
            in_quote = ch
        elif ch == "#":
            if _HEX_LITERAL_RE.match(text, i):
                continue
            return text[:i].rstrip()
    return text


# ---------------------------------------------------------------------------
# Politeness
# ---------------------------------------------------------------------------
# Roger's rule, 20-Sep-2026: politeness is not syntax, and it is not an error
# either. "make the rock bigger please" is one command with a courtesy on the
# end; the parser used to read `please` as part of the sentence and, on the
# create path, name the new object after it. The words come off, and what came
# off is reported — a room can then decide to refuse them outright (see
# `room.strict`), but nothing may silently keep them.

POLITENESS_LEADING: tuple[str, ...] = (
    r"please",
    r"pls",
    r"plz",
    r"kindly",
    r"can you",
    r"could you",
    r"would you",
    r"will you",
    r"i want to",
    r"i want you to",
    r"i'd like to",
    r"i would like to",
    r"go ahead and",
)

POLITENESS_TRAILING: tuple[str, ...] = (
    r"please",
    r"pls",
    r"plz",
    r"kindly",
    r"thanks a lot",
    r"thanks very much",
    r"many thanks",
    r"thank you very much",
    r"thank you",
    r"thankyou",
    r"thanks",
    r"thx",
    r"ty",
    r"cheers",
    r"if you would",
    r"if you don't mind",
    r"if you dont mind",
    r"if you please",
    r"for me",
)

# `say` is the one verb whose argument is the words themselves: `say thanks` is
# a greeting to the room, not an empty command with a courtesy attached.
_POLITENESS_EXEMPT_VERBS: frozenset[str] = frozenset({"say", "shout", "whisper"})

# Words after which the next token is a NAME, not a courtesy. `create object
# please` makes an object called please; `set sign.label to thanks` means
# thanks. Someone will do both, if only to find out whether we handle it.
_NAME_POSITION: frozenset[str] = frozenset({
    "object", "number", "string", "list", "scene", "to", "named", "call", "called",
    # After an article the next word is the thing being talked about, whatever
    # it is called: `make a please` is a daft object, not a polite nothing.
    "a", "an", "the",
})

_LEADING_RE = re.compile(
    r"^\s*(?:" + "|".join(POLITENESS_LEADING) + r")\s*[,:]?\s+",
    re.IGNORECASE,
)
_TRAILING_RE = re.compile(
    r"\s*[,;]?\s*(?:" + "|".join(POLITENESS_TRAILING) + r")\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def _quote_depth_before(text: str, index: int) -> bool:
    """True when `index` sits inside a quoted string."""
    in_quote = ""
    for i, ch in enumerate(text[:index]):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
        elif ch in ('"', "'"):
            in_quote = ch
    return bool(in_quote)


def strip_politeness(text: str) -> tuple[str, list[str]]:
    """Remove courtesy words from the ends of a command.

    Returns the command without them and the exact words removed, in the order
    they were typed, so the caller can say what it ignored. Only the ends of
    the sentence are considered: `make the please bigger` is about an object
    called `please` and is left alone.

    Never strips: a value position (the token before the match is `to`), the
    argument of `say`, anything inside quotes, or the last word of what would
    otherwise be a one-word command.
    """
    original = text or ""
    working = original.strip()
    if not working:
        return original, []

    head = working.split()[0].lower() if working.split() else ""
    if head in _POLITENESS_EXEMPT_VERBS:
        return original, []

    leading: list[str] = []
    trailing: list[str] = []

    # Leading, repeatedly: "could you please make a box" loses both.
    while True:
        match = _LEADING_RE.match(working)
        if not match:
            break
        remainder = working[match.end():].strip()
        if not remainder:
            break
        leading.append(match.group(0).strip().rstrip(",:").strip())
        working = remainder

    # Trailing, repeatedly: "make it red please, thanks" loses both.
    while True:
        match = _TRAILING_RE.search(working)
        if not match:
            break
        if _quote_depth_before(working, match.start()):
            break
        remainder = working[:match.start()].strip()
        # A name is not a courtesy, and a one-word command is not worth
        # emptying out.
        if len(remainder.split()) < 2 or remainder.split()[-1].lower() in _NAME_POSITION:
            break
        trailing.append(match.group(0).strip(" ,;.!?").strip())
        working = remainder

    # Reported in the order they were typed: the trailing ones came off
    # back-to-front.
    dropped = leading + list(reversed(trailing))
    if not dropped:
        return original, []
    return working, dropped


def normalise(line: str) -> str:
    """Normalise one line of natural-language Rosh into canonical form.

    Returns one or more canonical lines joined by newline.
    Returns the original line unchanged if no rewrite applies.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return line

    stripped = _strip_inline_comment(stripped)
    if not stripped:
        return ""

    # Courtesy words come off before anything tries to read the sentence. The
    # caller that wants to tell the person what was ignored calls
    # strip_politeness() itself; here they are simply not syntax.
    stripped, _politeness = strip_politeness(stripped)
    if not stripped:
        return ""

    tokens = stripped.split()
    head = tokens[0].lower()

    # -- if condition operator aliases: is / is not / equals → == / != -------
    # Uses token-based extraction so quoted string values like "is not real"
    # are never corrupted — only the operator token itself is replaced.
    if head == "if":
        rest = stripped[len("if"):].strip()
        parts = rest.split(None, 2)  # [field, op, value_rest]
        if len(parts) >= 2:
            field, op_word = parts[0], parts[1].lower()
            value_rest = parts[2] if len(parts) > 2 else ""
            if op_word == "is" and value_rest.lower().startswith("not "):
                return f"if {field} != {value_rest[4:].strip()}"
            elif op_word in ("is", "equals"):
                return f"if {field} == {value_rest}"

    # -- collision wildcard: "name all" → "name.*" in when collision lines ---
    if head == "when" and stripped.lower().startswith("when collision "):
        rest = stripped[len("when collision "):]
        candidate = re.sub(r'(\w[\w.-]*)\s+all\b', r'\1.*', rest)
        if candidate != rest:
            return "when collision " + candidate

    # -- destroy aliases: delete/remove -> destroy -------------------------
    # BUT: "remove X from Y" is a collection operation — leave it alone.
    if head in _DESTROY_VERBS and head != "destroy":
        rest = stripped[len(head):].strip()
        if head == "remove" and " from " in rest:
            pass  # collection remove — fall through unchanged
        else:
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

    # -- "make the X <colour>" — definite article means it already exists ---
    # `make` is the one ambiguous verb here: "make a red ball" creates, while
    # "make the dome purple" changes something already in the world. Every
    # other colour verb (turn/paint/colour) is unambiguous and handled above.
    #
    # Without this, `make` fell through to the create-verb alias below and
    # "make the dome purple" became "create object dome" — inventing an object
    # and reporting success (ROSH-NOW.md, 2026-09-14 round 17).
    #
    # Only the LAST token is colour-matched, deliberately: fuzzy_color("blue
    # box") returns "blue", so matching the whole description would turn
    # "make a big blue box" into "set big.color to blue".
    if head == "make" and len(tokens) >= 4 and tokens[1].lower() in _DEFINITE:
        rest = [t for t in tokens[2:] if t.lower() not in _ARTICLES]
        if len(rest) >= 2:
            obj = "_".join(rest[:-1])
            last = rest[-1].lower()
            if last in _OPACITY_WORDS:
                return f"set {obj}.opacity to {_OPACITY_WORDS[last]}"
            col = fuzzy_color(last)
            if col:
                return f"set {obj}.color to {col}"

    # -- turn X <colour|invisible|into Y> ----------------------------------
    if head == "turn":
        rest = [t for t in tokens[1:] if t.lower() not in _ARTICLES]
        if len(rest) >= 2:
            obj = rest[0]
            last = rest[-1].lower()
            # "turn X into <material>" — last word is the material noun
            if len(rest) >= 3 and rest[1].lower() == "into":
                material_words = list(rest[2:])
                # A quoted phrase ("dark wood") splits on whitespace with the
                # quote characters still attached to the first/last word.
                if material_words:
                    material_words[0] = material_words[0].lstrip("\"'")
                    material_words[-1] = material_words[-1].rstrip("\"'")
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
            # Strip enclosing quote characters before splitting into words —
            # otherwise a quoted value like "walrus ivory" leaves a stray
            # quote baked into the material noun (words[-1] == 'ivory"').
            # Stripped independently (not as a matched pair) so a missing
            # closing quote from a typo doesn't leave the other side dirty.
            if len(desc) >= 1 and desc[0] in ('"', "'"):
                desc = desc[1:]
            if len(desc) >= 1 and desc[-1] in ('"', "'"):
                desc = desc[:-1]
            desc = desc.strip()
            words = desc.split()
            if len(words) > 1:
                # Last word is the material noun; earlier words are adjectives
                return (
                    f"set {obj}.material to {words[-1].lower()}\n"
                    f"set {obj}.material_desc to {desc}"
                )

    # -- create aliases: build/put/place -> create -------------------------
    # BUT: "add X to Y" is a collection operation — leave it alone.
    if head in _CREATE_VERBS and head != "create":
        rest = stripped[len(head):].strip()
        if head == "add" and " to " in rest:
            pass  # collection add — fall through unchanged
        elif not rest.lower().startswith("object "):
            return f"create {rest}"

    return stripped


def normalise_programme(text: str) -> str:
    """Normalise a multi-line Rosh programme, expanding rewrites line by line."""
    out: list[str] = []
    for raw in text.splitlines():
        out.append(normalise(raw))
    return "\n".join(out)
