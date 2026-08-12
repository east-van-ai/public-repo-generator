"""Exercise the git layer against a real repository.

The fixture builds its own repo in a temp directory and supplies its own
identity, so the machine's git config stays out of the results.
"""

import os
import subprocess
from datetime import datetime

import pytest

from prg import gitio

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


@pytest.fixture(autouse=True)
def isolated_git_config(monkeypatch):
    """Cut the machine's git config out of every git call in this module.

    A developer's config can carry a signing key, a tag sort order, or a
    `core.hooksPath`, and any of those changes what git does inside a test.
    A hook that asks for confirmation is the sharp case: it reads the
    terminal, so the suite passes on a build server and hangs on a desk.
    """
    for name, value in GIT_ISOLATION.items():
        monkeypatch.setenv(name, value)


def git(path, *args, date=None):
    """Run a git command in `path` for test setup, raising on failure.

    `date` fixes both the author and committer date of whatever is created.
    Nothing here reads stdin, so it is closed rather than inherited.
    """
    env = dict(os.environ, **GIT_IDENTITY)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date

    subprocess.run(
        ["git"] + list(args),
        cwd=path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )


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


def test_is_repo_recognizes_a_repo(repo):
    assert gitio.is_repo(repo) is True


def test_is_repo_rejects_a_plain_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert gitio.is_repo(plain) is False


def test_default_branch_prefers_main(repo):
    assert gitio.default_branch(repo) == "main"


def test_default_branch_falls_back_to_master(tmp_path):
    path = init_repo(tmp_path / "old", "master")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")
    assert gitio.default_branch(path) == "master"


def test_default_branch_raises_without_either(tmp_path):
    path = init_repo(tmp_path / "empty", "main")
    with pytest.raises(gitio.GitError):
        gitio.default_branch(path)


def test_release_tags_finds_the_reachable_matches(repo):
    assert set(gitio.release_tags(repo, "main", "v*")) == {"v0.1.0", "v0.2.0"}


def test_release_tags_skips_a_side_branch_tag(repo):
    assert "v0.3.0" not in gitio.release_tags(repo, "main", "v*")


def test_release_tags_skips_a_tag_outside_the_pattern(repo):
    assert "release-1" not in gitio.release_tags(repo, "main", "v*")


def test_release_tags_is_empty_without_a_match(repo):
    assert gitio.release_tags(repo, "main", "nothing-*") == []


def test_commit_date_reads_the_tagged_commit(repo):
    assert gitio.commit_date(repo, "v0.1.0").startswith("2026-01-01")


def test_commit_date_handles_a_lightweight_tag(repo):
    assert gitio.commit_date(repo, "v0.2.0").startswith("2026-02-01")


def test_commit_date_is_strict_iso(repo):
    parsed = datetime.fromisoformat(gitio.commit_date(repo, "v0.1.0"))
    assert parsed.tzinfo is not None


def test_commit_date_spells_out_a_zero_offset(repo):
    """Git writes UTC as a trailing "Z", which fromisoformat rejects before
    Python 3.11. The floor is 3.9, so it has to come back spelled out."""
    assert gitio.commit_date(repo, "v0.1.0").endswith("+00:00")


def test_commit_date_leaves_other_offsets_alone(tmp_path):
    path = init_repo(tmp_path / "offset", "main")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00-08:00")
    assert gitio.commit_date(path, "main").endswith("-08:00")


def test_tag_message_reads_an_annotation(repo):
    assert gitio.tag_message(repo, "v0.1.0") == "First release"


def test_tag_message_is_empty_for_a_lightweight_tag(repo):
    """A lightweight tag has no message of its own, so git offers the
    commit's. That is a private message and must not leak through."""
    assert gitio.tag_message(repo, "v0.2.0") == ""


def test_tag_message_is_empty_for_an_unknown_name(repo):
    assert gitio.tag_message(repo, "v9.9.9") == ""


def test_run_git_raises_with_gits_own_stderr(repo):
    with pytest.raises(gitio.GitError) as failure:
        gitio.run_git(["log", "-1", "nosuchref"], cwd=repo)
    assert "nosuchref" in str(failure.value)


def test_run_git_raises_outside_a_repo(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(gitio.GitError):
        gitio.run_git(["status"], cwd=plain)


def test_run_git_raises_for_a_missing_directory(tmp_path):
    with pytest.raises(gitio.GitError):
        gitio.run_git(["status"], cwd=tmp_path / "gone")
