# HQ for agents

A simple way to not get overwhelmed with multiple AI chat sessions.

When you run many AI agent threads in parallel, decisions get buried in
scrollback, finished work waits unnoticed, workers stall quietly, threads grow
too long, and risky actions need a human to say "go". HQ fixes that with one
router thread that never does the work itself, one board with a **Needs you**
lane, a watchdog sweep, and a `/hq` command you can use from any thread.

It was built in [T3 Code](https://github.com/pingdotgg/t3code) with Claude, and
the pattern works with any agent tool that has sessions, messages between
them, scheduled tasks and a shared store.

```
                 you
                  |
          talk / "/hq ..."
                  |
                  v
   +==============================+
   |  HQ (router thread)          |
   |  routes, never codes         |
   +==============================+
      |  launches      ^  "Worker report"
      |  + brief       |  after every turn
      v                |
   +========+  +========+  +========+
   |worker A|  |worker B|  |worker C|
   +========+  +========+  +========+
                  ^
                  |  reads stalled threads
   +==============================+
   |  watchdog sweep              |
   |  every 30 min / every 4 h    |
   +==============================+
                  |
                  v
   +==============================+
   |  BOARD (single source of     |
   |  truth): Needs you | In      |
   |  progress | Ready | Done     |
   +==============================+
```

## Quick start (T3 Code)

1. Open [SETUP_PROMPT.md](SETUP_PROMPT.md).
2. Copy everything below the line and paste it into a Claude thread.
3. It installs the files into `~/hq/`, publishes the board, launches the HQ
   thread and creates the watchdog. HQ starts in **observe** mode, so it
   proposes and you approve.

Using another tool? Start with [docs/adapting.md](docs/adapting.md).

## What's inside

| File | What it is |
|---|---|
| [SETUP_PROMPT.md](SETUP_PROMPT.md) | The prompt you paste into your agent |
| [templates/HQ.md](templates/HQ.md) | The rulebook HQ follows: role, modes, board, workers, sweep, gates, handoff |
| [templates/state.json](templates/state.json) | The registry: HQ thread id, board URL, watchdog id, mode, thresholds |
| [templates/context_check.py](templates/context_check.py) | Checks a thread's context size and says when to hand off |
| [templates/board.html](templates/board.html) | The board page (four lanes, Needs you first) |
| [templates/hq-skill.md](templates/hq-skill.md) | The `/hq` command |
| [docs/adapting.md](docs/adapting.md) | How to run HQ outside T3 Code |

## How it works

- **Router only.** HQ routes. Anything bigger than reading state goes to a
  worker thread.
- **One board.** Four lanes: Needs you, In progress, Ready, Done. Chat replies
  point to the board and never become a second tracker. A Needs you row is
  written as a decision: what, why, and what HQ recommends.
- **Worker briefs.** Each worker gets a self-contained brief and ends every
  turn with `HQ: <item-id> <done|blocked|needs-user>: <one sentence>`, then
  sends that line to HQ as a `Worker report`.
- **Watchdog sweep.** Every 30 minutes while a worker is running, every 4 hours
  when idle. It finds stalled workers, checks PRs, and updates the board.
- **Observe and auto modes.** Observe proposes and waits for a yes. Auto
  launches up to 3 workers from Ready on its own.
- **Gates.** Deploys, migrations, production settings, SSH, deletes and
  spending always wait for you, in every mode.
- **`/hq` from anywhere.** `/hq <instruction>` forwards to HQ. `/hq` alone
  shows what needs you.
- **Context handoff.** Every thread checks its context size every 10 messages
  and hands off to a fresh thread above 300k tokens.

## Lessons from real use

- Relay only decisions the user actually made. If an answer is ambiguous, ask.
- Never name a PR by number alone. Add a one-sentence description.
- A thread in approval-required mode can't message an auto-mode router, so the
  sweep reads those threads instead.
- Workers that end a turn "waiting for a background run" often stall. The
  sweep nudges them.
- Type the context-check nonce literally. `$(...)` isn't recorded as expanded
  in the transcript, so the script can't find its own thread.
- Read the router's thread id from the registry every time. A worker once
  reported to a retired router after a handoff.
- Idle sweeps still cost context, so the cadence slows when nothing is expected.

## Credits

The shape (a router that hands work to worker sessions, plus a panel that shows
what needs a person) is borrowed from DeepSeek's
[Super-agent prototype](https://github.com/deepseek-ai/dsh-superagent-prototype).
The watchdog sweep, board lanes, gates and handoff rules are this project's own.

## License

[MIT](LICENSE)
