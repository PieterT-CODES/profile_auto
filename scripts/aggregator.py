#!/usr/bin/env python3
"""
Agregátor - každý večer prečíta všetky logy za dnešok,
skombinuje ich do jedného súhrnu a uloží do daily_summary/.
Tento súhrn potom použije LLM na aktualizáciu profile.md.
"""

import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path

LOG_DIR = Path.home() / "profile_auto" / "logs"
SUMMARY_DIR = Path.home() / "profile_auto" / "daily_summaries"
SUMMARY_DIR.mkdir(exist_ok=True)


def load_jsonl(filepath):
    """Načíta .jsonl súbor - každý riadok je jeden JSON objekt."""
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return records


def aggregate_claude(date_str):
    """Spracuje Claude konverzácie - čo som riešil, aké témy."""
    records = load_jsonl(LOG_DIR / f"{date_str}.jsonl")

    topics = []
    for r in records:
        msgs = r.get("user_messages", [])
        for msg in msgs:
            # Berieme len dlhšie správy - sú to reálne otázky/problémy
            if len(msg) > 30 and not msg.startswith("<ide_"):
                topics.append(msg[:200])  # prvých 200 znakov stačí

    return {
        "session_count": len(records),
        "topics": topics[:20]  # max 20 tém
    }


def aggregate_git(date_str):
    """Spracuje git commity - čo som dokončil."""
    records = load_jsonl(LOG_DIR / f"git-{date_str}.jsonl")

    commits = []
    for r in records:
        commits.append({
            "repo": r.get("repo", ""),
            "message": r.get("message", "").strip(),
            "files": r.get("changed_files", "")
        })

    return {
        "commit_count": len(commits),
        "commits": commits
    }


def aggregate_terminal(date_str):
    """Spracuje terminal príkazy - aké nástroje som používal."""
    records = load_jsonl(LOG_DIR / f"terminal-{date_str}.jsonl")

    all_commands = []
    for r in records:
        all_commands.extend(r.get("commands", []))

    # Zistíme aké nástroje dominovali (prvé slovo každého príkazu)
    tool_counts = {}
    for cmd in all_commands:
        tool = cmd.split()[0] if cmd.split() else ""
        if tool:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # Zoradíme podľa počtu použití
    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_commands": len(all_commands),
        "top_tools": dict(top_tools),
        "sample_commands": all_commands[:30]  # ukážka príkazov
    }


def aggregate_wakatime(date_str):
    """Spracuje WakaTime dáta - čas a jazyky."""
    records = load_jsonl(LOG_DIR / f"wakatime-{date_str}.jsonl")

    if not records:
        return {"available": False}

    r = records[-1]  # posledný záznam (najnovší)
    return {
        "available": True,
        "total_time": r.get("human_readable", "0 secs"),
        "total_seconds": r.get("total_seconds", 0),
        "languages": r.get("languages", []),
        "projects": r.get("projects", [])
    }


def aggregate_day(target_date=None):
    """Hlavná funkcia - skombinuje všetky zdroje za jeden deň."""
    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()

    print(f"Agregácia dát za {date_str}...")

    summary = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "sources": {
            "claude": aggregate_claude(date_str),
            "git": aggregate_git(date_str),
            "terminal": aggregate_terminal(date_str),
            "wakatime": aggregate_wakatime(date_str),
        }
    }

    # Vypíše stručný prehľad
    c = summary["sources"]["claude"]
    g = summary["sources"]["git"]
    t = summary["sources"]["terminal"]
    w = summary["sources"]["wakatime"]

    print(f"  Claude: {c['session_count']} konverzácií, {len(c['topics'])} tém")
    print(f"  Git:    {g['commit_count']} commitov")
    print(f"  Terminal: {t['total_commands']} príkazov, top nástroje: {list(t['top_tools'].keys())[:5]}")
    if w["available"]:
        print(f"  WakaTime: {w['total_time']}, projekty: {[p['name'] for p in w['projects']]}")
    else:
        print(f"  WakaTime: žiadne dáta")

    # Uložíme súhrn
    output_file = SUMMARY_DIR / f"{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nSúhrn uložený: {output_file}")
    return summary


if __name__ == "__main__":
    aggregate_day()
