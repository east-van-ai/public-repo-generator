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
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from itertools import groupby

from prg import gitio

RELEASE_TAG_PATTERN = "v*"
PUBLIC_BRANCH = "main"

# "Name <email>". The name is non-greedy so a name holding no angle bracket
# stops at the last space before the address.
AUTHOR_PATTERN = re.compile(r"^(.+?)\s*<([^<>]+)>$")

DEFAULT_TIME = "12:00:00"
DEFAULT_TZ = "local"
DEFAULT_WEED_OUT = None  # no sanitizer unless --weed-out names one

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

Build = namedtuple("Build", "source target tz time author weed_out start commit")
"""The settings for a single `generate` run.

`commit` is the safety switch. False means report only. `author` of None
means fall back to the ambient git identity. Assembled by `cli_generate`, so
nothing argparse produces reaches this module.
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


def start_at(releases, start):
    """Return the releases from `start` onward, or all of them for None.

    Filtering happens before any timestamp is worked out. The releases that
    do not cross over are not in the public repo, so they take no part in
    deciding which dates collide there.
    """
    if start is None:
        return releases

    for index, release in enumerate(releases):
        if release.name == start:
            return releases[index:]

    raise PRGError(f"--start names no release tag: {start}")


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
        start_at(release_tags(build.source), build.start), build.tz, build.time
    )


def preflight(build):
    """Refuse what a build can know is wrong before it writes anything.

    The target must not exist, since prg deletes nothing it did not create,
    and `--author` must be readable. A dry run runs this too, so both
    failures are met before `--commit` rather than during.
    """
    if os.path.exists(build.target):
        raise PRGError(f"target already exists: {build.target}")
    author_identity(build.author)


def author_identity(author):
    """Split an `--author` value into a name and an email.

    None passes through as None, which asks for whatever git identity is
    configured where prg runs.
    """
    if author is None:
        return None

    match = AUTHOR_PATTERN.match(author.strip())
    if match is None:
        raise PRGError(f'--author is not "Name <email>": {author}')
    return match.group(1), match.group(2)


def reconstruct(build, commits):
    """Build the target repo from `commits`, oldest first.

    Each commit carries no tree yet, so the round records the shape of the
    public repo and none of its contents: the parents, the stamps, the tag
    refs, and the branch. `commits` comes from `plan`, so the build lays down
    exactly what the dry run described.

    A failure part-way names the release it stopped at, and leaves the target
    as it stands.
    """
    identity = author_identity(build.author)
    os.makedirs(build.target)

    try:
        gitio.init(build.target, PUBLIC_BRANCH)
    except gitio.GitError as failure:
        raise PRGError(str(failure)) from failure

    for commit in commits:
        try:
            gitio.commit_empty(build.target, commit.name, commit.stamp, identity)
            gitio.tag(build.target, commit.name)
        except gitio.GitError as failure:
            raise PRGError(f"stopped at {commit.name}: {failure}") from failure
