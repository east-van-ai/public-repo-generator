"""Exercise `prg inspect` end to end, through main().

What is pinned here is the policy: which tags qualify, what order they come
in, and what each line says.
"""

import pytest
from conftest import commit_file, git, init_repo

from prg.cli import main


def inspect_lines(path, capsys, *flags):
    """Run `prg inspect path` and return its output lines, asserting success."""
    assert main(["inspect", str(path), *flags]) == 0
    return capsys.readouterr().out.splitlines()


def stamps(path, capsys, *flags):
    """Return just the timestamp column, one entry per release.

    The last two lines are the blank and the count, so the releases are
    everything before them.
    """
    lines = inspect_lines(path, capsys, *flags)
    return [line.split()[1] for line in lines[:-2]]


def test_inspect_lists_the_reachable_release_tags(repo, capsys):
    lines = inspect_lines(repo, capsys)
    assert lines[0].startswith("v0.1.0")
    assert lines[1].startswith("v0.2.0")


def test_inspect_orders_them_oldest_first(repo, capsys):
    lines = inspect_lines(repo, capsys)
    assert "2026-01-01" in lines[0]
    assert "2026-02-01" in lines[1]


def test_inspect_skips_a_side_branch_tag(repo, capsys):
    assert "v0.3.0" not in "\n".join(inspect_lines(repo, capsys))


def test_inspect_skips_a_tag_outside_the_pattern(repo, capsys):
    assert "release-1" not in "\n".join(inspect_lines(repo, capsys))


def test_a_line_is_a_name_and_a_stamp(repo, capsys):
    """Two columns, and no message.

    v0.1.0 is annotated and v0.2.0 is lightweight, so this also pins that the
    kind of tag no longer changes the shape of the line. The annotation is
    private writing, and it does not cross over.
    """
    for line in inspect_lines(repo, capsys)[:-2]:
        assert len(line.split()) == 2

    assert "First release" not in "\n".join(inspect_lines(repo, capsys))


def test_inspect_counts_the_releases(repo, capsys):
    assert inspect_lines(repo, capsys)[-1] == "2 releases."


def test_inspect_counts_one_release_in_the_singular(tmp_path, capsys):
    path = init_repo(tmp_path / "single", "main")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")
    git(path, "tag", "-a", "v1.0.0", "-m", "Only release")
    assert inspect_lines(path, capsys)[-1] == "1 release."


def test_inspect_orders_by_instant_not_by_text(tmp_path, capsys):
    """The later wall-clock time is the earlier instant here.

    Sorting the ISO strings as text would put v1.0.0 first, since "09:" sorts
    below "10:". Only the offsets say which commit came first.
    """
    path = init_repo(tmp_path / "offsets", "main")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00-08:00")
    git(path, "tag", "-a", "v1.0.0", "-m", "Cut in Vancouver")
    commit_file(path, "second.txt", "second", date="2026-01-01T10:00:00+00:00")
    git(path, "tag", "-a", "v2.0.0", "-m", "Cut in London")

    lines = inspect_lines(path, capsys)
    assert lines[0].startswith("v2.0.0")
    assert lines[1].startswith("v1.0.0")


def test_inspect_breaks_a_shared_date_on_the_tag_name(tmp_path, capsys):
    """Two tags on one commit share a date exactly, so the name decides."""
    path = init_repo(tmp_path / "tied", "main")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")
    git(path, "tag", "-a", "v2.0.0", "-m", "Tagged first")
    git(path, "tag", "-a", "v1.0.0", "-m", "Tagged second")

    lines = inspect_lines(path, capsys)
    assert lines[0].startswith("v1.0.0")
    assert lines[1].startswith("v2.0.0")


def test_inspect_stamps_noon_local_by_default(repo, capsys):
    """The tag's own date, at noon, in the zone prg is running in."""
    assert stamps(repo, capsys) == [
        "2026-01-01T12:00:00-08:00",
        "2026-02-01T12:00:00-08:00",
    ]


def test_tz_gmt_moves_the_stamp(repo, capsys):
    assert stamps(repo, capsys, "--tz", "gmt") == [
        "2026-01-01T12:00:00+00:00",
        "2026-02-01T12:00:00+00:00",
    ]


