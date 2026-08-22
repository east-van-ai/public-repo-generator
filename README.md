# prg - Public Repo Generator

Build a clean public git repository from a private one. Only your tagged
releases cross over, stamped with a uniform timestamp. Sanitizing is opt-in.

## Why `prg` Exists

Even when the code is clean, publishing the whole git repo means publishing the
whole process. The late-night refactorings, the abandoned experiments, the
messy middle. `prg` lets you create a showcase repo that includes only your
tagged releases and their timestamps.

- **Curated timeline**: only `v*` release tags become public commits
- **Clean room build**: the output repo starts empty and is built from
  extracted release trees, never from the private object store
- **Optional sanitizer**: point `--weed-out` at the sanitizer and every release
  is filtered by its own keep list on the way through
- **Uniform timestamps**: every commit lands at noon, so the log reads as a set
  of release markers
- **Honest about what it is**: a presentation of the work, not a record of how
  the work happened

## Clean logs

Imagine this.

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

## How That Log Is Made

Git presents a commit's dates as though it watched the clock. They are fields.
Set them to whatever you like, and what comes out the other side is an ordinary
repo that every git tool reads without complaint.

That is the whole trick. `prg` creates an empty repo, then lays down one commit
per release tag, oldest first. Each carries the calendar date its release was
cut, with the time forced to noon, and each descends from the release before it.
The message is the tag name and the branch is `main`.

Nothing is copied out of the private repo's object store. The public repo is
built forwards, out of nothing, which is why untagged commits, abandoned
branches, and the reflog have no route into it. That holds whether or not the
sanitizer runs.

## What This Replaces

Publishing a release without its history means an orphan commit: a root with no
parent. Publishing the next release means a second orphan sitting beside the
first. Do that three times and the graph shows three disconnected stems instead
of a sequence.

The ugly graph is the visible symptom. The real loss is ancestry. Nothing
descends from anything, so `git log --follow`, blame, and GitHub's compare view
have nothing to walk. A viewer can see that v3 exists. They cannot see what
changed between v2 and v3, which is the one thing a release history is for.

`prg` builds a real chain instead. Each release lands on top of the one before
it, so the comparisons work.

That comparison is the thing worth showing. The diff between two releases is
what a project actually did that cycle, in one view, without a tour. A private
repo holds the same information and will not offer it, because a checkout opens
on a file tree and a commit list, and nobody scrolls a log hunting for where one
release ended and the next began. A repo built by `prg` has nothing else in it.
The comparison is what a visitor lands on.

## How It Works

```text
┌─────────────────────┐
│   Private Repo      │
│   (full history)    │
└──────────┬──────────┘
           │  v* tags on main
           ▼
┌─────────────────────┐
│   prg Rebuild       │
│   - Check out tag   │
│   - Sanitize if set │
│   - Commit at noon  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Public Repo       │
│   (releases only)   │
└─────────────────────┘
```

1. Collect the `v*` tags reachable from main/master, oldest first
2. Check each tag out into a scratch tree
3. With `--weed-out`, run the sanitizer over that tree, keeping only what
   `.weed-out-ignore` names
4. Commit the result, using the tag's own date at a uniform time, signed with
   the key configured where `prg` runs
5. Recreate the tags on the new commits

Nothing from the private object store is ever copied. The public repo is built
from scratch out of trees extracted one release at a time, so untagged commits,
abandoned branches, and the reflog have no route into it.

Filtering the files inside those trees is the sanitizer's own job, and it runs
only when asked. Without `--weed-out`, each release tag's tree crosses over
whole. The report says which of the two happened.

## Install

`prg` requires Python 3.9 or newer and depends only on the standard library.
Tested in CI on Python 3.9 through 3.14.

```bash
pipx install "git+https://github.com/east-van-ai/public-repo-generator.git"
```

`pipx` installs Python CLI tools into isolated environments, so there are no
dependency conflicts to worry about. Worth having around if you use more than
one Python CLI tool.

You also need `git` on your `PATH` and a git identity configured. Git invents one
from your account name and your machine's hostname when it finds none, and a
repo built for showcasing is the last place that belongs, so `prg` refuses
instead. `prg inspect` reports what it found without building anything.

