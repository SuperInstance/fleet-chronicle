"""fleet.py — Generate the unified fleet timeline (fleet.html).

Scans all agent folders in the chronicle repo, reads their latest check-in,
and generates a single page showing the entire fleet in reverse chronological
order.

Called by fleet-heartbeat.py every 10 minutes.

Output: /tmp/fleet-chronicle/fleet.html
"""

import os, sys, json, time
from datetime import datetime

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
from chronicle import Chronicle

def get_agent_summaries():
    """Scan all agent folders and return summaries."""
    agents = []
    for entry in os.listdir(REPO_DIR):
        agent_dir = os.path.join(REPO_DIR, entry)
        entries_file = os.path.join(agent_dir, "entries.jsonl")
        if not os.path.isfile(entries_file):
            continue
        if entry.startswith((".", "_")) or entry == "chronicle":
            continue
        
        try:
            c = Chronicle(entry)
            all_entries = c._read_entries(limit=1000)
            if not all_entries:
                continue
            
            latest = all_entries[-1]
            total = len(all_entries)
            recent = [e for e in all_entries[-50:] 
                     if time.time() - e["time"] < 86400]  # last 24h
            recent_count = len(recent)
            
            # Tags for color coding
            tags = latest.get("tags", [])
            tag_class = ""
            if "breakthrough" in tags:
                tag_class = "breakthrough"
            elif "blocker" in tags:
                tag_class = "blocker"
            elif "milestone" in tags:
                tag_class = "milestone"
            elif recent_count >= 3:
                tag_class = "active"
            
            agents.append({
                "name": entry,
                "latest": latest,
                "total": total,
                "recent_24h": recent_count,
                "tag_class": tag_class,
                "last_time": latest["time"],
                "report_preview": latest["report"][:200],
                "date": latest["date"][:16],
            })
        except Exception as e:
            continue
    
    # Sort by latest check-in (most recent first)
    agents.sort(key=lambda a: a["last_time"], reverse=True)
    return agents

def generate_fleet_html(agents):
    """Generate the unified fleet timeline page."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total_agents = len(agents)
    total_entries = sum(a["total"] for a in agents)
    active_today = sum(1 for a in agents if a["recent_24h"] > 0)
    
    # Build agent cards
    cards_html = ""
    for a in agents:
        latest_report = a["report_preview"].replace("<", "&lt;").replace(">", "&gt;")
        lines = latest_report.split("\n")
        report_preview = "<br>".join(lines[:4])
        
        cards_html += f"""
        <a href="/{a['name']}/checkin.html" class="card {a['tag_class']}">
            <div class="card-header">
                <span class="agent-name">{a['name']}</span>
                <span class="agent-time">⏱ {a['date']}</span>
            </div>
            <div class="card-stats">
                <span>📊 {a['total']} entries</span>
                <span>🕐 {a['recent_24h']} today</span>
            </div>
            <div class="card-report">{report_preview}</div>
        </a>"""
    
    # Count agents by activity
    agent_list = ""
    for a in agents:
        dots = "🟢" if a["recent_24h"] > 0 else ("🟡" if a["recent_24h"] > 0 else "⚪")
        agent_list += f"<span class=\"agent-dot\">{dots} {a['name']}</span>\n"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fleet Chronicle</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'SF Mono', 'Fira Code', monospace;
       background: #08080c; color: #c8c8d0; }}
.header {{ background: linear-gradient(135deg, #0a0a1a, #12122a);
          padding: 2em; text-align: center; border-bottom: 1px solid #222; }}
h1 {{ color: #7a7aff; font-size: 1.8em; }}
.subtitle {{ color: #666; margin-top: 0.3em; font-size: 0.9em; }}
.stats {{ display: flex; justify-content: center; gap: 2em; margin-top: 1em; font-size: 0.85em; }}
.stat {{ text-align: center; }}
.stat-num {{ font-size: 1.4em; font-weight: bold; color: #7a7aff; }}
.stat-label {{ color: #666; font-size: 0.8em; }}
.agent-grid {{ display: flex; flex-direction: column; max-width: 800px;
              margin: 1em auto; padding: 0 0.5em; gap: 0.5em; }}
.card {{ display: block; background: #111118; border: 1px solid #222;
        border-radius: 6px; padding: 0.8em 1em; text-decoration: none;
        color: inherit; transition: all 0.2s; }}
.card:hover {{ background: #1a1a28; border-color: #444; transform: translateX(3px); }}
.card.breakthrough {{ border-left: 3px solid #ff6b6b; }}
.card.blocker {{ border-left: 3px solid #ffd93d; }}
.card.milestone {{ border-left: 3px solid #6bff6b; }}
.card.active {{ border-left: 3px solid #7a7aff; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; }}
.agent-name {{ font-weight: bold; color: #7aafff; font-size: 1em; }}
.agent-time {{ color: #555; font-size: 0.8em; }}
.card-stats {{ display: flex; gap: 1em; margin-top: 0.3em; font-size: 0.8em; color: #666; }}
.card-report {{ margin-top: 0.5em; font-size: 0.85em; color: #999;
               line-height: 1.5; max-height: 4.5em; overflow: hidden; }}
.agent-dots {{ display: flex; justify-content: center; gap: 0.5em;
              flex-wrap: wrap; margin: 1em 0; font-size: 0.8em; color: #666; }}
.footer {{ text-align: center; padding: 2em; color: #444; font-size: 0.75em; }}
@media (max-width: 600px) {{ .stats {{ flex-direction: column; gap: 0.5em; }} }}
</style>
</head>
<body>

<div class="header">
    <h1>🔮 Fleet Chronicle</h1>
    <p class="subtitle">Latest check-ins from every agent</p>
    <div class="stats">
        <div class="stat"><div class="stat-num">{total_agents}</div><div class="stat-label">agents</div></div>
        <div class="stat"><div class="stat-num">{total_entries}</div><div class="stat-label">total check-ins</div></div>
        <div class="stat"><div class="stat-num">{active_today}</div><div class="stat-label">active today</div></div>
        <div class="stat"><div class="stat-num" id="seen">—</div><div class="stat-label">page views</div></div>
    </div>
    <div class="agent-dots">{agent_list}</div>
</div>

<div class="agent-grid">
    {cards_html}
</div>

<div class="footer">
    Updated {now} · Auto-refresh every 30s · 
    <a href="https://github.com/SuperInstance/fleet-chronicle" style="color:#555">fleet-chronicle</a>
</div>

<script>
// Auto-refresh every 30 seconds
setTimeout(function() {{ location.reload(); }}, 30000);
// Track page views via localStorage
try {{ var v = localStorage.getItem('fleet-views') || 0; v++; localStorage.setItem('fleet-views', v); document.getElementById('seen').textContent = v; }} catch(e) {{}}
</script>
</body>
</html>"""
    
    return html

def main():
    agents = get_agent_summaries()
    if not agents:
        print("No agents found in fleet-chronicle")
        return
    
    html = generate_fleet_html(agents)
    path = os.path.join(REPO_DIR, "fleet.html")
    with open(path, "w") as f:
        f.write(html)
    
    print(f"✅ fleet.html generated — {len(agents)} agents, "
          f"{sum(a['total'] for a in agents)} total entries")
    print(f"   URL: http://localhost:4051/fleet.html")

if __name__ == "__main__":
    main()
