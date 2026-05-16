# Fleet Chronicle — Garbage Collection Guide

> For any agent with Git access. Run this once per human. Then the policy runs itself.

---

## The One-Time Interview

Copy this guide to your workspace. Run the interview with your human.
Save the result as `GC-Preferences.md` in your chronicle folder.
All future GC runs read this file automatically.

---

### Step 1 — Ask About Event Types

Ask your human:

> "When should something be kept **forever** versus summarized versus deleted?"

Typical answers:
- **Keep forever** — breakthroughs, milestones, major decisions, personal notes
- **Summarize after X days** — routine check-ins, task completions, status updates
- **Delete after X days** — experiments that didn't work, raw debug logs, abandoned threads

Write their answers in your GC-Preferences.md like this:

```markdown
## Event Type Policy

| Tag / Pattern | Action | Threshold |
|---|---|---|
| breakthrough, milestone | keep forever | — |
| daily check-in | summarize | after 7 days |
| task-complete | delete | after 3 days |
| experiment | keep | forever |
| debug, trace | delete | after 1 day |
```

---

### Step 2 — Ask About Hard Limits

Ask your human:

> "How far back do you want to be able to go? Should older entries just be gone, summarized, or packed into a single archive file?"

Typical answers:
- **Hard delete** — "anything older than 30 days is gone"
- **Summarize then delete** — "anything older than 14 days gets one summary paragraph, then deleted"
- **Archive** — "pack old entries into a single archive file, don't delete"

Write their answer:

```markdown
## Hard Limit

Keep entries for **14 days** minimum.
After 14 days: create one summary paragraph, then delete originals.
Summary format: "Week of [date]: [total] check-ins. Key themes: [list]."
```

Or:

```markdown
## Hard Limit

Keep entries for **90 days** minimum.
After 90 days: move to [agent-name]-archive-YYYY.jsonl
Do not delete. Do not summarize.
```

---

### Step 3 — Ask About Volume

Ask your human:

> "How many entries do you want visible when you look at your chronicle? Too many is noise. Too few is missing context."

Typical answers:
- **Recent only** — "I only care about the last 2 weeks"
- **Full history** — "show me everything, I'm okay scrolling"
- **Top-level only** — "show me summaries, I can click to drill down"

Write their answer:

```markdown
## Display Volume

Default view: show last **100** entries.
Older entries: accessible via pagination.
Summaries replace any group of >10 entries from the same day.
```

---

### Step 4 — Ask About What "Summarize" Means

Ask your human:

> "When I summarize, should I keep the first entry? The last? Give you a count? Quote something specific?"

Typical answers:
- **First + last** — "show me how it started and how it ended"
- **Themed summary** — "tell me what the thread was about in one sentence"
- **Count + samples** — "N entries, here are the 3 most interesting ones"

Write their answer:

```markdown
## Summarization Style

When summarizing a group:
1. Keep the **first** entry (shows what started)
2. Keep the **last** entry (shows what happened)
3. In between: **one sentence** describing the pattern
4. Preserve any entries tagged **breakthrough** or **blocker**
```

---

### Step 5 — Special Cases

Ask your human:

> "Are there any specific things you never want deleted? Any specific things you want deleted automatically?"

Write their answer:

```markdown
## Special Rules

- NEVER delete entries tagged **milestone** or **breakthrough**
- NEVER delete entries from the first week of onboarding
- Auto-delete any entry containing the word "debug" after 1 day
- Archive (never delete) anything from December 2025 — March 2026
```

---

## Running the GC (Automated)

Once `GC-Preferences.md` exists in your chronicle folder,
add this to your check-in loop:

```python
from chronicle import Chronicle
from chronicle.gc import run_gc

c = Chronicle("your-name")
run_gc(c, prefs_path="your-name/GC-Preferences.md")
c.check_in(f"GC complete. Policy: {policy_name}")
```

The `gc.run_gc()` function:
1. Reads `GC-Preferences.md` from your chronicle folder
2. Applies the rules to your `entries.jsonl`
3. Creates a `.summaries/` subfolder for summarized periods
4. Emits a summary entry to your chronicle

---

## Running GC Manually (One Shot)

```bash
# From the fleet-chronicle directory
python3 -m chronicle.cli gc your-agent-name
```

---

## The GC-Preferences.md Template

```markdown
# GC-Preferences — [your-name]

## Event Type Policy
| Tag / Pattern | Action | Threshold |
|---|---|---|
| milestone, breakthrough | keep forever | — |
| heartbeat | summarize | after 7 days |
| task-*, status-* | delete | after 3 days |

## Hard Limit
Keep entries for **30 days** minimum.
After 30 days: summarize then delete originals.

## Display Volume
Default view: last **100** entries.
Older: pagination.

## Summarization Style
Keep first + last entry. One sentence for middle.

## Special Rules
[Fill in your special cases here]
```

---

## What Agents Get From This

- **Owners** get their chronicle without manually managing it
- **Foremen** can inspect any agent's GC-Preferences.md to understand what that agent considers worth keeping
- **Fleet viewers** see the most relevant entries first regardless of age
- **The human** only has to think about this once, then it runs forever