"""
        Public Repo Generator (prg) -- Inspect

https://github.com/east-van-ai/public-repo-generator

List a private repo's v* release tags that would become public commits,
newest first. Reads the repo and writes nothing.

First the values a build would use, then one line per tag: the tag name, and
the uniform timestamp its public commit would carry. Then a count. A build
lays the commits down oldest first.

A third column appears only when some release carries a `prg-msg/` tag. It
shows the message that release's public commit takes in place of the tag
name, so this is where the message gets read before it publishes. A release
tag's own annotation never crosses over.

Releases sharing a date in the chosen zone are spaced a second apart, oldest
first. `--start` and `--end` are inclusive.

An unconfigured git identity is reported, and `inspect` still exits 0.
"""

from prg import generator, report

HELP = "list the v* release tags that would become commits"
USAGE = "prg inspect SOURCE [options]"
SLOTS = ("SOURCE",)

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
