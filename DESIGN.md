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

## Clean logs

Simply, imagine this ...

```text
$ git log --oneline --all --graph --format="%h %d %s %an <%ae> %ai"

* a450123 (HEAD -> main, tag: v1.2.1) v1.2.1 Jim Doe <jim.doe@example.com> 2026-06-03 12:00:00 -0700
* c691120 (tag: v1.2.0) v1.2.0 Jim Doe <jim.doe@example.com> 2026-05-21 12:00:00 -0700
* db90110 (tag: v1.1.0) v1.1.0 Jim Doe <jim.doe@example.com> 2026-04-10 12:00:00 -0700
* c80b100 (tag: v1.0.0) v1.0.0 Jim Doe <jim.doe@example.com> 2026-03-29 12:00:00 -0700
* abea031 (tag: v0.3.1) v0.3.1 Jim Doe <jim.doe@example.com> 2026-02-19 12:00:01 -0800
* c42f030 (tag: v0.3.0) v0.3.0 Jim Doe <jim.doe@example.com> 2026-02-19 12:00:00 -0800
* d80b020 (tag: v0.2.0) v0.2.0 Jim Doe <jim.doe@example.com> 2026-01-11 12:00:00 -0800
* c7a8010 (tag: v0.1.0) v0.1.0 Jim Doe <jim.doe@example.com> 2025-12-18 12:00:00 -0800
```

Every commit is a release. Every time is noon. Two releases cut on the same day
sit one second apart, oldest first. Nothing else is in there at all.

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

## The output is generated, not derived

`prg` runs `git init` in a directory that did not exist, leaves the branch
unborn, and lays the first public commit down as the root. The output is not a
clone, not a fork, and not a filtered copy. It shares no object with the source
and it has no remote.

So every hash in the public repo is new, and nothing in it inherits an identity
from the private side. That is the clean room argument below, arrived at from
the other direction.

It also means every field in a public commit is a decision rather than a
preservation. The date, the message, the author, the tag, and the signature all
get chosen, because there is nothing sitting there to carry over. Where this
document argues about what a public commit should say, that is why.

Regeneration replaces rather than updates. The public repo is discarded and
rebuilt whole, which the opening assumption permits: no outside commit ever
lands there, so nothing is lost by throwing it away. Two runs over the same
tags with the same flags produce the same hashes, so a rebuild that changed
nothing is a genuine no-op.

## Clean room, not history rewriting

`git filter-repo` and BFG work backwards. A sensitive object already exists in
the history, and the tool rewrites the past to remove it. The object lingers in
every clone and fork taken before the rewrite.

`prg` works forwards. The output repo is created empty, and it is built from
trees extracted one release at a time. The private object store and the public
object store never share an object.

That separation is structural, and it holds whether or not a sanitizer runs.
Untagged commits, abandoned branches, and the reflog have no route into the
output, because nothing is ever copied across.

No reflog purge and no `gc` at the end, either. Neither has anything to do.
Every object prg writes is reachable from the commit it was written for, so
nothing unreachable is ever created for a `gc` to find. And the target's own
reflog carries the manufactured dates rather than the real ones, since a reflog
entry takes its timestamp from `GIT_COMMITTER_DATE`. It agrees with the public
log instead of contradicting it, and a reflog crosses neither a clone nor a
push in any case.

Filtering the files inside those trees is a second job, narrower than the first,
and it belongs to `weed-out`.

No secret scanner is involved in that second job. Scanners like `gitleaks` and
`trufflehog` exist for the deny-list model, where everything ships unless a rule
catches it. `weed-out` works from an allow list, so when it runs, a file the
keep list does not name never reaches the output at all. There is nothing left
for a scanner to find.

## Where the sanitizer runs

`weed-out` has no special case for `.git`. It keeps what the keep list names,
and a keep list that forgets `.git/` takes the repository out with everything
else. Most keep lists do name it, because they are written for a working repo.
Leaning on that would make prg's safety a property of a file in somebody else's
project.

So the directory handed to `weed-out` never holds the target's git data. Each
tag's tree is extracted on its own, sanitized where it stands, and recorded
into the target from the outside. Nothing prg is building sits inside the blast
radius.

The source repo is only ever read. Nothing is checked out in place there.

### The sanitizer is opt-in

