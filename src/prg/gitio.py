"""Every git invocation prg makes.

This layer knows how to talk to git and nothing about why. Which tags count
as releases, what timestamp they get, and what order they land in are policy,
and policy lives in `generator.py`.

Read and write both. No reflog expiry and no `gc`: a repo built commit by
commit out of nothing holds nothing unreachable, and its reflog already carries
the manufactured dates. See DESIGN.md, "Clean room, not history rewriting".
"""

import os
import subprocess


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


def commit_empty(path, message, stamp, identity=None):
    """Record a commit carrying no tree at all, at a fixed date.

    Both dates take `stamp`. Setting only the author date would leave the
    committer date at "now", so the log would show one uniform time beside
    one real one.

    `identity` is a name and email pair, or None to let git use whatever is
    configured where prg runs. The environment is added to rather than
    replaced, since git still needs PATH and HOME.

    Hooks are off permanently. These commits are manufactured, and prg closes
    stdin, so a hook that stops to ask has no terminal to ask on.

    `--no-gpg-sign` overrides `commit.gpgsign`, so a machine configured to sign
    has that switched off here. It is a suppression waiting to be lifted rather
    than a decision to keep. See DESIGN.md, "Signing is opt-in".
    """
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = stamp.isoformat()
    env["GIT_COMMITTER_DATE"] = stamp.isoformat()
    if identity is not None:
        name, email = identity
        env["GIT_AUTHOR_NAME"] = name
        env["GIT_AUTHOR_EMAIL"] = email
        env["GIT_COMMITTER_NAME"] = name
        env["GIT_COMMITTER_EMAIL"] = email

    run_git(
        # --allow-empty is what makes a commit with no tree possible, and it
        # leaves with the trees. An empty tree is an error once there is one.
        ["commit", "--allow-empty", "--no-verify", "--no-gpg-sign", "-m", message],
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
