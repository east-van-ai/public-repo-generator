"""Exercise the CLI surface: dispatch, exit codes, and documented defaults.

What is pinned down here is the shape of the interface, not what the pipeline
builds.
"""

from datetime import time

import pytest

from prg import cli, cli_generate, cli_inspect, generator


def test_bare_prg_prints_the_module_documentation(capsys):
    """Not argparse's help. The banner in cli.py is what a bare prg answers."""
    assert cli.main([]) == cli.EXIT_OK
    printed = capsys.readouterr().out
    assert "East Van AI" in printed
    assert "generate" in printed
    assert "inspect" in printed


def test_the_banner_documents_the_exit_codes(capsys):
    """All three, since the contract is what a caller scripts against."""
    cli.main([])
    banner = capsys.readouterr().out
    assert "Exit codes:" in banner
    for code in (cli.EXIT_OK, cli.EXIT_ERROR, cli.EXIT_ARGPARSE):
        assert f"    {code}:    " in banner


@pytest.mark.parametrize("command", ["generate", "inspect"])
def test_a_bare_command_word_prints_its_own_documentation(command, capsys):
    """In the house voice, not argparse's. The banner belongs to bare prg."""
    assert cli.main([command]) == cli.EXIT_OK
    printed = capsys.readouterr().out
    assert f"prg {command}" in printed
    assert "Usage:" in printed
    assert "usage: prg" not in printed
    assert "East Van AI" not in printed


def test_the_options_are_documented_once(capsys):
    """The banner points at `prg generate` rather than repeating its flags."""
    cli.main([])
    banner = capsys.readouterr().out
    cli.main(["generate"])
    command_doc = capsys.readouterr().out

    assert "--weed-out" in command_doc
    assert "--weed-out" not in banner


def test_a_half_typed_generate_is_an_error(capsys):
    """One path named and one forgotten is a slip, not a question."""
    assert cli.main(["generate", "source"]) == cli.EXIT_ERROR
    printed = capsys.readouterr().err
    assert "TARGET" in printed
    assert cli_generate.USAGE in printed


def test_a_command_word_with_a_flag_is_not_a_question(capsys):
    """The test is the length of the command line, not a missing argument."""
    assert cli.main(["generate", "--commit"]) == cli.EXIT_ERROR
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "argv",
    [
        ["generate", "--commit"],
        ["generate", "--commit", "source", "target"],
        ["generate", "source", "--commit", "target"],
    ],
)
def test_a_flag_in_a_path_slot_is_an_error(argv, capsys):
    """A flag standing in a slot is not a path, whatever follows it.

    The last two parse on some supported interpreters and not others, so
    reading the slots is what makes them answer the same way everywhere.
    """
    assert cli.main(argv) == cli.EXIT_ERROR
    printed = capsys.readouterr().err
    assert "generate needs both SOURCE and TARGET" in printed
    assert cli_generate.USAGE in printed


@pytest.mark.parametrize(
    "argv, usage",
    [
        (["generate", "source", "target", "extra"], cli_generate.USAGE),
        (["inspect", "source", "extra"], cli_inspect.USAGE),
    ],
)
def test_a_path_too_many_is_prgs_own_error(argv, usage, capsys):
    """Argparse catches it too, but answers with the root parser's usage."""
    assert cli.main(argv) == cli.EXIT_ERROR
    printed = capsys.readouterr().err
    assert "'extra'" in printed
    assert usage in printed


def test_the_usage_line_is_written_once():
    """The docstring spells out the same line the error prints.

    A module docstring cannot interpolate, so this is what keeps the two in
    agreement now that the doc no longer quotes the constant.
    """
    assert cli_generate.USAGE in cli_generate.__doc__
    assert cli_inspect.USAGE in cli_inspect.__doc__


def test_generate_rejects_a_source_that_is_not_a_repo(capsys):
    assert cli.main(["generate", "source", "target"]) == cli.EXIT_ERROR
    assert "not a git repo" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["verify", "target"],
        ["nonsense"],
        ["generate", "source", "target", "--dry-run", "--commit"],
        ["generate", "source", "target", "--tz", "utc"],
        ["generate", "source", "target", "--bogus"],
    ],
)
def test_argparse_rejects_and_exits_two(argv):
    """Its own vocabulary: an unknown command, an unknown flag, a bad value.

    It raises rather than returns, since argparse calls `sys.exit` itself.
    """
    with pytest.raises(SystemExit) as exit_attempt:
        cli.main(argv)
    assert exit_attempt.value.code == cli.EXIT_ARGPARSE


def test_generate_defaults_match_the_documented_ones():
    args = cli.build_parser().parse_args(["generate", "source", "target"])
    assert args.tz == generator.DEFAULT_TZ == "local"
    assert args.time == time(12, 0, 0)
    assert generator.DEFAULT_TIME == "12:00:00"
    assert args.author is None
    assert args.start is None
    assert args.end is None


def test_no_sanitizer_runs_unless_asked_for():
    """`--weed-out` has no default, so nothing is filtered without it."""
    args = cli.build_parser().parse_args(["generate", "source", "target"])
    assert args.weed_out is None
    assert generator.DEFAULT_WEED_OUT is None


def test_inspect_shares_generates_plan_defaults():
    """A preview built on other defaults would preview another build."""
    inspect = cli.build_parser().parse_args(["inspect", "source"])
    generate = cli.build_parser().parse_args(["generate", "source", "target"])
    assert (inspect.tz, inspect.time, inspect.start, inspect.end) == (
        generate.tz,
        generate.time,
        generate.start,
        generate.end,
    )


def test_a_bad_time_is_argparses_error():
    """A bad value belongs to argparse's vocabulary, the same as a bad --tz."""
    with pytest.raises(SystemExit) as exit_attempt:
        cli.main(["inspect", "source", "--time", "noon"])
    assert exit_attempt.value.code == cli.EXIT_ARGPARSE


def test_dry_run_is_the_default():
    args = cli.build_parser().parse_args(["generate", "source", "target"])
    assert args.commit is False
    assert args.dry_run is False


def test_commit_is_opt_in():
    args = cli.build_parser().parse_args(["generate", "source", "target", "--commit"])
    assert args.commit is True
