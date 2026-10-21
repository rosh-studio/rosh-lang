"""The access rules every Rosh server shares.

This is the canonical copy's test. The rules live in
`rosh_lang/core/access.py` and are copied byte-for-byte into
`rosh-portal/rosh_lang/core/access.py` and `rosh-world/server/access.py`,
with CI diffing all three.

They were extracted because both servers had independently written the same
sha256 line and their own Bearer parsing, and because two parity bugs turned
up in two days — one rule living in two heads, disagreeing.
"""

from rosh_lang.core import access


def test_a_key_is_stored_as_its_hash_never_itself():
    hashed = access.hash_key("rosh_k1_secret")
    assert hashed != "rosh_k1_secret"
    assert len(hashed) == 64 and set(hashed) <= set("0123456789abcdef")
    assert access.hash_key("rosh_k1_secret") == hashed, "hashing must be stable"
    assert access.hash_key("rosh_k1_secrey") != hashed


def test_hashing_is_total():
    """Both servers call this on whatever arrived. It must not raise."""
    for value in ("", " ", "\n", "x" * 10000, "ünïcode"):
        assert len(access.hash_key(value)) == 64


def test_the_token_comes_out_of_the_header():
    assert access.bearer_token("Bearer abc123") == "abc123"
    assert access.bearer_token("Bearer   abc123  ") == "abc123"
    assert access.bearer_token("  Bearer abc123") == "abc123"


def test_anything_else_yields_nothing():
    for header in ("", None, "abc123", "Basic abc123", "bearer abc123",
                   "Bearer", "Bearer ", "Token abc123"):
        assert access.bearer_token(header) == ""


# --- P-034's order ----------------------------------------------------------

def test_the_four_answers():
    assert access.decide(True, True, True) == access.FOUND
    assert access.decide(True, True, False) == access.ACCESS_DENIED
    assert access.decide(True, False, False) == access.NOT_FOUND
    assert access.decide(False, True, True) == access.REQUEST_DENIED


def test_request_denied_does_not_depend_on_whether_it_exists():
    """The rule an implementer gets wrong.

    Returned only when something is there, `request denied` becomes a politer
    spelling of "yes, something is here" — the disclosure it exists to stop.
    """
    for exists in (True, False):
        for may_read in (True, False):
            assert access.decide(False, exists, may_read) == access.REQUEST_DENIED


def test_existence_is_not_tested_before_discovery():
    """A caller who may not discover gets one answer, whatever the truth is."""
    answers = {access.decide(False, exists, read)
               for exists in (True, False) for read in (True, False)}
    assert answers == {access.REQUEST_DENIED}


def test_the_refusal_never_names_what_it_is_hiding():
    for message in (access.NOT_FOUND_MESSAGE, access.ACCESS_DENIED_MESSAGE):
        assert message
        assert "{" not in message and "%" not in message, (
            "a formattable refusal is how the name of the thing gets back in"
        )
