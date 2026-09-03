"""The command line's own vocabulary: the parser, and the codes prg exits with.

`cli.py` reads an invocation and sends it somewhere. This module decides what
a valid invocation looks like in the first place.
"""

import argparse
from datetime import time
from importlib import metadata

from prg import cli_generate, cli_inspect
from prg.generator import DEFAULT_TIME, DEFAULT_TZ, RELEASE_TAG_PATTERN

# Argparse hardcodes 2 in `ArgumentParser.error()`, which calls `sys.exit`
# itself, so EXIT_ARGPARSE never returns through `main` and is only asserted
# against. See DESIGN.md, "Positions are decided, not inferred".
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

PROG = "prg"
"""The word typed on the command line, which the parser and `version_line` share."""


def installed_version():
    """Return the version of the installed public-repo-generator distribution.

    The literal lives in `pyproject.toml` and reaches the CLI through the
    installed metadata, never through a second copy in the source. A checkout
    that was never installed has no metadata to read, and every invocation past
    a bare word builds the parser, so the miss is answered rather than raised.
    See DESIGN.md, "`--version` reads the installed metadata".
    """
    try:
        return metadata.version("public-repo-generator")
    except metadata.PackageNotFoundError:
        return "unknown (not installed)"


def version_line():
    """Return the program name and the installed version on one line.

    Both `version` and `--version` print this, so the two spellings cannot
    drift apart. The name printed is `prg`, the word that was typed, not
    `public-repo-generator`, the distribution the number was read from.
    """
    return f"{PROG} {installed_version()}"


def clock_time(value):
    """Parse an HH:MM:SS argument, for argparse's `type=`.

    Raising here puts a bad `--time` in argparse's own vocabulary, exit 2,
    alongside the bad `--tz` that `choices` already catches.
    """
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an HH:MM:SS time: {value!r}") from None


def add_plan_flags(parser):
    """Add the flags deciding which releases cross over and what stamp they get.

    `generate` and `inspect` share all four, and they have to. A preview whose
    stamps came from different defaults would be previewing a build nobody is
    going to run, and one listing releases the build will skip would be
    previewing something else again.
    """
    parser.add_argument(
        "--tz",
        choices=["local", "gmt"],
        default=DEFAULT_TZ,
        help="Timezone for the uniform timestamp (default: %(default)s)",
    )
    parser.add_argument(
        "--time",
        type=clock_time,
        # Converted here rather than left as a string, so the default and a
        # supplied value arrive as the same type without leaning on argparse
        # putting string defaults through `type` for us.
        default=clock_time(DEFAULT_TIME),
        metavar="HH:MM:SS",
        help=f"Fixed time for every commit (default: {DEFAULT_TIME})",
    )
    parser.add_argument(
        "--start",
        metavar="TAG",
        help=f"Begin from this release tag (default: earliest {RELEASE_TAG_PATTERN})",
    )
    parser.add_argument(
        "--end",
        metavar="TAG",
        help=f"Stop at this release tag (default: latest {RELEASE_TAG_PATTERN})",
    )


def build_parser():
    """Construct the argument parser for the whole CLI.

    Positional paths are optional to argparse, so that a bare command word
    reaches `main` and gets an answer instead of a usage error. Their parsed
    values go unused: `main` reads the slots itself.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Public Repo Generator: build a curated public repo from a private one."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version_line(),
        help="Print the installed version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # Carries no arguments and no flags, which is what makes argparse reject
    # `prg version --tz gmt` as an unknown flag. `main` prints the line.
    subparsers.add_parser("version", help="Print the installed version and exit.")

    generate = subparsers.add_parser(
        "generate", help=cli_generate.HELP, description=cli_generate.HELP
    )
    generate.add_argument(
        "source", metavar="SOURCE", nargs="?", help="Private repo to read"
    )
    generate.add_argument(
        "target", metavar="TARGET", nargs="?", help="Public repo to create"
    )
    add_plan_flags(generate)
    generate.add_argument(
        "--author",
        metavar="IDENTITY",
        help='"Name <email>" for author and committer (default: git config)',
    )
    generate.add_argument(
        "--weed-out",
        action="store_true",
        help="Run the weed-out sanitizer over every release tree "
        "(default: off, nothing is filtered)",
    )
    generate.add_argument(
        "--weed-out-keep",
        metavar="LIST",
        help="Extra keep entries, comma-separated, added to every release. "
        "Turns the sanitizer on by itself",
    )
    generate.add_argument(
        "--no-sign",
        action="store_true",
        help="Build unsigned, whatever the git config says",
    )
    mode = generate.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the plan and write nothing. This is the default.",
    )
    mode.add_argument(
        "--commit",
        action="store_true",
        help="Actually build the repo",
    )

    inspect = subparsers.add_parser(
        "inspect", help=cli_inspect.HELP, description=cli_inspect.HELP
    )
    inspect.add_argument(
        "source", metavar="SOURCE", nargs="?", help="Private repo to read"
    )
    add_plan_flags(inspect)

    return parser
