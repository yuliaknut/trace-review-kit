---
name: trace-review
description: Stand up a one-trace-at-a-time review page (GitHub dark dimmed theme) for evaluating an AI agent or chatbot on any project. Use when the user wants to review, annotate, label, open-code, or adjudicate conversation traces, agent runs, tool-call logs, judge disagreements, or monitor flags in a browser, and export the decisions to a file.
---

# Trace review

A reusable review interface for error analysis: one conversation per screen, tool calls nested
under the narration that made them, an answer-key card beside the conversation, a decision panel
you configure, inline notes anchored to selected text, a tracker of coloured dots across the top,
autosave to a JSON file, and an exporter. The page, theme, and server are generic and live in
`assets/`. Two things are written per project, by you, following the steps below: an **adapter**
that maps the project's traces onto the sample contract, and a **review config** naming the
decision fields.

The human decides; you build. Never write the reviewer's annotations, and never invent expected
outcomes: the answer key in the context card must come from the project's own data, rules, or
scenario file, and the adapter must make its source visible. Nothing is inferred from silence: an
item without a decision stays undecided, a dot stays dim until the item has been looked at, and
the export writes `null` where the reviewer never chose.

## Setup

Copy the assets into the project, into a directory the project can commit. The default is `review/`:

```bash
mkdir -p review && cp "${CLAUDE_SKILL_DIR}/assets/"{index.html,theme.css,server.py,export.py} review/
```

Do not modify `index.html` or `server.py` for a project; put project logic in the adapter and the
config so the kit stays upgradable. If the theme needs a tweak, override tokens in a second
stylesheet rather than editing `theme.css`.

## Step 1: find the traces and their answer keys

Ask, or find in the repo, three things before writing any code:

1. **Where the traces are.** A trace store (Langfuse, LangSmith, an OpenTelemetry backend), a
   JSONL log, a results file written by a runner, or a database. Confirm you can read one full
   conversation including tool calls and tool results, not just the final reply. For a multi-turn
   conversation stored as one trace per turn, confirm you can join the turns by session.
2. **What identifies an item.** A scenario id, a conversation id, a trace id. The exporter keys
   on it, so it must be stable across reloads. Prefer scenario ids to trace ids: a rerun changes
   the trace id but not the scenario.
3. **What the reviewer compares against.** A scenario file with expected outcomes, a
   specification with numbered requirements, a rubric, a judge's verdict, or nothing. This fills
   the context card(s). If there is nothing, the card shows metadata only.

Read [examples/cartwheel/adapter.py](examples/cartwheel/adapter.py) for a trace-store project
with an answer key, [examples/chat-jsonl/adapter.py](examples/chat-jsonl/adapter.py) for a plain
log with none, and [examples/configs/README.md](examples/configs/README.md) for a judge-review
and a monitor-flag setup.

## Step 2: write the adapter

Write `review/adapter.py` that reads the project's source and writes `review/samples.json`, a JSON
list in the sample contract below. Keep it a plain script with a `convert(record) -> dict`
function so it can be rerun after every new run of the agent.

### The sample contract

```json
{
  "id": "support-0042",
  "group": "challenge",
  "batch": "b2-dimension",
  "chips": ["shopper", {"text": "dq-order-missing-delivery-date", "color": "red"}],
  "meta": ["user 392", "prompt 1b6ab97b", "gpt-5.5"],
  "link": "https://langfuse.local/project/p/traces/abc123",
  "link_label": "open in Langfuse ↗",
  "dot_class": "ring",
  "dot_title": "judge and human disagree",
  "messages": [
    {"role": "user", "text": "Can I still send back the pencil set?"},
    {"role": "assistant", "text": "I'll check the order."},
    {"role": "tool_call", "name": "get_order", "arguments": {"order_id": 8002}},
    {"role": "tool_result", "name": "get_order", "content": {"ok": true, "status": "delivered", "delivered_at": null}},
    {"role": "tool_call", "name": "search_help_center", "arguments": {"query": "return window"}},
    {"role": "tool_result", "name": "search_help_center", "content": {"ok": true, "results": []},
     "items": [{"title": "cw-returns", "meta": "score 0.81", "body": "Items can be returned within 30 days of delivery…"}]},
    {"role": "assistant", "text": "The order shows delivered but has no delivery date, so..."},
    {"role": "observation", "label": "guardrail", "text": "output filter passed"}
  ],
  "turns": [{"turn": 2, "label": "d37ad530…", "link": "https://langfuse.local/…", "link_label": "Langfuse ↗"}],
  "context": [
    {"title": "Expected outcome (scenario file)", "headline": "do_not_compute_return_deadline",
     "body": "The order has a delivered status but no delivery date.",
     "fields": {"source": "data_quality_table · dq-order-missing-delivery-date", "intent": "return_deadline"}},
    {"title": "Judge", "headline": "Fail · you said Pass", "body": "Critique text…", "collapsible": true}
  ]
}
```

