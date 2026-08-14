"""Exercise the git layer against a real repository.

The fixture and its helpers live in conftest.py, shared with the other
test modules.
"""

from datetime import datetime

import pytest
from conftest import commit_file, init_repo

from prg import gitio


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
