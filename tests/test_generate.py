"""Exercise `prg generate` end to end, through main().

What is pinned here is what only `generate` does: whether it writes at all,
and the shape of the repo it builds. Which tags qualify, what order they come
in, and what stamp each one gets belong to `plan`, and `test_inspect.py`
already covers them through that same code.

The tree tests read a built repo through `git ls-tree` rather than off the
filesystem. What crossed over is what the commit records, and the working tree
left behind after the last release is a side effect of building it.
"""

import subprocess

import pytest
from conftest import git, init_repo, table

from prg.args import EXIT_ERROR, EXIT_OK
from prg.cli import main

AUTHOR = "Jane Doe <jane@example.com>"


def generate(source, target, capsys, *flags):
    """Run `prg generate source target`, assert success, return its lines."""
    assert main(["generate", str(source), str(target), *flags]) == EXIT_OK
    return capsys.readouterr().out.splitlines()


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


def tree(path, rev):
    """Return a rev's tree as a path to file-mode mapping.

    `git ls-tree -r` prints `<mode> <type> <sha>\t<path>`, so the tab is what
    separates the path from the rest and a path holding a space survives.
    """
    entries = git(path, "ls-tree", "-r", rev).splitlines()
    return {line.split("\t", 1)[1]: line.split()[0] for line in entries}


def local_config(path):
    """Return a repo's own config as a name to value mapping.

    The whole list rather than one `--get` per name, because half of what
    these tests assert is that a name is absent, and `--get` answers that by
    failing.
    """
    entries = git(path, "config", "--local", "--list").splitlines()
    return dict(entry.split("=", 1) for entry in entries)


def ssh_key(path):
    """Make a passphrase-less SSH key at `path`, and return its public half.

    The suite's own key, so nothing here depends on one being on the machine,
    and no personal key is ever handed to a test.
    """
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "prg suite", "-f", path],
        check=True,
        capture_output=True,
    )
    return f"{path}.pub"


def signing_repo(path, key):
    """A repo whose own config names `key` as its SSH signing key.

    prg reads the signing values where it runs, so a build signs by being run
    from a directory configured to sign. One directory per account is the
    swap this rests on.
    """
    repo = init_repo(path, "main")
    git(repo, "config", "user.signingkey", key)
    git(repo, "config", "gpg.format", "ssh")
    return repo


def signed(path, rev):
    """Return True when the commit object at `rev` carries a signature.

    The object itself, never `git log --show-signature` or `%G?`. SSH
    verification wants an allowed-signers file, and with none configured both
    of those report a perfectly good signature as an absence.
    """
    header = git(path, "cat-file", "commit", rev).splitlines()
    return any(line.startswith("gpgsig") for line in header)


def ssh_signing_works(tmp_path):
    """Whether this git and this ssh-keygen can sign a commit between them.

    A probe rather than a version comparison. Git learned SSH signing in 2.34
    and prg runs on older, so what matters is what the pair on this machine
    can actually do.
    """
    repo = signing_repo(tmp_path / "probe", ssh_key(tmp_path / "id_probe"))
    try:
        git(repo, "commit", "--allow-empty", "-S", "-m", "probe")
    except subprocess.CalledProcessError:
        return False
    return signed(repo, "HEAD")


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

    assert main(["generate", str(repo), str(target), "--commit"]) == EXIT_ERROR
    assert "target already exists" in capsys.readouterr().err
    assert (target / "keep.txt").read_text() == "mine\n"


def test_a_malformed_author_stops_before_anything_is_written(repo, tmp_path, capsys):
    """preflight runs ahead of the build, so a bad identity costs no directory."""
    target = tmp_path / "public"
    argv = ["generate", str(repo), str(target), "--author", "Jane Doe", "--commit"]

    assert main(argv) == EXIT_ERROR
    assert not target.exists()


def test_one_commit_per_release_oldest_first(repo, tmp_path, capsys):
    target, _ = build(repo, tmp_path, capsys)
    assert log(target, "%s") == ["v0.1.0", "v0.2.0"]


