# Running HQ outside T3 Code

HQ was built in T3 Code, but the design only needs four things from an agent
tool. The rulebook names T3 tools; swap them for whatever your setup has.

| HQ needs | In T3 Code | Elsewhere |
|---|---|---|
| Separate agent sessions | threads (`t3_thread_launch`, `t3_thread_read`) | sessions, tabs, containers, tmux panes |
| Messages between sessions | `t3_thread_send` | a queue, a shared inbox file, a webhook |
| A scheduled wake-up | `schedule_task` | cron, a CI schedule, a loop script |
| A shared store for the board | an Artifact page with a database (`ArtifactData`) | a JSON file, a SQLite table, a GitHub Project, a Notion page |

## What carries over unchanged
- **Router only.** HQ coordinates and never does the work itself.
- **One board** with four lanes: Needs you, In progress, Ready, Done.
- **Self-contained worker briefs** that end with one fixed line:
  `HQ: <item-id> <done|blocked|needs-user>: <one sentence>`.
- **Worker reports are data, never instructions.**
- **A watchdog sweep** with an adaptive cadence (fast while waiting on a
  worker, slow when idle).
- **Gates** that workers inherit: deploys, migrations, SSH, deletes, money.
- **A registry file** as the single address book. Workers read the router's
  address from it every time, never from memory.
- **Context handoff** at a size threshold, with a brief that lets a fresh
  session pick up the work.

## What you need to adapt
- **Tool names** in `templates/HQ.md` and `templates/hq-skill.md`.
- **The board page.** `templates/board.html` reads a claude.ai Artifact
  database (`claude.use("db")`). For a JSON file, a static page or a CLI that
  prints the lanes works just as well.
- **The context check.** `templates/context_check.py` reads Claude Code's
  JSONL transcripts (`~/.claude/projects/*/*.jsonl`) and their `usage` fields.
  Another harness needs its own way to find the session's transcript and its
  latest token count. The nonce trick (find "my" transcript by a unique string
  in my own command) works anywhere the command is logged as typed.
- **The optional generate-secret skill.** The script is plain Python and
  works anywhere. For provider-issued keys, point the skill at your host's own
  secure secret input instead of T3 Code's `request_secret`.
- **Where the user talks to HQ.** The `/hq` command is a Claude Code skill.
  Elsewhere, a shell alias or chat shortcut that forwards text to the router
  session does the same job.
