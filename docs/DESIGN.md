# Design

Why `prg` works the way it does. The code says what it does; this says why, and
what a change must not break.

## Curated, not accurate

The public timeline is a presentation, and it is artificial on purpose. Dates
are flattened and most commits never appear. `prg` makes no effort to defend the
timeline's accuracy.

What ends up inside the files is the opposite. A drifted date costs nothing. A
leaked credential costs something real. So the timeline is relaxed and the
sanitizing is strict.

## Built, not derived

`prg` creates the public repo empty and lays each release down as a new commit.
It is not a clone, a fork, or a filtered copy, and it shares no object with the
source. Untagged commits, side branches, and the reflog have no route in.

This is what separates it from `git filter-repo` and BFG. Those rewrite a
history that already holds the secret, and every clone taken before the rewrite
keeps it. `prg` never copies the history in the first place.

It works because commit dates are fields, not observations. Git takes whatever
`GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` say, so each release keeps its own
date and descends from the one before.

Every field in a public commit is therefore a decision: the date, the message,
the author, the tag, the signature. Nothing is sitting there to carry over.

The source is only read, never checked out or written. The one destructive act
is emptying the target's working tree between releases, and it is confined to a
directory `prg` created.

Regenerating replaces the public repo rather than updating it. The same tags
and the same flags produce the same hashes, so a rebuild that changed nothing
is a no-op. Signing can break that; see "Signing decides whether a rebuild
repeats".

## Only release tags cross over

Public commits come from `v*` tags reachable from main or master, one commit per
tag. The public log should read as a release history, because that is what is
being shown. The pattern is not configurable, since `v*` is already the
convention and a flag would only add a way to get it wrong.

`--start` and `--end` cut the range. The start tag becomes the public root with
nothing summarizing what came before it, because there is nothing honest to put
there.

## Sanitizing

Filtering the files is the job of
[`weed-out`](https://github.com/east-van-ai/weed-out), a companion tool that
works from an allow list. A file the keep list does not name never reaches the
output, so there is nothing left for a secret scanner to find.

Sanitizing is opt-in. Most repos have nothing to strip.

`prg` adds `--keep ".git/"` to every run and protects nothing else. That keeps
the repository from being weeded along with the tree, without relying on a keep
list someone else wrote. `prg` checks nothing afterwards: keeping `.git` whole is
a rule `weed-out` enforces.

Each release is filtered by the `.weed-out-ignore` in its own tag. A release
ships what its own rules allowed when it was cut, not a judgement it was never
made with. `--weed-out-keep` adds entries across every release, for the ones
whose rules were missing or too narrow. It never subtracts.

Each public commit records the whole sanitized tree, never a change laid over
the release before. Layering would leak: what survived would be the previous
release's leftovers plus the current one's, which neither keep list allowed.

A release whose tree comes out empty still becomes a commit. Stopping at the
first one would report one per run while already knowing the rest.

## Timestamps

Each public commit keeps the calendar date of the commit its tag points at, not
the date the tag was typed. The time is forced to noon, in the local zone or GMT.
Author and committer dates both get it.

The uniform time is a signal. A log where every commit lands at 12:00:00 says
these are release markers, not a record of when hands were on the keyboard.

Two releases on one date take 12:00:00, 12:00:01, and so on, in their original
order. The date is the one in the selected zone, since two releases that share
a day in GMT can fall on different days locally.

## Commit message

The tag name, and nothing else, unless a marker says otherwise.

A release tag's own annotation never crosses over. `weed-out` filters files, so
prose is the one thing no keep list covers, and a tag message is written in a
private context. CHANGELOG.md ships and already says what each release changed.

### The marker

An annotated tag named `prg-msg/v0.4.5` sets the public message for `v0.4.5`:

```bash
git tag -a prg-msg/v0.4.5 -m "config files can be split across directories"
```

Its prose was written knowing where it goes, which is why it publishes and the
release annotation does not. Only the name binds and only the subject travels.
The marker itself stays private. No flag turns it on, so `inspect` is where the
prose gets read before it publishes.

A marker naming no release is refused, since otherwise a typo does nothing and
says nothing. So is a marker with no message, since git would quietly report
the tagged commit's subject in its place. Both refusals stop `inspect` as well,
because a preview that tolerates what the build rejects is not a preview.

## Tags, branch, and hooks

Public tags are lightweight. Nothing to write means nothing to leak.

The branch is always `main`. A repo built today has no older convention to
carry forward.

Hooks never run. The commits are manufactured, so there is nothing for a hook
to check, and one that prompts would hang with stdin closed.

## Author identity

The git identity configured where `prg` runs, or `--author`. The identity for
public releases is often not the one for development.

Configured means configured. Git invents an identity from the account and the
hostname when it finds none, and a public repo would then publish
`you@your-laptop.local`. No identity is a refusal, not a fallback.

The target keeps a copy of the identity and the signing choice in its own
config. A commit made there by hand later would otherwise take the development
identity and key, which is the mismatch `prg` refuses to build.

## Signing follows the key where prg runs

A showcase repo that reads "Unverified" undercuts itself, so `prg` signs when a
key is configured where it runs. The manufactured dates do not get in the way,
since verification checks the signature over the commit bytes and never the
date.

The key must belong to the account the author's address names. A mismatch
publishes a repo that is signed, Unverified, and linking two accounts kept apart
on purpose, so `prg` refuses it before building.

### Signing decides whether a rebuild repeats

| Build | Rebuild repeats |
| --- | --- |
| `--no-sign` | yes |
| signed, SSH ed25519 | yes |
| signed, OpenPGP | no |

A rebuild repeats when the signature embeds no timestamp and the algorithm is
deterministic. Read each row as the pair it names, not as its format.

## `prg` never touches a remote

It builds a local directory and stops. Pushing is a human step, so the tool
never needs credentials.

## Ingredients before the build

Every check runs before the first write, so a failed build leaves nothing
behind. All the failures are reported together rather than one per run.

The stage also returns the values a build would use. Every field in a public
commit is a decision, so what it will stamp is worth more than whether it can
run.

Some failures leave nothing to report, such as a source with no releases, and
those stop at once. A missing identity does not: the release table still
prints, and printing it is how the gap gets found.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and documentation in
this project are written in collaboration with Artificial Intelligence (AI). The
division of labour: the AI explores, challenges assumptions and edge cases, and
drafts; the human initiates, drafts the designs, explores alongside the AI,
reviews every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
