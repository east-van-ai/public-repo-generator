"""The one call prg makes to `weed-out`, and the keep list it hands over.

`weed-out` is a companion tool rather than a dependency. prg shells out to it,
so nothing here imports it and nothing here reads its file format. What this
module knows is how to invoke it and what to do when it comes back non-zero.

It does not check the tool's work afterwards. Whether `.git/` in a keep list
protects everything under `.git` is `weed-out`'s own invariant, and a caller
cannot do better than report what came back. See DESIGN.md, "Where the
sanitizer runs".
"""

import subprocess

# The entry prg supplies on every run, whatever the tag's own keep list says.
# A keep list written for a working repo names `.git/` already; one that
# forgets it would take the repository out with everything else, and the
# protection has to come from the caller to hold for a list prg never saw.
KEEP_ROOT = ".git/"


class SanitizeError(Exception):
    """The sanitizer exited non-zero, or could not be run at all."""


def keep_list(extra):
    """Return the `--keep` value for a run, `.git/` first.

    `extra` is `--weed-out-keep`, or None. Both sources are comma-separated
    the way the flag is, so joining them is the whole of the work: `weed-out`
    merges the result with the tag's own `.weed-out-ignore` and dedupes it.
    """
    if not extra:
        return KEEP_ROOT
    return f"{KEEP_ROOT},{extra}"


def run(command, tree, extra=None):
    """Sanitize `tree` in place, keeping `.git/` and whatever `extra` names.

    `delete` rather than `trash`, and `--commit` rather than a dry run. The
    tree is one prg extracted seconds earlier out of a tag that still exists,
    so there is nothing here worth recovering, and a preview would leave the
    staging step recording the tree unfiltered.

    The path argument is `.` and the directory is passed to the subprocess, so
    the command line stays the one a person would type.

    Stdout is discarded. A per-release listing of what went would bury the
    report, and stderr is kept only to carry a failure back.
    """
    argv = [command, "delete", ".", "--keep", keep_list(extra), "--commit"]
    try:
        result = subprocess.run(
            argv,
            cwd=tree,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError) as failure:
        raise SanitizeError(f"could not run {command}: {failure}") from failure

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise SanitizeError(f"{' '.join(argv)}: {detail}")