def test_a_release_holds_the_files_its_tag_held(churn_repo, tmp_path, capsys):
    """The whole tree crosses over, not a summary of it."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert tree(target, "v0.1.0") == tree(churn_repo, "v0.1.0")
    assert tree(target, "v0.2.0") == tree(churn_repo, "v0.2.0")


def test_a_dropped_file_is_gone_from_the_later_release(churn_repo, tmp_path, capsys):
    """Each commit is the whole tree, so the wipe has to reach the last one."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert "dropped.txt" in tree(target, "v0.1.0")
    assert "dropped.txt" not in tree(target, "v0.2.0")


def test_the_public_log_shows_the_drop_as_a_deletion(churn_repo, tmp_path, capsys):
    """What a reader comparing two releases expects to see."""
    target, _ = build(churn_repo, tmp_path, capsys)
    changes = git(target, "diff", "--name-status", "v0.1.0", "v0.2.0").splitlines()
    assert "D\tdropped.txt" in changes


def test_an_added_file_reaches_only_the_later_release(churn_repo, tmp_path, capsys):
    target, _ = build(churn_repo, tmp_path, capsys)
    assert "added.txt" not in tree(target, "v0.1.0")
    assert "added.txt" in tree(target, "v0.2.0")


def test_a_tracked_file_a_gitignore_names_still_ships(churn_repo, tmp_path, capsys):
    """Staging without --force would drop it, and say nothing about it."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert "tracked.txt" in tree(target, "v0.1.0")


def test_the_executable_bit_crosses_over(churn_repo, tmp_path, capsys):
    """A tar stream carries the mode git recorded, so a script stays runnable."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert tree(target, "v0.1.0")["tool.sh"] == "100644"
    assert tree(target, "v0.2.0")["tool.sh"] == "100755"


