"""Claude Code statusline: Session + Today + Project token counter.

Reads Claude Code's statusLine JSON from stdin, persists per-snapshot log
to ~/.claude/token_log.jsonl, and prints a one-line statusbar:

    Session 42.3k (18%) | Today 186k ¥0.81 | <project> 74k

Project label is derived from the current working directory using a mapping
configured in ~/.claude/cc_plugin_projects.json. If no mapping matches,
falls back to the leaf directory name.

Configure project mapping by creating ~/.claude/cc_plugin_projects.json:
    {
      "sts2mods":      "STS2",
      "myapp/backend": "Backend",
      "myapp/web":     "Web"
    }
The keys are case-insensitive substrings matched against the cwd.

Tune currency conversion / formatting via ~/.claude/cc_plugin_config.json:
    {
      "usd_to_local": 7.20,
      "currency_symbol": "¥",
      "today_label": "Today",
      "session_label": "Session"
    }
All fields optional; defaults shown above.
"""
from __future__ import annotations
import io
import json
import sys
from datetime import datetime, date
from pathlib import Path

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

LOG_PATH = Path.home() / ".claude" / "token_log.jsonl"
PROJECT_CONFIG = Path.home() / ".claude" / "cc_plugin_projects.json"
DISPLAY_CONFIG = Path.home() / ".claude" / "cc_plugin_config.json"

DEFAULTS = {
    "usd_to_local": 1.0,
    "currency_symbol": "$",
    "today_label": "Today",
    "session_label": "Session",
}


def load_project_map() -> list[tuple[str, str]]:
    if PROJECT_CONFIG.exists():
        try:
            raw = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
            return [(k.lower(), v) for k, v in raw.items()]
        except Exception:
            return []
    return []


def load_display_config() -> dict:
    cfg = dict(DEFAULTS)
    if DISPLAY_CONFIG.exists():
        try:
            cfg.update(json.loads(DISPLAY_CONFIG.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def classify(cwd: str, mapping: list[tuple[str, str]]) -> str:
    low = cwd.lower()
    for needle, label in mapping:
        if needle in low:
            return label
    name = Path(cwd).name
    return name if name else "?"


def fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"statusline: bad input ({e})\n")
        print("?", flush=True)
        return

    cfg = load_display_config()
    session_id = data.get("session_id", "")
    workspace = data.get("workspace") or {}
    cwd = workspace.get("current_dir") or data.get("cwd", "")
    cw = data.get("context_window") or {}
    sess_in = int(cw.get("total_input_tokens") or 0)
    sess_out = int(cw.get("total_output_tokens") or 0)
    sess_tot = sess_in + sess_out
    used_pct = float(cw.get("used_percentage") or 0)
    cost_usd = float((data.get("cost") or {}).get("total_cost_usd") or 0.0)

    mapping = load_project_map()
    project = classify(cwd, mapping)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    snap = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "date": date.today().isoformat(),
        "session_id": session_id,
        "project": project,
        "cwd": cwd,
        "tokens": sess_tot,
        "cost_usd": cost_usd,
    }
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
    except Exception:
        pass

    today = date.today().isoformat()
    per_session: dict[str, dict] = {}
    if LOG_PATH.exists():
        try:
            with LOG_PATH.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("date") != today:
                        continue
                    sid = rec.get("session_id", "")
                    if not sid:
                        continue
                    tk = int(rec.get("tokens") or 0)
                    c = float(rec.get("cost_usd") or 0.0)
                    p = rec.get("project", "")
                    prev = per_session.get(sid)
                    if (not prev) or c > prev["cost"]:
                        per_session[sid] = {"tokens": tk, "cost": c, "project": p}
                    elif tk > prev["tokens"]:
                        prev["tokens"] = tk
        except Exception:
            pass

    today_tok = sum(v["tokens"] for v in per_session.values())
    today_cost = sum(v["cost"] for v in per_session.values())
    proj_tok = sum(v["tokens"] for v in per_session.values() if v["project"] == project)
    today_local = today_cost * cfg["usd_to_local"]

    CYAN = "\033[36m"
    YEL = "\033[33m"
    GRN = "\033[32m"
    DIM = "\033[2m"
    RST = "\033[0m"

    out = (
        f"{CYAN}{cfg['session_label']}{RST} {fmt_tok(sess_tot)} {DIM}({used_pct:.0f}%){RST}"
        f" {DIM}|{RST} {YEL}{cfg['today_label']}{RST} {fmt_tok(today_tok)}"
        f" {DIM}{cfg['currency_symbol']}{today_local:.2f}{RST}"
        f" {DIM}|{RST} {GRN}{project}{RST} {fmt_tok(proj_tok)}"
    )
    sys.stdout.write(out)
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        sys.exit(0)
