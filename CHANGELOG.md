# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.4.2] - 2026-09-08

### Added

- An annotated `prg-msg/<version>` tag in the source sets that release's public
  commit message, in place of the tag name. The marker does not cross over.
- `inspect` and `generate` print a message column when a release carries one.

### Changed

- DESIGN.md moves to `docs/`, and the command surface splits out into `docs/CLI.md`.

## [0.4.1] - 2026-09-03

### Added

- `prg version` prints the installed version, the same line `--version` prints.

## [0.4.0] - 2026-08-25

### Added

- `--weed-out` runs the `weed-out` sanitizer over every release tree
  between extraction and staging, so a public commit records only what that
  release's keep list allowed.
- `--weed-out-keep LIST` adds entries to every release's keep list, and turns
  the sanitizer on by itself.
- `preflight` checks for `tar`, the second binary every build shells out to.

### Changed

- `--weed-out` is a bare switch instead of a path to the sanitizer.

### Removed

- The `sanitizer` row from the report.

## [0.3.1] - 2026-08-22

### Added

- `generate` extracts each release tag's tree and commits it, so a public repo
  built by `prg` holds files. Each commit records the whole tree, so a file
  dropped between two releases reads as a deletion in the public log.
- `prg --version` prints the installed version and exits 0.

## [0.3.0] - 2026-08-16

### Added

- A preflight stage. Both commands check the ingredients before any work starts:
  git on `PATH`, an author identity, a signing key that agrees with it, a target
  that does not exist, and a sanitizer that does.
- A readiness failure prints the whole report before failing, and carries no usage line.
- Both commands report the values a build would use, above the release table.
- `inspect` reports a missing identity there and still exits 0.
- Generated commits are signed with the key configured where `prg` runs, in
  whichever format that config names, and the report names it beside the author.
  No key means an unsigned build.
- A signing key naming a different account from the author is refused before
  anything is written.
- `--no-sign` builds unsigned whatever the config says.
- The target's own config takes the resolved identity, the signing key, and
  `user.useConfigOnly`. An unsigned build writes `commit.gpgsign = false`.
- `--end TAG` on both commands, the counterpart to `--start`. Both bounds are
  inclusive and either can stand alone.

### Changed

- No configured git identity is a refusal. Git invents one from the account
  name and the hostname, and that was reaching generated repos.
- `inspect` and `generate` print the release table newest first, the way
  `git log` reads. The build still lays commits down oldest first.

## [0.2.0] - 2026-08-14

### Added

- `prg generate SOURCE TARGET --commit` builds a repo. One empty commit per
  release tag, stamped, tagged, and descending from the one before it, on `main`.
- `prg inspect SOURCE` lists the release tags that would become commits, oldest first,
  with the uniform timestamp each one would carry.
- `--tz`, `--time`, and `--start` on `inspect`, sharing `generate`'s defaults
  so the preview matches the build.
- Tests for `generate`: a dry run writes nothing, an existing target is refused, and
  `--commit` builds the chain it printed.

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
  grammar no longer shifts with the interpreter.
- A path too many is now prg's own error, exit 1, naming the command's usage.
  Argparse answered at 2 with the usage of `prg` itself.

### Removed

- The reflog expiry and the `gc` at the end of a build.

## [0.1.0] - 2026-08-12

### Added

- DESIGN.md records the release-tag model, the clean-room build, and the timestamp rules.
- `inspect` subcommand, alongside `generate`.
- `--author` and `--start`, and a `--dry-run`/`--commit` pair with dry run as the default.
- `gitio`, the layer that talks to git. Read-only so far: reachable release tags, commit
  dates, and tag messages.
- Tests covering the CLI surface and the git layer.
- `generate` takes `SOURCE` and `TARGET` as positional arguments.
- `prg` is a regular package with `src/prg/__init__.py`.
