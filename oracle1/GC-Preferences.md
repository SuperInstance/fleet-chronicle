# GC-Preferences — oracle1

## Event Type Policy
| Tag / Pattern | Action | Threshold |
|---|---|---|
| breakthrough, milestone | keep forever | — |
| heartbeat | summarize | after 3 days |
| blocker | keep forever | — |

## Hard Limit
Keep entries for **7 days** minimum.
After 7 days: summarize then delete originals.

## Display Volume
Last **100** entries visible by default.

## Summarization Style
Keep first + last entry. One sentence for middle.

## Special Rules
- NEVER delete entries tagged milestone or breakthrough