Sanitizing is opt-in, and it is the only other thing. To use it, put
[weed-out](https://github.com/east-van-ai/weed-out) on your `PATH`, keep a
`.weed-out-ignore` file in the source repo listing what should ship, and pass
`--weed-out`.

## Quick Start

Preview which releases would cross over:

```bash
prg inspect ./private-repo
```

See what a build would produce, without writing anything:

```bash
prg generate ./private-repo ./public-repo
```

Build it for real:

```bash
prg generate ./private-repo ./public-repo --commit
```

Build it with the sanitizer, so every release ships only what its own
`.weed-out-ignore` allows:

```bash
prg generate ./private-repo ./public-repo --weed-out weed-out --commit
```

Build with a different public identity, starting from a later release:

```bash
prg generate ./private-repo ./public-repo \
    --author "Jane Doe <jane@example.com>" \
    --start v0.3.0 \
    --commit
```

Publish a stretch of releases and nothing outside it:

```bash
prg generate ./private-repo ./public-repo \
    --start v0.2.0 \
    --end v0.4.0 \
    --commit
```

Then push it yourself. `prg` never touches a remote.

## CLI Reference

`prg` with nothing after it prints its own documentation, and so does a
command word on its own. `prg --version` prints the installed version.
All three exit 0.

### Commands

| Command | Description |
| --- | --- |
| `prg generate SOURCE TARGET` | Rebuild TARGET from SOURCE's release tags |
| `prg inspect SOURCE` | List the tags that would become commits |

`SOURCE` must be an existing git repo. `TARGET` must not exist yet, since `prg`
never deletes anything it did not create.

### Flags for `generate`

| Flag | Default | Description |
| --- | --- | --- |
| `--tz {local,gmt}` | `local` | Timezone for the uniform timestamp |
| `--time HH:MM:SS` | `12:00:00` | Fixed time applied to every commit |
| `--author "Name <email>"` | git config | Identity for author and committer |
| `--weed-out CMD` | none | Path to the sanitizer. Without it, nothing is filtered |
| `--start TAG` | earliest `v*` tag | Begin from this release tag |
| `--end TAG` | latest `v*` tag | Stop at this release tag |
| `--no-sign` | off | Build unsigned, whatever the config says |
| `--dry-run` | on | Report the plan, write nothing |
| `--commit` | off | Actually build the repo |

Dry run is the default. `--commit` is what makes `prg` write. Both check the
ingredients first and print what a build would use, so a dry run that comes back
clean is the build's own gate rather than a guess at it.

`--start` and `--end` name release tags, and both are inclusive. Either can
stand alone. `--start` leaves the early releases out, which is how a public repo
begins at the version worth showing. `--end` leaves the late ones out, which is
how a release that is tagged but not yet announced stays private. A tag outside
the release set is an error, and so is an `--end` earlier than the `--start`
beside it.

`--author` falls back to the identity configured where `prg` runs. There has to
be one. `prg` refuses to build rather than let git invent a name and address
from your machine.

Commits are signed with the key configured in that same place, and unsigned when
there is none. `prg` reads `user.signingkey` and `gpg.format` and hands them to
git, so nothing new has to be set up: if your ordinary commits are signed, the
generated ones are too, in whichever format you already use. The report names the
key it found. That line earns its place once you keep more than one account,
because a host only shows a commit as verified when the key and the address
belong to the same one. `prg` refuses to build when they disagree, since what it
would produce looks finished and is not. `--no-sign` builds unsigned whatever the
config says, and is the way past a mismatch you actually want.

The target gets a copy of both halves in its own `.git/config`: the identity, the
key, and the format. None of it changes the build, which passes all three
directly. It is there for the day you amend the public repo by hand, so that
commit takes the public identity and the public key rather than the development
ones sitting in your global config. An unsigned build turns signing off there
instead. Local config never travels, so this reaches your working copy of the
target and nothing that gets pushed.

A key with a passphrase asks for it during the build, the same way any signed
commit does. A build with no terminal to ask on, under cron or an editor task,
wants the key unlocked first.

### Flags for `inspect`

| Flag | Default | Description |
| --- | --- | --- |
| `--tz {local,gmt}` | `local` | Timezone for the uniform timestamp |
| `--time HH:MM:SS` | `12:00:00` | Fixed time applied to every commit |
| `--start TAG` | earliest `v*` tag | Begin from this release tag |
| `--end TAG` | latest `v*` tag | Stop at this release tag |

`inspect` prints the timestamp each release would carry and lists the releases
that would cross over, so it takes the flags that shape both. It reads `SOURCE`
and stops there. Newest release first, the way `git log` reads, since that is
the log it is previewing.

Flags come after the command and its paths. Their order among themselves is
free, but the paths are read from their positions, so
`prg generate --commit ./private-repo ./public-repo` is an error rather than a
reordering.

### Exit codes

- `0`: success, and documentation. A bare command word is a question, so `prg`
    and `prg inspect` both print their documentation and exit 0
- `1`: any error `prg` raises itself (a half-typed command, a path too many,
    `SOURCE` is not a git repo, `TARGET` already exists, no `v*` tags found on
    main/master, no git identity configured, a signing key that disagrees with
    the author, or a sanitizer named by `--weed-out` is missing or fails)
- `2`: argparse's own errors (an unknown flag, an unknown command, or
    `--dry-run` and `--commit` together)

Exit 1 covers two different failures. A usage error, where what you typed is the
problem, prints the message and the usage line. A readiness failure, where the
command was right and something it needed was missing, prints the full report
instead, because a usage line would answer a question you did not ask.

Note where the line falls. `prg generate` asks what `generate` does and exits
0. `prg generate ./private-repo` names one path and forgets the other, which
is a slip rather than a question, and exits 1. So does `prg generate --commit`:
a flag asks for something specific, and both paths are still missing.

## Companion Tools

- [weed-out](https://github.com/east-van-ai/weed-out) is an allow-list file
  sanitizer. Pass `--weed-out` and `prg` runs it at every commit it builds.

## Philosophy

```text
    "Show the meal, not the dirty dishes."
```

`prg` isn't about hiding. It's about presentation. You decide what surfaces,
what stays backstage, and how the story reads.

## Notes

### Releases only, main/master only

Tags outside main/master are ignored, and so are tags that do not match `v*`.
The result is a linear release timeline. Untagged work never appears.

### The timeline is curated, not accurate

Dates are flattened to a uniform time and most commits never appear at all.
That is the point. A public repo built by `prg` shows what was released, not
how it was built.

See [DESIGN.md](DESIGN.md) for the reasoning behind these decisions and the
questions still open.

## Use of AI

This project is built with Artificial Intelligence (AI), deliberately
and in the open. Code and documentation are written in collaboration
with remote and local AI; design decisions, code review, and final
judgement stay human.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
