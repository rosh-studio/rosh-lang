"""Compatibility shim for rosh_lang.core.widgets."""

from rosh_lang.core import widgets as _widgets
from rosh_lang.core.widgets import *  # noqa: F401,F403

globals().update({
    name: getattr(_widgets, name)
    for name in dir(_widgets)
    if not name.startswith("__")
})

