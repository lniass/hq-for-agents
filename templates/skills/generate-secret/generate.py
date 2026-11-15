#!/usr/bin/env python3
"""Generate a random secret into a private file without ever printing it.

Run with:  python3 -I generate.py <name> --purpose "<one line>"
             [--bytes 32] [--format urlsafe|hex] [--dir ~/.config/secrets]
Cleanup:   python3 -I generate.py <name> --remove [--dir ...]

File layout: <dir>/<name> holds the value followed by exactly one "\n".
The printed SHA-256 is over the value WITHOUT that trailing newline.
"""
import argparse
import datetime
import hashlib
import os
import re
import secrets
import stat
import sys

DEFAULT_DIR = "~/.config/secrets"
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
MIN_BYTES = 16
MAX_BYTES = 1024


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def prepare_dir(path: str) -> str:
    path = os.path.abspath(os.path.expanduser(path))
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        os.makedirs(path, mode=0o700)  # umask 077 keeps any parents private too
        os.chmod(path, 0o700)
        return path
    if stat.S_ISLNK(st.st_mode):
        die(f"{path} is a symlink; refusing to use it")
    if not stat.S_ISDIR(st.st_mode):
        die(f"{path} exists and is not a directory")
    if st.st_uid != os.geteuid():
        die(f"{path} is owned by uid {st.st_uid}, not you; refusing to use it")
    if stat.S_IMODE(st.st_mode) != 0o700:
        os.chmod(path, 0o700)
    return path


def readme_path(d: str) -> str:
    return os.path.join(d, "README")


def open_private(path: str, flags: int) -> int:
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    os.fchmod(fd, 0o600)
    return fd


def generate(args) -> None:
    if "\n" in args.purpose or "\r" in args.purpose or not args.purpose.strip():
        die("--purpose must be one non-empty line")
    if not (MIN_BYTES <= args.bytes <= MAX_BYTES):
        die(f"--bytes must be between {MIN_BYTES} and {MAX_BYTES}")

    d = prepare_dir(args.dir)
    path = os.path.join(d, args.name)

    value = secrets.token_hex(args.bytes) if args.format == "hex" else secrets.token_urlsafe(args.bytes)
    digest = hashlib.sha256(value.encode("ascii")).hexdigest()
    length = len(value)

    try:
        fd = open_private(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        die(f"{path} already exists; refusing to overwrite (pick another name or remove it first)")
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(value + "\n")
    del value

    today = datetime.date.today().isoformat()
    line = (f"{args.name}: {args.purpose.strip()} (generated {today}). Copy to the password "
            "manager, set it where it belongs, then delete this file.\n")
    rfd = open_private(readme_path(d), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    with os.fdopen(rfd, "a", encoding="utf-8") as f:
        f.write(line)

    print(f"path:   {path}")
    print(f"length: {length} chars ({args.bytes} random bytes, {args.format})")
    print(f"sha256: {digest}  (over the value, without the trailing newline)")
    print(f"read it: cat {path}")


def remove(args) -> None:
    d = prepare_dir(args.dir)
    path = os.path.join(d, args.name)
    removed = []
    try:
        os.unlink(path)
        removed.append(path)
    except FileNotFoundError:
        pass
    rp = readme_path(d)
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            lines = f.readlines()
        keep = [l for l in lines if not l.startswith(args.name + ": ")]
        if len(keep) != len(lines):
            removed.append(f"README line for {args.name}")
            if keep:
                tmp = rp + ".tmp"
                fd = open_private(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.writelines(keep)
                os.replace(tmp, rp)
            else:
                os.unlink(rp)
    print("removed: " + (", ".join(removed) if removed else "nothing (not found)"))


def main() -> None:
    os.umask(0o077)
    p = argparse.ArgumentParser(description="Generate a secret into a private file; never prints the value.")
    p.add_argument("name", help="snake_case name, e.g. cron_secret")
    p.add_argument("--purpose", help="one line: what the secret is for")
    p.add_argument("--bytes", type=int, default=32, help="random bytes (default 32, min 16)")
    p.add_argument("--format", choices=["urlsafe", "hex"], default="urlsafe")
    p.add_argument("--dir", default=DEFAULT_DIR, help=f"folder (default {DEFAULT_DIR})")
    p.add_argument("--remove", action="store_true", help="delete the secret file and its README line")
    args = p.parse_args()

    if "/" in args.name or "\\" in args.name or not NAME_RE.fullmatch(args.name):
        die("name must be snake_case (a-z, 0-9, single underscores, starting with a letter), no path separators")
    if len(args.name) > 64:
        die("name too long (max 64)")

    if args.remove:
        remove(args)
    else:
        if not args.purpose:
            die("--purpose is required")
        generate(args)


if __name__ == "__main__":
    main()
