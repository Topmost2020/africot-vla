"""Run one controller on one scenario and seed, and compute metrics."""
import time as _time

from africot import scenarios as sc
from africot.env import JunctionEnv
from africot.metrics import StepSampler, compute


def run_episode(controller, scenario, seed, end_s=sc.END_S, observe=None, step_hooks=None,
                decision_hook=None):
    """Run `controller` for one episode.

    observe(state) -> observation given to the controller (defaults to ground truth;
    S2 replaces it with noisy perception). decision_hook(env, obs, decision) is
    called after every decision, for logging.
    Returns (metrics, info).
    """
    sampler = StepSampler()
    env = JunctionEnv(step_hooks=[sampler] + list(step_hooks or []))
    t0 = _time.time()
    state = env.reset(scenario, seed, end_s=end_s)
    controller.reset()
    decisions = 0
    try:
        phase, green = controller.first()
        while not env.done():
            state = env.apply_phase(phase, green)
            decisions += 1
            if env.done():
                break
            obs = observe(state) if observe else state
            phase, green = controller.decide(obs)
            if decision_hook:
                decision_hook(env, obs, (phase, green))
        info = {"teleports": env.teleports, "decisions": decisions,
                "incident": env.incident_log if env.incident else None,
                "demand": env.demand_summary, "wall_s": None}
        tripinfo = env.finish()
        info["teleport_reasons"] = env.teleport_reasons()
        metrics = compute(tripinfo, sampler, counters={"teleports": env.teleports,
                                                         "jam_teleports": info["teleport_reasons"].get("jam", 0)})
    finally:
        env.close()
    info["wall_s"] = round(_time.time() - t0, 1)
    return metrics, info
