# Changelog

## [Unreleased]

### Fixed

- `moodle_read` and `moodle_write`: an `args` field named `wsfunction` can no longer swap the checked function for another one.
- `moodle_download`: same-named files from different URLs no longer replace each other in the cache.

## [1.0.0] - 12:42 CEST 15-11-2026

### Added

- First release.
- `moodle_read`: runs read-only Moodle web-service functions (`_get_`, `_search_`, `_list_`).
- `moodle_write`: runs the functions that change things, such as submitting homework or posting; functions that handle keys, tokens or passwords, or call other functions, stay blocked.
- `moodle_upload` and `moodle_download`: move files to and from the site.
- `moodle-mcp login <site>`: signs in through the browser, which hands the key back to the terminal, or with a password on sites without single sign-on.
- `install`: registers the `moodlemobile://` link handler and, with `--mcp`, the server with Claude Code, Codex, Copilot CLI and Cursor.

[1.0.0]: https://github.com/MattFor/moodle-mcp/releases/tag/v1.0.0
