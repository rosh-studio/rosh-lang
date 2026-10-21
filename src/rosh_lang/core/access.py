"""Access rules shared by every Rosh server. One rule, one implementation.

**This file is the canonical copy. Two byte-identical copies exist:**

    rosh-portal/rosh_lang/core/access.py
    rosh-world/server/access.py

CI's `repository-contracts` job diffs all three on every push. Change this
one, copy it to the other two, or the build fails and says so.

It is copied as source rather than delivered through rosh-world's vendored
wheel on purpose: that wheel silently lagged the source by ten versions
between July and September 2026, and nothing warned. A delivery channel that
has already drifted once is not where security rules should live.

Why share these particular rules and not others: every bug worth fixing here
so far has been a **parity** bug — one rule living in two heads.

  * 2026-09-23 — the browser understood `make the cube bigger`; the wire
    created an object called `bigger` and reported success.
  * 2026-09-24 — a world-scoped key was required to OPEN a private room but
    not to DISCOVER one, so a compile-only key could still learn the room was
    there.

Both servers had independently written `sha256(raw.encode()).hexdigest()` and
their own Bearer-header parsing. That is not reuse waiting to happen; it is
two copies waiting to disagree.

Everything here is pure: no I/O, no database, no framework types. Each server
keeps its own storage and its own idea of who a caller is (the portal has
people, rosh-world has keys — see P-035); what they share is how a key is
read and what an answer may reveal.
"""

from __future__ import annotations

import hashlib

__all__ = [
    "hash_key",
    "bearer_token",
    "FOUND",
    "NOT_FOUND",
    "ACCESS_DENIED",
    "REQUEST_DENIED",
    "decide",
    "NOT_FOUND_MESSAGE",
    "ACCESS_DENIED_MESSAGE",
]

_BEARER = "Bearer "


def hash_key(raw: str) -> str:
    """How a key is stored. Never the key itself.

    Both servers arrived at this line independently. Keeping one copy means a
    future change — a different algorithm, a salt, a work factor — cannot land
    in one server and not the other, which would lock every existing key out
    of half the system.
    """
    return hashlib.sha256((raw or "").encode()).hexdigest()


def bearer_token(authorization: str) -> str:
    """The token out of an `Authorization: Bearer …` header, or "".

    A key belongs in a header. Not in a query string, which is written to every
    access log it passes through, and not in a URL that lands in a shell
    history, a screenshot or a bug report.
    """
    header = (authorization or "").strip()
    if not header.startswith(_BEARER):
        return ""
    return header[len(_BEARER):].strip()


# --- What an answer may reveal (P-034) --------------------------------------

FOUND = "found"
NOT_FOUND = "not_found"
ACCESS_DENIED = "access_denied"
REQUEST_DENIED = "request_denied"


def decide(may_discover: bool, exists: bool, may_read: bool) -> str:
    """Which of the four answers this caller gets, in the only safe order.

    Discovery is tested BEFORE existence, because testing existence first is
    what creates the side channel: the answer differs depending on something
    the caller was not entitled to learn.

      * `REQUEST_DENIED` — may not learn whether it exists. Returned whether or
        not it does. **This is the rule an implementer gets wrong.** Returned
        only when something is there, it becomes a politer spelling of "yes,
        something is here" — the disclosure it exists to prevent.
      * `NOT_FOUND` — does not exist, and the caller may know that.
      * `ACCESS_DENIED` — exists, the caller may know it exists, may not read it.
      * `FOUND` — go ahead.

    Callers that must not disclose treat REQUEST_DENIED and NOT_FOUND as the
    same response — same status, same body, same timing as far as is practical.
    The distinction is Rosh's own vocabulary and the server-side log, not
    something the caller can see.
    """
    if not may_discover:
        return REQUEST_DENIED
    if not exists:
        return NOT_FOUND
    if not may_read:
        return ACCESS_DENIED
    return FOUND


# One wording, so two servers cannot be told apart by their punctuation, and
# so a refusal never names the thing it is refusing to admit exists.
NOT_FOUND_MESSAGE = "Not found"
ACCESS_DENIED_MESSAGE = "You do not have access to that"
