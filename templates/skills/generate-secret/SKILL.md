---
name: generate-secret
description: Create a random secret that WE generate (signing or HMAC key, a webhook secret we choose, a cron secret, an internal API token) into a private file on this machine, so the value never appears in chat. Use whenever a task needs such a secret. NOT for keys a provider issues (payment, email, cloud or model API keys); those come from the user through the agent host's secure secret input, never pasted in chat.
---

# generate-secret

The value is written to a mode-600 file in a mode-700 folder and is **never printed**,
not by the script and not by you. Chat transcripts are stored, so a secret that appears in
chat, a command line, a commit, a log, or a memory file counts as leaked.

## Script

```
python3 -I ~/.claude/skills/generate-secret/generate.py <name> --purpose "<one line>" \
    [--bytes 32] [--format urlsafe|hex] [--dir ~/.config/<project>-secrets]
```

- Default folder: `~/.config/secrets` (created 700; an existing folder is chmod'ed to 700,
  refused if it is a symlink or owned by another user). Use `~/.config/<project>-secrets`
  when the secret belongs to one project.
- Default value: `secrets.token_urlsafe(32)`, which is 43 chars and 256-bit. `--format hex`
  uses `token_hex`, 64 chars for 32 bytes. Minimum 16 bytes.
- The file is created with `O_CREAT|O_EXCL`, mode 600: it **refuses to overwrite**.
- File content is the value plus exactly one trailing `\n`. **The printed SHA-256 is over
  the value without the newline.** To recompute: `tr -d '\n' < <path> | sha256sum`.
- A line `<name>: <purpose> (generated <date>). Copy to the password manager, set it where
  it belongs, then delete this file.` is appended to `<dir>/README` (mode 600).
- Output is only: path, length, SHA-256, `read it: cat <path>`.
- Cleanup: `python3 -I .../generate.py <name> --remove [--dir ...]` deletes the file and
  its README line (and the README once it is empty).

## Steps

a. **Pick a clear snake_case name** describing use and scope, e.g. `payments_webhook_secret`,
   `app_cron_secret`. The script rejects anything else (and path separators).

b. **Run the script.** Never run it in a way that echoes the file (no `cat`, `head`,
   `less`, `xxd` of the secret file by you, ever).

c. **Tell the user** (in chat, path and hash only):
   - Open a terminal on the machine (SSH in if it is remote) and run `cat <path>`, then
     paste the one line into their password manager.
   - Why it isn't in chat: transcripts are stored, so anything shown there is effectively
     copied to more places than the secret should live.
   - Whether the target service can show it again later (e.g. most env-var UIs can;
     many "create token" screens show it once), and what breaks if it is lost
     (e.g. "webhooks stop verifying until both sides are rotated").

d. **Use the value only from the file**:
   - Feed it via an env-file (`--env-file`, `set -a; . file`) or stdin (`< <path>`), never
     inline in a command, commit, log, memory, or message. Avoid `$(cat path)` on a command
     line that gets logged or shown.
   - Any temp file (e.g. a `.env` you assemble) is created mode 600 (`umask 077`) and
     deleted right after use.
   - Verify by SHA-256: compare the script's digest with the digest of the value the
     service stores (hash it on the server side, print only the hash).
   - **Ask before setting it on a live service** (changing production settings is a gate).

e. **After the user confirms it's saved in the password manager and set where it belongs**,
   ask, then delete the file and its README line (`--remove`). Remember (memory or notes)
   only the secret's **name, where it is set, and the date**, never its value.

## Provider-issued keys

Keys that a provider gives the user (payment, email, cloud, model APIs) are not generated
here. Ask the user to enter them through the agent host's secure secret input, so they
never appear in chat. In T3 Code, for example, that is the `request_secret` tool.
