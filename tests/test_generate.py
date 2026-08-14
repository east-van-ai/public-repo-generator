"""Exercise `prg generate` end to end, through main().

What is pinned here is what only `generate` does: whether it writes at all,
and the shape of the repo it builds. Which tags qualify, what order they come
in, and what stamp each one gets belong to `plan`, and `test_inspect.py`
already covers them through that same code.

Nothing here reads a file out of a built repo. `generate` records no trees
yet, and a test asserting an empty one would have to be rewritten the moment
it records a real one.
"""

from conftest import git

from prg.cli import main

AUTHOR = "Jane Doe <jane@example.com>"


def generate(source, target, capsys, *flags):
    """Run `prg generate source target`, assert success, return its lines."""
    assert main(["generate", str(source), str(target), *flags]) == 0
    return capsys.readouterr().out.splitlines()


def table(lines):
    """Return the release lines, dropping the blank and the closing summary.

    Asserts it found some. A caller looping over an empty table would pass
    without testing anything.
    """
    releases = lines[:-2]
    assert releases
    return releases


def build(source, tmp_path, capsys, *flags):
    """Build a public repo for real, returning its path and printed lines."""
    target = tmp_path / "public"
    return target, generate(source, target, capsys, "--commit", *flags)


def log(path, fmt):
    """Return one entry per commit, oldest first, formatted by `fmt`.

    `git log` walks HEAD's ancestry, so a commit reaching this list is one
    the branch actually descends from.
    """
    return git(path, "log", f"--format={fmt}").splitlines()[::-1]


def test_a_dry_run_writes_nothing(repo, tmp_path, capsys):
    """The default mode reports and stops. Nothing appears on disk."""
    target = tmp_path / "public"
    generate(repo, target, capsys)
    assert not target.exists()


def test_an_existing_target_is_refused(repo, tmp_path, capsys):
    """prg does not delete anything it did not create."""
    target = tmp_path / "public"
    target.mkdir()
    (target / "keep.txt").write_text("mine\n")

    assert main(["generate", str(repo), str(target), "--commit"]) == 1
    assert "target already exists" in capsys.readouterr().err
    assert (target / "keep.txt").read_text() == "mine\n"


def test_a_malformed_author_stops_before_anything_is_written(repo, tmp_path, capsys):
    """preflight runs ahead of the build, so a bad identity costs no directory."""
    target = tmp_path / "public"
    argv = ["generate", str(repo), str(target), "--author", "Jane Doe", "--commit"]

    assert main(argv) == 1
    assert not target.exists()


def test_one_commit_per_release_oldest_first(repo, tmp_path, capsys):
    target, _ = build(repo, tmp_path, capsys)
    assert log(target, "%s") == ["v0.1.0", "v0.2.0"]


def test_the_chain_is_linear_from_a_single_root(repo, tmp_path, capsys):
    """Ancestry is the payload, so the releases sit in one line of descent."""
    target, _ = build(repo, tmp_path, capsys)

    assert git(target, "rev-list", "--count", "HEAD") == "2"
    assert git(target, "rev-list", "--max-parents=0", "HEAD").splitlines() == [
        git(target, "rev-parse", "v0.1.0")
    ]


def test_the_public_branch_is_main_whatever_the_source_calls_it(
    master_repo, tmp_path, capsys
):
    target, _ = build(master_repo, tmp_path, capsys)
    assert git(target, "symbolic-ref", "HEAD") == "refs/heads/main"


def test_a_private_tag_annotation_does_not_cross_over(repo, tmp_path, capsys):
    """v0.1.0 is annotated "First release" in the source. The public commit
    message is the tag name and nothing else."""
    target, _ = build(repo, tmp_path, capsys)
    assert git(target, "log", "-1", "--format=%B", "v0.1.0") == "v0.1.0"


def test_each_release_gets_a_lightweight_tag(repo, tmp_path, capsys):
    """Lightweight whatever the source used, so nothing is written but the ref.

    The source's v0.1.0 is annotated, which is an object of its own. Here the
    name resolves straight to a commit.
    """
    target, _ = build(repo, tmp_path, capsys)

    assert git(target, "tag", "--list").splitlines() == ["v0.1.0", "v0.2.0"]
    assert git(target, "cat-file", "-t", "v0.1.0") == "commit"


def test_a_tag_names_its_own_commit(repo, tmp_path, capsys):
    target, _ = build(repo, tmp_path, capsys)
    for name in ("v0.1.0", "v0.2.0"):
        assert git(target, "log", "-1", "--format=%s", name) == name


def test_both_dates_carry_the_uniform_stamp(repo, tmp_path, capsys):
    """Setting only the author date would leave one real clock in the log."""
    target, lines = build(repo, tmp_path, capsys)

    for line in table(lines):
        name, stamp = line.split()
        assert git(target, "log", "-1", "--format=%aI", name) == stamp
        assert git(target, "log", "-1", "--format=%cI", name) == stamp


def test_author_sets_both_the_author_and_the_committer(repo, tmp_path, capsys):
    target, _ = build(repo, tmp_path, capsys, "--author", AUTHOR)

    assert log(target, "%an <%ae>") == [AUTHOR, AUTHOR]
    assert log(target, "%cn <%ce>") == [AUTHOR, AUTHOR]


def test_the_ambient_identity_comes_through(repo, tmp_path, capsys, monkeypatch):
    """Without --author, prg names nobody and git uses what it finds.

    The identity is planted in the environment rather than read from the
    machine. Git guesses an address from the hostname when nothing is
    configured at all, and that guess differs from one machine to the next.
    """
    ambient = "Ambient Dev <ambient@example.com>"
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Ambient Dev")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "ambient@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Ambient Dev")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "ambient@example.com")

    target, _ = build(repo, tmp_path, capsys)

    assert log(target, "%an <%ae>") == [ambient, ambient]
    assert log(target, "%cn <%ce>") == [ambient, ambient]


def test_the_dry_run_and_the_build_print_the_same_table(repo, tmp_path, capsys):
    """The preview is the build's own plan, not a second description of it."""
    preview = generate(repo, tmp_path / "preview", capsys)
    real = generate(repo, tmp_path / "public", capsys, "--commit")

    assert table(preview) == table(real)
