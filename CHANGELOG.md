# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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
