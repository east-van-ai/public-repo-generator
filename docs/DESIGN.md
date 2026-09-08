# Design

Why `prg` works the way it does: the model the public repo is built on, and the
reasoning under each decision.

## Curated, not accurate

The public timeline is a presentation, and it is artificial on purpose. Dates
are flattened. Most commits never appear. The log does not describe how the
work actually happened, and it is not trying to.

So `prg` makes no effort to defend the timeline's accuracy. Anyone curious
about the real development story can ask.

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
still lose it.

## The output is generated, not derived

`prg` runs `git init` in a directory that did not exist, leaves the branch
unborn, and lays the first public commit down as the root. The output is not a
clone, not a fork, and not a filtered copy. It shares no object with the source
and it has no remote.

So every hash in the public repo is new, and every field in a public commit is
a decision rather than a preservation. The date, the message, the author, the
tag, and the signature all get chosen, because there is nothing sitting there to
carry over. Where this document argues about what a public commit should say,
that is why.

Regeneration replaces rather than updates. The public repo is discarded and
rebuilt whole, and no outside commit ever lands there to be lost. Two runs over
the same tags with the same flags produce the same hashes, so a rebuild that
changed nothing is a genuine no-op. Whether a signature preserves that depends
on how the signature is made, which the next section covers.

## Signing decides whether a rebuild repeats

Whether a rebuild produces the same hashes depends on the signing method.

| Build | Rebuild repeats |
| --- | --- |
| `--no-sign` | yes |
| signed, SSH ed25519 | yes |
| signed, OpenPGP | no |

Measured with git 2.50.1 and GnuPG 2.5.22, by building one source twice and
comparing the commit hashes.

The signature is the only field a rebuild makes fresh. Everything else is fixed
from the source before any signing happens.

Two things settle it, and the format's name is neither. One is whether the
signature embeds a timestamp: OpenPGP always does, an SSHSIG never does, and
freezing the signing clock is what makes an OpenPGP build repeat. The other is
whether the algorithm is deterministic: ed25519 is, and ECDSA is not, since
three SSH signatures over identical bytes come back different every time. So an
SSH ECDSA key drifts and an ed25519 OpenPGP key drifts too. Read each row as
the pair it names rather than as its format.

## Clean room, not history rewriting

`git filter-repo` and BFG work backwards. A sensitive object already exists in
the history, and the tool rewrites the past to remove it. The object lingers in
every clone and fork taken before the rewrite.

`prg` works forwards. The output repo is created empty and built from trees
extracted one release at a time, so the private object store and the public one
never share an object. That separation is structural, and it holds whether or
not a sanitizer runs. Untagged commits, abandoned branches, and the reflog have
no route into the output.

No reflog purge and no `gc` at the end, either. Every object prg writes is
reachable from the commit it was written for, so nothing unreachable is ever
created for a `gc` to find. The target's own reflog carries the manufactured
dates rather than the real ones, since a reflog entry takes its timestamp from
`GIT_COMMITTER_DATE`, and it crosses neither a clone nor a push in any case.

Filtering the files inside those trees is a second job, narrower than the first,
and it belongs to `weed-out`. No secret scanner is involved in it. Scanners like
`gitleaks` and `trufflehog` exist for the deny-list model, where everything
ships unless a rule catches it. `weed-out` works from an allow list, so a file
the keep list does not name never reaches the output at all. There is nothing
left for a scanner to find.

## Where the sanitizer runs

`weed-out` has no special case for `.git`. It keeps what the keep list names,
and a keep list that forgets `.git/` takes the repository out with everything
else. Most keep lists do name it, because they are written for a working repo,
but leaning on that would make prg's safety a property of a file in somebody
else's project.

So `prg` supplies it. Every sanitizer run adds `--keep ".git/"` on top of
whatever the tag's own keep list allows, so the protection comes from the caller
rather than from the file being read. The run happens in the target's own
working tree, once the tag has been extracted into it and before anything is
staged:

