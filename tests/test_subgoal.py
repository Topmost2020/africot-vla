"""Subgoal schema, clamping and parsing (SPEC 5.8)."""
from africot import subgoal as sg


def test_default_is_valid_and_unchanged():
    out, notes = sg.validate(sg.DEFAULT_SUBGOAL)
    assert out == sg.DEFAULT_SUBGOAL and notes == []


def test_out_of_range_values_are_clamped():
    bad = {"queue_weights": {"east": 9, "west": 0.0, "south": 1.5}, "pedestrian_weight": -1,
           "max_wait_s": 10, "transit_priority": 7, "valid_for_s": 5000}
    out, notes = sg.validate(bad)
    assert out["queue_weights"] == {"east": 3.0, "west": 0.2, "south": 1.5}
    assert out["pedestrian_weight"] == 0.0 and out["max_wait_s"] == 45
    assert out["transit_priority"] == 2.0 and out["valid_for_s"] == 900
    assert len(notes) == 6


def test_missing_and_garbage_fields_keep_previous():
    prev = dict(sg.DEFAULT_SUBGOAL, max_wait_s=90)
    out, notes = sg.validate({"max_wait_s": "soon", "pedestrian_weight": 2}, previous=prev)
    assert out["max_wait_s"] == 90 and out["pedestrian_weight"] == 2.0
    out, notes = sg.validate("nonsense", previous=prev)
    assert out == prev


def test_parse_response():
    text = ("<reasoning>East queue is long.</reasoning>\n<subgoal>```json\n"
            '{"queue_weights": {"east": 2, "west": 1, "south": 1}, "pedestrian_weight": 1,'
            ' "max_wait_s": 100, "transit_priority": 1, "valid_for_s": 300}\n```</subgoal>')
    r, obj = sg.parse_response(text)
    assert r == "East queue is long." and obj["queue_weights"]["east"] == 2
    assert sg.parse_response("no tags here")[1] is None
    assert sg.parse_response("<subgoal>{broken</subgoal>")[1] is None


def test_schedule_covers_the_day():
    for t in (0, 1800, 3900, 20000, 80000):
        g, notes = sg.validate(sg.scheduled_subgoal(t))
        assert notes == []
