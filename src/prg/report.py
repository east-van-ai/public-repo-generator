"""How a report is laid out.

Both commands print the same page: the values a build would use, the releases
it would lay down, and a count. One renderer is what makes DESIGN.md's claim
hold, that a preview cannot drift from the build it previews. Two copies of
these loops could drift, and would.

Presentation only. Nothing here decides anything, and nothing that decides
anything prints.
"""


def identity(pair, absent):
    """Render a name and email pair, or `absent` when there is none.

    The words for no identity are the caller's, because the two commands owe
    the reader different things. `generate` lists the consequence among its
    failures. `inspect` has no failure list, so it says it on this line or not
    at all.
    """
    if pair is None:
        return absent
    return "{} <{}>".format(*pair)


NO_SIGNING = "none, commits will not be signed"


def signing(pair):
    """Render a signing key and its format, or the words for no key at all.

    The words live here rather than with the caller, unlike `identity`. An
    unsigned build is not a failure in either command, so neither has anything
    of its own to add to the other's wording.

    The format is printed beside the key because it decides what the key is:
    a path to an SSH public key, or an OpenPGP key ID.
    """
    if pair is None:
        return NO_SIGNING

    key, fmt = pair
    return f"{key} ({fmt})"


def page(values, commits):
    """Print the values, then the release table, then the count.

    `values` is a list of label and text pairs, assembled by each command for
    itself. What a build would use differs between the two: `inspect` has no
    target to name and no sanitizer to run.

    The table reads newest first, the way `git log` does. `plan` returns the
    commits oldest first, because that is the order a build lays them down in,
    so the reversal happens here at the last possible moment.
    """
    label = max(len(name) for name, _ in values)
    for name, text in values:
        print(f"{name:<{label}}  {text}")

    print()
    width = max(len(commit.name) for commit in commits)
    for commit in reversed(commits):
        print(f"{commit.name:<{width}}  {commit.stamp.isoformat()}")

    print(f"\n{len(commits)} release{'' if len(commits) == 1 else 's'}.")
