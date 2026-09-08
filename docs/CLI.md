# Command line

Why `prg`'s command surface works the way it does. What each command accepts,
what it prints, what it exits with, and what each flag decides.

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

### The documentation it answers with is the manual

Nothing installs the project's prose. `pipx install` puts a command on `PATH`
and leaves every document behind in the repository it was built from, so a bare
`prg generate` is the only manual most people who run `prg` will ever open.

Length is therefore the wrong thing to economize on there. A command's docstring
carries what a reader needs in order to use it, down to the detail that would
sit in a footnote elsewhere, because the reader has nowhere else to look it up.
That is why the sanitizer's entry explains weed-out's pattern grammar rather
than naming the flag and stopping.

### The version reads the installed metadata

`prg version` and `prg --version` print the same one line and exit 0. Both are
documentation, the same as a bare command word, so they share that code. One
helper builds the line and both spellings call it, so the two cannot say
different things.

The number lives in `pyproject.toml` and reaches the CLI through the installed
distribution's metadata. No second copy sits in the source. A checkout that has
never been installed has no metadata to read, and every invocation past a bare
word builds the parser, so an unguarded lookup would take down every command
rather than this one answer. The miss is answered instead, `unknown (not
installed)`, and the parser goes on being built.

The name printed is `prg`, the word that was typed, not
`public-repo-generator`, the distribution the number was read from. The two
differ here. The command line is what the reader is holding.

The flag sits on the root parser and nowhere else, so `prg generate --version`
is an unknown flag, exit 2. Asking what the tool is has one place to be asked,
and the tool answers it rather than a command.

The word is answered outside the command table. It has no path slot, no
options, and no documentation of its own to print, which is the whole of what
that table holds. Anything following it is a stray, exit 1. A flag following it
is argparse's unknown flag, exit 2, because the word is a subparser carrying
nothing.

## Dry run by default

`prg` reports what it would build. `--commit` makes it act. Same grammar as
`weed-out`, so the two tools behave like one set.

### What a dry run prints

The values the build would use, then the plan it would follow. One line per
release: the tag name and the uniform timestamp it would receive. Then a count.

It is the same table `inspect` prints. Both read the same plan, so a preview
cannot drift away from the build it is previewing.

Nothing is extracted, so a dry run says nothing about which files would ship.
What it does check is the ingredient list `preflight` runs, and that is where
the failures worth meeting before `--commit` get met.

A real build prints the plan, then lays it down. So the dry run is the build's
own plan, not a second description of it written alongside.

## The verdict is not the report

All three print the same page. The exit code is what differs.

| Command | Prints | Exit |
| --- | --- | --- |
| `inspect` | the values and the table | 0 |
| dry run | the values, the failures, and the table | 1 |
| `--commit` | the same, and that nothing was written | 1 |

`inspect` answers which releases cross over and at what time. That answer holds
whether or not an identity is configured, so a missing one is reported and the
command passes. It is the cheapest way to find the gap in the first place.

The dry run reports the same gap and fails on it, because meeting the failures
before `--commit` meets them is the reason it exists. It prints everything first.
A dry run that stopped at the first missing ingredient would drip-feed them, one
run per fix, while already knowing all of them.

`--commit` fails the same way and adds that nothing was written. There is no
second code path. The dry run is the build's own gate rather than a description
of one.

## Readiness failures print no usage line

An error normally prints `prg: message`, then the usage line, then exits 1. That
is right when what was typed is the problem. A readiness failure is not that. The
command line was correct and something it needed was missing, so a usage line
answers a question nobody asked.

The exit code does not move. Exit 1 is prg's own error and it covers both without
stretching. What differs is what gets printed beside it.

## What `inspect` prints

The values a build would use, then the tags that would become commits, latest
first. Two columns: the name, and the uniform timestamp it would receive. A
third when a marker gives some release a message of its own.

Newest first because the table previews a log, and `git log` reads that way. A
preview running the other way asks the reader to flip it in their head. The
build still lays the commits down oldest first, since that is what the parent
chain needs, so the reversal is presentation and nothing more.

