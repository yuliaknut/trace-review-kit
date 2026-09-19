"""Example adapter: Cartwheel course traces -> trace-review-kit samples.

Input: the Langfuse-derived samples file that the course loader writes (analysis/state/samples.json),
already joined to the scenario file. Output: the kit's normalized shape.

    python adapter.py analysis/state/samples.json review/samples.json

What this shows: mapping a project's message list onto the five roles, turning the scenario's
answer key into the context card, and putting role/model/prompt version into chips and meta.
"""
import json
import sys


def convert(sample: dict) -> dict:
    meta = sample.get("meta") or {}
    tup = sample.get("scenario") or {}
    exp = sample.get("expected") or {}
    src = exp.get("source") or {}
    sid = meta.get("scenario_id") or (sample.get("metadata") or {}).get("cartwheel.scenario_id") or sample["trace_id"]

    messages = []
    for m in sample.get("trace") or []:
        role = m.get("role")
        if role == "tool_call":
            messages.append({"role": "tool_call", "name": m.get("name"), "arguments": m.get("arguments")})
        elif role == "tool_result":
            messages.append({"role": "tool_result", "name": m.get("name"), "content": m.get("content")})
        elif role in ("user", "assistant"):
            messages.append({"role": role, "text": m.get("text") or m.get("content") or ""})
        else:
            messages.append({"role": "observation", "label": m.get("label") or role, "text": m.get("text") or m.get("content") or ""})

    chips = []
    if sample.get("scenario_group"):
        chips.append({"text": sample["scenario_group"], "color": "blue" if sample["scenario_group"] == "coverage" else "orange"})
    if sample.get("data_quality_case_id"):
        chips.append({"text": sample["data_quality_case_id"], "color": "red"})
    if tup.get("difficulty") and tup["difficulty"] != "well_specified":
        chips.append({"text": tup["difficulty"], "color": "yellow"})

    fields = {
        "source": f"{src.get('type', '?')} · {src.get('reference', '?')}",
        "intent": tup.get("intent"),
        "record": " · ".join(str(x) for x in [tup.get("record_state"), f"order {tup['order_id']}" if tup.get("order_id") else None, f"product {tup['product_id']}" if tup.get("product_id") else None] if x),
        "policy": tup.get("applicable_policy"),
        "style": tup.get("user_style"),
        "turns": f"{tup.get('turn_count')} · tools: {tup.get('tools_needed')}",
    }
    objective = exp.get("evaluation") == "objective"
    return {
        "id": sid,
        "group": sample.get("scenario_group"),
        "chips": chips,
        "meta": [f"{meta.get('role') or tup.get('role', '?')} · user {tup.get('user_id', '?')}", f"prompt {meta.get('prompt_version', '?')}", ", ".join(sample.get("models") or []) or "model ?"],
        "link": sample.get("permalink"),
        "link_label": "open in Langfuse ↗",
        "messages": messages,
        "context": {
            "title": "Expected outcome (scenario file)",
            "headline": exp.get("outcome") if objective else "human judgment",
            "body": exp.get("reason") if objective else exp.get("criterion"),
            "fields": {k: v for k, v in fields.items() if v},
        },
    }


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out = [convert(s) for s in json.load(open(src, encoding="utf-8"))]
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {len(out)} samples to {dst}")
