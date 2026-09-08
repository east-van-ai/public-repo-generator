"""Exercise the `prg-msg/` commit message override, through main().

What is pinned here is the binding: which release a marker names, what its
message becomes, and the three ways a marker is refused. A marker's own target
takes no part in any of it, which is the whole point of putting the version in
the name.
"""

from conftest import git, table

from prg.args import EXIT_ERROR, EXIT_OK
from prg.cli import main

OVERRIDE = "baseline v0.1.0 -- CLI surface and the git read layer"


def mark(path, version, *message, at=None):
    """Put an annotated `prg-msg/` marker for `version` on the repo at `path`.

    Several `message` arguments become several paragraphs, which is how a
    marker gets a body under its subject. `at` is what the marker points at,
    and leaving it off means HEAD, exactly as git would.
    """
    lines = []
    for paragraph in message:
        lines += ["-m", paragraph]
    git(path, "tag", "-a", *lines, f"prg-msg/{version}", *([at] if at else []))


def inspect_table(path, capsys, *flags):
    """Run `prg inspect`, assert it passed, and return its release lines."""
    assert main(["inspect", str(path), *flags]) == EXIT_OK
    return table(capsys.readouterr().out.splitlines())


def refusal(path, capsys, *flags):
    """Run `prg inspect`, assert it refused, and return what it said."""
    assert main(["inspect", str(path), *flags]) == EXIT_ERROR
    return capsys.readouterr().err


def public_log(source, tmp_path, capsys):
    """Build for real, and return the public commit subjects, oldest first."""
    target = tmp_path / "public"
    assert main(["generate", str(source), str(target), "--commit"]) == EXIT_OK
    capsys.readouterr()
    return target, git(target, "log", "--format=%s").splitlines()[::-1]


def test_a_marker_replaces_the_release_name(repo, tmp_path, capsys):
    mark(repo, "v0.1.0", OVERRIDE)
    _, subjects = public_log(repo, tmp_path, capsys)
    assert subjects == [OVERRIDE, "v0.2.0"]


def test_a_release_with_no_marker_keeps_its_tag_name(repo, tmp_path, capsys):
    """Which is every release in most builds, and the behaviour before this."""
    _, subjects = public_log(repo, tmp_path, capsys)
    assert subjects == ["v0.1.0", "v0.2.0"]


def test_only_the_subject_of_a_marker_crosses(repo, tmp_path, capsys):
    """A body under the message is prose nobody chose to publish."""
    mark(repo, "v0.1.0", OVERRIDE, "A paragraph written for no one.")
    _, subjects = public_log(repo, tmp_path, capsys)
    assert subjects == [OVERRIDE, "v0.2.0"]


def test_the_marker_itself_does_not_cross_over(repo, tmp_path, capsys):
    mark(repo, "v0.1.0", OVERRIDE)
    target, _ = public_log(repo, tmp_path, capsys)
    assert git(target, "tag", "-l").splitlines() == ["v0.1.0", "v0.2.0"]


def test_the_markers_own_target_does_not_matter(repo, tmp_path, capsys):
    """Only the name binds, so a marker made at HEAD reaches its own release."""
    mark(repo, "v0.1.0", OVERRIDE)
    assert git(repo, "rev-parse", "prg-msg/v0.1.0^{commit}") == git(
        repo, "rev-parse", "v0.2.0^{commit}"
    )

    _, subjects = public_log(repo, tmp_path, capsys)
    assert subjects == [OVERRIDE, "v0.2.0"]


def test_a_lightweight_marker_is_refused(repo, capsys):
    """It carries no message of its own, while looking exactly like one that
    does: the ref points at a commit, whose subject git reports in its place."""
    git(repo, "tag", "prg-msg/v0.1.0")
    assert "prg-msg/v0.1.0 is lightweight" in refusal(repo, capsys)


def test_a_marker_with_an_empty_message_is_refused(repo, capsys):
    """`git tag -a -m ""` is accepted by git, and overrides nothing here."""
    mark(repo, "v0.1.0", "")
    assert "prg-msg/v0.1.0 carries an empty message" in refusal(repo, capsys)


def test_a_marker_naming_no_release_is_refused(repo, capsys):
    """A typo would otherwise do nothing at all, and say nothing about it."""
    mark(repo, "v9.9.9", OVERRIDE)
    said = refusal(repo, capsys)
    assert "prg-msg/v9.9.9 names no release tag: v9.9.9" in said


def test_a_refused_marker_stops_generate_as_well(repo, tmp_path, capsys):
    """The preview refuses what the build refuses, or it is not a preview."""
    mark(repo, "v9.9.9", OVERRIDE)
    target = tmp_path / "public"
    assert main(["generate", str(repo), str(target), "--commit"]) == EXIT_ERROR
    assert "prg-msg/v9.9.9" in capsys.readouterr().err
    assert not target.exists()


def test_a_marker_outside_the_span_is_not_a_mistake(repo, capsys):
    """That release is not in this build. Nothing about it is wrong."""
    mark(repo, "v0.1.0", OVERRIDE)
    lines = inspect_table(repo, capsys, "--start", "v0.2.0")
    assert len(lines) == 1
    assert lines[0].startswith("v0.2.0")
    assert OVERRIDE not in lines[0]


def test_releases_on_one_commit_take_only_their_own_marker(
    churn_repo, tmp_path, capsys
):
    """v0.2.0 and v0.2.1 share a commit, and a marker names one of them."""
    mark(churn_repo, "v0.2.1", OVERRIDE)
    _, subjects = public_log(churn_repo, tmp_path, capsys)
    assert subjects == ["v0.1.0", "v0.2.0", OVERRIDE]


def test_the_message_column_appears_only_when_a_marker_does(repo, capsys):
    """With no override it would print the first column again on every row."""
    assert [len(line.split()) for line in inspect_table(repo, capsys)] == [2, 2]

    mark(repo, "v0.1.0", OVERRIDE)
    lines = inspect_table(repo, capsys)
    assert lines[0].split()[2:] == ["v0.2.0"]
    assert lines[1].endswith(OVERRIDE)
