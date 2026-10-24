"""Explainability log (SPEC 5.12): one JSON line per decision in logs/<run_id>.jsonl."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.environ.get("AFRICOT_LOG_DIR", os.path.join(ROOT, "logs"))


class ExplainLog:
    def __init__(self, run_id, controller, scenario, seed, vlam_backend=None, log_dir=LOG_DIR, ctrl=None):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"{run_id}.jsonl")
        self.f = open(self.path, "w")
        self.meta = {"controller": controller, "scenario": scenario, "seed": seed}
        self.vlam_backend = vlam_backend
        self.ctrl = ctrl

    def __call__(self, env, obs, proposal, applied, corrections):
        """Decision hook for runner.run_episode."""
        c = self.ctrl
        coord = getattr(c, "subgoal_source", None)
        last = getattr(coord, "last_decision", None) or {}
        call = last.get("call") or {}
        rec = {
            "sim_time": obs["time"], **self.meta,
            "trigger": last.get("trigger", "none"),
            "connectivity": last.get("connectivity", "n/a"),
            "vlam_backend": self.vlam_backend,
            "cot_reasoning": last.get("reasoning"),
            "vlam_parse_ok": call.get("parse_ok"),
            "vlam_latency_s": call.get("latency_s"),
            "subgoal": getattr(c, "last_subgoal", None),
            "cem_plan": getattr(c, "last_plan", None),
            "proposal": list(proposal),
            "shield_corrections": corrections,
            "shield_reason": "; ".join(x["reason"] for x in corrections) or None,
            "applied_phase": applied[0], "applied_green": applied[1],
            "wm_1step_error": getattr(c, "last_wm_error", None),
        }
        self.f.write(json.dumps(rec, default=float) + "\n")

    def close(self):
        self.f.close()
