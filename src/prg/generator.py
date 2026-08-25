"""The build policy: which tags cross over, and what they become.

Everything here answers a "why" question. Which tags count as releases, what
timestamp each one gets, and what order they land in.
The "how" of talking to git lives in `gitio.py`, and the printing of what
comes back lives in the `cli_<command>.py` modules. Nothing here writes to
stdout, so the policy can be tested without capturing it.

Functions, not a class. Each step takes the settings it uses rather than a
whole bundle, so a step growing a long parameter list stays visible as a step
doing too much. Only `reconstruct` takes the `Build` entire, because
orchestrating is what it is for.
"""

import os
import re
import shutil
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from itertools import groupby

from prg import gitio, sanitizer

RELEASE_TAG_PATTERN = "v*"
PUBLIC_BRANCH = "main"

# The sanitizer prg shells out to. `--weed-out` is a switch rather than a path,
# so PATH is what says where this lives. See DESIGN.md, "The sanitizer is named,
# not located".
WEED_OUT_COMMAND = "weed-out"

# "Name <email>". The name is non-greedy so a name holding no angle bracket
# stops at the last space before the address.
AUTHOR_PATTERN = re.compile(r"^(.+?)\s*<([^<>]+)>$")

DEFAULT_TIME = "12:00:00"
DEFAULT_TZ = "local"

# What `--tz` selects. None is the machine's own zone, and it stays None rather
# than becoming a fixed offset now: the offset a date gets has to be the one in
# force on that date, not the one in force today. `astimezone` reads None as
# local, so the same value serves both the conversion and the construction.
ZONE_BY_NAME = {"local": None, "gmt": timezone.utc}

Release = namedtuple("Release", "name date")
"""One tag that would become a public commit: its name and its date."""

PublicCommit = namedtuple("PublicCommit", "name stamp")
"""What a release tag becomes: its name and its uniform stamp.

`Release` is what git reported. This is what the public repo would carry, so
the date has been replaced by the timestamp the commit would actually get.

No message field. The public commit message is the tag name, so `name` is
already carrying it. See DESIGN.md, "Commit message".
"""

Build = namedtuple(
    "Build",
    "source target tz time author weed_out weed_out_keep start end commit",
)
"""The settings for a single `generate` run.

`commit` is the safety switch. False means report only. `author` of None
means fall back to the ambient git identity. `weed_out` is already resolved:
`cli_generate` folds `--weed-out-keep`'s implication into it, so everything
downstream reads one answer. Assembled by `cli_generate`, so nothing argparse
produces reaches this module.
"""


Ingredients = namedtuple("Ingredients", "identity signing failures")
"""What preflight resolved, and what it found missing.

`identity` is the name and email pair every public commit would carry, or
None when none could be resolved. `signing` is the key and format those
commits would be signed with, or None for an unsigned build. `failures` is
what stops a build, and it is empty when the table is the whole of what there
is to say.
"""


class PRGError(Exception):
    """An error prg raises itself. The CLI turns it into exit code 1."""


def release_tags(source):
    """Return the release tags reachable from main/master, oldest first.

    Tags on another branch are skipped, and so are tags that do not match
    the release pattern. Annotated and lightweight tags answer alike, since
    nothing here reads a tag's message.

    Sorting is by the date of the commit each tag points at. Two tags on
    one commit share that date exactly and nothing in the graph orders
    them, so the tag name breaks the tie: arbitrary, but stable.
    """
    if not gitio.is_repo(source):
        raise PRGError(f"not a git repo: {source}")

    try:
        branch = gitio.default_branch(source)
        releases = [
            Release(name, gitio.commit_date(source, name))
            for name in gitio.release_tags(source, branch, RELEASE_TAG_PATTERN)
        ]
    except gitio.GitError as failure:
        raise PRGError(str(failure)) from failure

    if not releases:
        raise PRGError(
            f"no {RELEASE_TAG_PATTERN} tags reachable from {branch} in {source}"
        )

    return sorted(
        releases,
        key=lambda release: (datetime.fromisoformat(release.date), release.name),
    )


def bound_index(releases, name, flag):
    """Return the position of the release `name`, or raise naming `flag`.

    A bound naming no release tag is an error rather than a silent fallback to
    the earliest or the latest. The flag is passed in so the message names the
    one that was actually typed.
    """
    for index, release in enumerate(releases):
        if release.name == name:
            return index

    raise PRGError(f"{flag} names no release tag: {name}")


def span(releases, start, end):
    """Return the releases from `start` to `end`, both inclusive.

    Either bound may be None, which leaves that end of the range where it is.

    Filtering happens before any timestamp is worked out. The releases that
    do not cross over are not in the public repo, so they take no part in
    deciding which dates collide there.

    A pair leaving nothing to build is an error, and the message names both
    bounds. Either one alone looks perfectly reasonable, so naming only the
    one that lost would send the reader to the wrong flag. Reaching that check
    means both were given: a None bound sits at an end of the list and cannot
    cross the other.
    """
    first = 0 if start is None else bound_index(releases, start, "--start")
    last = len(releases) - 1 if end is None else bound_index(releases, end, "--end")

    if first > last:
        raise PRGError(f"--end {end} comes before --start {start}")

    return releases[first : last + 1]


