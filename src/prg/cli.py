"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai/public-repo-generator
# contact: east-van-ai@proton.me
# license: MIT
# ==============================================

        Public Repo Generator (prg)

Public Repo Generator (prg) rebuilds a new public repo from an existing private
one. Only the v* release tags on main/master cross over, one commit per release,
each stamped at a uniform time. Nothing from the private history is copied: each
release's tree is extracted, optionally sanitized by weed-out, and committed
fresh, signed when a key is configured. Preview with `prg inspect`, build with
`prg generate`.

Run a command with nothing after it for its own page.

piped input:
    prg reads none.

exit codes:
    0:     success, and documentation
    1:     prg's own error: a path missing or one too many, or an ingredient
           a build needs that is not there
    2:     an unknown command, an unknown option, or a bad value
"""

import sys
from collections import namedtuple

from prg import args, cli_generate, cli_inspect, errors

# main() returns EXIT_OK or EXIT_ERROR. On usage errors, argparse's
# ArgumentParser.error() calls sys.exit(2) before main() can return, so
# EXIT_ARGPARSE is never returned by main(). It's defined for test assertions.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

Command = namedtuple("Command", "bare usage slots action")
"""A command word's answer to being typed alone, its usage line, the path slots it 
reads, and the action a full invocation runs.

`bare` returns the text for the bare word; `action` runs the command. For `version`, 
both read from `version_line`, since running the command answers the bare word.
"""


def command_page(module, add_command):
    """Return a command's answer to its bare word: its docstring, then its --help.

    argparse documents the usage, the paths, and the flags, so each has one copy.
    """
    doc = module.__doc__.strip("\n")  # not strip(): the title's indent is layout
    return f"{doc}\n\n{args.command_help(add_command).rstrip()}"


COMMANDS = {
    "generate": Command(
        lambda: command_page(cli_generate, args.add_generate),
        cli_generate.USAGE,
        cli_generate.SLOTS,
        lambda paths, parsed: cli_generate.run(*paths, parsed),
    ),
    "inspect": Command(
        lambda: command_page(cli_inspect, args.add_inspect),
        cli_inspect.USAGE,
        cli_inspect.SLOTS,
        lambda paths, parsed: cli_inspect.run(*paths, parsed),
    ),
    "version": Command(
        args.version_line,
        "prg version",
        (),
        lambda paths, parsed: print(args.version_line()),
    ),
}


def usage_error(usage, message):
    """Report a command line prg could not read, with that command's usage."""
    sys.stdout.flush()
    print(f"prg: {message}", file=sys.stderr)
    print(f"Usage: {usage}", file=sys.stderr)
    return EXIT_ERROR


def readiness_error(message):
    """Report what the run needed and did not find, with no usage line."""
    sys.stdout.flush()
    print(f"prg: {message}", file=sys.stderr)
    return EXIT_ERROR


def runtime_error(message):
    """Report a run that stopped partway, naming what was written."""
    sys.stdout.flush()
    print(f"prg: {message}", file=sys.stderr)
    return EXIT_ERROR


def main(argv=None):
    """Parse arguments, run the matching command, return an exit code."""
    tokens = list(sys.argv[1:] if argv is None else argv)

    if not tokens:
        print(f"{__doc__.strip()}\n\n{args.build_parser().format_help().rstrip()}")
        return EXIT_OK

    if len(tokens) == 1 and tokens[0] in COMMANDS:
        print(COMMANDS[tokens[0]].bare())
        return EXIT_OK

    parser = args.build_parser()
    parsed, extras = parser.parse_known_args(tokens)

    if any(extra.startswith("-") for extra in extras):
        parser.parse_args(tokens)  # argparse names the flag better, exit 2

    paths = args.leading_paths(tokens[1:])

    command = COMMANDS[parsed.command]

    if len(paths) < len(command.slots):
        needed = " and ".join(command.slots)
        if len(command.slots) > 1:
            needed = f"both {needed}"
        return usage_error(command.usage, f"{parsed.command} needs {needed}")

    if len(paths) > len(command.slots):
        stray = paths[len(command.slots)]
        last = command.slots[-1] if command.slots else "it"
        return usage_error(
            command.usage,
            f"{parsed.command} takes nothing after {last}: {stray!r}",
        )

    try:
        command.action(paths, parsed)
    except errors.ReadinessError as failure:
        return readiness_error(str(failure))
    except errors.RuntimeFailure as failure:
        return runtime_error(str(failure))

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
