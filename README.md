# profile_auto

## What this tool does
Automatically tracks your programming activity across multiple sources (Claude Code, Git, terminal, WakaTime) and builds a continuously updated personal profile. Every evening a local LLM processes the raw logs and writes a human-readable summary into `profile.md`.

## Main capabilities
- Hooks into Claude Code to log every conversation topic and problem solved
- Records Git commits to track completed work and active projects
- Collects terminal commands to identify tools and workflows you use
- Fetches WakaTime data for accurate coding time per language and project
- Combines all sources into a single daily summary via a local Ollama model
- Outputs a plain `profile.md` file that grows over time

## Typical use cases
- Feeding real developer context into an AI Twitter bot that replies in your voice
- Building a living record of your skills and tools without manual journaling
- Reviewing what you actually worked on over the past week or month
- Providing grounded context to any LLM-powered tool that needs to know who you are

## Installation

**Requirements**
- Python 3.10+
- [Ollama](https://ollama.com) with model `qwen2.5:7b` or `llama3`
- [WakaTime](https://wakatime.com) account + VS Code extension (optional)

**Clone the repository**
```bash
git clone https://github.com/PieterT-CODES/profile_auto.git
cd profile_auto
```

**Install Python dependencies**
```bash
pip install -r requirements.txt
```

**Set up Claude Code hook** — add to `~/.claude/settings.json`:
```json
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

**Set up global Git hook**
```bash
git config --global core.hooksPath ~/profile_auto/git-hooks
chmod +x ~/profile_auto/git-hooks/post-commit
```

**Add WakaTime API key** — insert your key into `scripts/wakatime_collector.py` at line 18.

**Schedule daily automation**
```bash
crontab -e
# Add these lines:
55 23 * * * python3 ~/profile_auto/scripts/terminal_collector.py
56 23 * * * python3 ~/profile_auto/scripts/wakatime_collector.py
57 23 * * * python3 ~/profile_auto/scripts/aggregator.py
58 23 * * * python3 ~/profile_auto/scripts/llm_summarizer.py
```

## Quick start
Run the full pipeline manually after your first day of activity:
```bash
python3 ~/profile_auto/scripts/aggregator.py
python3 ~/profile_auto/scripts/llm_summarizer.py
```
Open `profile.md` to see the result.

## Configuration

| File | What to configure |
|---|---|
| `scripts/wakatime_collector.py` line 18 | Your WakaTime API key |
| `scripts/llm_summarizer.py` | Ollama model name (`qwen2.5:7b` default) |
| `~/.claude/settings.json` | Path to `claude_hook.py` if not in home directory |
| `crontab` | Timing of daily collection (default: 23:55–23:58) |

Logs and summaries are written to `logs/` and `daily_summaries/` — both are gitignored by default.

## Output
- **`profile.md`** — the main output file. Contains dated entries written in plain prose by the LLM, describing what you worked on, what tools you used, and what problems you solved.
- **`logs/`** — raw daily JSON logs from each collector. Useful for debugging or reprocessing.
- **`daily_summaries/`** — intermediate aggregated files before LLM processing.

Each `profile.md` entry is timestamped and appended, so the file accumulates over time.

## Limitations
- Requires Ollama running locally — no cloud LLM support out of the box
- Terminal collection only captures commands run after the hook is active; no history import
- WakaTime data is only available if the VS Code extension is installed and syncing
- Profile quality depends on the volume of daily activity — low-activity days produce thin entries
- Git hook applies globally; projects using a different `core.hooksPath` will not be tracked

## Troubleshooting

**`profile.md` is not updating**
Check that cron jobs are running: `grep profile_auto /var/log/syslog` or `crontab -l`.

**Ollama model not found**
Run `ollama pull qwen2.5:7b` to download the model before running the summarizer.

**Claude hook not firing**
Verify the path in `~/.claude/settings.json` is absolute and the script is executable: `chmod +x ~/profile_auto/scripts/claude_hook.py`.

**WakaTime returns no data**
Confirm your API key is correct and that the WakaTime extension has synced at least once today.

**Git hook not running**
Check that `core.hooksPath` is set globally: `git config --global core.hooksPath` should return `~/profile_auto/git-hooks`.

## License
MIT — free to use, modify, and distribute.

## Author
Built by [Peter Tomašovič](https://github.com/PieterT-CODES). Contributions to data collection and AI automation are welcome.