```text
weed-out delete . --keep ".git/" --commit
```

`delete` rather than `trash`, and `--commit` rather than a dry run. The tree
being weeded is one `prg` laid down seconds earlier out of a tag that still
exists, so there is nothing worth recovering, and a preview would leave
`git add` staging the tree unfiltered.

That one entry is the whole of what `prg` protects. Nothing else is defended: a
tag whose keep list does not name `.weed-out-ignore` ships without it, since the
keep list is a fact about the private repo and the public one does not have to
carry it. Nothing is checked afterwards either. Whether the entry covers
everything under `.git` is `weed-out`'s own invariant, and a caller cannot do
better than report what came back. The one thing `prg` still looks at is whether
anything survived at all, which is a question about the commit it is about to
make.

One of `weed-out`'s refusals can never reach a `prg` user. `weed-out --commit`
stops when no keep list resolves at all, since silence there is likelier to be a
forgotten argument than an instruction to empty the directory. A run from `prg`
always carries at least `.git/`, so that refusal never fires.

The source repo is only ever read. Nothing is checked out in place there.

## One public commit per release tag

Public commits come from tags matching `v*` that are reachable from
main/master. Untagged work, side branches, and tags that do not match the
pattern all stay private.

The public log should read as a release history, because that is the artifact
being showcased. Replaying every private commit would reproduce the messy
middle in sanitized form, which defeats the purpose.

The pattern is not configurable. `v*` is already the release convention, so a
flag would only add a way to get it wrong.

## Which keep list applies

When the sanitizer runs, a tag carrying a `.weed-out-ignore` is filtered by that
one. A release ships what its own rules allowed at the time it was cut. Reaching
for today's keep list over a release's own would rebuild it under a judgement it
was never made with.

`--weed-out-keep` is what reaches a release whose own rules are not enough. Its
entries join the `--keep` list `prg` already builds, behind `.git/` and beside
whatever the tag's `.weed-out-ignore` adds, so one flag covers every release in
the range:

```text
weed-out delete . --keep ".git/,docs/,*.md" --commit
```

It adds and never subtracts. `weed-out`'s grammar is keep-only, so a tag that
allows a file will still ship that file. What the flag covers is the other case:
a release cut before the keep list existed, or one whose keep list never thought
about a path that has since become worth shipping. Duplicates need no handling,
since `weed-out` merges its two sources itself and dedupes while preserving
order.

A release cut before any `.weed-out-ignore` existed has no rules of its own, and
`prg` does not go looking for a substitute. Lending the latest release's keep
list backwards was considered and dropped: it costs a flag, a second reader for
`weed-out`'s file format, and a rule about which tag does the lending, in return
for something `--weed-out-keep` already does.

## Each commit is the whole tree

A public commit records the sanitized tree entire, not a change laid over the
release before it. A file that v0.1.0 shipped and v0.2.0 dropped shows up as a
deletion in the public log, which is what a reader comparing the two expects.

Layering would leak. What survived would be whatever the previous release left
behind plus whatever the current one adds, and that combination is not what
either keep list allowed on its own.

A release whose sanitized tree comes out empty still becomes a commit. It means
the keep list and the tag's layout have drifted apart, usually a release cut
before any `.weed-out-ignore` existed, and `--weed-out-keep` is what covers it.
Stopping at the first one would hand back a single release per run while already
knowing about the rest. The build finishes instead, so every empty release is in
the log at once and one round of the flag covers the lot.

## How a tree becomes a commit

Each release is extracted with `git archive`, straight into the target's working
tree. The source repo is read and never checked out, so nothing is written there
and a failed build leaves nothing behind to clean up.

Before each extraction the target's working tree is emptied, everything except
`.git`. Then `git add --all` records what landed. Emptying first is what buys
"Each commit is the whole tree" with no bookkeeping of prg's own: a dropped file
is already gone by the time git looks at the tree.

Staging is forced. Git keeps tracking a file once it is tracked, so a release
can ship a file that a `.gitignore` in its own tree also matches. Honouring that
rule would drop the file from the public commit without a word, and the tag's
tree is the whole instruction.

