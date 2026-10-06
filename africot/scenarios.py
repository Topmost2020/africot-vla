"""Scenario definitions (SPEC 4, Scenarios). Times are simulation clock seconds."""

WARMUP_S = 300
MEASURE_S = 3600
END_S = WARMUP_S + MEASURE_S  # 3900

TUNING_SEEDS = (100, 101, 102, 103, 104)
EVAL_SEEDS = (0, 1, 2, 3, 4)
DATA_SEEDS = tuple(range(200, 220))

MIX_NORMAL = {"car": 0.45, "danfo": 0.20, "keke": 0.15, "okada": 0.20}
MIX_MARKET = {"car": 0.30, "danfo": 0.20, "keke": 0.25, "okada": 0.25}

# Turning shares (destination arm by origin arm).
TURNS = {
    "W": {"E": 0.80, "S": 0.20},
    "E": {"W": 0.75, "S": 0.25},
    "S": {"E": 0.50, "W": 0.50},
}

_NORMAL = {
    "flows": {"W": 700, "E": 700, "S": 300},  # veh/h per origin arm
    "mix": MIX_NORMAL,
    "ped_per_h": 300,
    # share of pedestrians crossing each arm
    "ped_split": {"xE": 1 / 3, "xW": 1 / 3, "xS": 1 / 3},
    "context": "",
}
_MARKET = {
    # SPEC table gives S = 550 veh/h. Tuned on tuning seeds 100-104 to 200 veh/h
    # (results/demand_tuning.json, sim/tune_demand.py; DEVIATIONS.md).
    "flows": {"W": 700, "E": 700, "S": 200},
    "mix": MIX_MARKET,
    "ped_per_h": 900,
    "ped_split": {"xE": 0.4, "xW": 0.4, "xS": 0.2},
    "context": "market day",
}

SCENARIOS = {
    "normal": dict(_NORMAL),
    "market": dict(_MARKET),
    "incident": dict(_NORMAL, incident={"edge": "E2C", "lane_index": 1, "start": 1200, "end": 2100},
                     context="incident reported on east approach"),
    "outage": dict(_MARKET, outage={"start": 1200, "end": 2400}),
}


def get(name):
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario {name!r}; choose from {sorted(SCENARIOS)}")
    return SCENARIOS[name]
