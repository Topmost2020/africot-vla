"""Run one controller on one scenario and seed, and compute metrics.

Every decision goes controller -> shield -> environment. The shield cannot be
switched off here; that is what makes it non-bypassable.
"""
import time as _time

from africot import scenarios as sc
from africot.env import JunctionEnv
from africot.metrics import StepSampler, compute
from africot.shield import SafetyAudit, Shield


def run_episode(controller, scenario, seed, end_s=sc.END_S, observe=None, step_hooks=None,
                decision_hook=None, audit=True, overrides=None):
    """Run `controller` for one episode.

    observe(state) -> observation given to the controller and the shield
    (defaults to ground truth; run_experiment passes noisy perception).
    decision_hook(env, obs, proposal, applied, corrections) is called after every
    decision, for logging. Returns (metrics, info).
    """
    sampler = StepSampler()
    shield = Shield()
    hooks = [sampler] + list(step_hooks or [])
    auditor = SafetyAudit(shield.ctimes) if audit else None
    if auditor:
        hooks.append(auditor)
    env = JunctionEnv(step_hooks=hooks)
    t0 = _time.time()
    state = env.reset(scenario, seed, end_s=end_s, overrides=overrides)
    controller.reset()
    shield.reset()
    decisions = 0
    try:
        obs = observe(state) if observe else state
        proposal = controller.first()
        phase, green, corr = shield.check(proposal, obs)
        if decision_hook:
            decision_hook(env, obs, proposal, (phase, green), corr)
        while not env.done():
            state = env.apply_phase(phase, green)
            decisions += 1
            if env.done():
                break
            obs = observe(state) if observe else state
            proposal = controller.decide(obs)
            phase, green, corr = shield.check(proposal, obs)
            if decision_hook:
                decision_hook(env, obs, proposal, (phase, green), corr)
        info = {"teleports": env.teleports, "decisions": decisions,
                "incident": env.incident_log if env.incident else None,
                "demand": env.demand_summary, "wall_s": None}
        if auditor:
            auditor._close_segment(env.time, end_of_sim=True)
            info["safety_audit"] = auditor.summary()
        by_rule = {}
        for entry in shield.log:
            for c in entry["corrections"]:
                by_rule[c["rule"]] = by_rule.get(c["rule"], 0) + 1
        info["shield_corrections_by_rule"] = by_rule
        tripinfo = env.finish()
        info["teleport_reasons"] = env.teleport_reasons()
        counters = {"teleports": env.teleports, "jam_teleports": info["teleport_reasons"].get("jam", 0),
                    "shield_interventions": shield.interventions, "decisions": decisions}
        if auditor:
            counters["safety_violations"] = info["safety_audit"]["violations"]
        metrics = compute(tripinfo, sampler, counters=counters, route_file=env.route_file)
    finally:
        env.close()
    info["wall_s"] = round(_time.time() - t0, 1)
    return metrics, info
