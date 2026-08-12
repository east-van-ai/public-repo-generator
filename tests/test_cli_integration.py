"""Exercise the CLI surface: dispatch, exit codes, and documented defaults.

The pipeline is still a blueprint, so what is pinned down here is the shape
of the interface, not what it builds.
"""

import pytest

from prg import cli, generator


def test_bare_prg_prints_help(capsys):
    assert cli.main([]) == cli.EXIT_OK
    printed = capsys.readouterr().out
    assert "generate" in printed
    assert "inspect" in printed


@pytest.mark.parametrize(
    "argv",
    [
        ["generate", "source", "target"],
        ["inspect", "source"],
    ],
)
def test_a_command_reports_that_it_is_a_blueprint(argv, capsys):
    assert cli.main(argv) == cli.EXIT_ERROR
    assert "blueprint" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["verify", "target"],
        ["nonsense"],
        ["generate", "source"],
        ["generate", "source", "target", "--dry-run", "--commit"],
        ["generate", "source", "target", "--tz", "utc"],
        ["inspect", "source", "target"],
    ],
)
def test_argparse_rejects_and_exits_two(argv):
    with pytest.raises(SystemExit) as exit_attempt:
        cli.main(argv)
    assert exit_attempt.value.code == 2


def test_generate_defaults_match_the_documented_ones():
    args = cli.build_parser().parse_args(["generate", "source", "target"])
    assert args.tz == generator.DEFAULT_TZ == "local"
    assert args.time == generator.DEFAULT_TIME == "12:00:00"
    assert args.weed_out == generator.DEFAULT_WEED_OUT == "weed-out"
    assert args.author is None
    assert args.start is None


def test_dry_run_is_the_default():
    args = cli.build_parser().parse_args(["generate", "source", "target"])
    assert args.commit is False
    assert args.dry_run is False


def test_commit_is_opt_in():
    args = cli.build_parser().parse_args(["generate", "source", "target", "--commit"])
    assert args.commit is True
