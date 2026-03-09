#!/usr/bin/env python3
"""
LLM sumarizátor - pošle denný súhrn do Ollama (lokálny LLM)
a výsledok zapíše do profile.md.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

SUMMARY_DIR = Path.home() / "profile_auto" / "daily_summaries"
PROFILE_FILE = Path.home() / "profile_auto" / "profile.md"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"


def ask_ollama(prompt):
    """Pošle prompt do Ollama a vráti odpoveď ako text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False  # chceme celú odpoveď naraz, nie po častiach
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode())
            return result.get("response", "").strip()
    except urllib.error.URLError:
        print("Ollama nebeží. Spusti: ollama serve")
        return None


def build_prompt(summary):
    """Vytvorí prompt pre LLM zo súhrnu dňa."""
    date_str = summary["date"]
    c = summary["sources"]["claude"]
    g = summary["sources"]["git"]
    t = summary["sources"]["terminal"]
    w = summary["sources"]["wakatime"]

    # Pripravíme čitateľné bloky
    claude_topics = "\n".join(f"- {topic[:150]}" for topic in c["topics"][:10])
    git_commits = "\n".join(
        f"- [{r['repo']}] {r['message']}" for r in g["commits"]
    ) or "- žiadne commity"
    top_tools = ", ".join(f"{k}({v}x)" for k, v in t["top_tools"].items())
    wakatime_info = (
        f"{w['total_time']}, jazyky: {[l['name'] for l in w['languages'][:3]]}"
        if w.get("available") else "nedostupné"
    )

    prompt = f"""Si asistent ktorý analyzuje dennú aktivitu programátora a píše stručný profil záznam.

DÁTUM: {date_str}

CLAUDE KONVERZÁCIE ({c['session_count']} sessions) - čo riešil:
{claude_topics if claude_topics else "- žiadne záznamy"}

GIT COMMITY:
{git_commits}

TERMINAL - top nástroje: {top_tools}

WAKATIME (čas kódovania): {wakatime_info}

---
Napíš stručný záznam (max 150 slov) v slovenčine o tomto programátorovi pre tento deň.
Zameraj sa na:
1. Čo konkrétne riešil a na čom pracoval
2. Aké technológie a nástroje používal
3. Čo dokončil (git commity)

Formát - iba holý text, žiadne markdown nadpisy, žiadne odrážky. Píš ako keby si opisoval skúseného programátora tretej osobe.
"""
    return prompt


def update_profile(date_str, new_entry):
    """Pridá nový denný záznam do profile.md."""

    # Ak profile.md neexistuje, vytvoríme ho s hlavičkou
    if not PROFILE_FILE.exists():
        header = """# Profil - automaticky generovaný

Tento súbor sa aktualizuje automaticky každý večer na základe dennej aktivity.
Zdroje: Claude Code konverzácie, Git commity, Terminal história, WakaTime.

---

## Denné záznamy

"""
        PROFILE_FILE.write_text(header, encoding="utf-8")

    # Pridáme nový záznam na začiatok denných záznamov (najnovšie hore)
    current = PROFILE_FILE.read_text(encoding="utf-8")

    new_block = f"### {date_str}\n{new_entry}\n\n"

    # Vložíme za hlavičku (za "## Denné záznamy\n\n")
    marker = "## Denné záznamy\n\n"
    if marker in current:
        current = current.replace(marker, marker + new_block)
    else:
        current += new_block

    PROFILE_FILE.write_text(current, encoding="utf-8")


def summarize_day(target_date=None):
    """Hlavná funkcia - spracuje jeden deň."""
    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()
    summary_file = SUMMARY_DIR / f"{date_str}.json"

    if not summary_file.exists():
        print(f"Súhrn pre {date_str} neexistuje. Najprv spusti aggregator.py")
        return

    with open(summary_file, encoding="utf-8") as f:
        summary = json.load(f)

    print(f"Generujem profil záznam pre {date_str}...")
    prompt = build_prompt(summary)
    response = ask_ollama(prompt)

    if not response:
        return

    print(f"\n--- VYGENEROVANÝ ZÁZNAM ---\n{response}\n---")

    update_profile(date_str, response)
    print(f"Profil aktualizovaný: {PROFILE_FILE}")


if __name__ == "__main__":
    summarize_day()
