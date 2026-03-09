#!/usr/bin/env python3
"""
Terminal history collector - číta ~/.bash_history a ukladá zaujímavé príkazy.
Spúšťa sa cez cron raz denne, nie v reálnom čase.
"""

import os
import json
from datetime import datetime, date

LOG_DIR = os.path.expanduser("~/profile_auto/logs")
HISTORY_FILE = os.path.expanduser("~/.bash_history")
# Súbor kde si pamätáme koľko riadkov sme naposledy spracovali
STATE_FILE = os.path.expanduser("~/profile_auto/logs/.terminal_state")

# Príkazy ktoré ignorujeme — sú nezaujímavé pre profil
IGNORE_COMMANDS = {
    "ls", "ll", "la", "l", "cd", "pwd", "clear", "cls", "exit", "logout",
    "history", "cat", "less", "more", "man", "echo", "which", "whoami",
    "date", "cal", "df", "du", "free", "top", "htop", "ps", "kill",
    "mkdir", "rmdir", "rm", "cp", "mv", "touch", "chmod", "chown",
    "grep", "find", "head", "tail", "wc", "sort", "uniq",
    "z", "j",  # jump navigácia
}

# Zaujímavé prefixové slová — ak príkaz začína týmto, uložíme ho
INTERESTING_PREFIXES = [
    "python", "python3", "pip", "pip3", "uv",
    "node", "npm", "npx", "yarn", "bun",
    "git",
    "docker", "docker-compose",
    "ollama", "llm",
    "tmux", "screen",
    "ssh", "curl", "wget",
    "ffmpeg", "convert",
    "cargo", "rustc",
    "go ", "gob",
    "make", "cmake",
    "systemctl", "service",
    "cron", "crontab",
    "code ", "nvim", "vim",
]

def is_interesting(command):
    """Vráti True ak je príkaz hodný uloženia."""
    cmd = command.strip()
    if not cmd or cmd.startswith("#"):
        return False

    # Základný príkaz (prvé slovo pred medzerou)
    base = cmd.split()[0].strip()

    # Ignorujeme nudné príkazy
    if base in IGNORE_COMMANDS:
        return False

    # Ak je príkaz príliš krátky (1-2 znaky), ignorujeme
    if len(cmd) < 4:
        return False

    # Zaujímavé príkazy
    for prefix in INTERESTING_PREFIXES:
        if cmd.startswith(prefix):
            return True

    # Ak má príkaz aspoň 2 slová (napr. "flask run", "uvicorn main:app"), uložíme
    if len(cmd.split()) >= 2:
        return True

    return False


def load_state():
    """Načíta stav — koľko riadkov histórie sme naposledy spracovali."""
    try:
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_state(line_count):
    """Uloží aktuálny počet riadkov histórie."""
    with open(STATE_FILE, "w") as f:
        f.write(str(line_count))


def main():
    # Načítame celú históriu
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        print("História nenájdená")
        return

    total_lines = len(all_lines)
    last_processed = load_state()

    # Spracujeme len nové riadky od posledného spustenia
    new_lines = all_lines[last_processed:]

    interesting = []
    for line in new_lines:
        cmd = line.strip()
        if is_interesting(cmd):
            interesting.append(cmd)

    # Uložíme ak máme čo
    if interesting:
        today = date.today().isoformat()
        log_file = os.path.join(LOG_DIR, f"terminal-{today}.jsonl")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "terminal_history",
            "commands": interesting,
            "total_new_commands": len(new_lines),
            "interesting_count": len(interesting)
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"Uložených {len(interesting)} zaujímavých príkazov z {len(new_lines)} nových.")
    else:
        print("Žiadne nové zaujímavé príkazy.")

    # Zapamätáme si kde sme skončili
    save_state(total_lines)


if __name__ == "__main__":
    main()
