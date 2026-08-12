# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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
