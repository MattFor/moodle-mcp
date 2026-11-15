# Changelog

## [Unreleased]

### Added

- `moodle_read`: runs read-only Moodle web-service functions (`_get_`, `_search_`, `_list_`).
- `moodle_write`: runs the functions that change things, such as submitting homework or posting; functions that handle keys, tokens or passwords, or call other functions, stay blocked.
- `moodle_upload` and `moodle_download`: move files to and from the site.
- `moodle-mcp login <site>`: signs in through the browser, which hands the key back to the terminal, or with a password on sites without single sign-on.
- `install`: registers the `moodlemobile://` link handler and, with `--mcp`, the server with Claude Code, Codex, Copilot CLI and Cursor.
