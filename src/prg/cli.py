"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~ ~~~ ~~~ ~~~ ~~~ prg ~~~ ~~~ ~~~ ~~~ ~~~
#
# From a private repo, this CLI generates a new public repo holding only the
# v* release tags found on main/master.
#
# Usage:
#
#    prg generate SOURCE TARGET [--dry-run | --commit] [options]
#    prg inspect SOURCE [options]
#
# Commands:
#
#    generate    Rebuild TARGET from SOURCE's v* release tags.
#    inspect     List the tags that would become commits.
#
# SOURCE  an existing git repo, for `generate` and `inspect`.
# TARGET  the public repo. `generate` requires that it does not exist yet.
#
# Run a command with nothing else after it for its own documentation,
# including the options it takes:
#
#    prg generate
#    prg inspect
#
# Paths come first, then flags, whose order among themselves is free. Bare
# `prg` prints this text and exits 0. Asking is not a usage error.
#
# prg reads no piped input.
#
# Exit codes:
#
#    0:     success, and documentation
#    1:     prg's own error, a path missing or one too many included, or an
#           ingredient a build needs that is not there
#    2:     an unknown command, an unknown flag, or a bad value
#
# License: MIT
# ==============================================
"""

import argparse
import sys
from collections import namedtuple
from datetime import time

from prg import cli_generate, cli_inspect
from prg.generator import (
    DEFAULT_TIME,
    DEFAULT_TZ,
    DEFAULT_WEED_OUT,
    RELEASE_TAG_PATTERN,
    PRGError,
)

# Exit codes. 0 is success, and documentation too, since asking what a command
# does is not an error. 1 is prg's own: a path slot short, a path too many, or
# anything the pipeline raises. 2 is argparse's, for the vocabulary it owns,
# an unknown command, an unknown flag, a bad value.
#
# Only the first two return through `main`. Argparse calls `sys.exit` itself,
# so 2 arrives as a SystemExit unwinding past `main`, and a test for it catches
# rather than compares. See DESIGN.md, "Positions are decided, not inferred",
# for where the 1/2 line falls and why.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2  # argparse hardcodes it in `ArgumentParser.error()`

Command = namedtuple("Command", "module slots")
"""A command word's module, and the path slots it reads.

The module carries its own documentation, usage line, and action, so the
table only adds what the command line itself decides.
"""

COMMANDS = {
    "generate": Command(cli_generate, ("SOURCE", "TARGET")),
    "inspect": Command(cli_inspect, ("SOURCE",)),
}


def clock_time(value):
    """Parse an HH:MM:SS argument, for argparse's `type=`.

    Raising here puts a bad `--time` in argparse's own vocabulary, exit 2,
    alongside the bad `--tz` that `choices` already catches.
    """
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an HH:MM:SS time: {value!r}") from None


def leading_paths(tokens):
    """Return the tokens ahead of the first flag.

    The documented grammar puts every path before every flag, so the slots
    are read off the front of the command line. What argparse resolved from
    anywhere else is discarded, since how much it tolerates depends on the
    interpreter. See DESIGN.md, "Positions are decided, not inferred".
    """
    paths = []
    for token in tokens:
        if token.startswith("-"):
            break
        paths.append(token)
    return paths


def usage_error(command, message):
    """Report a command line prg could not read, with that command's usage.

    The usage line belongs here and nowhere else. A readiness failure exits 1
    too, and printing the usage beside it would answer a question nobody
    asked: the command line was right, and something it needed was missing.
    See DESIGN.md, "Readiness failures print no usage line".
    """
    print(f"prg: {message}", file=sys.stderr)
    print(f"Usage: {command.module.USAGE}", file=sys.stderr)
    return EXIT_ERROR


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
        prog="prg",
        description=(
            "Public Repo Generator: build a curated public repo from a private one."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

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
        default=DEFAULT_WEED_OUT,
        metavar="CMD",
        help="Path to the weed-out sanitizer (default: none, nothing is filtered)",
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


def main(argv=None):
    """Parse arguments, dispatch to a command module, and return an exit code.

    A command word and nothing else is a question and gets documentation,
    exit 0. Any other shortfall in the path slots is a slip and gets an
    error, exit 1. argparse keeps the vocabulary it owns: an unknown command,
    an unknown flag, or a bad value, exiting 2.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)

    if not tokens:
        print(__doc__.strip())
        return EXIT_OK

    if len(tokens) == 1 and tokens[0] in COMMANDS:
        print(COMMANDS[tokens[0]].module.__doc__.strip())
        return EXIT_OK

    parser = build_parser()
    args, extras = parser.parse_known_args(tokens)

    if any(extra.startswith("-") for extra in extras):
        parser.parse_args(tokens)  # argparse names the flag better, exit 2

    command = COMMANDS[args.command]
    paths = leading_paths(tokens[1:])

    if len(paths) < len(command.slots):
        needed = " and ".join(command.slots)
        if len(command.slots) > 1:
            needed = f"both {needed}"
        return usage_error(command, f"{args.command} needs {needed}")

    if len(paths) > len(command.slots):
        stray = paths[len(command.slots)]
        last = command.slots[-1]
        return usage_error(
            command, f"{args.command} takes nothing after {last}: {stray!r}"
        )

    # Each command's run() takes what that command needs, so the call is spelled
    # out rather than driven off the table. The table answers what is the same
    # for every command: its documentation, its usage line, and its slots.
    try:
        if args.command == "generate":
            cli_generate.run(paths[0], paths[1], args)
        else:
            cli_inspect.run(paths[0], args)
    except PRGError as failure:
        # A readiness failure is the verdict on a report already printed, so
        # stdout goes out first. Redirected, it block-buffers while stderr does
        # not, and the verdict would otherwise arrive ahead of what it judges.
        sys.stdout.flush()
        print(f"prg: {failure}", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
