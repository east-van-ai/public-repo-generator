"""
# ~~~ ~~~ ~~~ ~~~ ~~~ prg generate ~~~ ~~~ ~~~ ~~~ ~~~
#
# Rebuild TARGET from SOURCE's v* release tags, one commit per tag. Each commit
# carries the date of the commit its tag points at, and with --weed-out each
# tag's tree is sanitized on the way through.
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
#    --end TAG           stop at this release tag (default: latest v*)
#    --no-sign           build unsigned, whatever the git config says
#    --dry-run           report the plan and write nothing. The default.
#    --commit            actually build the repo.
#
# Dry run is the default. `--commit` is what makes prg write.
#
# Both modes check the ingredients first and print what a build would use: the
# identity, the signing key, the zone, the sanitizer. A missing one is reported
# with everything else, so a run names all of them at once rather than one per
# attempt, and then exits 1 without writing.
#
# Commits are signed with the key configured where prg runs, and unsigned when
# there is none. The key and the author have to name one account, since a host
# judges the address against the account holding the key, and prg refuses a
# pair that disagrees. `--no-sign` is the way past it, and the way to a build
# whose hashes can be compared with another's.
#
# `--start` and `--end` are inclusive, and either can stand alone. A bound
# naming no release tag is an error, and so is an `--end` earlier than the
# `--start` beside it.
#
# The table reads newest first, the way `git log` does. The build still lays
# the commits down oldest first.
"""

from prg import generator, report

HELP = "Rebuild TARGET from SOURCE's release tags"
USAGE = "prg generate SOURCE TARGET [--dry-run | --commit] [options]"

NO_SANITIZER = "none, every release tree crosses over whole"

# Terser than `inspect`'s answer to the same question, and deliberately. Here a
# missing identity appears again among the failures, which carries the
# consequence with it.
NO_IDENTITY = "not configured"


def run(source, target, args):
    """Rebuild the target repo from the source's release tags.

    Assembling the `Build` here is what keeps argparse out of `generator`.
    The parsed namespace stops at this line.

    Both modes print the same page, because both modes work from the same plan
    and the same checks. `--commit` is the only thing that turns it into a
    repo.

    A missing ingredient does not cut the page short. Everything prints, and
    the failures come last, so one run names all of them instead of one per
    attempt. Then it is prg's own error, exit 1, and nothing was written.
    """
    build = generator.Build(
        source=source,
        target=target,
        tz=args.tz,
        time=args.time,
        author=args.author,
        weed_out=args.weed_out,
        start=args.start,
        end=args.end,
        commit=args.commit,
    )

    ingredients = generator.preflight(
        source,
        target=target,
        author=args.author,
        weed_out=args.weed_out,
        sign=not args.no_sign,
    )
    commits = generator.plan(build)

    report.page(
        [
            ("author", report.identity(ingredients.identity, NO_IDENTITY)),
            ("signing", report.signing(ingredients.signing)),
            ("timezone", args.tz),
            ("time", args.time.isoformat()),
            ("target", str(target)),
            ("sanitizer", args.weed_out or NO_SANITIZER),
        ],
        commits,
    )

    if ingredients.failures:
        raise generator.PRGError(
            "not ready to build\n  " + "\n  ".join(ingredients.failures)
        )

    if not build.commit:
        print("Dry run, nothing written.")
        return

    generator.reconstruct(build, commits, ingredients.identity, ingredients.signing)
    print(f"Committed to {build.target}.")