`--weed-out` has no default. Without it nothing is filtered, and each release
tag's tree crosses over whole.

Sanitizing is a choice about one particular repo, not a property of every
rebuild. Plenty of repos have nothing to strip, and the ones that do are opting
in either way.

The report says whether a sanitizer ran, so the mode is never something to infer
from the output.

## One public commit per release tag

Public commits come from tags matching `v*` that are reachable from
main/master. Nothing else crosses over. Untagged work, side branches, and tags
that do not match the pattern all stay private.

The public log should read as a release history, because that is the artifact
being showcased. Replaying every private commit would reproduce the messy
middle in sanitized form, which defeats the purpose.

The pattern is not configurable. `v*` is already the release convention, so a
flag would only add a way to get it wrong.

## Where `--start` cuts

Releases earlier than the start tag do not appear at all. The start tag's
commit becomes the public root, carrying no parent and no summary of what came
before it.

There is nothing honest to put there. A squashed "everything up to v0.3.0"
commit would claim a history the public repo is not holding. A `--start` naming
a tag outside the release set is an error rather than a silent fallback to the
earliest one.

## Which keep list applies

When the sanitizer runs, each tag is filtered by the `.weed-out-ignore` found in
that tag's own tree. A release ships what its own rules allowed at the time it
was cut. Reaching for today's keep list instead would rebuild old releases under
a judgement they were never made with.

That leaves no way to retroactively drop a file an old release happened to
allow. A `--weed-out-keep` flag passing a list straight through to
`weed-out --keep` would cover it. Whether that override should also suppress
the tag's own `.weed-out-ignore` is open, and it needs `weed-out` to grow a way
of working from `--keep` alone.

## Each commit is the whole tree

A public commit records the sanitized tree entire, not a change laid over the
release before it. A file that v0.1.0 shipped and v0.2.0 dropped shows up as a
deletion in the public log, which is what a reader comparing the two expects to
see.

Layering would leak. What survived would be whatever the previous release left
behind plus whatever the current one adds, and that combination is not what
either keep list allowed on its own.

A release whose sanitized tree comes out empty is an error. An empty commit
says nothing in a showcase repo, and an empty tree nearly always means the keep
list and the tag's layout have drifted apart.

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

Same date means the date in the zone `--tz` selected, not the date git prints.
A stored commit date carries the committer's own offset, so a release cut in
Tokyo and one cut in Vancouver can read as the same day to the two people who
cut them and still land on different days once both are resolved to one zone.

So the grouping happens after the conversion, never before it. Which releases
collide is a property of the zone rather than of the commits: two that share a
day in GMT can sit on either side of midnight locally, and the tie-break has to
fire in one case and stay quiet in the other.

### Both dates get set

Git records an author date and a committer date. Setting only the author date
leaves the committer date as "now", so the log ends up showing one uniform time
next to one real one. Both get the uniform value.

## Commit message

The tag name, and nothing else. `v0.4.5` is the whole message.

The private annotation does not cross over. `weed-out` filters files, so prose
is the one thing no keep list covers, and a tag message is written in a private
context by someone who was not watching their words. Nothing that never gets
read is worth that.

Little is lost. CHANGELOG.md ships in the public repo and is the maintained
record of what each release changed. An annotation from six months ago was a
second copy of it, and the worse one.

What the log gains is a shape. A uniform message says the same thing the
uniform timestamp says: these are release markers, not a record of work.

## Tags on the public side

Lightweight, always. A ref pointing at the commit, carrying nothing else.

Nothing to write means nothing to leak, and no tagger date either, so there is
no second clock to keep in step with the commit's own.

Making them annotated with text written for the public is the obvious next
move, and that text would come from the release's own CHANGELOG.md section. It
stays parked. Version-only is enough for a showcase, and it costs no parsing of
a document `prg` does not own.

## The public branch is main

Always `main`, whatever the source calls its branch. The public repo is built
rather than mirrored, so a repo created today has no reason to carry an older
convention forward.

## Author identity

Defaults to the git identity configured where `prg` runs, overridable with
`--author "Name <email>"`. The identity used for public releases is not always
the one used for development. Author and committer both take the value.

## Hooks stay out