def test_time_moves_the_clock(repo, capsys):
    assert stamps(repo, capsys, "--time", "09:30:00") == [
        "2026-01-01T09:30:00-08:00",
        "2026-02-01T09:30:00-08:00",
    ]


def same_local_date(tmp_path):
    """Two releases that land on one date once read in Vancouver.

    v2.0.0 is the earlier instant despite the later wall-clock reading, so
    this also pins that the second gets the second, not the alphabetical
    runner-up.
    """
    path = init_repo(tmp_path / "collide", "main")
    commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00-08:00")
    git(path, "tag", "-a", "v1.0.0", "-m", "Cut in Vancouver")
    commit_file(path, "second.txt", "second", date="2026-01-01T10:00:00+00:00")
    git(path, "tag", "-a", "v2.0.0", "-m", "Cut in London")
    return path


def test_a_shared_date_spaces_the_releases_a_second_apart(tmp_path, capsys):
    path = same_local_date(tmp_path)
    assert stamps(path, capsys) == [
        "2026-01-01T12:00:00-08:00",
        "2026-01-01T12:00:01-08:00",
    ]


def test_start_renumbers_what_is_left(tmp_path, capsys):
    """Filtering happens before stamping, so v1.0.0 takes noon exactly.

    It was the second of the pair and held 12:00:01. Alone in the public repo,
    it has the date to itself.
    """
    path = same_local_date(tmp_path)
    assert stamps(path, capsys, "--start", "v1.0.0") == ["2026-01-01T12:00:00-08:00"]


def test_which_releases_collide_depends_on_the_zone(tmp_path, capsys):
    """The same two commits, grouped one way locally and another in GMT.

    Cut on the evening of the 5th and the morning of the 6th in Vancouver.
    That is two dates locally, so both take noon. In GMT the first has already
    rolled over, so the two share the 6th and the second is pushed a second on.
    """
    path = init_repo(tmp_path / "zoned", "main")
    commit_file(path, "first.txt", "first", date="2026-03-05T20:00:00-08:00")
    git(path, "tag", "-a", "v1.0.0", "-m", "Thursday evening")
    commit_file(path, "second.txt", "second", date="2026-03-06T10:00:00-08:00")
    git(path, "tag", "-a", "v2.0.0", "-m", "Friday morning")

    assert stamps(path, capsys) == [
        "2026-03-05T12:00:00-08:00",
        "2026-03-06T12:00:00-08:00",
    ]
    assert stamps(path, capsys, "--tz", "gmt") == [
        "2026-03-06T12:00:00+00:00",
        "2026-03-06T12:00:01+00:00",
    ]


def test_the_offset_comes_from_the_target_date(tmp_path, capsys):
    """Local noon in January and local noon in July are different offsets.

    Both commits were recorded at +00:00. Carrying that offset through, or
    reusing whichever one is in force today, would stamp the pair identically.
    """
    path = init_repo(tmp_path / "dst", "main")
    commit_file(path, "first.txt", "first", date="2026-01-15T12:00:00+00:00")
    git(path, "tag", "-a", "v1.0.0", "-m", "Winter release")
    commit_file(path, "second.txt", "second", date="2026-07-15T12:00:00+00:00")
    git(path, "tag", "-a", "v2.0.0", "-m", "Summer release")

    assert stamps(path, capsys) == [
        "2026-01-15T12:00:00-08:00",
        "2026-07-15T12:00:00-07:00",
    ]


def test_start_drops_the_releases_before_it(repo, capsys):
    lines = inspect_lines(repo, capsys, "--start", "v0.2.0")
    assert lines[0].startswith("v0.2.0")
    assert lines[-1] == "1 release."


def test_an_unknown_start_exits_one(repo, capsys):
    assert main(["inspect", str(repo), "--start", "v9.9.9"]) == 1
    assert capsys.readouterr().err.startswith("prg: ")


@pytest.mark.parametrize("kind", ["plain", "empty", "untagged"])
def test_inspect_exits_one_with_a_message(kind, tmp_path, capsys):
    """A directory prg cannot read releases out of is prg's own error."""
    path = tmp_path / kind
    if kind == "plain":
        path.mkdir()
    else:
        init_repo(path, "main")
    if kind == "untagged":
        commit_file(path, "first.txt", "first", date="2026-01-01T09:00:00+00:00")

    assert main(["inspect", str(path)]) == 1
    assert capsys.readouterr().err.startswith("prg: ")
