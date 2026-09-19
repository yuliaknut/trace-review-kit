---
name: trace-review
description: Stand up a one-trace-at-a-time review page (GitHub dark dimmed theme) for evaluating an AI agent or chatbot on any project. Use when the user wants to review, annotate, label, or open-code conversation traces, agent runs, tool-call logs, or eval results in a browser, and export the decisions to a file.
---

# Trace review

A reusable review interface for error analysis: one conversation per screen, tool calls as
collapsible cards, an answer-key card beside the conversation, a decision panel you configure,
inline notes on selected text, autosave to a JSON file, and an exporter. The page, theme, and
server are generic and live in `assets/`. Two things are written per project, by you, following
the steps below: an **adapter** that maps the project's traces onto the sample contract, and a
**review config** naming the decision fields.

The human decides; you build. Never write the reviewer's annotations, and never invent
expected outcomes: the answer key in the context card must come from the project's own data,
rules, or scenario file, and the adapter must make its source visible.

## Setup

Copy the assets into the project, into a directory the project can commit. The default is `review/`:

```bash
mkdir -p review && cp "${CLAUDE_SKILL_DIR}/assets/"{index.html,theme.css,server.py,export.py} review/
```

Do not modify `index.html` or `server.py` for a project unless a step below says so; put
project logic in the adapter and the config so the kit stays upgradable. If the theme needs a
tweak, override tokens in a second stylesheet rather than editing `theme.css`.

## Step 1: find the traces and their answer keys

Ask, or find in the repo, three things before writing any code:

1. **Where the traces are.** A trace store (Langfuse, LangSmith, an OpenTelemetry backend), a
   JSONL log, a results file written by a runner, or a database. Confirm you can read one full
   conversation including tool calls and tool results, not just the final reply.
2. **What identifies an item.** A scenario id, a conversation id, a trace id. The exporter keys
   on it, so it must be stable across reloads. If the project has scenario ids, prefer them to
   trace ids: a rerun changes the trace id but not the scenario.
3. **What the reviewer compares against.** A scenario file with expected outcomes, a
   specification with numbered requirements, a rubric, or nothing. This fills the context card.
   If there is nothing, the card shows metadata only and the config gets a `select` verdict.

Read [examples/cartwheel/adapter.py](examples/cartwheel/adapter.py) for a trace-store project
with an answer key, and [examples/chat-jsonl/adapter.py](examples/chat-jsonl/adapter.py) for a
plain log with none.

## Step 2: write the adapter

Write `review/adapter.py` that reads the project's source and writes `review/samples.json`, a JSON
list in the sample contract below. Keep it a plain script with a `convert(record) -> dict`
function so it can be rerun after every new run of the agent.

### The sample contract

```json
{
  "id": "support-0042",
  "group": "challenge",
  "chips": ["shopper", {"text": "dq-order-missing-delivery-date", "color": "red"}],
  "meta": ["user 392", "prompt 1b6ab97b", "gpt-5.5"],
  "link": "https://langfuse.local/project/p/traces/abc123",
  "link_label": "open in Langfuse ↗",
  "messages": [
    {"role": "user", "text": "Can I still send back the pencil set?"},
    {"role": "assistant", "text": "I'll check the order."},
    {"role": "tool_call", "name": "get_order", "arguments": {"order_id": 8002}},
    {"role": "tool_result", "name": "get_order", "content": {"ok": true, "status": "delivered", "delivered_at": null}},
    {"role": "assistant", "text": "The order shows delivered but has no delivery date, so..."},
    {"role": "observation", "label": "guardrail", "text": "output filter passed"}
  ],
  "context": {
    "title": "Expected outcome (scenario file)",
    "headline": "do_not_compute_return_deadline",
    "body": "The order has a delivered status but no delivery date.",
    "fields": {"source": "data_quality_table · dq-order-missing-delivery-date", "intent": "return_deadline"}
  }
}
```

Rules the page relies on:

- `id` is required and unique. Everything else is optional.
- `messages` roles are `user`, `assistant`, `tool_call`, `tool_result`, `observation`, `error`.
  A `tool_result` directly after a `tool_call` is rendered inside that call's card; keep them
  adjacent and in order. Assistant text renders light markdown (bold, code, bullets, pipe tables).
- `arguments` and `content` may be objects or JSON strings; both are pretty-printed.
- `chips` accept a string or `{"text", "color"}` with color in blue, orange, red, green, purple, yellow.
- `context.fields` is an ordered object of label to value; values are shown as text.
- If a request failed before the agent replied, still emit the item with an `error` message so
  the reviewer sees the gap rather than a silent omission.

Common mistakes seen in practice: taking the id from the wrong field so every item shows the
trace id instead of the scenario id; dropping tool results because they live on a different span
than the call; multi-turn conversations split into one item per turn (merge them by session);
and markdown tables in replies left unrendered, which reviewers then mark as "unreadable".

## Step 3: write the review config

Write `review/review.json`. The decision panel is generated from it:

```json
{
  "title": "Cartwheel trace review",
  "fields": [
    {"key": "scenario_valid", "type": "flag", "label": "scenario valid", "label_off": "scenario invalid", "default": true, "hint": "click to flag a defective scenario"},
    {"key": "scenario_change", "type": "text", "label": "What should change", "show_when": {"key": "scenario_valid", "equals": false}},
    {"key": "confirmed_failure", "type": "yesno", "label": "Confirmed failure?"},
    {"key": "failure_modes", "type": "checklist", "label": "Failure modes", "options": ["wrong fact", "ignored instruction"]},
    {"key": "verdict", "type": "select", "label": "Verdict", "options": ["pass", "fail", "unsure"]},
    {"key": "note", "type": "textarea", "label": "Annotation", "rows": 6}
  ]
}
```

Field types: `flag` (one button, holds its default until clicked, so the common case costs no
clicks), `yesno`, `select`, `checklist` (stored as a list), `text`, `textarea`. `show_when`
hides a field until another field has the given value. Put the free-text note last; it is where
the evidence goes.

Match the fields to the deliverable. If the assignment wants `scenario_id, decision, reason`,
use a `select` named `decision` and a `textarea` named `reason` so the export needs no renaming.

## Step 4: serve and hand over

```bash
python review/server.py --samples review/samples.json --annotations review/annotations.json --config review/review.json --port 8020
```

Open the URL, verify one item renders with its tool cards and context card (a screenshot via a
browser tool is the reliable check), then hand the page to the reviewer with three sentences:
what each decision field means, that it autosaves, and that selecting text adds an inline note.
Do not review on their behalf. The dot strip shows progress: green reviewed, red flagged.

Keyboard: left and right arrows move between items; while typing, hold Option or Alt, or press
Escape to leave the box.

## Step 5: export

```bash
python review/export.py --samples review/samples.json --annotations review/annotations.json --config review/review.json --out review/decisions.jsonl
```

One row per reviewed item, flag defaults applied, inline notes attached as `[{"quote", "note"}]`.
If a deliverable wants another shape, write a ten-line reshaper over this file rather than
changing the exporter, and report to the reviewer how many items are missing a decision.

## Reloading after a new run

Rerun the adapter over the new traces and reload the page; the server re-reads the samples file
on every request. Annotations are keyed by item id, so notes survive as long as ids are stable.
Keep `annotations.json` under version control when the review is a deliverable.

## Limits

Single reviewer, single JSON file, no auth: run it on localhost. Inline highlights are matched
by exact quote text, so an edited reply loses its highlight but keeps the note card. The page
holds every sample in memory; a few thousand items is fine, tens of thousands is not.
