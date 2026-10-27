# Config-only examples

Two `review.json` files from later homeworks, kept because they show patterns the first two examples do not:

- `judge-review.json`: a verdict whose options write nothing (`"sets": {}`) because the decision itself is the
  deliverable, a `summary` table of metrics across judge versions with the current one bolded, and a `store_key`
  so the browser backup of one judge version can never leak into another's annotations file. The adapter that fed
  it put `"dot_class": "ring"` on every disagreement, so ↑ and ↓ stepped through exactly the items needing a decision.
- `monitor-flagged.json`: the steps layout turned on explicitly, and a summary of the monitor's before/after
  periods so the reviewer sees the estimate the flags came from.

Their adapters depended on course-specific judge and monitor files, so they are not included; the adapter
patterns they used are in `../cartwheel/adapter.py`.
