"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ prg inspect ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/public-repo-generator
#
# List the v* release tags in SOURCE that would become public commits, newest
# first. Reads SOURCE and writes nothing.
#
# Usage:
#
#    prg inspect SOURCE [options]
#
# SOURCE  an existing git repo.
#
# Options:
#
#    --tz {local,gmt}    timezone for the uniform timestamp (default: local)
#    --time HH:MM:SS     fixed time for every commit (default: 12:00:00)
#    --start TAG         begin from this release tag (default: earliest v*)
#    --end TAG           stop at this release tag (default: latest v*)
#
# First the values a build would use, then one line per tag: the tag name, and
# the uniform timestamp its public commit would carry. Then a count.
#
# Newest first, the way `git log` reads, since that is the log being
# previewed. A build still lays the commits down oldest first.
#
# A third column appears only when some release carries a `prg-msg/` tag,
# whose message its public commit takes in place of the tag name. With no such
# tag the column would print the first one again on every line.
#
# That column is where the prose gets read before it publishes, so `inspect` is
# the review step for it. A release tag's own annotation still never crosses
# over.
#
# The stamp is the one a build would use, so `inspect` takes the flags that
# shape it. Releases sharing a date in the chosen zone are spaced a second
# apart, oldest first. `--start` and `--end` come along for the same reason:
# they decide which releases cross over, and both are inclusive.
#
# An unconfigured git identity is reported and nothing more. `inspect` answers
# which releases cross over and when, and that answer holds either way. Exit 0.
"""

from prg import generator, report

HELP = "List the tags that would become commits"
USAGE = "prg inspect SOURCE [options]"

# Naming the consequence is what makes a missing identity a report rather than
# a shrug. `inspect` passes either way, so this line is the only place the part
# that matters can be said.
NO_IDENTITY = "not configured, generate would refuse"


def run(source, args):
    """Print what a build would use, then the tags that would become commits.

    The date on each line is the uniform timestamp, not the commit's own.
    `inspect` carries `--tz`, `--time`, `--start`, and `--end`, so both the
    stamp it prints and the set it lists are what a build would produce.

    Newest first. The table previews a log, and a log reads that way.
    `public_timeline` still returns them oldest first, because that is the
    order a build needs, so the reversal is presentation and lives here.

    That one call rather than the steps spelled out here, because resolving
    `prg-msg/` markers can refuse. A preview assembling its own arrangement of
    the same calls is how a preview comes to tolerate what a build rejects.
    """
    ingredients = generator.preflight(source)
    commits = generator.public_timeline(
        source, args.start, args.end, args.tz, args.time
    )

    report.page(
        [
            ("author", report.identity(ingredients.identity, NO_IDENTITY)),
            ("signing", report.signing(ingredients.signing)),
            ("timezone", args.tz),
            ("time", args.time.isoformat()),
        ],
        commits,
    )