def test_two_tags_on_one_commit_both_reach_the_public_log(churn_repo, tmp_path, capsys):
    """Identical trees are a fact about the releases, not an error."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert log(target, "%s") == ["v0.1.0", "v0.2.0", "v0.2.1"]
    assert tree(target, "v0.2.0") == tree(target, "v0.2.1")


def test_the_target_survives_every_release(churn_repo, tmp_path, capsys):
    """The wipe runs once per release and never reaches `.git`."""
    target, _ = build(churn_repo, tmp_path, capsys)
    assert (target / ".git").is_dir()
    assert git(target, "status", "--porcelain") == ""


def test_the_source_is_left_as_it_was(churn_repo, tmp_path, capsys):
    """git archive reads the tag. Nothing is checked out on the private side."""
    before = git(churn_repo, "rev-parse", "HEAD")
    build(churn_repo, tmp_path, capsys)

    assert git(churn_repo, "status", "--porcelain") == ""
    assert git(churn_repo, "rev-parse", "HEAD") == before
    assert not (churn_repo / ".git" / "worktrees").exists()


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


def test_a_build_is_unsigned_when_no_key_is_configured(repo, tmp_path, capsys):
    """No key where prg runs means no signature, which is every build so far."""
    target, _ = build(repo, tmp_path, capsys)

    assert [signed(target, name) for name in ("v0.1.0", "v0.2.0")] == [False, False]


def test_every_commit_is_signed_with_the_key_where_prg_runs(
    repo, tmp_path, capsys, monkeypatch
):
    """The key comes from the directory prg is run from, not from the target.

    Standing in a repo configured to sign is what turns signing on, and the
    tags are the reason to check every commit rather than HEAD: a tag pointing
    at an unsigned commit is a release with no signature.
    """
    if not ssh_signing_works(tmp_path):
        pytest.skip("this git and ssh-keygen cannot sign a commit between them")

    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    target, _ = build(repo, tmp_path, capsys)

    assert [signed(target, name) for name in ("v0.1.0", "v0.2.0")] == [True, True]


def test_no_sign_builds_unsigned_with_a_key_configured(
    repo, tmp_path, capsys, monkeypatch
):
    """The one flag signing has, and the way to comparable hashes."""
    if not ssh_signing_works(tmp_path):
        pytest.skip("this git and ssh-keygen cannot sign a commit between them")

    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    target, _ = build(repo, tmp_path, capsys, "--no-sign")

    assert [signed(target, name) for name in ("v0.1.0", "v0.2.0")] == [False, False]


def test_an_author_the_key_disagrees_with_is_refused(repo, tmp_path, monkeypatch):
    """The pair names two accounts, which can only build an Unverified repo.

    The suite's ambient identity is what supplied the key, so an `--author`
    naming another address is the mismatch prg exists to catch.
    """
    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    target = tmp_path / "public"

    assert main(["generate", str(repo), str(target), "--author", AUTHOR, "--commit"])
    assert not target.exists()


def test_the_refusal_names_no_sign_as_the_way_out(repo, tmp_path, capsys, monkeypatch):
    """A refusal that leaves no route forward is only half a message."""
    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    argv = ["generate", str(repo), str(tmp_path / "public"), "--author", AUTHOR]

    assert main(argv) == EXIT_ERROR
    assert "--no-sign" in capsys.readouterr().err


def test_no_sign_settles_the_disagreement(repo, tmp_path, capsys, monkeypatch):
    """Refusing over a key nobody is going to use would be a refusal too many."""
    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    target, _ = build(repo, tmp_path, capsys, "--author", AUTHOR, "--no-sign")

    assert log(target, "%an <%ae>") == [AUTHOR, AUTHOR]
    assert not signed(target, "v0.1.0")


def test_an_author_restating_the_configured_address_still_signs(
    repo, tmp_path, capsys, monkeypatch
):
    """Naming the address the key already belongs to is not a mismatch.

    This is the case a rule of "--author means unsigned" would have got wrong.
    """
    if not ssh_signing_works(tmp_path):
        pytest.skip("this git and ssh-keygen cannot sign a commit between them")

    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    ambient = "Suite Ambient <ambient@example.com>"
    target, _ = build(repo, tmp_path, capsys, "--author", ambient)

    assert signed(target, "v0.1.0")


def test_the_report_names_the_key_a_build_would_use(
    repo, tmp_path, capsys, monkeypatch
):
    """A dry run says which key, so a wrong swap shows before the push."""
    key = ssh_key(tmp_path / "id_named")
    monkeypatch.chdir(signing_repo(tmp_path / "signer", key))

    lines = generate(repo, tmp_path / "public", capsys)
    values = [line for line in lines if line.startswith("signing")]

    assert values == [f"signing    {key} (ssh)"]


def test_the_release_range_reaches_the_build(repo, tmp_path, capsys):
    """The wiring, not the policy.

    Which releases a range leaves is `plan`'s business and `test_inspect.py`
    covers it through that same code. What only `generate` can get wrong is
    passing the bound on, and an `--end` that never reached `Build` would
    quietly build the whole set.
    """
    rows = table(generate(repo, tmp_path / "public", capsys, "--end", "v0.1.0"))

    assert len(rows) == 1
    assert rows[0].startswith("v0.1.0")


def test_the_dry_run_and_the_build_print_the_same_table(repo, tmp_path, capsys):
    """The preview is the build's own plan, not a second description of it."""
    preview = generate(repo, tmp_path / "preview", capsys)
    real = generate(repo, tmp_path / "public", capsys, "--commit")

    assert table(preview) == table(real)


def test_the_target_keeps_the_identity_in_its_own_config(repo, tmp_path, capsys):
    """A hand-made commit in the target later must not take the dev identity."""
    target, _ = build(repo, tmp_path, capsys, "--author", AUTHOR)

    assert git(target, "config", "--local", "user.name") == "Jane Doe"
    assert git(target, "config", "--local", "user.email") == "jane@example.com"
    assert git(target, "config", "--local", "user.useConfigOnly") == "true"