Emptying a directory is the one destructive thing `prg` does, and it is confined
to a directory `prg` created, since `preflight` refuses a target that already
exists. No scratch directory stands between the source and the target, and the
sanitizer does not need one either: it runs where the tree stands, with `.git/`
added to the keep list by `prg`. Care is what keeps the repository out of the
blast radius, not distance.

`--allow-empty` covers three cases. Two tags on one commit, two releases whose
trees match, and a sanitized tree that came out with nothing in it. All three
leave `git commit` nothing to record, and a release that crossed over belongs in
the public log either way.

## Timestamps

Each public commit keeps the real calendar date of the commit its release tag
points at. The time is forced to noon.

The date comes from that commit, not from the tag object. A tag object records
when the tag was typed, which is not what the public log is claiming. Reading
the commit also removes the split between the two kinds of tag: annotated and
lightweight answer the same way.

Noon local by default, with `--tz gmt` to switch. Local reads naturally for a
project built in one place, and a release cut in Vancouver shows Vancouver's
noon. `--time` moves it off noon, but noon is the value that reads as
deliberate. Local means the machine doing the rebuilding, not the machine that
cut the release, so a release cut near midnight can land on a different day.
`--tz gmt` pins it.

The time is uniform on purpose, as a signal. A repo where every commit lands at
exactly 12:00:00 is announcing that these are release markers, not a record of
when hands were on the keyboard.

### Same-day releases

Two releases on the same date would otherwise collide. The first takes
12:00:00, the second 12:00:01, and so on, ordered by their original commit
order. One release per second is the ceiling, so 43200 of them between noon
and midnight.

Same date means the date in the zone `--tz` selected, not the date git prints.
A stored commit date carries the committer's own offset, so the grouping happens
after the conversion, never before it. Which releases collide is a property of
the zone rather than of the commits: two that share a day in GMT can sit on
either side of midnight locally, and the tie-break has to fire in one case and
stay quiet in the other.

### Both dates get set

Git records an author date and a committer date. Setting only the author date
leaves the committer date as "now", so the log ends up showing one uniform time
next to one real one. Both get the uniform value.

## Commit message

The tag name, and nothing else. `v0.4.5` is the whole message, unless the source
carries a marker naming that release.

A release tag's own annotation never crosses over. `weed-out` filters files, so
prose is the one thing no keep list covers, and a tag message is written in a
private context by someone who was not watching their words. Little is lost by
that. CHANGELOG.md ships in the public repo and is the maintained record of what
each release changed, so an annotation from six months ago was a second copy of
it, and the worse one.

What the log gains is a shape. A uniform message says the same thing the uniform
timestamp says: these are release markers, not a record of work.

### The marker is a tag named for its release

An annotated tag named `prg-msg/v0.4.5` in the source hands its own subject to
`v0.4.5`'s public commit:

```bash
git tag -a prg-msg/v0.4.5 -m "config files can be split across directories"
```

The prose in a marker exists for one purpose, and whoever wrote it knew where it
was going. That is the whole difference between it and the release tag's
annotation, and it is why one publishes and the other does not. The marker
itself stays behind, falling outside the `v*` filter.

The version sits in the name because tag names are unique. One fixed marker name
could mark a single release in the whole repo, ever.

Only the name binds. What a marker points at is never read, so tagging it at
HEAD and tagging it at its release both work: with the name right, a wrong
target has no consequence. Only the subject travels, too. A body under the
message is dropped, which holds the one-line shape the log is for.

No flag turns this on. The marker is a deliberate act by itself, and `prg-msg/`
is a namespace nothing else writes into. The cost of that lands on `inspect`,
the one place a marker's prose can be read before it publishes.

### What a marker cannot do

Two refusals, and each names the marker rather than the version decoded out of
it.

A marker naming no release tag is a typo. Left alone it would do nothing at all
and say nothing about it, which is the failure worth spending an error on.