Generated commits run with `--no-verify`, permanently. A personal `commit-msg`
hook can stop and ask for confirmation, and `prg` closes stdin, so the hook has
no terminal to ask on. It would hang or fail once per release. These commits are
manufactured rather than authored, and there is nothing in them for a hook to
check.

## Signing is opt-in

A showcase repo whose every commit reads "Unverified" undercuts the thing it is
showing. Signing fixes that, and the manufactured dates do not stand in the way.

A signature covers the commit object, and the dates are fields inside it.
Verification asks whether the signature validates over those bytes. It never
asks whether the date is plausible. Ordinary rebasing already produces
signatures made months after the author date they cover, and those verify like
any other.

The signature also carries its own creation time, which is the real moment of
signing. Key validity is judged against that clock rather than the commit's, so
a key made this year signs a commit dated last year without complaint.

### Stop suppressing, rather than add

`--no-gpg-sign` overrides `commit.gpgsign`, so `prg` has been turning signing
off on machines already configured to do it. What the tool needs is to stop
suppressing, not to grow a signing feature.

`prg` holds no key material either way. `user.signingkey`, `gpg.format`, and the
agent are git's own configuration, read where `prg` runs. `prg` asks for a
signature and stops there. So the line below about never needing credentials
still holds, and the git version floor is untouched, since whether the format is
OpenPGP or SSH is the configuration's business.

Whether the switch is an explicit opt-in or simply the absence of the override
is not settled. It sits in the open questions at the end.

Two things follow whichever way it lands. Stdin is closed, so a passphrase
prompt has nowhere to go, and the agent has to be unlocked before a build rather
than during one. And whatever `--author` sets has to match both the signing key
and a verified address on the hosting account, or the commit comes out signed
and still unverified.

### What the badge test showed

A repo built by `prg` and pushed carried no badge at all. Not "Unverified", and
the difference is the whole finding. A host renders a badge only when there is a
signature to judge, so an empty result means the commit object carries none.
"Unverified" would have meant a signature was present and could not be tied to
the account, which is a different problem with different causes.

The machine that ran the test was already configured to sign: SSH format, a
signing key, and `commit.gpgsign` set true. Every ordinary commit it makes is
signed. `prg` was the one thing switching that off.

So the suppression is confirmed as the cause on a real machine, rather than
argued from the armchair. What the test did not reach is whether the host
accepts a signature once one exists. That turns on the key being registered for
signing rather than only for authentication, and on the commit's address being
verified on the account. Those two decide Verified against Unverified, and both
are still untested.

A trap sits next to all of this. Signing and verifying are configured
separately, and SSH verification additionally wants `gpg.ssh.allowedSignersFile`
to exist. Without it, `git log --show-signature` answers "No signature" and
`%G?` answers `N`, on a commit carrying a perfectly good one. Both report a
failure to verify as an absence. Reading the commit object for its `gpgsig`
header is the check that cannot mislead, and it is the one to reach for when
the signing round starts disagreeing with itself.

### What signing costs

The rebuild stops being reproducible. A fresh signature carries a fresh creation
time, so the same source and the same flags produce a different chain of hashes
on every run. Comparing two builds stops being a way to show that nothing
changed.

## `prg` never touches a remote

It builds a local directory and stops. Pushing is a separate, human step.

Keeping remote access out of the tool means it never needs credentials.

## Dry run by default

`prg` reports what it would build. `--commit` makes it act. Same grammar as
`weed-out`, so the two tools behave like one set.

### What a dry run prints

Whether a sanitizer is in play, then the plan the build would follow. One line
per release: the tag name and the uniform timestamp it would receive. Then a
count.

It is the same table `inspect` prints. Both read the same plan, so a preview
cannot drift away from the build it is previewing.

Nothing is extracted, so a dry run says nothing about which files would ship. It
does check what is cheap to check: the source is a repo, the target does not
exist, `--author` parses, and a named sanitizer is on `PATH`. Those are the
failures worth meeting before `--commit` rather than during.

A real build prints the plan, then lays it down. So the dry run is the build's
own plan, not a second description of it written alongside.

## A bare command word is a question

| Typed | Answer |
| --- | --- |
| `prg` | the tool's documentation, exit 0 |
| `prg inspect` | that command's documentation, exit 0 |
| `prg generate SOURCE` | missing TARGET, exit 1 |
| `prg generate --commit` | missing SOURCE, exit 1 |
| `prg generate SOURCE TARGET EXTRA` | one path too many, exit 1 |
| an unknown command or flag | argparse's error, exit 2 |

