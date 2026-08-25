"""Exercise the sanitizer layer through main().

The sanitizer under test is a stub on PATH, never the real `weed-out`. What is
pinned here is prg's half: the command line it hands over, when it hands one
over at all, and what it does with the tree that comes back. Whether a keep
list naming `.git/` protects everything under `.git` is weed-out's own
invariant, so two cases cover the plumbing and no more.
"""

import os

import pytest
from conftest import git, table

from prg import generator
from prg.args import EXIT_ERROR, EXIT_OK
from prg.cli import main

# The stub records every invocation, then does whatever the test asked for.
STUB = """#!/usr/bin/env python3
import os
import pathlib
import shutil
import sys

with open(os.environ["STUB_LOG"], "a") as record:
    record.write("\\t".join(sys.argv[1:]) + "\\n")

{body}
"""

# Empty the tree the way a keep list of `.git/` alone would.
EMPTY_IT = """
for entry in os.scandir("."):
    if entry.name == ".git":
        continue
    shutil.rmtree(entry.path) if entry.is_dir() else os.remove(entry.path)
"""

DROP_ONE = """
pathlib.Path("second.txt").unlink(missing_ok=True)
"""

REFUSE = """
sys.stderr.write("weed-out: keep list resolved to nothing\\n")
sys.exit(1)
"""


def without(monkeypatch, missing):
    """Take one binary off PATH, as far as preflight can tell.

    The machine running the suite may well have the real `weed-out` and will
    certainly have `tar`, so the absence has to be arranged rather than found.
    """
    monkeypatch.setattr(
        generator.shutil,
        "which",
        lambda name: None if name == missing else f"/usr/bin/{name}",
    )


@pytest.fixture
def sanitizer(tmp_path, monkeypatch):
    """Put a stub `weed-out` on PATH, and return an installer for its body.

    The installer hands back a reader rather than the log path, so a test asks
    what was invoked instead of knowing where that was written down.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "invocations"
    monkeypatch.setenv("STUB_LOG", str(log))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    def install(body="pass"):
        """Write the stub, and return a reader for the argv it records."""
        script = bin_dir / "weed-out"
        script.write_text(STUB.format(body=body))
        script.chmod(0o755)
        return lambda: [
            line.split("\t")
            for line in (log.read_text() if log.exists() else "").splitlines()
        ]

    return install


def build(source, tmp_path, capsys, *flags):
    """Build a public repo for real, returning its path and printed lines."""
    target = tmp_path / "public"
    assert main(["generate", str(source), str(target), "--commit", *flags]) == EXIT_OK
    return target, capsys.readouterr().out.splitlines()


def tree(path, rev):
    """Return the paths a commit's tree records, sorted."""
    listed = git(path, "ls-tree", "-r", "--name-only", rev)
    return sorted(listed.splitlines())


def test_the_sanitizer_runs_once_per_release(repo, tmp_path, capsys, sanitizer):
    calls = sanitizer()
    _, lines = build(repo, tmp_path, capsys, "--weed-out")

    assert len(calls()) == len(table(lines))


def test_the_command_line_keeps_the_repository(repo, tmp_path, capsys, sanitizer):
    """prg supplies `.git/` itself, so a keep list that forgot it still holds."""
    calls = sanitizer()
    build(repo, tmp_path, capsys, "--weed-out")

    assert calls()[0] == ["delete", ".", "--keep", ".git/", "--commit"]


def test_weed_out_keep_joins_the_keep_list(repo, tmp_path, capsys, sanitizer):
    calls = sanitizer()
    build(repo, tmp_path, capsys, "--weed-out", "--weed-out-keep", "docs/,*.md")

    assert calls()[0][3] == ".git/,docs/,*.md"


def test_the_keep_flag_turns_the_sanitizer_on(repo, tmp_path, capsys, sanitizer):
    """Naming keep entries is an intention to sanitize, so prg reads it as one."""
    calls = sanitizer()
    build(repo, tmp_path, capsys, "--weed-out-keep", "docs/")

    assert calls()
    assert calls()[0][3] == ".git/,docs/"


def test_neither_flag_leaves_the_sanitizer_alone(repo, tmp_path, capsys, sanitizer):
    calls = sanitizer()
    build(repo, tmp_path, capsys)

    assert calls() == []


def test_a_dry_run_never_runs_the_sanitizer(repo, tmp_path, capsys, sanitizer):
    """Nothing is extracted, so there is no tree to sanitize."""
    calls = sanitizer()
    argv = ["generate", str(repo), str(tmp_path / "public"), "--weed-out"]
    assert main(argv) == EXIT_OK

    assert calls() == []


def test_a_missing_sanitizer_is_a_readiness_failure(
    repo, tmp_path, capsys, monkeypatch
):
    """Nothing to run, and the flag still asked for one."""
    without(monkeypatch, "weed-out")
    assert (
        main(["generate", str(repo), str(tmp_path / "public"), "--weed-out"])
        == EXIT_ERROR
    )

    assert "sanitizer not on PATH: weed-out" in capsys.readouterr().err


def test_a_removed_file_is_absent_from_the_commit(repo, tmp_path, capsys, sanitizer):
    sanitizer(DROP_ONE)
    target, _ = build(repo, tmp_path, capsys, "--weed-out")

    assert tree(target, "v0.1.0") == ["first.txt"]
    assert tree(target, "v0.2.0") == ["first.txt"]


def test_the_repository_survives_every_release(repo, tmp_path, capsys, sanitizer):
    """One case, not a suite. `.git/` surviving a keep list is weed-out's own."""
    sanitizer(EMPTY_IT)
    target, _ = build(repo, tmp_path, capsys, "--weed-out")

    assert git(target, "rev-parse", "--git-dir")
    assert git(target, "tag", "--list").splitlines() == ["v0.1.0", "v0.2.0"]


def test_an_emptied_release_commits_empty(repo, tmp_path, capsys, sanitizer):
    """Stopping there would hand back one release per run. The build finishes."""
    sanitizer(EMPTY_IT)
    target, _ = build(repo, tmp_path, capsys, "--weed-out")

    assert git(target, "ls-tree", "-r", "--name-only", "v0.1.0") == ""
    assert git(target, "log", "--format=%s").splitlines()[::-1] == ["v0.1.0", "v0.2.0"]


def test_a_failing_sanitizer_stops_the_build(repo, tmp_path, capsys, sanitizer):
    sanitizer(REFUSE)
    assert (
        main(
            [
                "generate",
                str(repo),
                str(tmp_path / "public"),
                "--commit",
                "--weed-out",
                "true",
            ]
        )
        == EXIT_ERROR
    )

    reported = capsys.readouterr().err
    assert "stopped at v0.1.0" in reported
    assert "keep list resolved to nothing" in reported


def test_a_missing_tar_is_a_readiness_failure(repo, tmp_path, capsys, monkeypatch):
    """Extraction is `git archive` piped into tar, so tar is an ingredient."""
    without(monkeypatch, "tar")
    assert main(["generate", str(repo), str(tmp_path / "public")]) == EXIT_ERROR

    assert "tar is not on PATH" in capsys.readouterr().err
