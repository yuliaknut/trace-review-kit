# trace-review-kit

A one-trace-at-a-time review interface for error analysis of AI agents, packaged as a Claude Code
plugin. The page, theme, server, and exporter are generic; a skill teaches a coding agent to write
the two project-specific pieces, an adapter from the project's traces and a config of decision fields.

Built during the "Evaluating and Improving AI Agents" course for the Cartwheel support agent, then
extracted. Single reviewer, localhost, no dependencies beyond Python 3.10.

## Install

In Claude Code:

```
/plugin install trace-review-kit --source github --repo yuliaknut/trace-review-kit
```

Then in any project: "set up a trace review page for these traces" invokes the `trace-review` skill.

## Use without the skill

```bash
cp skills/trace-review/assets/{index.html,theme.css,server.py,export.py} review/
python skills/trace-review/examples/chat-jsonl/adapter.py skills/trace-review/examples/chat-jsonl/sample_log.jsonl review/samples.json
python review/server.py --samples review/samples.json --annotations review/annotations.json --config skills/trace-review/examples/chat-jsonl/review.json
```

Open http://localhost:8020/. The sample contract, config schema, and export format are in
[skills/trace-review/SKILL.md](skills/trace-review/SKILL.md).

## Layout

```
.claude-plugin/plugin.json
skills/trace-review/
  SKILL.md                 the instructions a coding agent follows
  assets/index.html        the page (reads /api/samples, /api/config, /api/annotations)
  assets/theme.css         GitHub dark dimmed tokens and components
  assets/server.py         stdlib server and JSON annotation store
  assets/export.py         annotations -> JSONL decisions
  examples/cartwheel/      adapter + config for a Langfuse-traced agent with scenario answer keys
  examples/chat-jsonl/     adapter + config for a plain chat log with no answer key
```