def test_the_target_keeps_the_signing_key_in_its_own_config(
    repo, tmp_path, capsys, monkeypatch
):
    """The other half of the identity pin, and it names the format too.

    The format decides what the key is, an SSH path or an OpenPGP key ID, so a
    config carrying one without the other only works by luck.
    """
    if not ssh_signing_works(tmp_path):
        pytest.skip("this git and ssh-keygen cannot sign a commit between them")

    key = ssh_key(tmp_path / "id_pinned")
    monkeypatch.chdir(signing_repo(tmp_path / "signer", key))
    target, _ = build(repo, tmp_path, capsys)

    assert local_config(target)["user.signingkey"] == key
    assert local_config(target)["gpg.format"] == "ssh"
    assert local_config(target)["commit.gpgsign"] == "true"


def test_an_unsigned_build_turns_signing_off_in_the_target(repo, tmp_path, capsys):
    """No key resolved means the target says do not sign here.

    There is no `user.useConfigOnly` for signing, so without this line a
    hand-made commit later takes whatever key the wider config names, which is
    the development one beside a public address.
    """
    target, _ = build(repo, tmp_path, capsys)
    config = local_config(target)

    assert config["commit.gpgsign"] == "false"
    assert "user.signingkey" not in config


def test_no_sign_turns_signing_off_in_the_target_too(
    repo, tmp_path, capsys, monkeypatch
):
    """A key is configured here, and the flag keeps it out of the target.

    The case the flag exists for on a machine that signs everything. Silence
    would leave that key one hand-made commit away.
    """
    if not ssh_signing_works(tmp_path):
        pytest.skip("this git and ssh-keygen cannot sign a commit between them")

    monkeypatch.chdir(signing_repo(tmp_path / "signer", ssh_key(tmp_path / "id_test")))
    target, _ = build(repo, tmp_path, capsys, "--no-sign")
    config = local_config(target)

    assert config["commit.gpgsign"] == "false"
    assert "user.signingkey" not in config


def no_identity(monkeypatch):
    """Take away everything preflight could resolve an identity from.

    The suite's git config already points at /dev/null, so the environment is
    all that is left to remove.
    """
    for name in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL"):
        monkeypatch.delenv(name)


def test_no_identity_refuses_to_build(repo, tmp_path, capsys, monkeypatch):
    """Git would invent one from the account and the hostname. prg will not."""
    no_identity(monkeypatch)
    target = tmp_path / "public"

    assert main(["generate", str(repo), str(target), "--commit"]) == EXIT_ERROR
    assert not target.exists()
    assert "no git identity configured" in capsys.readouterr().err


def test_a_readiness_failure_still_prints_the_whole_report(
    repo, tmp_path, capsys, monkeypatch
):
    """The report is the deliverable. The exit code is the verdict on it."""
    no_identity(monkeypatch)

    assert main(["generate", str(repo), str(tmp_path / "public")]) == EXIT_ERROR
    printed = capsys.readouterr()

    assert [line.split()[0] for line in table(printed.out.splitlines())] == [
        "v0.2.0",
        "v0.1.0",
    ]
    assert "not configured" in printed.out


def test_every_missing_ingredient_is_named_at_once(repo, tmp_path, capsys, monkeypatch):
    """One run per fix is what a stopping-at-the-first check would cost."""
    no_identity(monkeypatch)
    target = tmp_path / "public"
    target.mkdir()

    assert (
        main(["generate", str(repo), str(target), "--weed-out", "no-such-tool"])
        == EXIT_ERROR
    )
    failures = capsys.readouterr().err

    assert "no git identity configured" in failures
    assert "target already exists" in failures
    assert "sanitizer not on PATH" in failures


def test_a_readiness_failure_prints_no_usage_line(repo, tmp_path, capsys, monkeypatch):
    """The command line was right. Its usage answers a question nobody asked."""
    no_identity(monkeypatch)

    assert main(["generate", str(repo), str(tmp_path / "public")]) == EXIT_ERROR
    assert "Usage:" not in capsys.readouterr().err


def test_a_missing_git_is_fatal_before_any_report(repo, tmp_path, capsys, monkeypatch):
    """Without git there is no table to print, so there is nothing to report."""
    monkeypatch.setenv("PATH", "")

    assert main(["generate", str(repo), str(tmp_path / "public")]) == EXIT_ERROR
    printed = capsys.readouterr()

    assert "git is not on PATH" in printed.err
    assert printed.out == ""
