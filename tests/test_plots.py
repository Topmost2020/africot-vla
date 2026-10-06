"""S8: tables and figures use only reportable evaluation runs."""
import json

import plots


def _write(d, name, **kw):
    rec = {"controller": "max_pressure", "scenario": "normal", "seed": 0, "seed_role": "evaluation",
           "vlam_backend": None, "reportable": True, "git_hash": "abc12345",
           "config": {}, "metrics": {"awt": 10.0, "att": 50.0, "aql": 3.0, "throughput": 100, "ped_wait": 5.0,
                                     "not_inserted": 0, "awt_completed": 9.0, "shield_interventions": 1,
                                     "safety_violations": 0, "jam_teleports": 0}}
    rec.update(kw)
    (d / name).write_text(json.dumps(rec))


def test_mock_and_tuning_runs_excluded(tmp_path):
    _write(tmp_path, "max_pressure__normal__0.json")
    _write(tmp_path, "max_pressure__normal__1.json", seed=1, metrics={**json.loads(
        (tmp_path / "max_pressure__normal__0.json").read_text())["metrics"], "awt": 20.0})
    _write(tmp_path, "africot_full__normal__0.json", controller="africot_full", vlam_backend="mock", reportable=False)
    _write(tmp_path, "max_pressure__normal__100.json", seed=100, seed_role="tuning")
    rows = plots.load(str(tmp_path))
    assert {(r["controller"], r["seed"]) for r in rows} == {("max_pressure", 0), ("max_pressure", 1)}
    s = plots.summarise(rows)
    assert len(s) == 1 and s[0]["awt_mean"] == 15.0 and s[0]["n_seeds"] == 2


def test_main_writes_outputs(tmp_path):
    _write(tmp_path, "max_pressure__normal__0.json")
    figs = tmp_path / "figs"
    assert plots.main(["--results-dir", str(tmp_path), "--figures-dir", str(figs)]) == 0
    assert (tmp_path / "summary.csv").exists() and (figs / "awt_by_scenario.png").exists()
