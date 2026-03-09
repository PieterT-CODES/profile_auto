#!/usr/bin/env python3
"""
Claude Code hook - spustí sa automaticky po každej konverzácii.
Číta transcript a ukladá čistý záznam do denného logu.
"""

import json
import sys
import os
from datetime import datetime

LOG_DIR = os.path.expanduser("~/profile_auto/logs")

def extract_messages(transcript_path):
    """
    Prečíta transcript súbor a vytiahne z neho správy.
    Transcript je .jsonl = každý riadok je jeden JSON objekt (jedna udalosť).
    """
    user_messages = []
    assistant_summary = ""

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Správy od používateľa
                if event.get("type") == "user":
                    content = event.get("message", {}).get("content", "")
                    if isinstance(content, list):
                        # Obsah môže byť pole objektov alebo jednoduchý text
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "").strip()
                                if text and len(text) > 3:  # ignoruj krátke "ok", "test"
                                    user_messages.append(text)
                    elif isinstance(content, str) and len(content) > 3:
                        user_messages.append(content.strip())

                # Posledná odpoveď asistenta (berieme len poslednú)
                if event.get("type") == "assistant":
                    content = event.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                assistant_summary = block.get("text", "")[:300]  # prvých 300 znakov

    except FileNotFoundError:
        pass

    return user_messages, assistant_summary


def main():
    # Prečítame dáta od Claude Code
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    transcript_path = data.get("transcript_path", "")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd", "")

    # Extrahujeme správy z transcriptu
    user_messages, assistant_summary = extract_messages(transcript_path)

    # Ak nebol žiadny zmysluplný obsah, nič neukladáme
    if not user_messages:
        return

    # Dnešný log súbor
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.jsonl")

    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "working_directory": cwd,
        "user_messages": user_messages,        # čo si písal
        "assistant_preview": assistant_summary, # čo som odpovedal (skrátene)
        "transcript_path": transcript_path      # odkaz na plný prepis
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
