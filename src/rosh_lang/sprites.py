"""Compatibility shim for rosh_lang.media.sprites."""

from rosh_lang.media import sprites as _sprites
from rosh_lang.media.sprites import *  # noqa: F401,F403

globals().update({
    name: getattr(_sprites, name)
    for name in dir(_sprites)
    if not name.startswith("__")
})

