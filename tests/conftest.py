"""Shared git fixtures.

Every test that touches git builds its own repo in a temp directory and
supplies its own identity, so the machine's git config stays out of the
results.
"""

import os
import subprocess
import time

import pytest

# Whether the local zone can be moved from inside the process. Unix only, and
# the CI matrix is Ubuntu, so the zone tests run there and skip elsewhere.
CAN_SET_TZ = hasattr(time, "tzset")

# The zone the suite pretends to run in. Somewhere with daylight saving, since
# a fixed-offset zone would let a stamp built from the wrong date's offset pass
# unnoticed.
SUITE_TZ = "America/Vancouver"

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
}

GIT_ISOLATION = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}

# What prg's own preflight finds. Deliberately not `GIT_IDENTITY`: the source
# repo's commits and the identity prg would stamp have to stay tellable apart.
AMBIENT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Suite Ambient",
    "GIT_AUTHOR_EMAIL": "ambient@example.com",
    "GIT_COMMITTER_NAME": "Suite Ambient",
    "GIT_COMMITTER_EMAIL": "ambient@example.com",
}


@pytest.fixture(autouse=True)
def isolated_git_config(monkeypatch):
    """Cut the machine's git config out of every git call in the suite.

    A developer's config can carry a signing key, a tag sort order, or a
    `core.hooksPath`, and any of those changes what git does inside a test.
    A hook that asks for confirmation is the sharp case: it reads the
    terminal, so the suite passes on a build server and hangs on a desk.
    """
    for name, value in GIT_ISOLATION.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def ambient_identity(monkeypatch):
    """Give prg an identity to resolve, since the config it would read is gone.

    `isolated_git_config` points git at /dev/null, which leaves nothing for
    preflight to find, and preflight refuses rather than letting git invent
    one. So the suite plants an identity in the environment, which is the
    other half of what git's own resolution accepts.

    A test that wants the refusal deletes these again.
    """
    for name, value in AMBIENT_IDENTITY.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def local_zone():
    """Pin the zone `--tz local` reads, and hand a test the means to change it.

    Without this the dates the suite expects would move with wherever it runs,
    since local means the machine running prg. Yields a setter, so a test that
    needs a particular zone names one and the rest get the suite's.

    `TZ` is restored by hand rather than through monkeypatch. The C library
    caches the zone until `tzset` is called, so the restore and the call have
    to happen together.
    """
    previous = os.environ.get("TZ")

    def use(name):
        if not CAN_SET_TZ:
            pytest.skip("changing the local zone needs tzset, which is Unix only")
        os.environ["TZ"] = name
        time.tzset()

    if CAN_SET_TZ:
        use(SUITE_TZ)

    yield use

    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    if CAN_SET_TZ:
        time.tzset()


def git(path, *args, date=None):
    """Run a git command in `path` and return its stdout, stripped.

    Raises on failure. Used to build a source repo and to read a built one,
    so the stripping matters: a format that can come back empty, `%p` on a
    root commit, loses its line here. Ask such a question another way.

    `date` fixes both the author and committer date of whatever is created.
    Nothing here reads stdin, so it is closed rather than inherited.
    """
    env = dict(os.environ, **GIT_IDENTITY)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date

    result = subprocess.run(
        ["git"] + list(args),
        cwd=path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def table(lines):
    """Return the release lines out of a printed report.

    A report is three blocks: the values a build would use, the releases, and
    the count. So the releases are what sits between the first blank line and
    the last one, whatever either side grows later.

    Asserts it found some. A caller looping over an empty table would pass
    without testing anything.
    """
    first = lines.index("")
    last = len(lines) - 1 - lines[::-1].index("")
    releases = lines[first + 1 : last]
    assert releases
    return releases


def commit_file(path, name, message, date):
    """Write a file, stage it, and commit it at a fixed date."""
    (path / name).write_text(f"{name}\n")
    git(path, "add", name)
    git(path, "commit", "-m", message, date=date)


def init_repo(path, branch):
    """Create an empty repo at `path` with `branch` as its unborn HEAD."""
    path.mkdir()
    git(path, "init")
    git(path, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    return path


@pytest.fixture
def repo(tmp_path):
    """A repo with two reachable release tags, plus two decoys.

    v0.1.0 is annotated and v0.2.0 is lightweight, so the two kinds of tag
    are both covered. release-1 is outside the release pattern, and v0.3.0
    sits on a side branch that main cannot reach.
    """
    path = init_repo(tmp_path / "source", "main")

    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")
    git(path, "tag", "-a", "v0.1.0", "-m", "First release")

    commit_file(path, "second.txt", "second", date="2026-02-01T09:00:00+00:00")
    git(path, "tag", "v0.2.0")
    git(path, "tag", "-a", "release-1", "-m", "Outside the release pattern")

    git(path, "switch", "-c", "side")
    commit_file(path, "side.txt", "side work", date="2026-03-01T09:00:00+00:00")
    git(path, "tag", "-a", "v0.3.0", "-m", "Side release")
    git(path, "switch", "main")

    return path


@pytest.fixture
def churn_repo(tmp_path):
    """A repo whose two releases differ in more than one way.

    `dropped.txt` ships in v0.1.0 and not in v0.2.0, `added.txt` the other way
    around, and `tool.sh` gains its executable bit between them. `.gitignore`
    names `tracked.txt`, which is tracked all the same, since git keeps
    tracking a file a later rule matches. v0.2.1 sits on v0.2.0's own commit,
    so the two have identical trees.

    The mode is set on the file and in the index both. `chmod` alone misses a
    filesystem that does not carry the bit, and `update-index` alone leaves the
    working tree disagreeing with the index, which is a dirty source repo.
    """
    path = init_repo(tmp_path / "churn", "main")

    (path / ".gitignore").write_text("tracked.txt\n")
    (path / "tracked.txt").write_text("tracked all along\n")
    (path / "dropped.txt").write_text("here for one release\n")
    (path / "tool.sh").write_text("#!/bin/sh\n")
    git(path, "add", "--all", "--force")
    git(path, "commit", "-m", "first", date="2026-01-01T09:00:00+00:00")
    git(path, "tag", "v0.1.0")

    git(path, "rm", "--quiet", "dropped.txt")
    (path / "added.txt").write_text("here from the second\n")
    (path / "tool.sh").chmod(0o755)
    git(path, "add", "--all")
    git(path, "update-index", "--chmod=+x", "tool.sh")
    git(path, "commit", "-m", "second", date="2026-02-01T09:00:00+00:00")
    git(path, "tag", "v0.2.0")
    git(path, "tag", "v0.2.1")

    return path


@pytest.fixture
def master_repo(tmp_path):
    """A one-release repo whose branch is `master`.

    The public branch is always `main`, so proving it needs a source that
    calls its own branch something else.
    """
    path = init_repo(tmp_path / "legacy", "master")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")
    git(path, "tag", "v1.0.0")
    return path
