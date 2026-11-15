# Moodle MCP

[![CI](https://github.com/MattFor/moodle-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/MattFor/moodle-mcp/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/MattFor/moodle-mcp)](https://github.com/MattFor/moodle-mcp/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MCP server that lets AI agents use a Moodle account: courses, deadlines, grades, files and homework submissions.

## Requirements

- Linux, Python 3.10+, `~/.local/bin` on `PATH`
- A Moodle site that allows the Moodle app
- Any MCP client: Claude Code, Codex, Copilot CLI, Cursor, …

## Install

```sh
git clone https://github.com/MattFor/moodle-mcp
cd moodle-mcp
./install --all
moodle-mcp login moodle.example.edu
```

`--all` registers the server with the clients above that it finds. For any other client, add a stdio server with the command `moodle-mcp`. `login` signs in through your browser, or asks for your password if the site signs in that way.

## Usage

Ask your agent what is due this week, or to hand in `report.pdf` for an assignment. Reading (`moodle_read`) and changing (`moodle_write`) are separate tools, so you can let it read freely and approve every change. When the site expires the key, run `login` again.

## Removal

```sh
claude mcp remove --scope user moodle; codex mcp remove moodle; copilot mcp remove moodle
rm -r ~/.local/bin/moodle-mcp ~/.local/share/applications/moodle-mcp.desktop ~/.config/moodle-mcp ~/.cache/moodle-mcp
```

Remove `moodle` from `~/.cursor/mcp.json` if you use Cursor.

## License

MIT, see [LICENSE](LICENSE). By [MattFor](https://github.com/MattFor).