def resolved_date(moment, zone):
    """Return the calendar date an instant falls on, read in `zone`.

    A stored commit date carries the committer's own offset, so the date git
    reports is the date where the commit was made. The public commit carries
    the date in the chosen zone instead, which is not always the same one.
    """
    return moment.astimezone(zone).date()


def public_commits(releases, tz, clock):
    """Stamp each release with the timestamp its public commit would carry.

    Releases are grouped by their date in the chosen zone, and each group is
    ordered by the instant its commits were made. Grouping is by key rather
    than by adjacency: sorting on the instant alone does not guarantee that
    releases sharing a date sit next to each other, since a zone whose
    daylight saving transition falls at midnight can rewind the local date.

    Ordering is on the parsed instant, never on the date git printed. Two
    releases an hour apart can carry ISO text that sorts the other way round,
    since each string holds the offset of the machine that made it.
    """
    zone = ZONE_BY_NAME[tz]

    dated = []
    for release in releases:
        moment = datetime.fromisoformat(release.date)
        dated.append((resolved_date(moment, zone), moment, release))
    dated.sort(key=lambda entry: entry[:2])

    commits = []
    for date, group in groupby(dated, key=lambda entry: entry[0]):
        for ordinal, (_, _, release) in enumerate(group):
            commits.append(
                PublicCommit(
                    release.name,
                    uniform_timestamp(zone, clock, date, ordinal),
                )
            )
    return commits


def uniform_timestamp(zone, clock, date, ordinal):
    """Return `date` at `clock` in `zone`, pushed on by `ordinal` seconds.

    `ordinal` is the release's position among those sharing that date. The
    first takes the clock exactly, the second one second later, and so on, so
    same-day releases keep their order.

    The offset comes from the target date, never from the source commit. A
    naive datetime handed to `astimezone` is read as local wall time and gets
    the offset in force on that date, which is what local noon means in both
    August and December.
    """
    naive = datetime.combine(date, clock)
    stamp = naive.astimezone() if zone is None else naive.replace(tzinfo=zone)
    return stamp + timedelta(seconds=ordinal)


def plan(build):
    """Return the public commits a build would make, oldest first.

    Everything a dry run needs, and everything a real build works from. The
    two run the same code so the preview cannot drift from the build.
    """
    return public_commits(
        span(release_tags(build.source), build.start, build.end), build.tz, build.time
    )


def sanitizing(weed_out, weed_out_keep):
    """Return whether a build runs the sanitizer.

    `--weed-out-keep` answers yes on its own. Naming extra keep entries is an
    intention to sanitize, so prg reads it as one rather than refusing a
    command line whose meaning was never in doubt. Whether the sanitizer can
    actually be run is `preflight`'s question, not this one.

    Resolved once, in `cli_generate`, and carried in the `Build`. Deriving it
    twice is how a report and a build come to disagree.
    """
    return bool(weed_out or weed_out_keep)


def preflight(source, target=None, author=None, sanitize=False, sign=True):
    """Check the ingredients a build needs, and resolve the values it would use.

    Runs once, after the command line is parsed and before any of the work.
    `target` is None for a command that writes nothing, and `sanitize` False
    for one that runs no sanitizer, so those checks are skipped rather than
    passed.

    `sign` False is `--no-sign`, and it resolves no key at all. Nothing is
    checked about a key that will not be used.

    Two kinds of result. Git missing is fatal and raises, because without it
    there is no report to produce and nothing to say about it. Everything else
    comes back in `failures`, so a caller can print the whole page before
    deciding what the exit code should be. See DESIGN.md, "Ingredients before
    the build".

    `source` is named for the checks that will join it here. Its own shape is
    still `release_tags`' to judge, and that judgement is fatal too.
    """
    if not gitio.git_available():
        raise PRGError("git is not on PATH")

    failures = []

    # Extraction is `git archive` piped into `tar`, so tar is the second binary
    # every build shells out to. Checked whether or not a sanitizer runs, since
    # every build extracts. Not fatal like git: the table still prints, and
    # printing it is how the gap gets found.
    if shutil.which("tar") is None:
        failures.append("tar is not on PATH")

    identity = author_identity(author)
    if identity is None:
        identity = resolved_identity()
        if identity is None:
            failures.append(
                "no git identity configured: set user.name and user.email, "
                "or pass --author"
            )

    signing = resolved_signing() if sign else None

    if identity is not None:
        disagreement = signing_mismatch(identity, signing)
        if disagreement is not None:
            failures.append(disagreement)

    if target is not None and os.path.exists(target):
        failures.append(f"target already exists: {target}")

    if sanitize and shutil.which(WEED_OUT_COMMAND) is None:
        failures.append(f"sanitizer not on PATH: {WEED_OUT_COMMAND}")

    return Ingredients(identity, signing, failures)