A marker carrying no message is that same failure wearing a different hat. A
lightweight tag is the common way to reach it, and the trap underneath is that
git reports the tagged commit's own subject in that case, so a marker with
nothing of its own reads exactly like one that has a message.

A marker for a release outside `--start` and `--end` is not an error. That
release is not in this build. The span decides what gets built, never what
counts as valid.

Both refusals stop `inspect` as well as `generate`. A preview tolerating what
the build rejects would not be a preview.

## Tags on the public side

Lightweight, always. A ref pointing at the commit, carrying nothing else.

Nothing to write means nothing to leak, and no tagger date either, so there is
no second clock to keep in step with the commit's own.

## The public branch is main

Always `main`, whatever the source calls its branch. The public repo is built
rather than mirrored, so a repo created today has no reason to carry an older
convention forward.

## Author identity

Defaults to the git identity configured where `prg` runs, overridable with
`--author "Name <email>"`. The identity used for public releases is not always
the one used for development. Author and committer both take the value.

Configured means configured. Git invents an identity when it finds none, built
from the account name and the machine's hostname, so a repo whose whole purpose
is being public ends up publishing `you@your-laptop.local`, at an address no
hosting account can verify. No identity is therefore a refusal, not a fallback.

The probe is `git -c user.useConfigOnly=true var GIT_AUTHOR_IDENT`, satisfied by
either git config or the `GIT_AUTHOR_NAME` and `GIT_AUTHOR_EMAIL` variables.
Asking git the question directly beats reimplementing its resolution order.

The identity is resolved once, before the build, and passed to every commit
explicitly. Nothing is left for git to resolve inside the target, so what the
report printed is what the commits carry.

### The target keeps a copy

The resolved name and email are written into the target's own config right after
`git init`, along with `user.useConfigOnly = true`. The signing key and its
format go in beside them, with `commit.gpgsign` set to match the build.

None of it touches the build. The identity arrives through the environment and
the key is passed per commit, so both sit there outranked while `prg` works.

It is for afterwards. The target gets pushed from, and one day it gets amended
in by hand. That commit would take the global identity and the global key, which
are the development ones, and that is the same mismatched pair `preflight`
refuses to build, arriving by the back door. Local config pins the public pair
to the directory instead.

The two halves need different mechanisms. `user.useConfigOnly` makes the
invented identity impossible rather than merely unnecessary. Signing has no such
switch, since nothing stops git inheriting `user.signingkey` from a wider scope,
so an unsigned build writes `commit.gpgsign = false` and a signed one writes
`true`. A hand-made commit later is then not the one bare commit in a verified
log.

`.git/config` is local and never travels, so this protects the working copy of
the target, not the published repo.

## Hooks stay out

Generated commits run with `--no-verify`, permanently. A personal `commit-msg`
hook can stop and ask for confirmation, and `prg` closes stdin, so the hook has
no terminal to ask on and would hang or fail once per release. These commits are
manufactured rather than authored, and there is nothing in them for a hook to
check.

## Signing follows the key where prg runs

A showcase repo whose every commit reads "Unverified" undercuts the thing it is
showing. Signing fixes that, and the manufactured dates do not stand in the way.

A signature covers the commit object, and the dates are fields inside it.
Verification asks whether the signature validates over those bytes, never
whether the date is plausible. Ordinary rebasing already produces signatures
made months after the author date they cover, and those verify like any other.
The signature carries its own creation time, and key validity is judged against
that clock rather than the commit's, so a key made this year signs a commit
dated last year without complaint.

### Resolved once, then passed

The target's own config is empty at the moment it matters, since `prg` creates
that repo. The values are resolved beforehand, in `prg`'s own working directory,
and handed to each commit on the command line. Same as the identity, and for the
same reason: one resolution is what stops the report and the commits
disagreeing.

`-S` on every commit rather than a reliance on `commit.gpgsign`. A key resolved
for this build is already the instruction to sign. With no key, `--no-gpg-sign`
stays and the build is unsigned.

