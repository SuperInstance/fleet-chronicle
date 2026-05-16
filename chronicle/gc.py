"""gc.py — Garbage collector for fleet-chronicle entries.

Reads GC-Preferences.md from the agent's chronicle folder and applies
the owner's retention policy to entries.jsonl.

Usage:
    from chronicle.gc import run_gc
    run_gc(chronicle_instance)

Or:
    python3 -m chronicle.cli gc your-agent-name
"""

import os, json, time, re
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_PREFS = {
    "keep_forever_tags": ["breakthrough", "milestone", "milestone-candidate"],
    "summarize_days": 7,
    "delete_days": 30,
    "hard_delete_days": 90,
    "max_entries_default_view": 100,
    "summarize_style": "first_last",  # first_last | themed | count_samples
    "special_never_delete": [],
    "auto_delete_patterns": [],
}

def parse_prefs(prefs_path):
    """Parse a GC-Preferences.md file into a rules dict."""
    if not os.path.exists(prefs_path):
        return DEFAULT_PREFS.copy()
    
    text = open(prefs_path).read()
    prefs = DEFAULT_PREFS.copy()
    
    # Extract tag rules from table
    tag_rules = []
    for line in text.split("\n"):
        if "|" in line and ("breakthrough" in line.lower() or "milestone" in line.lower() or 
                           "heartbeat" in line.lower() or "delete" in line.lower() or
                           "summarize" in line.lower() or "keep" in line.lower()):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1] and parts[2]:
                pattern = parts[1].lower()
                action = parts[2].lower()
                threshold = parts[3].strip() if len(parts) > 3 else ""
                tag_rules.append((pattern, action, threshold))
    prefs["tag_rules"] = tag_rules
    
    # Extract day thresholds from prose
    day_matches = re.findall(r"(\d+)\s+days?", text)
    if day_matches:
        prefs["delete_days"] = int(day_matches[0])
    
    # Check for archive vs delete
    if "archive" in text.lower() and "never delete" not in text.lower():
        prefs["hard_delete"] = False
    else:
        prefs["hard_delete"] = True
    
    # Check summarize style
    if "first" in text.lower() and "last" in text.lower():
        prefs["summarize_style"] = "first_last"
    elif "themed" in text.lower() or "one sentence" in text.lower():
        prefs["summarize_style"] = "themed"
    elif "count" in text.lower():
        prefs["summarize_style"] = "count_samples"
    
    return prefs

def categorize_entries(entries, prefs, now=None):
    """Categorize entries by age and tags."""
    if now is None:
        now = time.time()
    
    keep_forever = []
    summarize = []
    delete = []
    
    for e in entries:
        tags = [t.lower() for t in e.get("tags", [])]
        age_days = (now - e.get("time", now)) / 86400
        
        # Check tag rules first
        action = None
        for pattern, act, threshold in prefs.get("tag_rules", []):
            if pattern in " ".join(tags) or pattern in e.get("report", "").lower():
                action = act
                break
        
        if not action:
            # Default by age
            if age_days < prefs["summarize_days"]:
                action = "keep"
            elif age_days < prefs["delete_days"]:
                action = "summarize"
            else:
                action = "delete"
        
        if action == "keep forever":
            keep_forever.append(e)
        elif action == "summarize":
            summarize.append(e)
        elif action == "delete":
            delete.append(e)
        else:
            keep_forever.append(e)
    
    return keep_forever, summarize, delete

def summarize_group(entries, style="first_last"):
    """Create a summary from a group of entries."""
    if not entries:
        return None
    
    if style == "first_last":
        first = entries[0]
        last = entries[-1]
        middle_count = len(entries) - 2
        
        report = f"[Summary of {len(entries)} entries]\n"
        report += f"Started: {first.get('date', '')[:16]} — {first.get('report', '')[:100]}\n"
        if middle_count > 0:
            report += f"({middle_count} entries between)\n"
        report += f"Ended: {last.get('date', '')[:16]} — {last.get('report', '')[:100]}"
        return report
    
    elif style == "themed":
        themes = []
        for e in entries[:5]:
            word_count = {}
            words = re.findall(r"\b[a-z]{4,}\b", e.get("report", "").lower())
            for w in words:
                word_count[w] = word_count.get(w, 0) + 1
            if word_count:
                top = max(word_count, key=word_count.get)
                themes.append(top)
        theme_str = ", ".join(set(themes[:5])) if themes else "general"
        last = entries[-1]
        return f"[{len(entries)} entries, themes: {theme_str}] Last: {last.get('report', '')[:100]}"
    
    else:  # count_samples
        samples = [e.get("report", "")[:80] for e in entries[-3:]]
        return f"[{len(entries)} entries] Recent: {' | '.join(samples)}"

def run_gc(chronicle, prefs_path=None, dry_run=False):
    """Run garbage collection on a chronicle.
    
    Args:
        chronicle: Chronicle instance
        prefs_path: path to GC-Preferences.md (defaults to agent folder)
        dry_run: if True, only reports what would happen
    """
    if prefs_path is None:
        prefs_path = os.path.join(chronicle.dir, "GC-Preferences.md")
    
    prefs = parse_prefs(prefs_path)
    entries = chronicle._read_entries(limit=999999)
    
    if not entries:
        return {"kept": 0, "summarized": 0, "deleted": 0, "dry_run": dry_run}
    
    keep_forever, to_summarize, to_delete = categorize_entries(entries, prefs)
    
    result = {"kept": len(keep_forever), "summarized": 0, "deleted": 0}
    
    if dry_run:
        return {**result, "would_summarize": len(to_summarize), "would_delete": len(to_delete)}
    
    # Apply deletes (append summaries first)
    if to_summarize and not prefs.get("hard_delete", True):
        # Summarize and add as new entry
        summary_text = summarize_group(to_summarize, prefs.get("summarize_style", "first_last"))
        if summary_text:
            chronicle.check_in(
                f"[GC] Summarized {len(to_summarize)} old entries: {summary_text}",
                tags=["gc-summarize"]
            )
            result["summarized"] = len(to_summarize)
    
    # Write surviving entries back
    surviving = keep_forever
    chronicle._write_all_entries(surviving)
    
    result["deleted"] = len(to_delete)
    return result

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 -m chronicle.gc <agent-name> [--dry-run]")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chronicle import Chronicle
    
    c = Chronicle(agent_name)
    prefs_path = os.path.join(c.dir, "GC-Preferences.md")
    result = run_gc(c, prefs_path, dry_run=dry_run)
    
    if dry_run:
        print(f"DRY RUN — would keep {result['kept']}, "
              f"would summarize {result.get('would_summarize', 0)}, "
              f"would delete {result.get('would_delete', 0)}")
    else:
        print(f"GC complete: {result['kept']} kept, "
              f"{result['summarized']} summarized, {result['deleted']} deleted")

if __name__ == "__main__":
    main()