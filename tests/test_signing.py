"""Exercise the rule pairing a signing key with an author.

Unit level, unlike the rest of the signing coverage, which runs through
`main()` in test_generate.py. The OpenPGP half asks gpg for a key's own user
IDs, and a test cannot conjure a keyring, so that lookup is stood in for here.

The suite's ambient identity is `ambient@example.com`, planted in the
environment by conftest. That is the address a key is taken to belong to
whenever the key itself cannot answer.
"""

from prg import generator, gitio

AMBIENT = "ambient@example.com"
OTHER = "jane@example.com"

SSH_KEY = ("/keys/id_ed25519.pub", "ssh")
PGP_KEY = ("E68923AA0F79A38E", "openpgp")


def carrying(monkeypatch, emails):
    """Answer the OpenPGP lookup with `emails`, or None for unanswerable."""
    monkeypatch.setattr(gitio, "signing_key_emails", lambda key, cwd: emails)


def test_no_key_has_nothing_to_disagree_with():
    assert generator.signing_mismatch(("Someone", OTHER), None) is None


def test_an_ssh_key_agrees_with_the_address_that_configured_it():
    assert generator.signing_mismatch(("Suite Ambient", AMBIENT), SSH_KEY) is None


def test_an_ssh_key_disagrees_with_another_address():
    failure = generator.signing_mismatch(("Jane Doe", OTHER), SSH_KEY)

    assert failure is not None
    assert AMBIENT in failure and OTHER in failure


def test_an_openpgp_key_carrying_the_address_agrees(monkeypatch):
    """The key answers for itself, and its answer is the one that counts."""
    carrying(monkeypatch, {OTHER})

    assert generator.signing_mismatch(("Jane Doe", OTHER), PGP_KEY) is None


def test_an_openpgp_key_carrying_another_address_disagrees(monkeypatch):
    carrying(monkeypatch, {AMBIENT})

    failure = generator.signing_mismatch(("Jane Doe", OTHER), PGP_KEY)

    assert failure is not None
    assert PGP_KEY[0] in failure


def test_an_unreadable_openpgp_key_falls_back_to_the_config(monkeypatch):
    """No keyring is not the same answer as a key carrying nothing.

    Reading it as one would refuse a build over a question that was never
    answered, so the address that configured the key decides instead.
    """
    carrying(monkeypatch, None)

    assert generator.signing_mismatch(("Suite Ambient", AMBIENT), PGP_KEY) is None
    assert generator.signing_mismatch(("Jane Doe", OTHER), PGP_KEY) is not None


def test_the_remedy_is_named(monkeypatch):
    """Every refusal here says how to get past it."""
    carrying(monkeypatch, {AMBIENT})

    for signing in (SSH_KEY, PGP_KEY):
        assert "--no-sign" in generator.signing_mismatch(("Jane Doe", OTHER), signing)
