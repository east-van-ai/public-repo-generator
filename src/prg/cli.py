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
#    prg inspect SOURCE
#
# Commands:
#
#    generate    Rebuild TARGET from SOURCE's v* release tags.
#    inspect     List the tags that would become commits.
#
# SOURCE  an existing git repo, for `generate` and `inspect`.
# TARGET  the public repo. `generate` requires that it does not exist yet.
#
# Options for `generate`:
#
#    --tz {local,gmt}    timezone for the uniform timestamp (default: local)
#    --time HH:MM:SS     fixed time for every commit (default: 12:00:00)
#    --author IDENTITY   "Name <email>" for author and committer
#    --weed-out CMD      path to the weed-out sanitizer (default: weed-out)
#    --start TAG         begin from this release tag (default: earliest v*)
#    --dry-run           report the plan and write nothing. The default.
#    --commit            actually build the repo.
#
# Flags come after the command and its paths. Their order among themselves is
# free. Bare `prg` prints this help.
#
# STATUS: blueprint. The CLI surface below is settled, and the git layer in
# gitio.py works. The pipeline behind `generate` does not. See DESIGN.md for
# the reasoning.
#
# License: MIT
# ==============================================
"""

import argparse
import sys

from prg.generator import (
    DEFAULT_TIME,
    DEFAULT_TZ,
    DEFAULT_WEED_OUT,
    PRG,
    RELEASE_TAG_PATTERN,
)

EXIT_OK = 0
EXIT_ERROR = 1


def build_parser():
    """Construct the argument parser for the whole CLI."""
    parser = argparse.ArgumentParser(
        prog="prg",
        description=(
            "Public Repo Generator: build a curated public repo from a private one."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    generate = subparsers.add_parser(
        "generate", help="Rebuild TARGET from SOURCE's release tags"
    )
    generate.add_argument("source", metavar="SOURCE", help="Private repo to read")
    generate.add_argument("target", metavar="TARGET", help="Public repo to create")
    generate.add_argument(
        "--tz",
        choices=["local", "gmt"],
        default=DEFAULT_TZ,
        help="Timezone for the uniform timestamp (default: %(default)s)",
    )
    generate.add_argument(
        "--time",
        default=DEFAULT_TIME,
        metavar="HH:MM:SS",
        help="Fixed time for every commit (default: %(default)s)",
    )
    generate.add_argument(
        "--author",
        metavar="IDENTITY",
        help='"Name <email>" for author and committer (default: git config)',
    )
    generate.add_argument(
        "--weed-out",
        default=DEFAULT_WEED_OUT,
        metavar="CMD",
        help="Path to the weed-out sanitizer (default: %(default)s)",
    )
    generate.add_argument(
        "--start",
        metavar="TAG",
        help=f"Begin from this release tag (default: earliest {RELEASE_TAG_PATTERN})",
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
        "inspect", help="List the tags that would become commits"
    )
    inspect.add_argument("source", metavar="SOURCE", help="Private repo to read")

    return parser


def main(argv=None):
    """Parse arguments, dispatch to PRG, and return an exit code.

    Bare `prg` prints help and exits 0. argparse handles its own errors and
    exits 2 on its own.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_OK

    if args.command == "generate":
        prg = PRG(
            source=args.source,
            target=args.target,
            tz=args.tz,
            time=args.time,
            author=args.author,
            weed_out=args.weed_out,
            start=args.start,
            commit=args.commit,
        )
        action = prg.reconstruct
    else:
        action = PRG(source=args.source, target=None).inspect

    try:
        action()
    except NotImplementedError:
        print(
            f"prg is a blueprint: '{args.command}' is not implemented yet. "
            "See DESIGN.md.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
