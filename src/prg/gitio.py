"""Every git invocation prg makes, and the one gpg call that goes with it.

This layer knows how to talk to git and nothing about why. Which tags count
as releases, what timestamp they get, and what order they land in are policy,
and policy lives in `generator.py`.

The gpg call is here for the same reason the git ones are: it shells out, and
it reaches the binary git itself was configured to use. Reading a key's
addresses is asking the signing backend a question about git's own config,
not a second concern.

Read and write both. No reflog expiry and no `gc`: a repo built commit by
commit out of nothing holds nothing unreachable, and its reflog already carries
the manufactured dates. See DESIGN.md, "Clean room, not history rewriting".

`extract` is the one call that does not go through `run_git`. It carries a tar
stream rather than text, and it hands that stream to `tar`.
"""

import os
import re
import shutil
import subprocess

# The address inside a gpg user ID, which reads "Name (comment) <email>".
UID_ADDRESS = re.compile(r"<([^<>]+)>")


class GitError(Exception):
    """A git command exited non-zero, or git could not be run at all."""


def run_git(args, cwd, env=None):
    """Run git with `args` inside `cwd` and return its stdout, stripped.

    Raises GitError on a non-zero exit, carrying git's own stderr. The
    working directory is passed to the subprocess rather than to `git -C`,
    so the command line stays the one a person would type.

    Stdin is closed rather than inherited. No git command prg runs wants
    input, and a git that finds a terminal there can sit waiting on one.
    """
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise GitError(f"could not run git in {cwd}: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise GitError(f"git {' '.join(args)}: {detail}")

    return result.stdout.strip()


def run_binary(args, cwd, payload=None):
    """Run `args` in `cwd` and return its stdout as bytes.

    The bytes twin of `run_git`, for the one call carrying an archive rather
    than text. It raises GitError the same way, so a caller meets one kind of
    failure whichever half of a pipe broke.

    `payload` is written to stdin. Without one, stdin is closed, for the same
    reason `run_git` closes it.
    """
    stream = (
        {"input": payload} if payload is not None else {"stdin": subprocess.DEVNULL}
    )
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, check=False, **stream
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise GitError(f"could not run {args[0]} in {cwd}: {exc}") from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        detail = stderr or f"exit status {result.returncode}"
        raise GitError(f"{' '.join(args)}: {detail}")

    return result.stdout


def git_available():
    """Return True when a git executable is on PATH.

    `shutil.which` rather than a git invocation, because every other question
    here needs a directory to ask it in. This one has to answer before there
    is anywhere to stand.
    """
    return shutil.which("git") is not None


def ambient_identity(cwd):
    """Return the configured git identity as "Name <email>", or None.

    `user.useConfigOnly` stops git inventing an identity out of the account
    name and the hostname, so a refusal here means nothing is configured.
    Either git config or the `GIT_AUTHOR_NAME` and `GIT_AUTHOR_EMAIL`
    variables satisfies it, which is git's own resolution order rather than a
    reimplementation of it.

    `git var` answers with a trailing timestamp and offset, the date it would
    stamp on a commit made this second. Only the identity is wanted, so the
    last two fields go.
    """
    try:
        answer = run_git(
            ["-c", "user.useConfigOnly=true", "var", "GIT_AUTHOR_IDENT"], cwd=cwd
        )
    except GitError:
        return None

    return answer.rsplit(None, 2)[0] or None


def ambient_signing(cwd):
    """Return the configured signing key and format, or None for neither.

    Asked where prg runs, the same place `ambient_identity` asks its own
    question, and for the same reason: a signing key belongs to the identity
    being published under rather than to the machine. Standing somewhere else
    is what selects a different key.

    No `user.signingkey` means no signing at all. A key with no `gpg.format`
    beside it takes openpgp, which is git's own default rather than a choice
    made here.

    No key material passes through. These two values name a key, and git and
    its agent do everything after that.
    """
    try:
        key = run_git(["config", "--get", "user.signingkey"], cwd=cwd)
    except GitError:
        return None

    if not key:
        return None

    try:
        fmt = run_git(["config", "--get", "gpg.format"], cwd=cwd)
    except GitError:
        fmt = ""

    return key, fmt or "openpgp"


def signing_key_emails(key, cwd):
    """Return the addresses an OpenPGP key carries, or None when unanswerable.

    `gpg --list-keys --with-colons` prints one `uid` record per user ID, with
    the ID itself in the tenth field. Only the address inside the angle
    brackets is wanted.

    None means the question could not be answered: no gpg on the machine, a key
    the keyring does not hold, a listing carrying no address. It is not the
    same answer as "this key carries none of them", and a caller that reads it
    as one turns an unanswered question into a refusal.

    The program comes from `gpg.program` where that is set, so the binary asked
    is the binary git would have signed with.
    """
    try:
        program = run_git(["config", "--get", "gpg.program"], cwd=cwd)
    except GitError:
        program = ""

    try:
        listing = subprocess.run(
            [program or "gpg", "--list-keys", "--with-colons", key],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return None

    if listing.returncode != 0:
        return None

    emails = set()
    for line in listing.stdout.splitlines():
        fields = line.split(":")
        if fields[0] == "uid" and len(fields) > 9:
            found = UID_ADDRESS.search(fields[9])
            if found:
                emails.add(found.group(1))

    return emails or None


def is_repo(path):
    """Return True when `path` resolves as a git repository.

    This is git's own notion of the question, so a subdirectory of a repo
    answers True as well.
    """
    try:
        run_git(["rev-parse", "--git-dir"], cwd=path)
    except GitError:
        return False
    return True


def default_branch(path):
    """Return "main" if the repo has it, otherwise "master".

    Raises GitError when neither exists, which includes a repo with no
    commits yet. No remote is consulted: prg never touches one, and a repo
    with neither branch is not something to guess about.
    """
    for name in ("main", "master"):
        try:
            run_git(
                ["rev-parse", "--verify", "--quiet", f"refs/heads/{name}"], cwd=path
            )
        except GitError:
            continue
        return name

    raise GitError(f"no local main or master branch in {path}")


def release_tags(path, branch, pattern):
    """Return the tags matching `pattern` that are reachable from `branch`.

    Reachability is git's answer rather than a walk of prg's own, and the
    order is git's too. Putting releases in order needs commit dates, which
    is the caller's business.
    """
    listed = run_git(["tag", "--list", pattern, "--merged", branch], cwd=path)
    return listed.splitlines()


def commit_date(path, rev):
    """Return the committer date of the commit at `rev`, strict ISO 8601.

    `rev` may name a tag. It is resolved to its commit first, so annotated
    and lightweight tags answer the same way.

    Git writes a zero offset as a trailing "Z". That is valid ISO 8601, but
    `datetime.fromisoformat` cannot read it before Python 3.11, and 3.9 is
    the floor here. It comes back as "+00:00" instead, which means the same
    thing and parses everywhere.
    """
    stamp = run_git(["log", "-1", "--format=%cI", f"{rev}^{{commit}}"], cwd=path)
    if stamp.endswith("Z"):
        return stamp[:-1] + "+00:00"
    return stamp


def init(path, branch):
    """Create an empty repo at `path`, with `branch` unborn.

    `symbolic-ref` rather than `git init --initial-branch`, which arrived in
    git 2.28. The pair works on any git old enough to run the rest of prg,
    and it leaves the branch unborn either way, so the first commit is the
    one that creates it.
    """
    run_git(["init", "--quiet"], cwd=path)
    run_git(["symbolic-ref", "HEAD", f"refs/heads/{branch}"], cwd=path)


def set_identity(path, name, email):
    """Pin an identity into a repo's own config, and forbid a guessed one.

    None of it reaches the build. prg passes the identity through the
    environment, and `GIT_AUTHOR_NAME` outranks `user.name`, so this config
    sits outranked while prg works.

    It is for the commits made in the target by hand afterwards, which would
    otherwise take the ambient identity. `user.useConfigOnly` makes the
    invented identity impossible in this repo rather than merely unnecessary.
    Local config never travels, so this protects the working copy and not the
    published repo. See DESIGN.md, "The target keeps a copy".
    """
    run_git(["config", "user.name", name], cwd=path)
    run_git(["config", "user.email", email], cwd=path)
    run_git(["config", "user.useConfigOnly", "true"], cwd=path)


def set_signing(path, signing):
    """Pin the signing key into a repo's own config, or turn signing off there.

    The other half of `set_identity`, and it reaches the build no more than
    that one does: `commit` passes the key per commit. This is for the
    commits made by hand afterwards, which would otherwise take the key from
    the wider config, meaning the development one beside a public address.

    `None` is an unsigned build, and it writes `commit.gpgsign = false`. There
    is no `user.useConfigOnly` for signing, nothing that makes an inherited key
    impossible, so the switch that reaches the same result is the instruction
    not to sign. A key is written with `commit.gpgsign = true` beside it, so a
    hand-made commit is not the one bare commit in a verified log.

    See DESIGN.md, "The target keeps a copy".
    """
    if signing is None:
        run_git(["config", "commit.gpgsign", "false"], cwd=path)
        return

    key, fmt = signing
    run_git(["config", "user.signingkey", key], cwd=path)
    run_git(["config", "gpg.format", fmt], cwd=path)
    run_git(["config", "commit.gpgsign", "true"], cwd=path)


def extract(source, tag, into):
    """Write `tag`'s tree from `source` into the directory `into`.

    `git archive` reads the tag and writes a tar stream. The source repo is
    never checked out, so nothing is written there, no worktree registration
    has to be unwound, and a build that stops halfway leaves the source as it
    found it.

    `tar` unpacks the stream rather than Python's `tarfile`. Unpacking is the
    kind of work this module already shells out for, and the system unpacker
    lays down the modes and the symlinks git recorded without prg owning any
    extraction semantics of its own across five Python versions. The cost is a
    second binary that has to be there, which on the machines prg runs on it
    already is.

    The stream is held in memory between the two commands. A release tree is
    source code, and buffering keeps git's own stderr readable when the archive
    step is the half that failed.
    """
    archive = run_binary(["git", "archive", "--format=tar", tag], cwd=source)
    run_binary(["tar", "-x", "-f", "-"], cwd=into, payload=archive)


def stage_all(path):
    """Stage the whole working tree, including what a `.gitignore` names.

    `--force` because the tag's tree is the whole instruction. Git lets a file
    stay tracked once it is tracked, so a release can ship a file that a
    `.gitignore` in its own tree also matches. Without `--force` that file
    would drop out of the public commit without a word.

    `--all` covers deletions too, which is what records a file the previous
    release shipped and this one dropped.
    """
    run_git(["add", "--all", "--force"], cwd=path)


def commit(path, message, stamp, identity, signing=None):
    """Record what is staged as a commit, at a fixed date.

    Both dates take `stamp`. Setting only the author date would leave the
    committer date at "now", so the log would show one uniform time beside
    one real one.

    `identity` is a name and email pair, always. Preflight resolved it before
    the build started, so nothing is left for git to work out here. The
    environment is added to rather than replaced, since git still needs PATH
    and HOME.

    Hooks are off permanently. These commits are manufactured, and prg closes
    stdin, so a hook that stops to ask has no terminal to ask on.

    `signing` is a key and format pair, or None for an unsigned commit. The
    values are handed to git on the command line rather than left to the
    target's own config, which holds neither: like the identity, they were
    resolved once before the build and are passed through.

    `-S` rather than a reliance on `commit.gpgsign`, since a key resolved for
    this build is the whole of the instruction to sign. Without a key,
    `--no-gpg-sign` stays, which is every build prg made before.
    """
    name, email = identity
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = stamp.isoformat()
    env["GIT_COMMITTER_DATE"] = stamp.isoformat()
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email

    config = []
    sign = "--no-gpg-sign"
    if signing is not None:
        key, fmt = signing
        config = ["-c", f"user.signingkey={key}", "-c", f"gpg.format={fmt}"]
        sign = "-S"

    run_git(
        # --allow-empty covers two tags sitting on one commit, and two
        # releases whose trees happen to match. A release that crossed over
        # belongs in the public log either way.
        config + ["commit", "--allow-empty", "--no-verify", sign, "-m", message],
        cwd=path,
        env=env,
    )


def tag(path, name):
    """Put a lightweight tag on HEAD.

    No `-a` and no `-m`, so nothing is written but the ref. Nothing written
    means nothing to leak, and no tagger date to keep in step with the
    commit's own.
    """
    run_git(["tag", name], cwd=path)
