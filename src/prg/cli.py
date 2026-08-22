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
# `prg --version` prints the installed version. That is documentation too, so
# it exits 0. It belongs to the tool, never to a command.
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

import sys
from collections import namedtuple

from prg import cli_generate, cli_inspect
from prg.args import EXIT_ERROR, EXIT_OK, build_parser
from prg.generator import PRGError

Command = namedtuple("Command", "module slots")
"""A command word's module, and the path slots it reads.

The module carries its own documentation, usage line, and action, so the
table only adds what the command line itself decides.
"""

COMMANDS = {
    "generate": Command(cli_generate, ("SOURCE", "TARGET")),
    "inspect": Command(cli_inspect, ("SOURCE",)),
}


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