The message column appears only when a marker put a message there. Otherwise
the public commit message is the tag name, so a third column would print the
first one again on every line. Once one release says something else, every line
shows what its commit will say, since a column going blank for the rest would
leave the reader inferring.

That column is also the only place a marker's prose can be read before it
publishes. Reviewing it is what `inspect` is for here.

A timestamp belongs to the command that owns the flags shaping it, so `inspect`
carries `--tz` and `--time`, with the same defaults `generate` uses. The stamp
is the part of a preview most worth having, since it is what the public log will
actually read.

`--start` and `--end` come along for the same reason. They decide which releases
cross over, and a preview listing releases the build will skip is previewing
something else.

One stamp per line, not two. The commit's real date is a click away in the
source repo, and a preview of the public timeline is not the place to show the
private one beside it.

`inspect` stops at `SOURCE`. It never looks at a target, so it answers the
question that comes before a target has been picked. That is the line between it
and a dry run.

## Where the range cuts

`--start` and `--end` are inclusive, and either can stand alone. Both name a
release tag rather than a date, since the tags are what cross over.

Releases earlier than the start tag do not appear at all. The start tag's
commit becomes the public root, carrying no parent and no summary of what came
before it.

There is nothing honest to put there. A squashed "everything up to v0.3.0"
commit would claim a history the public repo is not holding.

`--end` points the same instrument the other way. Releases after the end tag do
not appear, and the end tag becomes the tip of `main`. `--start` hides history;
`--end` holds work back, so a release that is cut but not yet announced stays
private without having to build before tagging it.

A bound naming a tag outside the release set is an error rather than a silent
fallback to the earliest or the latest. So is an `--end` earlier than the
`--start` beside it, and that message names both bounds: either one alone looks
fine, and the pair is what went wrong.

The cut happens before any timestamp is worked out. Releases that do not cross
over are not in the public repo, so they take no part in deciding which dates
collide there.

## The sanitizer is opt-in

`--weed-out` has no default. Without it nothing is filtered, and each release
tag's tree crosses over whole.

Sanitizing is a choice about one particular repo, not a property of every
rebuild. Plenty of repos have nothing to strip, and the ones that do are opting
in either way.

The report says nothing about it. Which mode a build ran in is what the command
line was, and the page carries no row for it. A page that claims less needs no
qualifying; the row can arrive later, with something worth putting in it.

## The sanitizer is named, not located

`--weed-out` is a bare switch. It never carries a path.

`weed-out` is a companion tool with one name, installed the way any CLI is
installed, and `PATH` is what says where it lives. A flag answering that question
too would be a second place for the answer to be wrong, and a build pointed at
the wrong binary does not announce itself.

What that costs is the ability to see which binary a build reached, which the
flag carried when it held a path. Nothing pays that back for now. `which
weed-out` answers it from the shell that ran the build, and one that is wrong
there was going to be wrong either way.

## `--weed-out-keep` implies the sanitizer

`--weed-out-keep` on its own turns the sanitizer on, with `weed-out` as the
command. Naming extra keep entries is an intention to sanitize, so `prg` reads it
as one. Refusing a command line whose meaning was never in doubt would be a
second flag to type for nothing.

Nothing about the failure moves. `weed-out` still has to be on `PATH`, and
`preflight` reports a missing one exactly as it does for `--weed-out`. An
intention to sanitize is taken as true; whether it can be carried out is still
checked.

## No flag turns signing on

A signing key configured where `prg` runs is the whole instruction. There is no
`--sign`, because the answer is already on disk and a flag would only repeat it.

The key belongs to the identity being published under rather than to the
machine. Two accounts mean two keys, often in two formats, and the way to choose
between them is to stand in a directory configured for one of them. That is the
same question `--author` answers, so both are resolved from the same place.

The format travels with the key, because it decides what the key is: a path to a
public key file for SSH, a key ID for OpenPGP. A key found with no format beside
it takes openpgp, which is git's own default rather than a choice made here.

`prg` holds no key material. Those two values name a key, and git and its agent
do everything after that. So a build still needs no credentials, and the git
version floor is untouched, since whether the format is OpenPGP or SSH is the
configuration's business.

## Existing output directory

Refuse and stop. `prg` does not delete anything it did not create.

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
