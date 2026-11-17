# Changelog

## [1.0.3] - 12:43 CET 17-11-2026

### Added

- Published on PyPI as `moodle-mcp-server`: `uv tool install moodle-mcp-server` (or `pipx`) installs the `moodle-mcp` command, and `uvx moodle-mcp-server` runs the server without installing.

## [1.0.2] - 12:19 CET 16-11-2026

### Fixed

- `moodle_download`: notebooks (`.ipynb`) and other files Moodle serves as JSON are saved instead of being reported as a refusal; only Moodle's own error reply counts as one.

## [1.0.1] - 08:00 CET 16-11-2026

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

[1.0.3]: https://github.com/MattFor/moodle-mcp/releases/tag/v1.0.3
[1.0.2]: https://github.com/MattFor/moodle-mcp/releases/tag/v1.0.2
[1.0.1]: https://github.com/MattFor/moodle-mcp/releases/tag/v1.0.1
[1.0.0]: https://github.com/MattFor/moodle-mcp/releases/tag/v1.0.0
