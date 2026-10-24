"""S1: network geometry and signal phases."""
import xml.etree.ElementTree as ET

import pytest

from africot import signals

NET = ET.parse(signals.NET_FILE).getroot()


def _edge(eid):
    return next(e for e in NET.findall("edge") if e.get("id") == eid)


@pytest.mark.parametrize("eid,lanes,speed", [
    ("W2C", 2, 13.89), ("C2W", 2, 13.89), ("E2C", 2, 13.89), ("C2E", 2, 13.89),
    ("S2C", 1, 11.11), ("C2S", 1, 11.11)])
def test_edges_lanes_speed_sidewalk(eid, lanes, speed):
    e = _edge(eid)
    ls = e.findall("lane")
    assert ls[0].get("allow") == "pedestrian"  # sidewalk
    road = ls[1:]
    assert len(road) == lanes
    for lane in road:
        assert float(lane.get("speed")) == pytest.approx(speed)


def test_three_crossings():
    cross = [e for e in NET.findall("edge") if e.get("function") == "crossing"]
    arms = {signals.CROSSING_ARM[frozenset(e.get("crossingEdges").split())] for e in cross}
    assert arms == {"xE", "xW", "xS"}


def test_all_movements_and_no_uturns():
    movs = set(signals.load_links().values())
    assert movs == {"WE", "WS", "EW", "ES", "SE", "SW", "xE", "xW", "xS"}


def test_no_conflicting_greens_in_any_signal_state():
    st = signals.build_states()
    links = st["links"]
    all_states = list(st["green"].values()) + list(st["amber"].values()) + [st["all_red"]]
    for s in all_states:
        assert signals.conflicts_in_state(s, links) == [], s


def test_conflict_checker_catches_unsafe_state():
    st = signals.build_states()
    links = st["links"]
    # W->E and E->S both protected green must be flagged.
    bad = list(st["all_red"])
    for idx, mov in links.items():
        if mov in ("WE", "ES"):
            bad[idx] = "G"
    assert signals.conflicts_in_state("".join(bad), links)


def test_phase_contents():
    st = signals.build_states()
    links = st["links"]
    a = signals.green_movements(st["green"]["A"], links)
    assert a == {"WE": "G", "WS": "g", "EW": "G", "ES": "g", "xS": "G"}
    b = signals.green_movements(st["green"]["B"], links)
    assert b == {"ES": "G", "EW": "G"}
    c = signals.green_movements(st["green"]["C"], links)
    assert c == {"SE": "g", "SW": "g", "xE": "G", "xW": "G"}
    for p in signals.PHASES:
        assert set(st["amber"][p]) <= {"y", "r"}
    assert set(st["all_red"]) == {"r"}


def test_sublane_and_vtypes():
    vt = ET.parse(signals.SIM_DIR + "/vtypes.add.xml").getroot()
    types = {v.get("id"): v for v in vt.findall("vType")}
    assert float(types["okada"].get("width")) == 0.8
    assert types["okada"].get("latAlignment") == "arbitrary"
    assert types["okada"].get("vClass") == "motorcycle"
    assert types["danfo"].get("vClass") == "bus"
    assert float(types["keke"].get("width")) == 1.4
    for vid, length, kmh in (("car", 4.5, 60), ("danfo", 5.5, 50), ("keke", 2.7, 40), ("okada", 2.0, 60)):
        assert float(types[vid].get("length")) == length
        assert float(types[vid].get("maxSpeed")) == pytest.approx(kmh / 3.6, abs=0.01)
