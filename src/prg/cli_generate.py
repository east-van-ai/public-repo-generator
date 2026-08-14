"""
# ~~~ ~~~ ~~~ ~~~ ~~~ prg generate ~~~ ~~~ ~~~ ~~~ ~~~
#
# Rebuild TARGET from SOURCE's v* release tags, one commit per tag, oldest
# first. Each commit carries the date of the commit its tag points at, and
# with --weed-out each tag's tree is sanitized on the way through.
#
# Usage:
#
#    prg generate SOURCE TARGET [--dry-run | --commit] [options]
#
# SOURCE  an existing git repo.
# TARGET  the public repo. It must not exist yet.
#
# Options:
#
#    --tz {local,gmt}    timezone for the uniform timestamp (default: local)
#    --time HH:MM:SS     fixed time for every commit (default: 12:00:00)
#    --author IDENTITY   "Name <email>" for author and committer
#    --weed-out CMD      path to the weed-out sanitizer (default: none)
#    --start TAG         begin from this release tag (default: earliest v*)
#    --dry-run           report the plan and write nothing. The default.
#    --commit            actually build the repo.
#
# Dry run is the default. `--commit` is what makes prg write.
"""

from prg import generator

HELP = "Rebuild TARGET from SOURCE's release tags"
USAGE = "prg generate SOURCE TARGET [--dry-run | --commit] [options]"


def run(source, target, args):
    """Rebuild the target repo from the source's release tags.

    Assembling the `Build` here is what keeps argparse out of `generator`.
    The parsed namespace stops at this line.

    Both modes print the same table, because both modes work from the same
    plan. `--commit` is the only thing that turns it into a repo.
    """
    build = generator.Build(
        source=source,
        target=target,
        tz=args.tz,
        time=args.time,
        author=args.author,
        weed_out=args.weed_out,
        start=args.start,
        commit=args.commit,
    )

    commits = generator.plan(build)
    generator.preflight(build)

    width = max(len(commit.name) for commit in commits)
    for commit in commits:
        print(f"{commit.name:<{width}}  {commit.stamp.isoformat()}")

    count = f"{len(commits)} release{'' if len(commits) == 1 else 's'}"

    if not build.commit:
        print(f"\n{count}. Dry run, nothing written.")
        return

    generator.reconstruct(build, commits)
    print(f"\n{count} committed to {build.target}.")