def resolved_identity():
    """Return the ambient git identity as a name and email pair, or None.

    Asked in prg's own working directory, which is what "the identity
    configured where prg runs" means. The target is not consulted and could
    not be: it does not exist yet, and by the time it does the identity has
    already been decided and passed in.

    A value git returns in a shape `--author` would not accept reads as no
    identity at all. Reporting it as a malformed `--author` would name a flag
    nobody used.
    """
    ambient = gitio.ambient_identity(os.getcwd())
    return None if ambient is None else parse_identity(ambient)


def resolved_signing():
    """Return the signing key and format configured where prg runs, or None.

    prg's own working directory, the same one `resolved_identity` reads. The
    key and the identity are two halves of one decision, so they come from one
    place: a directory configured for the account being published to answers
    with that account's key.

    Never a failure. No key configured means an unsigned build, which is what
    every build made before this existed.
    """
    return gitio.ambient_signing(os.getcwd())


def signing_mismatch(identity, signing):
    """Return why a key and an author disagree, or None when they can agree.

    A host verifies a commit by asking whether the committer's address is
    verified on the account holding the key. A pair naming two accounts can
    only produce a signed repo that reads Unverified, so it is worth refusing
    over. See DESIGN.md, "The key and the address have to agree".

    Addresses are compared and names ignored, since the address is what a host
    judges.

    An OpenPGP key can be asked directly, and its own user IDs settle it. That
    also catches a config naming `user.email` in one scope while inheriting
    `user.signingkey` from another. When the key cannot be read, and always for
    SSH, the comparison falls back to the identity the config supplied, which
    rests on the two having been written as a pair.

    No key means nothing to disagree with.
    """
    if signing is None:
        return None

    _, email = identity
    key, fmt = signing
    remedy = f"pass --no-sign, or build where {email}'s key is configured"

    if fmt == "openpgp":
        carried = gitio.signing_key_emails(key, os.getcwd())
        if carried is not None:
            if email in carried:
                return None
            return f"signing key {key} carries no address for {email}: {remedy}"

    ambient = resolved_identity()
    if ambient is None or ambient[1] == email:
        return None

    return f"the signing key here belongs to {ambient[1]}, not {email}: {remedy}"


def parse_identity(value):
    """Split "Name <email>" into its two parts, or None when it is neither."""
    match = AUTHOR_PATTERN.match(value.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def author_identity(author):
    """Split an `--author` value into a name and an email.

    None passes through as None, which sends preflight to the ambient git
    identity instead. A value that will not parse is prg's own error, since
    the flag was typed and typed wrongly.
    """
    if author is None:
        return None

    identity = parse_identity(author)
    if identity is None:
        raise PRGError(f'--author is not "Name <email>": {author}')
    return identity


def clear_worktree(target):
    """Empty the target's working tree, everything except `.git`.

    Each public commit records the whole tree rather than a layer over the
    release before it, so the previous release's files go before the next
    ones land. `git add --all` then reads a file dropped between two releases
    as the deletion it is, with no bookkeeping of prg's own.

    Filesystem work rather than git work, which is why it sits here and not in
    `gitio`.

    This is the one destructive thing prg does, and it is confined to a
    directory prg created: `preflight` refuses a target that already exists,
    so nothing sitting in there arrived any other way. A link is unlinked
    rather than followed, so nothing outside the tree is reachable from here.
    """
    for entry in os.scandir(target):
        if entry.name == ".git":
            continue
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.path)
        else:
            os.remove(entry.path)


def reconstruct(build, commits, identity, signing):
    """Build the target repo from `commits`, oldest first.

    Each release is laid down whole: the working tree is emptied, the tag's
    tree is extracted into it, and what landed becomes the commit. `commits`
    comes from `plan`, so the build lays down exactly what the dry run
    described.

    `identity` and `signing` are what preflight resolved, passed in rather
    than worked out again here. One resolution means the report and the
    commits cannot disagree, which is the whole point of printing the key
    before the build rather than after the push.

    Both go into the target's own config as well as onto every commit. That
    copy is for the commits made there by hand later, and it changes nothing
    about this build.

    With `weed_out`, the sanitizer runs over each extracted tree before
    anything is staged. A tree it empties is committed like any other: stopping
    there would hand back one release per run while already knowing about the
    rest, and the log shows every empty release at once instead.

    A failure part-way names the release it stopped at, and leaves the target
    as it stands. The `try` wraps the loop rather than its body: every step
    inside re-raises, so the first failure ends the build either way, and the
    loop variable is still bound to the release that failed.
    """
    os.makedirs(build.target)

    try:
        gitio.init(build.target, PUBLIC_BRANCH)
        gitio.set_identity(build.target, *identity)
        gitio.set_signing(build.target, signing)
    except gitio.GitError as failure:
        raise PRGError(str(failure)) from failure

    try:
        for commit in commits:
            clear_worktree(build.target)
            gitio.extract(build.source, commit.name, build.target)
            if build.weed_out:
                sanitizer.run(WEED_OUT_COMMAND, build.target, build.weed_out_keep)
            gitio.stage_all(build.target)
            gitio.commit(build.target, commit.name, commit.stamp, identity, signing)
            gitio.tag(build.target, commit.name)
    except (gitio.GitError, sanitizer.SanitizeError, OSError) as failure:
        raise PRGError(f"stopped at {commit.name}: {failure}") from failure
