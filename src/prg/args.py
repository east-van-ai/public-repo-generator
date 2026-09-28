"""The command line's own vocabulary: the parser, and the codes prg exits with.

`cli.py` reads an invocation and sends it somewhere. This module decides what
a valid invocation looks like in the first place.
"""

import argparse
import sys
from datetime import time
from importlib import metadata

from prg import cli_generate, cli_inspect
from prg.generator import DEFAULT_TIME, DEFAULT_TZ, RELEASE_TAG_PATTERN

PROG = "prg"
"""The word typed on the command line, which the parser and `version_line` share."""

PATHS = """\
paths:
  SOURCE    an existing git repo, for `generate` and `inspect`.
  TARGET    the public repo. `generate` needs it not to exist yet.
  Both come right after COMMAND, then options in any order."""
"""The section `prg --help` closes with, since the paths belong to no one command."""

MONOCHROME = {"color": False} if sys.version_info >= (3, 14) else {}
"""argparse's `color=` switch, from 3.14. Older versions print no colour."""


def installed_version():
    """Return the version of the installed public-repo-generator distribution.

    The literal lives in `pyproject.toml` and reaches the CLI through the
    installed metadata, never through a second copy in the source. A checkout
    that was never installed has no metadata to read, and every invocation past
    a bare word builds the parser, so the miss is answered rather than raised.
    See docs/CLI.md, "The version reads the installed metadata".
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


def leading_paths(tokens):
    """Return the tokens ahead of the first flag.

    Every path comes before every flag, so the slots are read off the front of the
    line. Argparse's own positional matches are discarded, since how much it
    back-fills depends on the interpreter version.
    """
    paths = []
    for token in tokens:
        if token.startswith("-"):
            break
        paths.append(token)
    return paths


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
        help="timezone for the uniform timestamp (default: %(default)s)",
    )
    # clock_time is converted here rather than left as a string, so the default and
    # a supplied value arrive as the same type without leaning on argparse putting
    # string defaults through `type` for us.
    parser.add_argument(
        "--time",
        type=clock_time,
        default=clock_time(DEFAULT_TIME),
        metavar="HH:MM:SS",
        help=f"fixed time for every commit (default: {DEFAULT_TIME})",
    )
    parser.add_argument(
        "--start",
        metavar="TAG",
        help=f"begin from this release tag (default: earliest {RELEASE_TAG_PATTERN})",
    )
    parser.add_argument(
        "--end",
        metavar="TAG",
        help=f"stop at this release tag (default: latest {RELEASE_TAG_PATTERN})",
    )


def add_generate(subparsers):
    """Add the `generate` subparser and return it."""
    generate = subparsers.add_parser(
        "generate",
        help=cli_generate.HELP,
        usage=cli_generate.USAGE,
        allow_abbrev=False,
    )
    paths = generate.add_argument_group("paths")
    paths.add_argument(
        "source", metavar="SOURCE", nargs="?", help="the private repo to read"
    )
    paths.add_argument(
        "target", metavar="TARGET", nargs="?", help="the public repo to create"
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
        help="run the weed-out sanitizer over every release tree (default: off)",
    )
    generate.add_argument(
        "--weed-out-keep",
        metavar="LIST",
        help="extra keep entries, comma-separated, added to every release; "
        "turns the sanitizer on by itself",
    )
    generate.add_argument(
        "--no-sign",
        action="store_true",
        help="build unsigned, whatever the git config says",
    )
    mode = generate.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="report the plan and write nothing (default)",
    )
    mode.add_argument(
        "--commit",
        action="store_true",
        help="actually build the repo",
    )
    return generate


def add_inspect(subparsers):
    """Add the `inspect` subparser and return it."""
    inspect = subparsers.add_parser(
        "inspect",
        help=cli_inspect.HELP,
        usage=cli_inspect.USAGE,
        allow_abbrev=False,
    )
    paths = inspect.add_argument_group("paths")
    paths.add_argument(
        "source", metavar="SOURCE", nargs="?", help="the private repo to read"
    )
    add_plan_flags(inspect)
    return inspect


def build_parser():
    """Construct the argument parser for the whole CLI.

    Positional paths are optional to argparse, so that a bare command word
    reaches `main` and gets an answer instead of a usage error. Their parsed
    values go unused: `main` reads the slots itself.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        **MONOCHROME,
        allow_abbrev=False,
        usage=f"{cli_generate.USAGE}\n       {cli_inspect.USAGE}",
        epilog=PATHS,
        # Keeps the epilog's lines as written rather than joined into one paragraph.
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    add_generate(subparsers)
    add_inspect(subparsers)

    version_help = "print the installed version and exit"
    parser.add_argument(
        "--version", action="version", version=version_line(), help=version_help
    )
    subparsers.add_parser("version", help=version_help, allow_abbrev=False)

    return parser


def command_help(add_command):
    """Return one command's own `--help` text, as argparse prints it.

    `add_command` is `add_generate` or `add_inspect`.
    """
    subparsers = argparse.ArgumentParser(prog=PROG, **MONOCHROME).add_subparsers()
    return add_command(subparsers).format_help()
