# HQ setup prompt

Copy everything below the line and paste it into your agent (a Claude thread in
T3 Code). It sets up HQ on that machine: a router thread, a board, a watchdog
and a `/hq` command. Using a different agent tool? Read
[docs/adapting.md](docs/adapting.md) first.

---

Set up "HQ" on this machine from the repo https://github.com/lniass/hq-for-agents.
HQ is one router thread that coordinates all my work threads here, a board that
shows what needs me, a watchdog that checks in on a schedule, and a `/hq`
command I can use from any thread.

Do these steps in order. Ask me before anything in the "Gates" section of HQ.md
(deploys, migrations, SSH, deleting things, spending money). If `~/hq/HQ.md`
already exists, stop and ask me whether to update it instead.

## 1. Get the files
Clone the repo to a temporary folder, or download these raw files:
- https://raw.githubusercontent.com/lniass/hq-for-agents/main/templates/HQ.md
- https://raw.githubusercontent.com/lniass/hq-for-agents/main/templates/state.json
- https://raw.githubusercontent.com/lniass/hq-for-agents/main/templates/context_check.py
- https://raw.githubusercontent.com/lniass/hq-for-agents/main/templates/board.html
- https://raw.githubusercontent.com/lniass/hq-for-agents/main/templates/hq-skill.md

Read each one fully before installing it. Then:
- Create `~/hq/` (in the home folder of the user T3 runs as) and copy
  `HQ.md`, `state.json`, `context_check.py` and `board.html` into it.
  Set `createdAt` in state.json to today's date.
- Copy `hq-skill.md` to `~/.claude/skills/hq/SKILL.md`.
- If Claude Code's home isn't `~/.claude`, set `CLAUDE_PROJECTS` for the
  context check (see the top of `context_check.py`).

## 2. Test the context check
Run `python3 -I ~/hq/context_check.py ctx-hq-setup-test-0001` with the nonce
typed literally (no `$(...)`). It should print a session and a context size,
not an error. Then delete `~/hq/context-checks/` so the counts start clean.

## 3. Find this machine's work
- List T3 projects (`t3_project_list`) and threads in all projects
  (`t3_thread_list`, allProjects).
- Look at the repos under the workspace root: open PRs (`gh pr list`),
  uncommitted changes (`git status`), and worktrees.
- Read my memory index (`MEMORY.md` in this machine's Claude memory folder)
  and any AGENTS.md or CLAUDE.md files.
- Make a short list of work items. For each: a kebab-case id, title, lane
  (`needs_you`, `in_progress`, `ready` or `done`), 1 to 3 plain sentences of
  detail, the thread that owns it, and any PR links with a one-sentence label.

## 4. Publish the board
Publish `~/hq/board.html` as a private Artifact with the shared database
(`db` capability). Load the `artifact-capabilities` skill first. Put its URL in
`boardUrl` in state.json. Then write the items from step 3, plus a `meta/hq`
doc (`lastSweep`, `mode: "observe"`, `note`), with one `ArtifactData` batch.

## 5. Launch the HQ thread
Use `t3_thread_launch` with the title `*HQ: <short summary of what it routes>`,
`runtimeMode: "auto"` and the main project. Send this as the first message:

> You are HQ, the router that coordinates all of this user's work threads.
> Read ~/hq/HQ.md now and follow it for the life of this thread. The registry
> is ~/hq/state.json and the board is the artifact named there. You start in
> observe mode.
> Setup tasks for this first turn:
> 1. Read ~/hq/state.json. Add your own thread id and link if they are missing
>    (`t3_thread_list` shows `currentThreadId`).
> 2. Create the watchdog: call `mcp__t3-code__schedule_task` (load it with
>    ToolSearch first) with title "HQ watchdog", schedule
>    `{type: "interval", everyMs: 14400000}`, `bindToCurrentThread: true`, and
>    prompt "HQ sweep: follow section 5 of ~/hq/HQ.md." Record the returned
>    scheduledTaskId as `watchdogTaskId` in state.json.
> 3. Run one sweep now, following section 5. Threads that already own open
>    work count as existing workers for it. Don't start new workers.
> 4. Reply in under 100 words: what's waiting on me, and which Ready item a
>    worker should take first.

Wait for HQ's first turn to finish (`t3_thread_wait`). Then check that
state.json has `hqThreadId`, `boardUrl` and `watchdogTaskId`.

## 6. Save it to memory
Write a memory file `hq-router-setup.md` (type `reference`): where the rules,
registry, board and `/hq` command live, and that new work goes through HQ or
onto the board instead of a parallel tracker. Add a one-line pointer in
`MEMORY.md`.

## Troubleshooting
- **Running as root:** Claude threads in Full access mode fail at startup with
  "--dangerously-skip-permissions cannot be used with root/sudo privileges".
  Launch workers with `runtimeMode: "auto"`. To make new threads default to
  Auto, set `"defaultRuntimeMode": "auto"` in `~/.t3/userdata/settings.json`
  and restart T3. Ask me before restarting.
- **Sandbox errors:** if read-only commands like `gh pr view` fail inside the
  shell sandbox, run them outside it. Say so once and carry on.

## When done, reply with
The HQ thread link, the board link, the watchdog's next run time, the
"Needs you" list, and anything you couldn't set up.
