# Internals — ako systém funguje zvnútra

Detailný popis každého procesu, formátu dát a rozhodnutí v systéme.

---

## 1. Claude Code hook (`scripts/claude_hook.py`)

### Ako sa spustí
Claude Code má built-in systém hookov definovaný v `~/.claude/settings.json`. Typ `Stop` znamená že hook sa spustí vždy keď Claude dokončí odpoveď. Claude Code spustí príkaz a pošle mu cez **stdin** JSON objekt s metadátami session.

### Čo dostane na vstupe
```json
{
  "session_id": "a3c47b29-...",
  "transcript_path": "/home/user/.claude/projects/.../abc123.jsonl",
  "cwd": "/home/user/moj-projekt",
  "hook_event_name": "Stop",
  "last_assistant_message": "posledná odpoveď..."
}
```

### Čo robí
1. Prečíta JSON zo stdin
2. Otvorí `transcript_path` — súbor kde Claude Code ukladá celú konverzáciu
3. Prejde každý riadok transcriptu (každý riadok = jedna udalosť: správa, tool call, atď.)
4. Vyfiltruje správy od používateľa (`type == "user"`) dlhšie ako 30 znakov
5. Uloží čistý záznam do `logs/YYYY-MM-DD.jsonl`

### Formát výstupu
```json
{
  "timestamp": "2026-03-09T22:00:00",
  "session_id": "a3c47b29-...",
  "working_directory": "/home/user/projekt",
  "user_messages": ["čo som písal", "ďalšia správa"],
  "assistant_preview": "prvých 300 znakov odpovede...",
  "transcript_path": "/cesta/k/transcriptu.jsonl"
}
```

### Prečo `.jsonl` formát?
JSONL (JSON Lines) = každý riadok je samostatný JSON objekt. Ideálne pre append-only logy — nikdy nemusíme čítať celý súbor a prepísať ho, len pridáme riadok na koniec.

---

## 2. Git hook (`git-hooks/post-commit`)

### Ako sa spustí
Git spúšťa `post-commit` hook automaticky po každom úspešnom `git commit`. Normálne sa hook hľadá v `.git/hooks/` každého repozitára — to by znamenalo manuálne nastavenie pre každý projekt. Namiesto toho používame **globálny hooks adresár**:

```bash
git config --global core.hooksPath ~/profile_auto/git-hooks
```

Toto povie Gitu: *pre každý repozitár na tomto počítači hľadaj hooks tu.*

### Čo robí
Spustí sa bash script ktorý zavolá Git príkazy na získanie info o práve vykonanom commite:
- `git rev-parse HEAD` → hash commitu
- `git log -1 --pretty=%B` → správa commitu
- `git branch --show-current` → aktuálna vetva
- `git rev-parse --show-toplevel` → koreňový adresár repozitára (z toho `basename` = názov repo)
- `git diff-tree --no-commit-id -r --name-only HEAD` → zmenené súbory

### Formát výstupu
```json
{
  "timestamp": "2026-03-09T22:00:00+00:00",
  "type": "git_commit",
  "repo": "moj-projekt",
  "branch": "main",
  "commit_hash": "fc2ffd0",
  "message": "feat: pridanie novej funkcie",
  "changed_files": "src/main.py,tests/test_main.py"
}
```

---

## 3. Terminal collector (`scripts/terminal_collector.py`)

### Prečo nie hook ale polling?
Terminal príkazy sa nedajú jednoducho zachytiť cez hook v reálnom čase (bash hook `PROMPT_COMMAND` je nestabilný a interferuje s terminálom). Jednoduchšie a spoľahlivejšie je **raz denne prečítať** `~/.bash_history`.

### State management
Script si pamätá koľko riadkov histórie spracoval — uložené v `logs/.terminal_state`. Pri každom spustení:
1. Načíta celú históriu
2. Porovná s uloženým počtom
3. Spracuje len **nové riadky**
4. Uloží nový počet

Toto zabraňuje duplicitám ak script beží opakovane.

### Filter logiky
```
is_interesting(cmd):
  1. Ignoruj prázdne a komentáre (#)
  2. Ignoruj príkazy kratšie ako 4 znaky
  3. Ignoruj "nudné" príkazy: ls, cd, pwd, clear, exit...
  4. Zachovaj príkazy začínajúce zaujímavým nástrojom: python, git, docker, ollama...
  5. Zachovaj príkazy s aspoň 2 slovami (napr. "flask run")
```

