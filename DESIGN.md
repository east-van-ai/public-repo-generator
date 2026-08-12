# Design

Why `prg` works the way it does. The README covers what it does. This file
covers the reasoning, and the questions still open.

## What the public repo is for

Showcasing finished work, and serving as a `pipx` install endpoint. It is not
a collaboration surface. Public PRs are not welcome, simply because there
is another repo for development. Issues for the public repo stay disabled.
Contact goes through the email address in the README or the repo account page.

This is the assumption everything else rests on. Since no outside commit ever
lands on the public side, there is nothing to reconcile, and the public repo
can be discarded and rebuilt whole on every release.

## Curated, not accurate

The public timeline is a presentation, and it is artificial on purpose. Dates
are flattened. Most commits never appear. The log does not describe how the
work actually happened, and it is not trying to.

So `prg` makes no effort to defend the timeline's accuracy. Anyone curious
about the real development story can ask, and that is a better conversation
than a commit log anyway.

One thing does get strict treatment: what ends up inside the files. A drifted
date costs nothing. A leaked credential costs something real. Where this
document sounds relaxed and the sanitizing sections sound careful, that split
is the reason.

## Commit dates are writable

Git presents a commit's dates as though it observed them. They are fields.
`GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` set them to whatever you like, and
what comes out is an ordinary repo.

That is what makes `prg` possible at all. Without it, a rebuild would stamp
every release with the moment of the rebuild. With it, releases can be laid
down in order, each carrying its own date, each descending from the one before.

Ancestry is the payload. Orphan commits can hold identical file contents and
still lose it, which is the failure the README describes under "What This
Replaces".

The fact itself was one question away and free. Forming the question took
months.

## Clean room, not history rewriting

`git filter-repo` and BFG work backwards. A sensitive object already exists in
the history, and the tool rewrites the past to remove it. The object lingers in
every clone and fork taken before the rewrite.

`prg` works forwards. The output repo is created empty. Only trees that
`weed-out` has already passed are ever committed to it. The private object
store and the public object store never share an object.

That is the whole thesis. The reflog purge and the `gc` at the end are
housekeeping, not the guarantee.

No secret scanner is involved. Scanners like `gitleaks` and `trufflehog`
exist for the deny-list model, where everything ships unless a rule catches
it. `weed-out` works from an allow list, so a file not named in
`.weed-out-ignore` never reaches the output at all. There is nothing left for
a scanner to find.

## One public commit per release tag

Public commits come from tags matching `v*` that are reachable from
main/master. Nothing else crosses over. Untagged work, side branches, and tags
that do not match the pattern all stay private.

The public log should read as a release history, because that is the artifact
being showcased. Replaying every private commit would reproduce the messy
middle in sanitized form, which defeats the purpose.

The pattern is not configurable. `v*` is already the release convention, so a
flag would only add a way to get it wrong.

## Which keep list applies

Each tag is sanitized with the `.weed-out-ignore` found in that tag's own tree.
A release ships what its own rules allowed at the time it was cut. Reaching for
today's keep list instead would rebuild old releases under a judgement they
were never made with.

That leaves no way to retroactively drop a file an old release happened to
allow. A `--weed-out-keep` flag passing a list straight through to
`weed-out --keep` would cover it. Whether that override should also suppress
the tag's own `.weed-out-ignore` is open, and it needs `weed-out` to grow a way
of working from `--keep` alone.

## Timestamps

Each public commit keeps the real calendar date of the commit its release tag
points at. The time is forced to noon.

The date comes from that commit, not from the tag object. A tag object records
when the tag was typed, which is not what the public log is claiming. Reading
the commit also removes the split between the two kinds of tag: annotated and
lightweight answer the same way.

Noon local by default, with `--tz gmt` to switch. Local reads naturally for a
project built in one place. A release cut in Vancouver shows Vancouver's noon.
`--time` moves it off noon for anyone who wants that, but noon is the value
that reads as deliberate.

Local means the machine doing the rebuilding, not the machine that cut the
release. Regenerate somewhere else and the times move with it. A release cut
near midnight can land on a different day. `--tz gmt` pins it.

The time is uniform on purpose, as a signal. A repo where every commit lands at
exactly 12:00:00 is announcing that these are release markers, not a record of
when hands were on the keyboard.

### Same-day releases

Two releases on the same date would otherwise collide. The first takes
12:00:00, the second 12:00:01, and so on, ordered by their original commit
order. One release per second is the ceiling, so 43200 of them between noon
and midnight.

### Both dates get set

Git records an author date and a committer date. Setting only the author date
leaves the committer date as "now", so the log ends up showing one uniform time
next to one real one. Both get the uniform value.

## Commit message

The tag's annotation message. A lightweight tag carries no message, so it
falls back to the tag name.

## Author identity

Defaults to the git identity configured where `prg` runs, overridable with
`--author "Name <email>"`. The identity used for public releases is not always
the one used for development. Author and committer both take the value.

## Hooks and signing stay out

Generated commits run with `--no-verify` and with signing forced off. A
personal `commit-msg` hook can stop and ask for confirmation, and `prg` would
sit there waiting once per release.

Signing is the harder failure. The machine rebuilding the public repo is not
always the machine that cut the releases, and git refuses the commit outright
when the key is missing. Neither belongs in a machine-built showcase anyway.
These commits are manufactured, not authored.

## `prg` never touches a remote

It builds a local directory and stops. Pushing is a separate, human step.

Keeping remote access out of the tool means it never needs credentials.

## Dry run by default

`prg` reports what it would build. `--commit` makes it act. Same grammar as
`weed-out`, so the two tools behave like one set.

## Existing output directory

Refuse and stop. `prg` does not delete anything it did not create.

## Open questions

- **Retroactive exclusion.** A `--weed-out-keep` flag, and whether it layers on
  top of the tag's own `.weed-out-ignore` or replaces it. Blocked on `weed-out`
  supporting a `--keep`-only mode.
- **Reporting.** What `inspect` and a dry run print, and whether they are the
  same output. Low stakes, deferred.
- **Timezone vocabulary.** `--tz {local,gmt}` offers an abbreviation where a
  zone belongs. IANA names such as `America/Vancouver` would accept any zone
  and get daylight saving right, with `local` kept as the special value.
  Nothing implements the flag yet, so the change stays free until something
  does.
- **An audit command.** Structural only: refs beyond the expected tags, and
  unreachable objects. The part that stalls it is checking the output's files
  against the keep list, since a command given only the output repo cannot
  see a keep list unless a release happened to ship one.
