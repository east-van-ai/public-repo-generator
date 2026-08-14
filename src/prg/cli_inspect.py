"""
# ~~~ ~~~ ~~~ ~~~ ~~~ prg inspect ~~~ ~~~ ~~~ ~~~ ~~~
#
# List the v* release tags in SOURCE that would become public commits, oldest
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
#
# One line per tag: the tag name, and the uniform timestamp its public commit
# would carry. Then a count.
#
# No message column. The public commit message is the tag name, so a third
# column would print the first one again. A private tag annotation never
# crosses over.
#
# The stamp is the one a build would use, so `inspect` takes the flags that
# shape it. Releases sharing a date in the chosen zone are spaced a second
# apart, oldest first.
"""

from prg import generator

HELP = "List the tags that would become commits"
USAGE = "prg inspect SOURCE [options]"


def run(source, args):
    """Print the tags that would become commits, oldest first.

    The date on each line is the uniform timestamp, not the commit's own.
    `inspect` carries `--tz`, `--time`, and `--start`, so the stamp it prints
    is one a build would genuinely produce.
    """
    releases = generator.start_at(generator.release_tags(source), args.start)
    commits = generator.public_commits(releases, args.tz, args.time)
    width = max(len(commit.name) for commit in commits)

    for commit in commits:
        print(f"{commit.name:<{width}}  {commit.stamp.isoformat()}")

    print(f"\n{len(commits)} release{'' if len(commits) == 1 else 's'}.")