Rules the page relies on:

- `id` is required and unique. Everything else is optional.
- `messages` roles are `user`, `assistant`, `tool_call`, `tool_result`, `observation`, `error`.
  A `tool_result` directly after a `tool_call` is rendered inside that call's card; keep them
  adjacent and in order. Assistant text renders light markdown (bold, code, bullets, pipe tables,
  headings). `arguments` and `content` may be objects or JSON strings; both are pretty-printed.
- **Layout.** By default the page draws each turn as the user message, then *steps* (an
  assistant narration plus the tool calls it made) indented on a rail, then the reply as the
  loudest block. Turns are inferred from user messages, or set explicitly with `turn` on each
  message plus an optional `turns` list for separator labels and links. Set
  `"conversation_layout": "flat"` in the config to get a plain top-to-bottom list instead.
- **Readable results.** A `tool_result` may carry `items` (a list of `{title, meta, body}`) to
  render retrieved documents as separate blocks, `body_md` (with `title`) for one markdown body,
  or `summary` to replace the auto-generated one-line summary in the card header. A result whose
  content has `ok: false` or `error` draws the card in red.
- `chips` accept a string or `{"text", "color"}` with color in blue, orange, red, green, purple,
  yellow. `meta` strings sit after the chips in muted text.
- `context` is one card or a list of cards, each `{title, headline, body, fields}`; `fields` is an
  ordered object of label to value. `collapsible: true` lets the reviewer fold a card and
  remembers the choice; `collapsed: true` starts it folded, showing its headline in the header.
- `dot_class: "ring"` (or `ring: true`) draws a ring around the item's tracker dot and puts it in
  the ↑ ↓ cycle. It means "this one needs your attention first": a judge disagreement, a monitor
  flag, a proposed relabel. There is one ring style; do not invent per-reason colours, the tooltip
  (`dot_title`) carries the reason.
- `batch` groups consecutive items; the tracker draws a thin separator where the batch changes.
- If a request failed before the agent replied, still emit the item with an `error` message so
  the reviewer sees the gap rather than a silent omission.

Mistakes seen in practice: taking the id from the wrong field so every item shows the trace id
instead of the scenario id; dropping tool results because they live on a different span than the
call; a multi-turn conversation split into one item per turn (merge them by session and set
`turn`); markdown tables in replies left unrendered, which reviewers then mark as "unreadable";
and raw JSON for retrieval results, which hides what the agent actually read (use `items`).

## Step 3: write the review config

Write `review/review.json`. The decision panel is generated from it:

```json
{
  "title": "Cartwheel trace review",
  "store_key": "final-run-2026-09",
  "instructions": "Read until the first failure. Select the text that shows it and annotate it.",
  "fields": [
    {"key": "verdict", "type": "verdict", "label": "Verdict", "options": [
       {"value": "pass", "color": "green", "sets": {"scenario_valid": true, "confirmed_failure": false}},
       {"value": "fail", "color": "red", "sets": {"scenario_valid": true, "confirmed_failure": true}},
       {"value": "invalid", "label": "invalid scenario", "color": "orange", "sets": {"scenario_valid": false, "confirmed_failure": false}}]},
    {"key": "scenario_change", "type": "text", "label": "What should change", "show_when": {"key": "verdict", "equals": "invalid"}},
    {"key": "failure_modes", "type": "checklist", "label": "Failure modes", "options": ["wrong fact", "ignored instruction"]},
    {"key": "note", "type": "textarea", "label": "Annotation", "rows": 6}
  ],
  "summary": {"title": "Metrics", "columns": ["version", "TPR", "TNR"], "rows": [["v1", "0.78", "0.95"]], "current_row": 0, "note": "…"},
  "conversation_layout": "steps",
  "poll_seconds": 5,
  "seen_after_ms": 5000
}
```

