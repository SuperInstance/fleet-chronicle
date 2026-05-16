"""Core Chronicle — an agent's personal reporting office.

Usage:
    from chronicle import Chronicle
    c = Chronicle("oracle1")
    c.check_in("Refactored gate pipeline")
    c.generate_html()
"""

import json, time, os
from datetime import datetime
from collections import defaultdict

class Chronicle:
    """An agent's persistent, auto-summarizing check-in log."""

    # All agent chronicles live under this repo
    REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, agent_name):
        self.name = agent_name
        self.dir = os.path.join(self.REPO_DIR, agent_name)
        self.entries_file = os.path.join(self.dir, "entries.jsonl")
        self.html_file = os.path.join(self.dir, "checkin.html")
        self.count = 0
        os.makedirs(self.dir, exist_ok=True)
        self._load_count()
        self._register_agent()

    def _register_agent(self):
        """Register this agent in the fleet index. No heartbeat needed."""
        index_file = os.path.join(self.REPO_DIR, "agents.json")
        try:
            with open(index_file) as f:
                agents = json.load(f)
        except:
            agents = []
        if self.name not in agents:
            agents.append(self.name)
            agents.sort()
            with open(index_file, "w") as f:
                json.dump(agents, f, indent=2)

    def _load_count(self):
        try:
            with open(os.path.join(self.dir, ".count")) as f:
                self.count = int(f.read().strip())
        except:
            self.count = 0

    def _save_count(self):
        with open(os.path.join(self.dir, ".count"), "w") as f:
            f.write(str(self.count))

    def _read_entries(self, limit=500):
        entries = []
        try:
            with open(self.entries_file) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except:
            pass
        return entries[-limit:]

    def _write_all_entries(self, entries):
        """Overwrite entries.jsonl with a list of entries."""
        entries_file = os.path.join(self.dir, "entries.jsonl")
        with open(entries_file, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def check_in(self, report, status="ok", tags=None, metadata=None):
        """File a check-in report. Returns entry ID."""
        self.count += 1
        now = time.time()
        entry = {
            "id": f"ci-{self.count}",
            "checkin": self.count,
            "time": now,
            "date": datetime.utcfromtimestamp(now).strftime("%Y-%m-%d %H:%M"),
            "report": report[:2000],
            "status": status,
            "tags": tags or [],
            "metadata": metadata or {},
        }
        with open(self.entries_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._save_count()
        return entry["id"]

    def summarize(self, max_entries=200):
        """Summarize old entries. Keeps recent, groups old by day/week."""
        entries = self._read_entries(limit=1000)
        if len(entries) <= max_entries:
            return len(entries)

        now = time.time()
        recent = []
        day_groups = defaultdict(list)
        week_groups = defaultdict(list)
        important = []

        for e in entries:
            age_days = (now - e["time"]) / 86400
            tags = " ".join(e.get("tags", []))
            is_imp = any(kw in tags.lower() for kw in
                         ["breakthrough", "blocker", "milestone", "finding"])
            if is_imp:
                important.append(e)
            elif age_days < 3:
                recent.append(e)
            elif age_days < 7:
                day_groups[datetime.utcfromtimestamp(e["time"]).strftime("%Y-%m-%d")].append(e)
            else:
                week_groups[datetime.utcfromtimestamp(e["time"]).strftime("%Y-W%W")].append(e)

        summaries = []
        for day, day_entries in sorted(day_groups.items()):
            if len(day_entries) >= 2:
                reports = [e["report"][:100] for e in day_entries[:5]]
                summaries.append({
                    "id": f"sum-{day}", "type": "summary",
                    "date": day, "original_count": len(day_entries),
                    "report": f"Summary for {day}: {len(day_entries)} check-ins — {'; '.join(reports[:3])}",
                    "time": day_entries[-1]["time"],
                })
            else:
                recent.extend(day_entries)

        for week, week_entries in sorted(week_groups.items()):
            if len(week_entries) >= 2:
                days = len(set(e["date"][:10] for e in week_entries))
                summaries.append({
                    "id": f"sum-{week}", "type": "summary",
                    "date": week, "original_count": len(week_entries),
                    "report": f"Weekly summary {week}: {len(week_entries)} entries across {days} days.",
                    "time": week_entries[-1]["time"],
                })
            else:
                recent.extend(week_entries)

        all_out = sorted(important + recent + summaries, key=lambda e: e.get("time", 0))
        with open(self.entries_file, "w") as f:
            for e in all_out:
                f.write(json.dumps(e) + "\n")
        return len(all_out)

    def generate_html(self, output_path=None):
        """Generate a dark-themed HTML page of this chronicle."""
        entries = self._read_entries(limit=200)
        path = output_path or self.html_file

        healthy = sum(1 for e in entries[-20:] if e.get("status") in ("ok", "alive"))
        tags_map = {"breakthrough": "bt", "blocker": "bl", "summary": "sm"}

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{self.name} chronicle</title>
<style>
body {{ font-family: -apple-system, monospace; max-width: 800px; margin: 2em auto; padding: 1em; background: #0a0a0f; color: #c8c8d0; }}
h1 {{ color: #7a7aff; border-bottom: 1px solid #333; }}
.tile {{ margin: 0.8em 0; padding: 0.4em 1em; border-left: 2px solid #444; background: #12121a; border-radius: 0 4px 4px 0; }}
.tile:hover {{ background: #1a1a2a; }}
.tile .time {{ color: #666; font-size: 0.75em; }}
.tile .a {{ white-space: pre-wrap; font-size: 0.8em; color: #aaa; line-height: 1.4; }}
.bt {{ border-left-color: #ff6b6b; }}
.bl {{ border-left-color: #ffd93d; }}
.sm {{ border-left-color: #6bff6b; opacity: 0.6; }}
.footer {{ margin-top: 3em; color: #444; font-size: 0.75em; text-align: center; }}
</style></head><body>
<h1>📋 {self.name}</h1>
<p style="color:#888;font-size:0.85em">{len(entries)} entries · summarization after 3 days</p>
<div style="display:flex;gap:0.5em;margin:1em 0;font-size:0.8em">
  <span style="background:#1a1a3a;padding:0.2em 0.5em;border-radius:3px">📊 {len(entries)} entries</span>
  <span style="background:#1a1a3a;padding:0.2em 0.5em;border-radius:3px">✅ {healthy} healthy</span>
</div>
<script>setTimeout(function(){{ location.reload(); }}, 300000);</script>"""

        for e in reversed(entries[-100:]):
            cls = " ".join(tags_map.get(t, "") for t in e.get("tags", []))
            html += f'<div class="tile {cls}">'
            html += f'<div class="time">#{e["id"]} · {e["date"]}</div>'
            html += f'<div class="a">{e["report"]}</div></div>'

        html += f'<div class="footer">fleet-chronicle/{self.name} · Auto-summarized after 3 days</div></body></html>'

        with open(path, "w") as f:
            f.write(html)
        return path
