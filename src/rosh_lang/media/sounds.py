"""Procedural sound parameter generator.

Turns a name + description into a dict of Web Audio API synthesis
parameters. No external dependencies — parameters are ~200 bytes of
JSON, played on-the-fly in the browser via OscillatorNode + GainNode.

Algorithm:
  1. Hash name → seed a Random instance (deterministic fallback).
  2. Scan description for preset keywords → map to parameter dict.
  3. If no preset matches, derive params from hash.

Each sound is a list of layers (most have one, explosion has two).
"""

from __future__ import annotations

import hashlib
import random
from typing import Any


# ── Preset keyword map ──────────────────────────────────────

_PRESETS: list[tuple[list[str], list[dict[str, Any]]]] = [
    # (keywords, layers)
    (
        ["laser", "shoot", "zap", "beam"],
        [
            {
                "waveform": "square",
                "frequency": 800,
                "duration": 0.15,
                "attack": 0.01,
                "decay": 0.14,
                "volume": 0.3,
                "sweep": -600,
                "sweep_time": 0.15,
            }
        ],
    ),
    (
        ["explosion", "boom", "blast", "explode"],
        [
            {
                "waveform": "noise",
                "frequency": 0,
                "duration": 0.4,
                "attack": 0.005,
                "decay": 0.395,
                "volume": 0.4,
                "sweep": 0,
                "sweep_time": 0,
            },
            {
                "waveform": "sine",
                "frequency": 100,
                "duration": 0.4,
                "attack": 0.005,
                "decay": 0.395,
                "volume": 0.3,
                "sweep": -80,
                "sweep_time": 0.4,
            },
        ],
    ),
    (
        ["coin", "collect", "pickup", "catch", "gem"],
        [
            {
                "waveform": "triangle",
                "frequency": 987,
                "duration": 0.1,
                "attack": 0.005,
                "decay": 0.095,
                "volume": 0.3,
                "sweep": 400,
                "sweep_time": 0.1,
            }
        ],
    ),
    (
        ["jump", "bounce", "hop"],
        [
            {
                "waveform": "sine",
                "frequency": 300,
                "duration": 0.2,
                "attack": 0.005,
                "decay": 0.195,
                "volume": 0.3,
                "sweep": 300,
                "sweep_time": 0.2,
            }
        ],
    ),
    (
        ["hit", "damage", "hurt", "ouch"],
        [
            {
                "waveform": "square",
                "frequency": 200,
                "duration": 0.08,
                "attack": 0.005,
                "decay": 0.075,
                "volume": 0.3,
                "sweep": -100,
                "sweep_time": 0.08,
            }
        ],
    ),
    (
        ["powerup", "upgrade", "levelup"],
        [
            {
                "waveform": "triangle",
                "frequency": 523,
                "duration": 0.3,
                "attack": 0.005,
                "decay": 0.295,
                "volume": 0.3,
                "sweep": 200,
                "sweep_time": 0.3,
            }
        ],
    ),
    (
        ["gameover", "lose", "fail", "death"],
        [
            {
                "waveform": "sine",
                "frequency": 440,
                "duration": 0.6,
                "attack": 0.005,
                "decay": 0.595,
                "volume": 0.3,
                "sweep": -200,
                "sweep_time": 0.6,
            }
        ],
    ),
    (
        ["click", "select", "menu", "tap"],
        [
            {
                "waveform": "sine",
                "frequency": 1000,
                "duration": 0.05,
                "attack": 0.005,
                "decay": 0.045,
                "volume": 0.2,
                "sweep": 0,
                "sweep_time": 0,
            }
        ],
    ),
    (
        ["win", "victory", "success"],
        [
            {
                "waveform": "triangle",
                "frequency": 659,
                "duration": 0.4,
                "attack": 0.005,
                "decay": 0.395,
                "volume": 0.3,
                "sweep": 100,
                "sweep_time": 0.4,
            }
        ],
    ),
]

# Valid waveforms for the Web Audio API OscillatorNode
_WAVEFORMS = ["sine", "square", "sawtooth", "triangle"]


# ── Public API ────────────────────────────────────────────

def generate_sound_params(name: str, description: str = "") -> dict[str, Any]:
    """Return Web Audio API synthesis parameters for a sound.

    Args:
        name: Sound name — used as seed for deterministic fallback.
        description: Description for preset matching
                     (e.g. "laser blast", "coin collect").

    Returns:
        A dict with key ``layers`` containing a list of layer dicts.
        Each layer has: waveform, frequency, duration, attack, decay,
        volume, sweep, sweep_time.
    """
    # Try preset matching first
    desc_lower = description.lower().replace("-", "").replace("_", "")
    for keywords, layers in _PRESETS:
        for kw in keywords:
            if kw in desc_lower:
                return {"layers": [dict(layer) for layer in layers]}

    # Fallback: deterministic params from name hash
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    rng = random.Random(digest)

    waveform = rng.choice(_WAVEFORMS)
    frequency = rng.randint(200, 1200)
    duration = round(rng.uniform(0.1, 0.4), 3)
    sweep = rng.randint(-300, 300)

    return {
        "layers": [
            {
                "waveform": waveform,
                "frequency": frequency,
                "duration": duration,
                "attack": 0.005,
                "decay": round(duration - 0.005, 3),
                "volume": 0.3,
                "sweep": sweep,
                "sweep_time": duration,
            }
        ]
    }