Asking what a command does is not a usage complaint. Naming one path and
forgetting the other is a slip, and a slip is an error.

The test is the length of the command line: a command word and nothing else.
Not whether an argument came back missing. Once any other token is present,
something specific was asked for, and answering with documentation would bury
the mistake instead of reporting it.

`isatty` decides nothing. What was typed decides, so the same command line
answers the same way from a shell, from cron, and from a test.

## Positions are decided, not inferred

The command word sits at `sys.argv[1]`, `SOURCE` at `argv[2]`, and `TARGET` at
`argv[3]`. Those slots are read directly, and whatever the parser resolved from
elsewhere is discarded.

Argparse accepts more than the documented grammar, and how much more depends on
the interpreter. `prg generate . --commit ./public-repo` is a usage error on
Python 3.9 and a finished build on Python 3.14, which fills a trailing optional
positional from a token following a flag. `prg` supports both. One command line
carrying two meanings across the supported range is worse than either meaning
on its own.

Reading the slots settles it in `prg`'s own code, so the grammar is the same
everywhere. Paths first, then flags.

Two positionals is the ceiling. The pair reads the way `cp` does, what is read
and then what is written. A third would stop being read and start being
memorized.

So anything past a command's last slot is `prg`'s own error, exit 1, reported
the way every other `prg` error is. Argparse does catch it, but it raises from
the top-level parser after the subcommand has already returned, so the usage
line it prints names the tool rather than the command whose grammar was broken.
The reader is told the shape of `prg` when what they need is the shape of
`generate`.

Exit 2 keeps the vocabulary argparse owns, where its own message is the better
one: an unknown command, an unknown flag, a bad value.

## What `inspect` prints

The tags that would become commits, oldest first. Two columns: the name, and
the uniform timestamp it would receive.

No message column. The public commit message is the tag name, so a third column
would print the first one again.

A timestamp belongs to the command that owns the flags shaping it, so `inspect`
carries `--tz` and `--time`, with the same defaults `generate` uses. The stamp
is the part of a preview most worth having, since it is what the public log will
actually read.

`--start` comes along for the same reason. It decides which releases cross over,
and a preview listing releases the build will skip is previewing something else.

One stamp per line, not two. The commit's real date is a click away in the
source repo, and a preview of the public timeline is not the place to show the
private one beside it.

`inspect` stops at `SOURCE`. It never looks at a target, so it answers the
question that comes before a target has been picked. That is the line between it
and a dry run.

## Existing output directory

Refuse and stop. `prg` does not delete anything it did not create.

## Open questions

- **The shape of the signing switch.** Whether `prg` simply stops overriding
  `commit.gpgsign` and honours the configuration it finds, or whether signing
  becomes an explicit `--sign` opt-in. Honouring the config adds no surface and
  matches the tool getting out of the way. An explicit flag keeps a generated
  showcase from inheriting a habit set for ordinary work. Either way an escape
  hatch is wanted in the opposite direction.
- **Retroactive exclusion.** A `--weed-out-keep` flag, and whether it layers on
  top of the tag's own `.weed-out-ignore` or replaces it. Blocked on `weed-out`
  supporting a `--keep`-only mode.
- **Timezone vocabulary.** `--tz {local,gmt}` offers an abbreviation where a
  zone belongs. IANA names such as `America/Vancouver` would accept any zone
  and get daylight saving right, with `local` kept as the special value.
  `inspect` prints the flag's result now, so the change is no longer free: it
  would move stamps a reader has already seen.
- **Release notes on the public tags.** Annotating each public tag with the
  release's own CHANGELOG.md section, matching `v0.4.5` to `## [0.4.5]`. It
  would make `git tag -n` and `git log --oneline` read as notes without any
  private prose crossing over. The cost is a format dependency on a document
  `prg` does not own, and a fallback for a release with no matching section.
  Parked deliberately, not blocked.
- **An audit command.** Structural only: refs beyond the expected tags, and
  unreachable objects. The part that stalls it is checking the output's files
  against the keep list, since a command given only the output repo cannot
  see a keep list unless a release happened to ship one.
