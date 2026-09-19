"""Example adapter: a plain JSONL chat log -> trace-review-kit samples.

Input: one JSON object per line, {"id": "...", "messages": [{"role": "user"|"assistant"|"tool"|"system", "content": ..., "name"?: ..., "tool_calls"?: [...]}]}
in the OpenAI chat-completions shape most logging setups produce. Output: the kit's normalized shape.

    python adapter.py logs/conversations.jsonl review/samples.json

What this shows: unpacking assistant tool_calls into separate tool_call messages so the page can
pair each with the tool message that follows, and building a context card when there is no answer key.
"""
import json
import sys


def convert(rec: dict) -> dict:
    messages = []
    for m in rec.get("messages") or []:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            if m.get("content"):
                messages.append({"role": "assistant", "text": m["content"]})
            for tc in m["tool_calls"]:
                fn = tc.get("function") or {}
                messages.append({"role": "tool_call", "name": fn.get("name") or tc.get("name"), "arguments": fn.get("arguments") or tc.get("arguments")})
        elif role == "tool":
            messages.append({"role": "tool_result", "name": m.get("name") or m.get("tool_call_id"), "content": m.get("content")})
        elif role in ("user", "assistant"):
            messages.append({"role": role, "text": m.get("content") or ""})
        else:
            messages.append({"role": "observation", "label": role or "note", "text": m.get("content") or ""})
    n_tools = sum(1 for m in messages if m["role"] == "tool_call")
    return {
        "id": str(rec.get("id")),
        "chips": [{"text": f"{n_tools} tool call{'s' if n_tools != 1 else ''}", "color": "purple"}] if n_tools else [],
        "meta": [rec.get("model") or "", rec.get("timestamp") or ""],
        "messages": messages,
        "context": {"title": "About this conversation", "fields": {k: v for k, v in (rec.get("metadata") or {}).items()}},
    }


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out = [convert(json.loads(l)) for l in open(src, encoding="utf-8") if l.strip()]
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {len(out)} samples to {dst}")
