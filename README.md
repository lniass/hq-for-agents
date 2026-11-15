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

## Commands

Type these in any thread. More commands will be added here as HQ grows.

| Command | What it does |
|---|---|
| `/hq` | Shows what needs you: the Needs you items, plus links to the board and the HQ thread. |
| `/hq <instruction>` | Sends an instruction to HQ from whatever thread you're in. HQ acts on it in the HQ thread, and you get a one-line confirmation where you typed it. |

Things you can ask with `/hq <instruction>`, in plain words:

```
/hq add a task: clean up the old feature flags
/hq switch to auto mode
/hq set the context handoff limit to 200k tokens
/hq check context size every 5 messages
```

The last two change the [context limits](#context-limits). HQ updates
`~/hq/state.json` and confirms, and every thread uses the new value from its
next check. No file editing needed.

**Preferences every thread follows.** Rules you want in every thread, HQ and
running workers included, go in your user-level `~/.claude/CLAUDE.md`. Claude
Code loads it in every session, so a new rule there reaches all threads on
their next start. For workers that are already running, ask HQ to pass the
rule on in its next follow-up.

## What's inside

| File | What it is |
|---|---|
| [SETUP_PROMPT.md](SETUP_PROMPT.md) | The prompt you paste into your agent |
| [templates/HQ.md](templates/HQ.md) | The rulebook HQ follows: role, modes, board, workers, sweep and idle pause, gates, handoff, choice questions |
| [templates/state.json](templates/state.json) | The registry: HQ thread id, board URL, watchdog id, mode, thresholds |
| [templates/context_check.py](templates/context_check.py) | Checks a thread's context size and says when to hand off |
| [templates/board.html](templates/board.html) | The board page (four lanes, Needs you first) |
| [templates/hq-skill.md](templates/hq-skill.md) | The `/hq` command |
| [templates/skills/generate-secret/](templates/skills/generate-secret/) | Optional: create secrets without showing them in chat |
| [templates/skills/caveman/](templates/skills/caveman/) | Optional: a terse chat style that saves output tokens |
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
  when idle. It finds stalled workers, checks PRs, and updates the board. After
  2 idle sweeps in a row it pauses itself, and the next message of any kind
  (from you, via `/hq`, or a worker report) wakes it up again.
- **Observe and auto modes.** Observe proposes and waits for a yes. Auto
  launches up to 3 workers from Ready on its own.
- **Gates.** Deploys, migrations, production settings, SSH, deletes and
  spending always wait for you, in every mode.
- **Tap-friendly choices.** Decisions come as numbered questions with lettered
  options. One option per question is marked "(recommended)", placed first,
  with a reason. Letters never repeat, even across messages (1: A, B;
  2: C, D), so you can answer "1A, 2D".
- **`/hq` from anywhere.** `/hq <instruction>` forwards to HQ. `/hq` alone
  shows what needs you.
- **Context handoff.** Every thread checks its context size every 10 messages
  and hands off to a fresh thread above 300k tokens. See below.

## Context limits

Long agent threads get slow, cost more, and start forgetting early details.
So every thread HQ manages (HQ and its workers) watches its own size and hands
off before that happens.

**Defaults**

| Setting | Default | What it means |
|---|---|---|
| `contextCheckEveryMessages` | `10` | How often a thread checks its size, counted in user messages |
| `contextHandoffTokens` | `300000` | Above this many tokens, the thread hands off to a fresh one |

**How it works.** At the end of every turn, a thread runs
`templates/context_check.py` (installed as `~/hq/context_check.py`). When a
check is due and the thread is over the limit, it writes a self-contained
brief (goal, decisions, gates, current state, open questions), launches a
fresh thread with it, and retires itself. HQ does the same for itself and
records the new HQ thread in `~/hq/state.json`, so workers always report to
the right place.

**Changing it.** Ask HQ; see [Commands](#commands) for what to type. Lower the
limit if threads feel slow before they hand off. Raise it if handoffs happen
too often.

## Optional: the generate-secret skill

[templates/skills/generate-secret/](templates/skills/generate-secret/) is an
optional extra skill. Workers often need a secret that *you* create, such as a
webhook signing secret, a cron secret or an internal API token. This skill
writes a random value into a private file (folder mode 700, file mode 600,
never overwritten) and prints only the path, the length and a SHA-256 hash. The
value itself never appears in chat, where transcripts are stored. You copy it
into your password manager, and the skill deletes the file afterwards
(`--remove`).

It is **not** for keys a provider issues to you (payment, email, cloud or model
API keys). Those go through your agent host's secure secret input, for example
`request_secret` in T3 Code, never pasted into chat.

To install it, copy the folder to `~/.claude/skills/generate-secret/`.

## Optional: caveman chat style

[templates/skills/caveman/](templates/skills/caveman/) is an optional,
token-saving preference, not part of the core HQ. It makes agents reply in a
terse style (no filler, fragments OK) while code, errors and technical terms
stay exact, which cuts output tokens a lot on long working days. It switches
back to normal wording for security warnings and irreversible actions.

To enable it:

1. Copy the folder to `~/.claude/skills/caveman/`.
2. Add a line to `~/.claude/CLAUDE.md`, for example:
   `Reply to the user in caveman style, level full: follow ~/.claude/skills/caveman/SKILL.md. Code, commits, PRs and docs stay normal.`
3. Optional: ask HQ to add the matching line to worker briefs (see
   `templates/HQ.md` section 4), so running workers get it in their next
   follow-up.

Turn it off by saying "stop caveman" or "normal mode", or remove the line.

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