The report prints the key directly under the author, because the two are halves
of one decision and reading them together is the point.

### The key and the address have to agree

A host verifies a commit by asking whether the committer's address is verified
on the account holding the key. Both halves have to name the same account, so
`preflight` refuses when they do not.

The case this catches is `--author` naming one account while the ambient key
belongs to another. It produces a repo that is signed, Unverified, and carrying
a development key in public, which links two accounts that were kept apart on
purpose. Nothing about it looks wrong until the push.

Addresses are compared and names ignored, since the address is what a host
judges. For OpenPGP the key's own UIDs can be asked for as well, which catches a
config naming `user.email` in one scope while inheriting `user.signingkey` from
another. SSH keys carry no address, so that format gets the comparison alone and
rests on the config having been written as a pair.

`--no-sign` is the way through for a build that genuinely wants the mismatch.

### Verification failures read as an absence

Signing and verifying are configured separately, and SSH verification
additionally wants `gpg.ssh.allowedSignersFile` to exist. Without it,
`git log --show-signature` answers "No signature" and `%G?` answers `N`, on a
commit carrying a perfectly good one. Reading the commit object for its `gpgsig`
header is the check that cannot mislead.

### What signing costs

An OpenPGP signature costs the reproducible rebuild. It carries a fresh creation
time, so the same source and the same flags produce a different chain of hashes
on every run. An SSH ed25519 signature carries no such time and leaves the
rebuild comparable. See "Signing decides whether a rebuild repeats" above.

A locked key still asks, and the asking works. `prg` closes stdin, but the
prompt does not arrive through it: the agent runs pinentry itself and opens the
terminal it was told to use, so a passphrase typed during a build is accepted.
Take the terminal away, as cron or an editor task does, and pinentry has nothing
to open. An unattended build wants the key unlocked in advance.

`--no-sign` is the way out of both, and it is the only flag signing has. For the
first cost alone there is a second way out, which is to sign with an SSH ed25519
key. A machine set up to sign otherwise signs every build made from it, which is
not always what is wanted.

## `prg` never touches a remote

It builds a local directory and stops. Pushing is a separate, human step, and
keeping remote access out of the tool means it never needs credentials.

## Ingredients before the build

Every check `prg` can make happens before any of the work. Git on `PATH`, and
`tar` beside it. The source being a repo with releases in it. `--start` and
`--end` naming ones that are there. `--author` parsing. An identity to build
under. A signing key that names the same account as that identity. A target that
does not exist. `weed-out` on `PATH`, when a sanitizer was asked for.

`tar` is on that list because extracting a release is `git archive` piped into
it, which makes it the second binary every build shells out to, checked whether
or not a sanitizer runs. Without it a build fails at the first release, with the
target directory already created, which is the shape of failure this stage
exists to prevent.

Presence on `PATH` is the whole of the git check. No version is asserted,
because nothing the build runs needs one. The public branch is set with
`symbolic-ref` rather than `git init --initial-branch`, which arrived later. A
floor nobody has to meet beats a floor to keep current.

The stage returns two things: the failures, and the values a build would use.
Validation alone answers whether the build can run, but for a repo where every
field in a public commit is a decision, the more useful answer is what it will
stamp. A report showing the timestamps and hiding the author shows half the
decision. The signing key is resolved here too. Finding none is not a failure,
since an unsigned build is still a build. A key that disagrees with the author
is, because what it produces looks finished and is not.

Some ingredients are fatal and the rest are reported. Without git, with a source
holding no releases, or with a range naming none, there is no report to produce.
The fatal ones raise where the fact is learned, which for the range means while
the tags are being read, not in `preflight`. A missing identity is different:
the table can still be printed, and printing it is how the gap gets found.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and
documentation in this project are written in collaboration with
Artificial Intelligence (AI). The division of labour: the AI explores,
challenges assumptions and edge cases, and drafts; the human
initiates, drafts the designs, explores alongside the AI, reviews
every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
