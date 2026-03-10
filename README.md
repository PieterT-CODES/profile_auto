# profile_auto

Systém ktorý automaticky sleduje tvoju programátorskú aktivitu a buduje z nej živý osobný profil.

## Na čo to je?

Keď programuješ, riešiš problémy a používaš nástroje — všetko sa ticho zaznamenáva na pozadí. Každý večer sa záznamy skombinujú a lokálny LLM z nich napíše ľudský záznam do `profile.md`. Výsledkom je súbor ktorý **reálne opisuje teba** — čo vieš, čo riešiš, aké nástroje používaš.

Primárne použitie: kontext pre Twitter bota ktorý odpovedá na príspevky tvojím hlasom a so znalosťou tvojich reálnych skúseností.

## Čo systém sleduje

| Zdroj | Čo zachytáva |
|---|---|
| Claude Code | Každú konverzáciu — otázky, riešené problémy, témy |
| Git | Každý commit — čo si dokončil, na čom pracuješ |
| Terminal | Príkazy — aké nástroje používaš, čo spúšťaš |
| WakaTime | Čas kódovania — jazyky, projekty, editory |

## Výstup

`profile.md` — automaticky aktualizovaný súbor s dennými záznamami o tvojej aktivite.

## Štruktúra

```
profile_auto/
├── scripts/
│   ├── claude_hook.py        ← spúšťa sa po každej Claude konverzácii
│   ├── terminal_collector.py ← zbiera zaujímavé terminal príkazy
│   ├── wakatime_collector.py ← sťahuje dáta z WakaTime API
│   ├── aggregator.py         ← kombinuje všetky zdroje
│   └── llm_summarizer.py     ← generuje profil cez Ollama
├── git-hooks/
│   └── post-commit           ← spúšťa sa po každom git commite
├── logs/                     ← surové denné záznamy (gitignored)
├── daily_summaries/          ← agregované denné súhrny (gitignored)
└── profile.md                ← výsledný profil
```

## Nastavenie

### Požiadavky
- Python 3.10+
- [Ollama](https://ollama.com) s modelom `qwen2.5:7b` alebo `llama3`
- [WakaTime](https://wakatime.com) účet a VS Code extension (voliteľné)

### Inštalácia

**1. Claude Code hook**
```bash
# Pridaj do ~/.claude/settings.json:
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/profile_auto/scripts/claude_hook.py"
      }]
    }]
  }
}
```

**2. Globálne Git hooks**
```bash
git config --global core.hooksPath ~/profile_auto/git-hooks
chmod +x ~/profile_auto/git-hooks/post-commit
```

**3. WakaTime API kľúč**
Vlož svoj kľúč do `scripts/wakatime_collector.py` na riadku 18.

**4. Denná automatizácia (cron)**
```bash
crontab -e
# Pridaj:
55 23 * * * python3 ~/profile_auto/scripts/terminal_collector.py
56 23 * * * python3 ~/profile_auto/scripts/wakatime_collector.py
57 23 * * * python3 ~/profile_auto/scripts/aggregator.py
58 23 * * * python3 ~/profile_auto/scripts/llm_summarizer.py
```

### Manuálne spustenie
```bash
python3 ~/profile_auto/scripts/aggregator.py
python3 ~/profile_auto/scripts/llm_summarizer.py
```
<div align="center">
<img src="https://img.shields.io/github/license/PieterT-CODES/tvoj-repo?color=blue&style=flat-square" alt="License">
Copyright © 2026 Peter Tomašovič (PieterT-CODES). Focus: data scraping & AI.
</div>
