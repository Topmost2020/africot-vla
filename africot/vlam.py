"""Slow-loop vision-language-action model (SPEC 5.10).

Backends:
- `mock`: deterministic rules. ONLY for tests and wiring. Never report its runs
  as VLAM results; every record carries `backend`.
- `hf`: Hugging Face transformers, Qwen2.5-VL family by default
  (Qwen/Qwen2.5-VL-3B-Instruct on CPU, Qwen/Qwen2.5-VL-7B-Instruct on GPU).
  The model id is configurable. Greedy decoding.

The model sees the junction image, a context block (clock time, scenario
context when known, current queues, current subgoal) and the subgoal schema
with its ranges. It reasons inside <reasoning>...</reasoning> and answers with
JSON inside <subgoal>...</subgoal>. The answer is parsed and validated.
"""
import json
import time

from africot import subgoal as sg

DEFAULT_HF_MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"

SYSTEM_PROMPT = (
    "You are the strategic reasoning module of a traffic signal controller for a signalised "
    "T-junction in Lagos, Nigeria (traffic drives on the right). Arms: west and east (main road, "
    "2 lanes each way) and south (side road, 1 lane each way). Phases: A main road (W-E, W-S, E-W; "
    "E-S permissive; pedestrians cross the south arm), B east protected left (E-S and E-W), "
    "C side road (S-E, S-W; pedestrians cross the east and west arms). Vehicles include cars, "
    "danfo minibuses (public transit), keke tricycles and okada motorcycles.\n"
    "You do not choose signal timings. You set a subgoal that weights the objectives of a "
    "fast planner for the next few minutes."
)


def schema_text():
    lines = ["Subgoal JSON schema (values outside a range are clamped):"]
    lines.append('  "queue_weights": {"east": w, "west": w, "south": w}   each w in [0.2, 3.0]')
    for k in ("pedestrian_weight", "max_wait_s", "transit_priority", "valid_for_s"):
        lo, hi = sg.RANGES[k]
        lines.append(f'  "{k}": number in [{lo}, {hi}]')
    lines.append("Default: " + json.dumps(sg.DEFAULT_SUBGOAL))
    return "\n".join(lines)


def build_prompt(context):
    """Text part of the prompt. `context` has clock, scenario_context, queues, ped_waiting, subgoal."""
    q = context["queues"]
    p = context.get("ped_waiting", {})
    lines = [
        f"Simulated clock time: {context['clock']}",
        f"Scenario context: {context.get('scenario_context') or 'none reported'}",
        "Current observed queues (halting vehicles): " + ", ".join(f"{a} {q[a]:.0f}" for a in ("east", "west", "south")),
        "Waiting pedestrians: " + ", ".join(f"{x} arm {p.get(k, 0):.0f}" for x, k in
                                            (("east", "xE"), ("west", "xW"), ("south", "xS"))),
        "Waiting danfos (transit): " + ", ".join(f"{a} {context.get('danfos', {}).get(a, 0):.0f}"
                                                for a in ("east", "west", "south")),
        "Current subgoal: " + json.dumps(context["subgoal"]),
        "",
        schema_text(),
        "",
        "Look at the image of the junction and the context. Reason step by step about which "
        "approaches and road users need priority now and why, inside <reasoning>...</reasoning>. "
        "Then output only the new subgoal as JSON inside <subgoal>...</subgoal>.",
    ]
    return "\n".join(lines)


class MockVLAM:
    """Deterministic rule-based stand-in. ONLY for tests and wiring checks."""
    backend = "mock"
    model_id = "mock-rules"

    def query(self, image_path, context):
        t0 = time.time()
        q = context["queues"]
        total = max(1.0, sum(q.values()))
        weights = {a: round(min(3.0, max(0.2, 3.0 * q[a] / total + 0.5)), 2) for a in ("east", "west", "south")}
        ctx = (context.get("scenario_context") or "").lower()
        reasons = [f"Queues east {q['east']:.0f}, west {q['west']:.0f}, south {q['south']:.0f}."]
        ped_w, max_wait, transit = 1.0, 120, 1.0
        if "market" in ctx:
            ped_w = 1.5
            reasons.append("Market day: many pedestrians, raise pedestrian weight.")
        if "incident" in ctx and "east" in ctx:
            weights["east"] = min(3.0, weights["east"] + 0.5)
            max_wait = 90
            reasons.append("Incident on east approach: favour east and shorten maximum wait.")
        goal = {"queue_weights": weights, "pedestrian_weight": ped_w, "max_wait_s": max_wait,
                "transit_priority": transit, "valid_for_s": 300}
        raw = f"<reasoning>{' '.join(reasons)}</reasoning>\n<subgoal>{json.dumps(goal)}</subgoal>"
        return _finish(self, raw, context, time.time() - t0)


class HFVLAM:
    """Hugging Face transformers backend (Qwen2.5-VL by default). Greedy decoding."""
    backend = "hf"

    def __init__(self, model_id=DEFAULT_HF_MODEL, max_new_tokens=400, dtype="bfloat16", device=None):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, dtype=getattr(torch, dtype), device_map=device)
        self.model.eval()
        self.device = device

    def query(self, image_path, context):
        import torch
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": build_prompt(context)}]},
        ]
        text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt").to(self.model.device)
        t0 = time.time()
        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)
        latency = time.time() - t0
        raw = self.processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        return _finish(self, raw, context, latency)


def _finish(vlam, raw, context, latency):
    reasoning, obj = sg.parse_response(raw)
    previous = context.get("subgoal")
    if obj is None:
        goal, notes, ok = previous or sg.DEFAULT_SUBGOAL, ["unparseable response; kept previous subgoal"], False
    else:
        goal, notes = sg.validate(obj, previous)
        ok = True
    return {"backend": vlam.backend, "model": vlam.model_id, "raw": raw, "reasoning": reasoning,
            "parsed": obj, "subgoal": goal, "validator_notes": notes, "parse_ok": ok,
            "latency_s": round(latency, 3)}


def make_vlam(backend="mock", model_id=None):
    if backend == "mock":
        return MockVLAM()
    if backend == "hf":
        return HFVLAM(model_id or DEFAULT_HF_MODEL)
    raise ValueError(f"unknown VLAM backend {backend!r}")
