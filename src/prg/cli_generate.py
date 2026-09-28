"""
        Public Repo Generator (prg) -- Generate

https://github.com/east-van-ai/public-repo-generator

Build a new public repo from a private repo's v* release tags, one commit per
tag. Each commit carries the date of the commit its tag points at, and with
--weed-out each tag's tree is sanitized on the way through.

A dry run and `--commit` both check the ingredients first and print what a
build would use: the identity, the signing key, the zone. Every missing one
is reported together, and then prg exits 1 without writing.

`--weed-out`, `--weed-out-keep`: the sanitizer is off unless asked for.
`--weed-out` turns it on, and so does `--weed-out-keep` on its own. prg adds
`--keep ".git/"` itself and protects nothing else. The sanitizer is weed-out,
https://github.com/east-van-ai/weed-out

Each release is filtered by the `.weed-out-ignore` file in its own tree, plus
whatever `--weed-out-keep` names. A release with no such file keeps `.git/`
alone, so it is committed as an empty tree, and the build carries on.

Keep entries are weed-out's patterns. A pattern with no `/` matches a
filename at any depth, so `*.md` reaches every markdown file in the tree. One
containing a `/` matches the path instead, so `src/*.py` reaches only that
directory. `*.*` wants a dot in the name, so `LICENSE` and `Makefile` fall
out of it. `--weed-out-keep "*"` keeps every file.

`--no-sign`: commits are signed with the key configured where prg runs, and
unsigned when there is none. prg refuses a key and an author that name two
different accounts. `--no-sign` is the way past it, and the way to a build
whose hashes can be compared with another's.

`--start`, `--end`: both are inclusive, and either can stand alone. A bound
naming no release tag is an error, and so is an `--end` earlier than the
`--start` beside it.

`prg-msg/`: each public commit says its tag name, `v2.3.4` and nothing else.
A release with an annotated `prg-msg/v2.3.4` tag beside it in the private
repo says that tag's message instead. The marker does not cross over, and a
release tag's own annotation never does. `prg inspect` shows the messages
first.

A marker naming no release tag is an error, and so is one carrying no message
at all, a lightweight tag included. A marker for a release outside `--start`
and `--end` is ignored.

The table reads newest first. The build lays the commits down oldest first.
"""

from prg import errors, generator, report

HELP = "rebuild TARGET from SOURCE's v* release tags"
USAGE = "prg generate SOURCE TARGET [--dry-run | --commit] [options]"
SLOTS = ("SOURCE", "TARGET")

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
    sanitize = generator.sanitizing(args.weed_out, args.weed_out_keep)

    build = generator.Build(
        source=source,
        target=target,
        tz=args.tz,
        time=args.time,
        author=args.author,
        weed_out=sanitize,
        weed_out_keep=args.weed_out_keep,
        start=args.start,
        end=args.end,
        commit=args.commit,
    )

    ingredients = generator.preflight(
        source,
        target=target,
        author=args.author,
        sanitize=sanitize,
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
        ],
        commits,
    )

    if ingredients.failures:
        raise errors.ReadinessError(
            "not ready to build\n  " + "\n  ".join(ingredients.failures)
        )

    if not build.commit:
        print("Dry run, nothing written.")
        return

    generator.reconstruct(build, commits, ingredients.identity, ingredients.signing)
    print(f"Committed to {build.target}.")
