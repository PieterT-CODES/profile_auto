#!/usr/bin/env python3
"""
WakaTime collector - sťahuje dennú aktivitu z WakaTime API.
Zachytáva: jazyky, projekty, súbory, čas strávený kódovaním.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
import base64

# ─────────────────────────────────────────────
# SEM VLOŽ SVOJ API KĽÚČ:
# Nájdeš ho na: https://wakatime.com/settings/api-key
# ─────────────────────────────────────────────
WAKATIME_API_KEY = "waka_0acea100-e11c-4434-a547-b6179915903b"

LOG_DIR = os.path.expanduser("~/profile_auto/logs")


def fetch_wakatime(endpoint, date_str):
    """
    Zavolá WakaTime API a vráti JSON dáta.
    WakaTime používa Basic Auth kde kľúč sa zakóduje do base64.
    """
    encoded_key = base64.b64encode(WAKATIME_API_KEY.encode()).decode()
    url = f"https://wakatime.com/api/v1/{endpoint}?start={date_str}&end={date_str}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {encoded_key}")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API chyba {e.code}: skontroluj API kľúč")
        return None
    except urllib.error.URLError as e:
        print(f"Sieťová chyba: {e.reason}")
        return None


def collect(target_date=None):
    if target_date is None:
        target_date = date.today() - timedelta(days=1)  # včera (dáta sú kompletné)

    date_str = target_date.isoformat()

    # Stiahne sumár dňa: celkový čas, jazyky, projekty, editory
    summary = fetch_wakatime("users/current/summaries", date_str)
    if not summary:
        return

    data = summary.get("data", [])
    if not data:
        print(f"Žiadne dáta pre {date_str}")
        return

    day = data[0]  # jeden deň = jeden záznam

    # Vyberieme len čo nás zaujíma — nie všetky technické detaily
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "wakatime",
        "date": date_str,

        # Celkový čas kódovania v sekundách (napr. 7200 = 2 hodiny)
        "total_seconds": day.get("grand_total", {}).get("total_seconds", 0),
        "human_readable": day.get("grand_total", {}).get("text", ""),

        # Jazyky zoradené podľa času (napr. Python 80%, JavaScript 20%)
        "languages": [
            {"name": l["name"], "seconds": l["total_seconds"]}
            for l in day.get("languages", [])[:10]  # top 10
        ],

        # Projekty na ktorých si pracoval
        "projects": [
            {"name": p["name"], "seconds": p["total_seconds"]}
            for p in day.get("projects", [])[:10]
        ],

        # Editory (VS Code, terminal...)
        "editors": [
            {"name": e["name"], "seconds": e["total_seconds"]}
            for e in day.get("editors", [])
        ],
    }

    log_file = os.path.join(LOG_DIR, f"wakatime-{date_str}.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"WakaTime {date_str}: {entry['human_readable']} | "
          f"projekty: {[p['name'] for p in entry['projects']]}")


if __name__ == "__main__":
    collect()
