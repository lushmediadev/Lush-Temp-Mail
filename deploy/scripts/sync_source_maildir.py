#!/usr/bin/env python3
"""Copy late-arriving Maildir messages from the old VPS during DNS cutover."""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import subprocess
from pathlib import Path


def message_key(name: str) -> str:
    return name.split(":2,", 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-host", required=True)
    parser.add_argument("--source-maildir", required=True)
    parser.add_argument("--target-maildir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    args = parser.parse_args()

    target = args.target_maildir.resolve(strict=True)
    state = args.state_dir.resolve(strict=True)
    identity = args.identity.resolve(strict=True)
    if not target.is_dir() or not (target / "cur").is_dir() or not (target / "new").is_dir():
        raise RuntimeError("Target Maildir is incomplete")
    if not identity.is_file():
        raise RuntimeError("Migration SSH identity is missing")

    lock_path = state / "bridge.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = state / "copied-message-keys.txt"
        if ledger_path.exists():
            seen = set(ledger_path.read_text().splitlines())
        else:
            seen = {
                message_key(path.name)
                for folder in ("cur", "new")
                for path in (target / folder).iterdir()
                if path.is_file()
            }
            ledger_path.write_text("".join(f"{key}\n" for key in sorted(seen)))
            os.chmod(ledger_path, 0o600)

        ssh = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -i {identity}"
        for folder in ("cur", "new"):
            mirror = state / "source-mirror" / folder
            mirror.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "rsync", "-a", "--delete", "-e", ssh,
                    f"root@{args.source_host}:{args.source_maildir.rstrip('/')}/{folder}/",
                    f"{mirror}/",
                ],
                check=True,
            )

        copied = 0
        with ledger_path.open("a") as ledger:
            for folder in ("cur", "new"):
                for source in (state / "source-mirror" / folder).iterdir():
                    if not source.is_file():
                        continue
                    key = message_key(source.name)
                    if key in seen:
                        continue
                    destination = target / "new" / key
                    if destination.exists():
                        continue
                    shutil.copy2(source, destination)
                    os.chown(destination, 5000, 5000)
                    seen.add(key)
                    ledger.write(key + "\n")
                    ledger.flush()
                    os.fsync(ledger.fileno())
                    copied += 1
        print(f"late messages copied: {copied}")


if __name__ == "__main__":
    main()
