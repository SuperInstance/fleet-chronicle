"""gc.py — Garbage collector for fleet-chronicle entries.

Two modes:
1. Per-agent GC:  python3 -m chronicle.cli gc my-agent
2. Fleet-wide GC:  python3 -m chronicle.cli gc --fleet

For heartbeat/cron GC, add to crontab:
    0 3 * * * cd /path/to/fleet-chronicle && python3 -m chronicle.cli gc --fleet >> gc.log 2>&1

For vibe-coded GC, just tell an agent:
    "Run GC on the fleet-chronicle repo using the owner's preferences"

Design principle: agents without GC-Preferences.md are SKIPPED.
No policy = no touch. No guessing.
"""

import os, json, time, re
from pathlib import Path

DEFAULT_PREFS = {
    "keep_forever_tags": ["breakthrough", "milestone"],
    "summarize_days": 7,
    "delete_days": 30,
    "hard_delete_days": 90,
    "max_entries_default_view": 100,
    "summarize_style": "first_last",
    "special_never_delete": [],
    "auto_delete_patterns": [],
}

def parse_prefs(prefs_path):
    """Parse a GC-Preferences.md file into a rules dict."""
    if not os.path.exists(prefs_path):
        return DEFAULT_PREFS.copy()

    text = open(prefs_path).read()
    prefs = DEFAULT_PREFS.copy()

    tag_rules = []
    for line in text.split("\n"):
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4 and parts[1] and parts[2] and parts[1] not in ("Tag / Pattern", "Pattern"):
            tag_rules.append((parts[1].lower(), parts[2].lower(), parts[3].strip()))
    prefs["tag_rules"] = tag_rules

    day_matches = re.findall(r"(\d+)\s+days?", text)
    if day_matches:
        prefs["delete_days"] = int(day_matches[0])

    prefs["hard_delete"] = not ("archive" in text.lower() and "never delete" not in text.lower())

    if "first" in text.lower() and "last" in text.lower():
        prefs["summarize_style"] = "first_last"
    elif "themed" in text.lower() or "one sentence" in text.lower():
        prefs["summarize_style"] = "themed"
    elif "count" in text.lower():
        prefs["summarize_style"] = "count_samples"

    return prefs


def categorize_entries(entries, prefs, now=None):
    """Return (keep_forever, to_summarize, to_delete) lists."""
    if now is None:
        now = time.time()

    keep_forever, to_summarize, to_delete = [], [], []

    for e in entries:
        tags = [t.lower() for t in e.get("tags", [])]
        age_days = (now - e.get("time", now)) / 86400
        report_lower = e.get("report", "").lower()

        action = None
        for pattern, act, _threshold in prefs.get("tag_rules", []):
            if pattern in " ".join(tags) or pattern in report_lower:
                action = act
                break

        if not action:
            if age_days < prefs["summarize_days"]:
                action = "keep"
            elif age_days < prefs["delete_days"]:
                action = "summarize"
            else:
                action = "delete"

        if action in ("keep", "keep forever"):
            keep_forever.append(e)
        elif action == "summarize":
            to_summarize.append(e)
        else:
            to_delete.append(e)

    return keep_forever, to_summarize, to_delete


def summarize_group(entries, style="first_last"):
    """Create one summary text from a group of entries."""
    if not entries:
        return None

    if style == "first_last":
        first, last = entries[0], entries[-1]
        middle = len(entries) - 2
        report = f"[Summary: {len(entries)} entries]\n"
        report += f"Start: {first.get('date','')[:16]} — {first.get('report','')[:100]}\n"
        if middle > 0:
            report += f"  ({middle} entries between)\n"
        report += f"End: {last.get('date','')[:16]} — {last.get('report','')[:100]}"
        return report

    elif style == "themed":
        words = re.findall(r"\b[a-z]{4,}\b",
                           " ".join(e.get("report","") for e in entries).lower())
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        top = ", ".join(sorted(freq, key=freq.get, reverse=True)[:4])
        last = entries[-1]
        return f"[{len(entries)} entries, top words: {top}] Last: {last.get('report','')[:100]}"

    else:  # count_samples
        samples = [e.get("report","")[:80] for e in entries[-3:]]
        return f"[{len(entries)} entries] Recent: {' | '.join(samples)}"


def run_gc(chronicle, prefs_path=None, dry_run=False):
    """Run GC on one chronicle instance.

    Args:
        chronicle: Chronicle instance
        prefs_path: path to GC-Preferences.md (defaults to agent folder)
        dry_run: if True, only report what would happen
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
        return {**result,
                "would_summarize": len(to_summarize),
                "would_delete": len(to_delete)}

    if to_summarize:
        summary_text = summarize_group(to_summarize, prefs.get("summarize_style", "first_last"))
        if summary_text:
            chronicle.check_in(
                f"[GC] Summarized {len(to_summarize)} entries: {summary_text}",
                tags=["gc-summarize"]
            )
            result["summarized"] = len(to_summarize)

    chronicle._write_all_entries(keep_forever)
    result["deleted"] = len(to_delete)
    return result


def run_fleet_gc(repo_dir=None, dry_run=False):
    """Run GC on every agent folder that has a GC-Preferences.md.

    Agents without a policy file are skipped — no touch, no guess.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chronicle import Chronicle
    if repo_dir is None:
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    agents = [d for d in os.listdir(repo_dir)
              if os.path.isdir(os.path.join(repo_dir, d))
              and not d.startswith((".", "_", "chronicle"))
              and os.path.exists(os.path.join(repo_dir, d, "GC-Preferences.md"))]

    if not agents:
        print("No agents with GC-Preferences.md found — nothing to GC")
        return []

    results = []
    for name in sorted(agents):
        prefs_path = os.path.join(repo_dir, name, "GC-Preferences.md")
        try:
            c = Chronicle(name)
            result = run_gc(c, prefs_path, dry_run=dry_run)
            results.append((name, result))

            deleted = result.get("deleted", 0)
            summarized = result.get("summarized", 0)
            kept = result["kept"]
            tag = "DRY RUN" if dry_run else "GC done"
            if deleted or summarized:
                print(f"  {name}: {tag} — {kept} kept, {summarized} summarized, {deleted} deleted")
            else:
                print(f"  {name}: {tag} — {kept} kept, nothing to clean")
        except Exception as e:
            print(f"  ⚠️  {name}: {e}")

    return results


def main():
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from chronicle import Chronicle

    argv = [a for a in sys.argv[1:] if not a.startswith("--") or a in ("--dry-run", "--fleet")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    dry_run = "--dry-run" in flags
    fleet_mode = "--fleet" in flags

    if not argv and not fleet_mode:
        print("Usage: python3 -m chronicle.cli gc <agent-name> [--dry-run]")
        print("       python3 -m chronicle.cli gc --fleet [--dry-run]")
        sys.exit(1)

    if fleet_mode:
        results = run_fleet_gc(dry_run=dry_run)
        print(f"Fleet GC: {len(results)} agents processed")
    else:
        agent_name = argv[0]
        c = Chronicle(agent_name)
        prefs_path = _os.path.join(c.dir, "GC-Preferences.md")
        result = run_gc(c, prefs_path, dry_run=dry_run)
        if dry_run:
            print(f"DRY RUN — would keep {result['kept']}, "
                  f"would summarize {result.get('would_summarize', 0)}, "
                  f"would delete {result.get('would_delete', 0)}")
        else:
            print(f"GC: {result['kept']} kept, "
                  f"{result['summarized']} summarized, {result['deleted']} deleted")


if __name__ == "__main__":
    main()