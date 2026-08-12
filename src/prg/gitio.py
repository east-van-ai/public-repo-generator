"""Every git invocation prg makes.

This layer knows how to talk to git and nothing about why. Which tags count
as releases, what timestamp they get, and what order they land in are policy,
and policy lives in `generator.py`.

Read-only for now. The write side (init, commit, tag, gc) arrives with the
pipeline that needs it, so nothing here has a caller yet.
"""

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


def tag_message(path, tag):
    """Return the tag's annotation, or "" for a lightweight tag.

    The object type is checked first, and it has to be. A lightweight tag is
    a ref straight to a commit, so asking git for its contents hands back the
    commit's own message. That message is private, and it must not reach the
    public log by way of a tag that never carried one.

    A name that matches no tag also answers "", since git reports an empty
    list rather than failing.
    """
    listed = run_git(
        ["tag", "--list", tag, "--format=%(objecttype)%0a%(contents)"], cwd=path
    )
    kind, _, contents = listed.partition("\n")
    return contents.strip() if kind == "tag" else ""