Field types: `verdict` (one segmented control; each option has a colour and a `sets` map of
underlying fields it writes, so one click records several facts; the dots and the "decided" count
follow it; click the active option again to clear), `yesno`, `select`, `checklist` (stored as a
list), `text`, `textarea`. `show_when` hides a field until another field has the given value.

Prefer `verdict` for any decision the deliverable will count, with options that say what the
reviewer is deciding ("judge wrong → fix the prompt", not "yes"). A verdict whose options write
nothing (`"sets": {}`) is fine when the choice itself is the record. Put the free-text field last;
it is where the evidence goes. There is no default-on field type: a default the reviewer never
touched would be counted as a decision, which is the mistake the pilot review taught.

Other keys: `store_key` isolates the browser-side backup per review so two reviews served on the
same port over time cannot leak decisions into each other (this happened; always set it);
`summary` draws a foldable table under the top bar for numbers the reviewer should keep in view,
`current_row` bolds one; `instructions` prints one sentence above the fields; `poll_seconds` is
how often the page re-reads the samples file (0 disables); `seen_after_ms` is how long an item
must be on screen before its dot counts as seen.

Match the fields to the deliverable. If the assignment wants `scenario_id, decision, reason`, use
a `verdict` named `decision` and a `textarea` named `reason` so the export needs no renaming.

## Step 4: serve and hand over

```bash
python review/server.py --samples review/samples.json --annotations review/annotations.json --config review/review.json --port 8020
```

Open the URL, verify one item renders with its tool cards and context card (a screenshot via a
browser tool is the reliable check), then hand the page to the reviewer with three sentences:
what the decision field means, that it autosaves, and that selecting text adds an inline note.
Do not review on their behalf.

What the reviewer gets, so you can explain it:

- **Tracker dots** across the top, one per item: dim until the item has been on screen for the
  seen delay, blue once it has a note, the verdict's colour once decided, a ring if the adapter
  flagged it. Click a dot to jump. The status line counts decided, note-only, and seen.
- **Keyboard.** ← → move between items. ↑ jumps to the next ringed item (rightward on the
  tracker) and ↓ to the previous, wrapping at the ends, with a toast saying "ringed k of n"; up
  means forward because that is how the reviewer read it, so do not flip it. While typing, plain arrows edit the text; ⌥/Alt + arrow navigates; Esc leaves
  the box. In a note, Enter saves and leaves, Shift+Enter is a newline.
- **Tool cards** show the call name, arguments, and a one-line result summary; a click anywhere on
  the card shows or hides the full result. Open cards stay open while notes are added. Expand all
  and collapse all are in the item header. The call name is selectable, because "the agent called
  escalate_to_human" is itself evidence.
- **Inline notes.** Select any text in the conversation, including inside a tool result, and click
  "＋ annotate". The note is anchored to its message and character offsets, so a phrase that occurs
  eight times highlights in the right place and a selection across bold text or a table cell
  highlights whole. Clicking a note's quote scrolls to it and reopens a folded tool card; hovering
  a note card lights its highlight. "＋ note without a quote" covers failures with nothing to
  quote, such as a call that never happened. Notes are editable and deletable.

## Step 5: export

```bash
python review/export.py --samples review/samples.json --annotations review/annotations.json --config review/review.json --out review/decisions.jsonl
```

One row per decided or noted item, every config field present (`null` where unset), inline notes
attached as `[{"quote", "note"}]`, plus `seen`. If a deliverable wants another shape, write a
ten-line reshaper over this file rather than changing the exporter, and report to the reviewer how
many items still lack a decision.

## Reloading after a new run

Rerun the adapter over the new traces; the page re-reads the samples file on its poll and shows a
toast, so no restart is needed. Annotations are keyed by item id and survive as long as ids are
stable. Keep `annotations.json` under version control when the review is a deliverable. To run a
second review of the same items (a new judge version, a new period), use a new annotations file
and a new `store_key`.

## Limits

Single reviewer, single JSON file, no auth: run it on localhost. The page saves by replacing the
whole annotations file and never re-reads it, so a second tab or a second device will silently
overwrite the first. Inline highlights fall back to quote matching when a block's text changes, and
lose the highlight (not the note) if the quote is gone. The page holds every sample in memory; a
few thousand items is fine, tens of thousands is not.
