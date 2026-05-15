# claude-code-token-statusline

A tiny [Claude Code](https://docs.claude.com/claude-code) status line plugin that shows your token consumption at a glance:

```
Session 42.3k (18%) | Today 186k $0.81 | <project> 74k
```

- **Session** — current session token total and context-window fill percent
- **Today** — total tokens across all of today's sessions, with cost
- **&lt;project&gt;** — today's tokens for the project matching your current `cwd`

Cross-session, cross-project aggregation is persisted to `~/.claude/token_log.jsonl`.

## Why

Claude Code's built-in display doesn't show cumulative usage across sessions or projects. If you're juggling multiple repos, this is the difference between "I have no idea what I burned today" and a one-line answer at the bottom of every prompt.

## Requirements

- Python 3.8+
- Claude Code with `statusLine` support (recent versions)
- Zero third-party dependencies — uses only the Python standard library

## Install

### 1. Drop the script anywhere

```bash
git clone https://github.com/Malygos1016/claude-code-token-statusline.git
```

You can put `statusline.py` wherever — `~/.claude/plugins/`, the cloned directory, anywhere readable by your shell.

### 2. Wire it into `~/.claude/settings.json`

Add a top-level `statusLine` key. **On Windows, use forward slashes** in the path — backslashes get partially eaten by shell-style argument splitting:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python /absolute/path/to/statusline.py"
  }
}
```

Windows example:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python D:/path/to/claude-code-token-statusline/statusline.py"
  }
}
```

### 3. Reload

Run `/hooks` inside Claude Code to refresh settings, or restart Claude Code. The status line should appear at the bottom of the screen.

## Configuration

Two optional JSON files in `~/.claude/`. Both are reloaded every time the status line renders (no restart needed).

### `~/.claude/cc_plugin_projects.json` — project labels

Maps case-insensitive substrings against the current working directory to short project labels. Use whatever makes sense to you — repo slugs, internal codenames, anything:

```json
{
  "my-monorepo/api":      "API",
  "my-monorepo/web":      "Web",
  "personal-blog":        "Blog",
  "client-acme":          "Acme"
}
```

The first matching key wins, in JSON-declared order. If nothing matches, the leaf directory name is used as the label.

### `~/.claude/cc_plugin_config.json` — display tweaks

```json
{
  "usd_to_local":    1.0,
  "currency_symbol": "$",
  "today_label":     "Today",
  "session_label":   "Session"
}
```

All fields optional; defaults are shown above. The cost reported by Claude Code is USD; this lets you display it in your local currency at a fixed rate.

Example for CNY display:

```json
{
  "usd_to_local":    7.20,
  "currency_symbol": "¥",
  "today_label":     "今日"
}
```

## Data files

| Path | What |
|---|---|
| `~/.claude/token_log.jsonl` | Per-render snapshot log. Each line is a JSON object with `ts`, `date`, `session_id`, `project`, `cwd`, `tokens`, `cost_usd`. Aggregation deduplicates per `session_id` and takes max within today. |
| `~/.claude/cc_plugin_projects.json` | Project label mapping (see above). |
| `~/.claude/cc_plugin_config.json` | Display config (see above). |

To reset today's tally, delete `~/.claude/token_log.jsonl`. To start fresh forever, delete and keep deleting.

## Behavior notes

- **Output is single-line** with ANSI color escapes. Claude Code's status line supports both.
- **Today is computed in local time**, based on calendar date (`YYYY-MM-DD`).
- **Cost is USD** as reported by Claude Code's `cost.total_cost_usd` field. The script multiplies by `usd_to_local`.
- **Fail-safe**: if anything goes wrong (bad stdin, log file write error), the script prints `?` and exits silently. It will never crash your status line.
- **Cumulative tokens may underestimate** sessions that were `/compact`-ed mid-day, because the `context_window` field reflects current context not lifetime accumulation. The cost field is monotonic and accurate.
- **Sessions spanning midnight may overestimate "today"**. Aggregation groups by `session_id` and takes the max cost/tokens within today's snapshots. If a session starts at 23:30 and continues past midnight, the post-midnight snapshots carry cumulative-since-session-start, so yesterday's late-night portion is double-counted into today. The error is bounded by what the session burned before midnight; for a session that started fresh after midnight it doesn't apply. A proper fix needs delta-per-snapshot tracking, which is on the roadmap if anyone hits this in practice.

## License

MIT. See [LICENSE](LICENSE).
