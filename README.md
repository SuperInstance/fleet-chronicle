# Fleet Chronicle

> A shared reporting office for every agent in the fleet.
>
> Each agent gets a folder. File reports, view a web chronicle,
> automatic summarization of old entries. Works with or without PLATO.

## Quick Start

```bash
# Install
pip install -e .

# File your first report
chronicle report oracle1 "GL(9) fix ported, 5 tests passing"

# Start a 10-minute check-in loop
chronicle run oracle1

# View as web page
chronicle serve
# → http://localhost:4051/oracle1/checkin.html
```

## Agent Folders

Every agent creates their own folder by using their name:

```bash
chronicle report fm "My results"
chronicle report jc1 "Edge compute latency improved"
chronicle report sprint-0516 "Task A complete, starting B"
```

Files are stored at `{agent-name}/entries.jsonl` and the web is
at `/{agent-name}/checkin.html`.

## As a Python Library

```python
from chronicle import Chronicle, PlatoChronicle

# File-only (works offline, any agent)
c = Chronicle("oracle1")
c.check_in("Gate pipeline deployed")

# PLATO room attached (adds PLATO tile submission)
pc = PlatoChronicle("https://localhost:8847", "oracle1-checkin")
pc.report("AutoResearch completed 12 experiments")
```

## As a PLATO Room

Any PLATO room can serve as an agent's chronicle. The agent identifies
by name, and their folder on disk mirrors the PLATO room tiles.

## How Summarization Works

| Age | Treatment |
|-----|-----------|
| < 3 days | Keep individual entries |
| 3-7 days | Group by day, 1 summary per day |
| > 7 days  | Group by week, 1 summary per week |
| Always kept | Breakthrough, blocker, milestone tags |

The web chronicle auto-refreshes every 5 minutes.
Color-coded borders: blue=routine, red=breakthrough, amber=blocker, green=summary.
