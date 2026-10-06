"""TraCI wrapper for the T-junction (SPEC 5.1).

Decisions happen at the end of each green. A controller returns
(next_phase, green_seconds); `apply_phase` inserts amber 3 s and all-red 2 s
whenever the phase changes, then holds the new green.
"""
import itertools
import os
import shutil
import tempfile

import traci

from africot import scenarios as sc
from africot import signals
from africot.sumo_utils import sumo_binary
from sim import demand

APPROACH_EDGES = {"west": "W2C", "east": "E2C", "south": "S2C"}
APPROACHES = tuple(APPROACH_EDGES)
CLASSES = ("car", "danfo", "keke", "okada")
CROSSINGS = ("xE", "xW", "xS")
VTYPES_FILE = os.path.join(signals.SIM_DIR, "vtypes.add.xml")

_label_counter = itertools.count()


class JunctionEnv:
    def __init__(self, out_dir=None, keep_outputs=False, step_hooks=None):
        self.out_dir = out_dir
        self.keep_outputs = keep_outputs
        self.step_hooks = list(step_hooks or [])
        self.conn = None
        self.label = None
        self._tmp = None
        st = signals.build_states()
        self.states = st
        self.links = st["links"]
        self.lanes = {}

    # ------------------------------------------------------------------ setup
    def reset(self, scenario, seed, end_s=sc.END_S):
        self.close()
        self.scenario = scenario
        self.seed = seed
        self.cfg = sc.get(scenario)
        self.end_s = end_s
        self._tmp = self.out_dir or tempfile.mkdtemp(prefix="africot_")
        os.makedirs(self._tmp, exist_ok=True)
        tag = f"{scenario}_{seed}_{os.getpid()}_{next(_label_counter)}"
        self.route_file = os.path.join(self._tmp, f"routes_{tag}.rou.xml")
        self.tripinfo_file = os.path.join(self._tmp, f"tripinfo_{tag}.xml")
        self.log_file = os.path.join(self._tmp, f"sumo_{tag}.log")
        self.demand_summary = demand.generate(scenario, seed, self.route_file, end_s=end_s)
        cmd = [sumo_binary("sumo"), "-n", signals.NET_FILE, "-r", self.route_file,
               "-a", VTYPES_FILE, "--lateral-resolution", "0.8", "--step-length", "1",
               "--seed", str(seed), "--end", str(end_s), "--time-to-teleport", "300",
               "--tripinfo-output", self.tripinfo_file, "--tripinfo-output.write-unfinished", "true",
               "--no-step-log", "true", "--log", self.log_file, "--duration-log.disable", "true"]
        self.label = f"env_{tag}"
        traci.start(cmd, label=self.label)
        self.conn = traci.getConnection(self.label)
        for name, edge in APPROACH_EDGES.items():
            n = self.conn.edge.getLaneNumber(edge)
            # lane 0 is the sidewalk
            self.lanes[name] = [f"{edge}_{i}" for i in range(1, n)]
        self.phase = "A"
        self.phase_start = 0.0
        self.signal = "green"
        self.teleports = 0
        self.departed_counts = {a: 0 for a in APPROACHES}
        self._prev_ids = {a: set() for a in APPROACHES}
        self.served_since = {a: 0.0 for a in APPROACHES}
        self.incident = self.cfg.get("incident")
        self.incident_log = {"inserted": None, "stopped": None, "stop_pos": None}
        self.conn.trafficlight.setRedYellowGreenState(signals.TLS_ID, self.states["green"]["A"])
        return self.get_state()

    @property
    def time(self):
        return self.conn.simulation.getTime()

    # --------------------------------------------------------------- stepping
    def _step(self):
        self.conn.simulationStep()
        self.teleports += self.conn.simulation.getStartingTeleportNumber()
        if self.incident:
            self._incident()
        for a, edge in APPROACH_EDGES.items():
            ids = set(self.conn.edge.getLastStepVehicleIDs(edge))
            self.departed_counts[a] += len(self._prev_ids[a] - ids)
            self._prev_ids[a] = ids
        for hook in self.step_hooks:
            hook(self)

    def _incident(self):
        """Right lane of the east approach blocked by a broken-down vehicle (SPEC 4, incident)."""
        inc, c, t, log = self.incident, self.conn, self.time, self.incident_log
        vid = "incident_blocker"
        if log["inserted"] is None and t >= inc["start"] - 1 and "incident_route" not in c.route.getIDList():
            c.route.add("incident_route", [inc["edge"], "C2W"])
            c.vehicle.add(vid, "incident_route", typeID="blocker", depart="now",
                          departLane=str(inc["lane_index"]), departPos="free", departSpeed="0")
        elif log["inserted"] is None and vid in c.vehicle.getIDList():
            log["inserted"] = t
            pos = c.vehicle.getLanePosition(vid)
            stop_pos = min(pos + 5.0, c.lane.getLength(f"{inc['edge']}_{inc['lane_index']}") - 5.0)
            log["stop_pos"] = round(stop_pos, 1)
            c.vehicle.setStop(vid, inc["edge"], pos=stop_pos, laneIndex=inc["lane_index"],
                              duration=float(inc["end"]) - t, until=float(inc["end"]))
        elif log["stopped"] is None and log["inserted"] is not None and vid in c.vehicle.getIDList() \
                and c.vehicle.isStopped(vid):
            log["stopped"] = t

    def step_until(self, t):
        t = min(t, self.end_s)
        while self.time < t:
            self._step()

    def done(self):
        return self.time >= self.end_s

    def _set(self, kind, phase):
        self.signal = kind
        state = self.states["all_red"] if kind == "all_red" else self.states[kind][phase]
        self.conn.trafficlight.setRedYellowGreenState(signals.TLS_ID, state)

    def apply_phase(self, phase, green_s):
        """Run (phase, green_s) to the end of its green. Inserts amber and all-red on a change."""
        if phase not in signals.PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        green_s = int(round(green_s))
        if phase != self.phase:
            self._set("amber", self.phase)
            self.step_until(self.time + signals.AMBER_S)
            self._set("all_red", None)
            self.step_until(self.time + signals.ALL_RED_S)
            self.phase = phase
            self.phase_start = self.time
            self._set("green", phase)
        for a in signals.PHASE_APPROACHES[phase]:
            self.served_since[a] = self.time + green_s
        self.step_until(self.time + green_s)
        return self.get_state()

    # ------------------------------------------------------------------ state
    def current_state_string(self):
        return self.conn.trafficlight.getRedYellowGreenState(signals.TLS_ID)

    def get_state(self):
        """Ground-truth junction state. Perception adds noise on top of this."""
        c = self.conn
        st = {"time": self.time, "phase": self.phase, "time_in_phase": self.time - self.phase_start,
              "approaches": {}, "ped_waiting": {x: 0 for x in CROSSINGS},
              "ped_max_wait": {x: 0.0 for x in CROSSINGS}}
        for a, lanes in self.lanes.items():
            counts = {k: 0 for k in CLASSES}
            halting_by_class = {k: 0 for k in CLASSES}
            max_wait = 0.0
            halting = 0
            occ = 0.0
            for lane in lanes:
                halting += c.lane.getLastStepHaltingNumber(lane)
                occ += c.lane.getLastStepOccupancy(lane)
                for v in c.lane.getLastStepVehicleIDs(lane):
                    vt = c.vehicle.getTypeID(v)
                    if vt not in counts:
                        continue  # incident blocker is not traffic demand
                    counts[vt] += 1
                    w = c.vehicle.getWaitingTime(v)
                    if c.vehicle.getSpeed(v) < 0.1:
                        halting_by_class[vt] += 1
                    max_wait = max(max_wait, w)
            st["approaches"][a] = {"queue": halting, "counts": counts, "halting_by_class": halting_by_class,
                                   "occupancy": occ / len(lanes), "max_wait": max_wait,
                                   "departures": self.departed_counts[a]}
        crossing_of = {e: x for e, x in self._crossing_edges().items()}
        for p in c.person.getIDList():
            road = c.person.getRoadID(p)
            if road.startswith(":C_w") and c.person.getSpeed(p) < 0.1:
                nxt = c.person.getNextEdge(p)
                if nxt in crossing_of:
                    x = crossing_of[nxt]
                    st["ped_waiting"][x] += 1
                    st["ped_max_wait"][x] = max(st["ped_max_wait"][x], c.person.getWaitingTime(p))
        st["teleports"] = self.teleports
        return st

    def _crossing_edges(self):
        if not hasattr(self, "_cross_cache"):
            import xml.etree.ElementTree as ET
            root = ET.parse(signals.NET_FILE).getroot()
            out, lengths = {}, {}
            for e in root.findall("edge"):
                if e.get("function") == "crossing":
                    x = signals.CROSSING_ARM[frozenset(e.get("crossingEdges").split())]
                    out[e.get("id")] = x
                    lengths[x] = float(e.find("lane").get("length"))
            self._cross_cache = out
            self.crossing_lengths = lengths
        return self._cross_cache

    def finish(self):
        """Close SUMO so tripinfo is flushed. Returns the tripinfo path."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        return getattr(self, "tripinfo_file", None)

    def teleport_reasons(self):
        """Count teleports by SUMO's reason (jam, yield, wrongLane, ...) from the log. Call after finish()."""
        reasons = {}
        if not os.path.exists(getattr(self, "log_file", "")):
            return reasons
        with open(self.log_file) as f:
            for line in f:
                if "Teleporting vehicle" in line and "waited too long" in line:
                    r = line.split("waited too long")[1].split(",")[0].strip(" ()")
                    reasons[r or "unknown"] = reasons.get(r or "unknown", 0) + 1
                elif "Teleporting vehicle" in line:
                    reasons["other"] = reasons.get("other", 0) + 1
        return reasons

    def close(self):
        self.finish()
        if self._tmp and not self.keep_outputs and not self.out_dir:
            shutil.rmtree(self._tmp, ignore_errors=True)
            self._tmp = None


def crossing_lengths():
    """{crossing: length in m} read from the network."""
    env = JunctionEnv.__new__(JunctionEnv)
    env._crossing_edges()
    return env.crossing_lengths
