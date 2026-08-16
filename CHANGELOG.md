# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.3.0] - 2026-08-16

### Added

- A preflight stage. Both commands check the ingredients before any work starts:
  git on `PATH`, an author identity, a signing key that agrees with it, a target
  that does not exist, and a sanitizer that does.
- A readiness failure prints the whole report before failing, so one run names
  every missing ingredient. It carries no usage line, since the command line was
  not the problem.
- Both commands report the values a build would use, above the release table.
- `inspect` reports a missing identity there and still exits 0. It answers which
  releases cross over, and that answer holds either way.
- Generated commits are signed with the key configured where `prg` runs, in
  whichever format that config names, and the report names it beside the author.
  No key means an unsigned build.
- A signing key naming a different account from the author is refused before
  anything is written. The pair could only produce commits a host reads as
  unverified.
- `--no-sign` builds unsigned whatever the config says. It is the way past a
  deliberate mismatch, and the way to two builds whose hashes can be compared.
- The target's own config takes the resolved identity, the signing key, and
  `user.useConfigOnly`, so a commit made there by hand later cannot fall back to
  the dev identity or the dev key. An unsigned build writes
  `commit.gpgsign = false` there instead.
- `--end TAG` on both commands, the counterpart to `--start`. Both bounds are
  inclusive and either can stand alone, so a release that is tagged but not yet
  announced can be held back.

### Changed

- No configured git identity is a refusal. Git invents one from the account
  name and the hostname, and that was reaching generated repos.
- `inspect` and `generate` print the release table newest first, the way
  `git log` reads. The build still lays commits down oldest first.

## [0.2.0] - 2026-08-14

### Added

- `prg generate SOURCE TARGET --commit` builds a repo. One empty commit per
  release tag, stamped, tagged, and descending from the one before it, on
  `main`. Release trees and the sanitizer are not in it yet.
- `prg inspect SOURCE` lists the release tags that would become commits,
  oldest first, with the uniform timestamp each one would carry.
- `--tz`, `--time`, and `--start` on `inspect`, sharing `generate`'s defaults
  so the preview matches the build.
- Tests for `generate`: a dry run writes nothing, an existing target is
  refused, and `--commit` builds the chain it printed.

### Changed

- `--weed-out` has no default. Sanitizing is opt-in, and without the flag each
  release tag's tree crosses over whole.
- Public commit messages are the tag name, and public tags are lightweight. A
  private tag annotation no longer crosses over.
- A command word and nothing else prints documentation and exits 0. `prg`
  prints the tool's, `prg inspect` prints that command's.
- A half-typed command is prg's own error at exit 1, including
  `prg generate SOURCE` and `prg generate --commit`. Argparse answered at 2.
- Paths are read from their positions on the command line, so the accepted
  grammar no longer shifts with the interpreter. `prg generate . --commit out`
  was a usage error on Python 3.9 and a finished build on 3.14.
- A path too many is now prg's own error, exit 1, naming the command's usage.
  Argparse answered at 2 with the usage of `prg` itself.

### Removed

- The reflog expiry and the `gc` at the end of a build. A repo built out of
  nothing holds nothing unreachable, so there was never anything to collect.

## [0.1.0] - 2026-08-12

### Added

- DESIGN.md, recording the release-tag model, the clean-room build, and the
  timestamp rules.
- `inspect` subcommand, alongside `generate`.
- `--author` and `--start`, and a `--dry-run`/`--commit` pair with dry run as
  the default.
- `gitio`, the layer that talks to git. Read-only so far: reachable release
  tags, commit dates, and tag messages, where a lightweight tag reads as
  carrying none of its own.
- Tests covering the CLI surface and the git layer.

### Changed

- `generate` takes `SOURCE` and `TARGET` as positional arguments. `--output` is
  gone.
- README.md documents the settled CLI surface, replacing the earlier sketch.
- `PRG` and the defaults moved to `generator.py`, leaving `cli.py` with the
  command surface alone.
- `prg` is a regular package now that `src/prg/__init__.py` exists. It shipped
  as a namespace package before.

### Removed

- The `--verify` flag. Auditing a generated repo is deferred.
