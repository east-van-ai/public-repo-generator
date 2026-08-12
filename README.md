# prg - Public Repo Generator

Build a clean public repo from a private one. Only your tagged releases cross
over, sanitized and stamped with a uniform timestamp.

## Why `prg` Exists

Even when the code is clean, publishing the whole repo means publishing the
whole process. The late-night refactorings, the abandoned experiments, the
messy middle. `prg` lets you show the releases without showing the road there.

- **Curated timeline**: only `v*` release tags become public commits
- **Clean room build**: the output repo starts empty, and only sanitized trees
  are ever committed to it
- **Uniform timestamps**: every commit lands at noon, so the log reads as a set
  of release markers
- **Honest about what it is**: a presentation of the work, not a record of how
  the work happened

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
│   - Apply weed-out  │
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
3. Run `weed-out` over that tree, keeping only what `.weed-out-ignore` names
4. Commit the result, using the tag's own date at a uniform time
5. Recreate the tags on the new commits
6. Expire the reflog and prune unreachable objects

Nothing from the private object store is ever copied. The public repo is built
from scratch out of trees that have already passed the sanitizer.

## Install

`prg` requires Python 3.9 or newer and depends only on the standard library.
Tested in CI on Python 3.9 through 3.14.

```bash
pipx install "git+https://github.com/east-van-ai/public-repo-generator.git"
```

`pipx` installs Python CLI tools into isolated environments, so there are no
dependency conflicts to worry about. Worth having around if you use more than
one Python CLI tool.

You also need [weed-out](https://github.com/east-van-ai/weed-out) on your
`PATH`, and a `.weed-out-ignore` file in the source repo listing what should
ship.

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

Build with a different public identity, starting from a later release:

```bash
prg generate ./private-repo ./public-repo \
    --author "Jane Doe <jane@example.com>" \
    --start v0.3.0 \
    --commit
```

Then push it yourself. `prg` never touches a remote.

## CLI Reference

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
| `--weed-out CMD` | `weed-out` | Path to the sanitizer |
| `--start TAG` | earliest `v*` tag | Begin from this release tag |
| `--dry-run` | on | Report the plan, write nothing |
| `--commit` | off | Actually build the repo |

Dry run is the default. `--commit` is what makes `prg` write.

Flags come after the command and its paths. Their order among themselves is
free. Bare `prg` prints help.

### Exit codes

- `0`: success. Bare `prg` prints help and exits 0, since help is what was
    asked for
- `1`: any error `prg` raises itself (`SOURCE` is not a git repo, `TARGET`
    already exists, no `v*` tags found on main/master, or `weed-out` is missing
    or fails)
- `2`: argparse's own errors (unknown flag, an unknown command, a missing path,
    or `--dry-run` and `--commit` together)

Note that the two "bad path" cases differ. A *missing* path is argparse's error
and exits 2, while a path that exists but is wrong is `prg`'s own and exits 1.

## Companion Tools

- [weed-out](https://github.com/east-van-ai/weed-out) is an allow-list file
  sanitizer. `prg` runs it at every commit it builds.

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
