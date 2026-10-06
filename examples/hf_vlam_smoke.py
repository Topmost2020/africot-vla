"""S6 check: the hf backend produces a parseable subgoal on a real junction snapshot.

    HF_HOME=hf_cache python examples/hf_vlam_smoke.py [--model Qwen/Qwen2.5-VL-3B-Instruct]

Uses examples/snapshot_market_100.png (market scenario, tuning seed 100, t = 226 s)
and writes examples/vlam_hf_output.json. Model weights are not committed.
"""
import argparse
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from africot import subgoal as sg  # noqa: E402
from africot.vlam import HFVLAM, DEFAULT_HF_MODEL, build_prompt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_HF_MODEL)
    p.add_argument("--image", default=os.path.join(HERE, "snapshot_market_100.png"))
    p.add_argument("--out", default=os.path.join(HERE, "vlam_hf_output.json"))
    args = p.parse_args()
    meta = json.load(open(os.path.join(HERE, "snapshot_market_100.json")))
    context = {"clock": meta["clock"], "scenario_context": "market day", "queues": meta["queues"],
               "ped_waiting": meta["ped_waiting"], "danfos": meta["danfos"],
               "subgoal": sg.DEFAULT_SUBGOAL}
    t0 = time.time()
    vlam = HFVLAM(args.model)
    load_s = time.time() - t0
    rec = vlam.query(args.image, context)
    rec.update({"image": os.path.relpath(args.image, os.path.dirname(HERE)), "context": context,
                "prompt_text": build_prompt(context), "load_s": round(load_s, 1),
                "machine": {"platform": platform.platform(), "cpu_count": os.cpu_count()},
                "decoding": "greedy (do_sample=False)", "max_new_tokens": vlam.max_new_tokens})
    with open(args.out, "w") as f:
        json.dump(rec, f, indent=1)
    print(json.dumps({k: rec[k] for k in ("model", "parse_ok", "latency_s", "subgoal", "validator_notes")}, indent=1))


if __name__ == "__main__":
    main()