681 zaujímavých z 2000 nových = ~34% filter rate pri prvom spustení.

---

## 4. WakaTime collector (`scripts/wakatime_collector.py`)

### API autentifikácia
WakaTime používa HTTP Basic Auth kde meno je prázdne a heslo je API kľúč. Kľúč sa zakóduje do **Base64** a pošle v hlavičke:
```
Authorization: Basic <base64(api_key)>
```

### Endpoint
```
GET https://wakatime.com/api/v1/users/current/summaries?start=YYYY-MM-DD&end=YYYY-MM-DD
```
Vracia denný súhrn: celkový čas, breakdown podľa jazykov, projektov, editorov.

### Prečo zbierame včerajšie dáta?
WakaTime sync nie je okamžitý — dáta za dnešok môžu byť ešte neúplné. Preto collector vždy sťahuje **včerajší deň** (dáta sú vtedy kompletné).

---

## 5. Agregátor (`scripts/aggregator.py`)

### Čo robí
Číta všetky 4 typy log súborov za jeden deň a kombinuje ich do jedného štruktúrovaného JSON súhrnu v `daily_summaries/`.

### De-duplikácia Claude tém
Claude hook sa spúšťa po **každej odpovedi** — v jednej konverzácii ich môže byť 20+. Ale každá session má rovnaké `session_id` a transcript obsahuje všetky správy. Agregátor spracuje každý záznam ale témy vyfiltruje na max 20 unikátnych.

### Výstup
```json
{
  "date": "2026-03-09",
  "sources": {
    "claude": {
      "session_count": 8,
      "topics": ["čo som riešil...", "..."]
    },
    "git": {
      "commit_count": 3,
      "commits": [{"repo": "...", "message": "...", "files": "..."}]
    },
    "terminal": {
      "total_commands": 681,
      "top_tools": {"python": 132, "code": 102},
      "sample_commands": ["python main.py", "..."]
    },
    "wakatime": {
      "available": true,
      "total_time": "5 hrs 23 mins",
      "languages": [{"name": "Python", "seconds": 12000}],
      "projects": [{"name": "moj-projekt", "seconds": 8000}]
    }
  }
}
```

---

## 6. LLM sumarizátor (`scripts/llm_summarizer.py`)

### Prečo Ollama a nie Claude/OpenAI API?
Ollama beží **lokálne** — nulové náklady, žiadne odosielanie osobných dát na externé servery, funguje bez internetu. Model `qwen2.5:7b` (4.7GB) je dostatočne silný na sumarizáciu.

### Komunikácia s Ollama
Ollama beží ako lokálny HTTP server na porte 11434. Pošleme POST request:
```json
{
  "model": "qwen2.5:7b",
  "prompt": "...",
  "stream": false
}
```
`stream: false` znamená že dostaneme celú odpoveď naraz (nie po tokenoch).

### Prompt engineering
Prompt je štruktúrovaný tak aby LLM:
1. Dostal všetky 4 zdroje dát v čitateľnej forme
2. Vedel čo má ignorovať (technické detaily) a čo zachytiť (témy, nástroje, výsledky)
3. Písal v slovenčine, tretia osoba, bez markdown formátovania

### Aktualizácia profile.md
Nový záznam sa vkladá **na začiatok** sekcie `## Denné záznamy` — najnovšie záznamy sú vždy hore. Funguje to ako string replace: nájde marker `## Denné záznamy\n\n` a vloží nový blok hneď za neho.

---

## Dátový tok — celkový pohľad

```
[REÁLNY ČAS]
  Každá Claude odpoveď → claude_hook.py → logs/YYYY-MM-DD.jsonl
  Každý git commit    → post-commit     → logs/git-YYYY-MM-DD.jsonl

[RAZ DENNE — cron 23:55-23:58]
  terminal_collector.py → logs/terminal-YYYY-MM-DD.jsonl
  wakatime_collector.py → logs/wakatime-YYYY-MM-DD.jsonl
  aggregator.py         → daily_summaries/YYYY-MM-DD.json
  llm_summarizer.py     → profile.md (append)
```

---

## Súkromnosť

- Logy a súhrny sú v `.gitignore` — neidú do gitu
- `profile.md` ide do gitu — obsahuje len sumarizácie, nie surové dáta
- WakaTime API kľúč je hardcoded v skripte — nepoužívaj tento repo ako verejný kým ho nevytiahneš do env premennej
- Ollama beží lokálne — žiadne dáta neodchádzajú na externé servery
