# Command line

Why `prg`'s command surface works the way it does. What each command accepts,
what it prints, what it exits with, and what each flag decides.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success, and documentation |
| 1 | `prg`'s own error |
| 2 | argparse's error: an unknown command, an unknown flag, or a bad value |

Exit 1 covers what was typed and what was missing alike, from a stray path to a
build that stopped part-way.

## Positions are decided, not inferred

`prg` reads the command word, `SOURCE`, and `TARGET` from fixed slots in the
command line, and discards whatever the parser resolved from elsewhere.

Argparse accepts more than the documented grammar, and how much more depends on
the interpreter. `prg generate . --commit ./public-repo` is a usage error on
Python 3.9 and a finished build on Python 3.14. One command line carrying two
meanings across the supported range is worse than either meaning on its own. So
the grammar is the same everywhere: paths first, then flags.

Flags take the full name only. Argparse accepts any unambiguous prefix, so
`--com` would mean `--commit` until a second flag shared the prefix, and then
mean nothing.

Two positionals is the ceiling. The pair reads the way `cp` does, what is read
and then what is written. A third would stop being read and start being
memorized.

Anything past a command's last slot is `prg`'s own error, exit 1, so the usage
line names the command whose grammar was broken rather than the tool. Exit 2
keeps what argparse owns, where its own message is the better one.

## A bare command word is a question

| Typed | Answer |
| --- | --- |
| `prg` | the tool's documentation, exit 0 |
| `prg inspect` | that command's documentation, exit 0 |
| `prg generate SOURCE` | missing TARGET, exit 1 |
| `prg generate --commit` | missing SOURCE, exit 1 |
| `prg generate SOURCE TARGET EXTRA` | one path too many, exit 1 |
| an unknown command or flag | argparse's error, exit 2 |

Asking what a command does is not a usage complaint. Forgetting one of two
paths is a slip, and a slip is an error.

The test is a command word and nothing else. Once any other token is present,
something specific was asked for, and documentation would bury the mistake.
`isatty` decides nothing, so a command line answers the same way from a shell,
from cron, and from a test.

### The documentation it answers with is the manual

`pipx install` puts a command on `PATH` and leaves every document behind, so a
bare `prg generate` is the only manual most users will ever open. Length is the
wrong thing to save there. The page carries every flag, every default, and what
happens. Why the tool behaves that way stays in these documents.

`prg generate --help` is not that page, and most users try it first. So the
banner points to the bare words. The command's own `--help` does not, since the
page ends with it and would point at itself.

The usage line, the paths, and the flags are written once, where they are
parsed, so the page cannot document a flag the parser rejects.

### The version reads the installed metadata

`prg version` and `prg --version` print the same line and exit 0. Both are
documentation, like a bare command word, and `prg --help` lists both. Argparse
names `version` among the commands in its own errors anyway, so hiding one
spelling would never be complete.

The number lives in `pyproject.toml` alone and reaches the CLI through the
installed metadata. A checkout that was never installed answers `unknown (not
installed)` rather than failing. The lookup runs on every command, so a failure
there would take them all down.

The line says `prg`, the word that was typed, not `public-repo-generator`, the
distribution the number came from.

The flag belongs to the tool, not to a command, so `prg generate --version` is
an unknown flag, exit 2. Asking what the tool is has one place to be asked.

## Dry run by default

`prg` reports what it would build, and `--commit` makes it act. The grammar
matches `weed-out`, so the two tools behave like one set.

A dry run prints the page a real build prints, read from the same plan, so a
preview cannot drift from the build it previews. Nothing is extracted, so it
says nothing about which files would ship. What it checks is every ingredient
the build needs.

### The verdict is not the report

With an identity missing, all three print the same page. The exit code is what
differs.

| Command | Prints | Exit |
| --- | --- | --- |
| `inspect` | the values and the table | 0 |
| dry run | the values, the table, and the failures | 1 |
| `--commit` | the same, and writes nothing | 1 |

`inspect` answers which releases cross over and when. That answer holds without
an identity, so it passes. The dry run exists to meet failures before `--commit`
does, so it fails. `--commit` fails the same way before writing anything, since
the dry run is the build's own gate rather than a description of one.

### Readiness failures print no usage line

The command line was correct and something it needed was missing, so a usage
line would answer a question nobody asked. A build that stopped part-way prints
none either. Both still exit 1, since both are `prg`'s own error.

## What `inspect` prints

The values a build would use, then the releases that would become commits, each
with the timestamp it would receive. Newest first, because the table previews a
log and `git log` reads that way. The build still lays the commits down oldest
first, so the order is presentation only.

A third column shows each commit's message, but only once a `prg-msg/` marker
gives some release a message of its own. Otherwise the message is the tag name,
and the column would repeat the first one on every line. It is also the only
place a marker's prose can be read before it publishes.

`inspect` takes the flags that shape what it previews. `--tz` and `--time` come
with `generate`'s defaults, since the stamp is what the public log will read.
`--start` and `--end` come too, since a preview listing releases the build will
skip is previewing something else. One stamp per line: the private date has no
place in a preview of the public timeline.

`inspect` stops at `SOURCE` and never looks at a target, so it answers the
question that comes before one is picked. That is the line between it and a dry
run.

## Where the range cuts

`--start` and `--end` are inclusive, and either can stand alone. Both name a
release tag rather than a date, since the tags are what cross over.

`--start` hides history. Earlier releases do not appear, and the start tag
becomes the public root. `--end` holds work back. Later releases do not appear,
so a release that is cut but not yet announced stays private without building
before tagging it.

A bound outside the release set is an error, not a fallback to the earliest or
the latest. So is an `--end` earlier than its `--start`, and that message names
both, since either one alone looks fine.

The cut happens before any timestamp is worked out, so a release that does not
cross over takes no part in deciding which dates collide.

## The sanitizer is opt-in

`--weed-out` has no default, so each release tag's tree crosses over whole
unless it is asked for. The report carries no row for the mode, since the
command line already says it.

`--weed-out-keep` on its own turns the sanitizer on. Naming keep entries is an
intention to sanitize, and refusing a command line whose meaning is not in doubt
would ask for a second flag for nothing. `weed-out` still has to be on `PATH`,
and a missing one is reported the same either way.

### The sanitizer is named, not located

`--weed-out` is a bare switch and never carries a path. `PATH` says where
`weed-out` lives, and a flag answering that too would be a second place for the
answer to be wrong. A build pointed at the wrong binary does not announce
itself. `which weed-out`, run from the same shell, shows which one a build
reached.

## No flag turns signing on

A signing key configured where `prg` runs is the whole instruction. There is no
`--sign`, because the answer is already on disk and a flag would only repeat it.

The key belongs to the identity being published under, not to the machine. So
choosing between two accounts means standing in a directory configured for one
of them. The identity comes from the same place when `--author` is not given.

The format travels with the key, since it decides what the key is: a public key
path for SSH, a key ID for OpenPGP. A key with no format beside it takes
openpgp, git's own default. `prg` holds no key material. Git and its agent do
the signing, so a build needs no credentials.

## Existing output directory

Refuse and stop. `prg` does not delete anything it did not create.

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
