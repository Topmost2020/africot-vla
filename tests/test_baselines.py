"""S2: baseline controller logic and metric extraction."""
from africot.baselines import CountTimer, FixedTime, MaxPressure, served_queue
from africot.metrics import parse_tripinfo


def _obs(phase="A", t_in=10, mq=None):
    mq = mq or {"WE": 0, "WS": 0, "EW": 0, "ES": 0, "SE": 0, "SW": 0}
    return {"phase": phase, "time_in_phase": t_in, "movement_queues": mq}


def test_fixed_time_cycle():
    f = FixedTime()
    assert f.first() == ("A", 35)
    assert f.decide(_obs("A")) == ("B", 12)
    assert f.decide(_obs("B")) == ("C", 25)
    assert f.decide(_obs("C")) == ("A", 35)


def test_count_timer_extends_and_caps():
    c = CountTimer()
    busy = {"WE": 3, "WS": 0, "EW": 0, "ES": 0, "SE": 0, "SW": 0}
    assert c.first() == ("A", 10)
    assert c.decide(_obs("A", 10, busy)) == ("A", 5)
    assert c.decide(_obs("A", 55, busy)) == ("A", 5)  # reaches 60
    assert c.decide(_obs("A", 60, busy)) == ("B", 10)  # capped
    quiet = dict(busy, WE=2)
    assert c.decide(_obs("A", 10, quiet)) == ("B", 10)
    assert c.decide(_obs("C", 10, quiet)) == ("A", 10)


def test_max_pressure_picks_largest_served_queue():
    m = MaxPressure()
    mq = {"WE": 2, "WS": 1, "EW": 1, "ES": 6, "SE": 1, "SW": 1}
    assert served_queue(_obs(mq=mq), "B") == 7
    assert m.decide(_obs("A", 15, mq)) == ("B", 15)
    mq = {"WE": 0, "WS": 0, "EW": 0, "ES": 0, "SE": 5, "SW": 4}
    assert m.decide(_obs("A", 15, mq)) == ("C", 15)
    # ties keep the current phase
    zero = {k: 0 for k in mq}
    assert m.decide(_obs("B", 15, zero)) == ("B", 15)


def test_tripinfo_excludes_warmup_and_counts_insertion_delay(tmp_path):
    p = tmp_path / "t.xml"
    p.write_text("""<tripinfos>
<tripinfo id="Wa" depart="100" departDelay="0" arrival="200" duration="100" waitingTime="50" vType="car"/>
<tripinfo id="Wb" depart="400" departDelay="0" arrival="460" duration="60" waitingTime="20" vType="car"/>
<tripinfo id="Sc" depart="520" departDelay="20" arrival="600" duration="80" waitingTime="40" vType="okada"/>
<tripinfo id="Sd" depart="3800" departDelay="0" arrival="-1" duration="100" waitingTime="40" vType="car"/>
<tripinfo id="Se" depart="400" departDelay="150" arrival="500" duration="100" waitingTime="0" vType="car"/>
<personinfo id="p" depart="350"><walk depart="350" arrival="400" waitingTime="12"/></personinfo>
<personinfo id="q" depart="100"><walk depart="100" arrival="150" waitingTime="99"/></personinfo>
</tripinfos>""")
    r = tmp_path / "r.xml"
    r.write_text("""<routes>
<vehicle id="Wa" type="car" depart="100"/><vehicle id="Wb" type="car" depart="400"/>
<vehicle id="Sc" type="okada" depart="500"/><vehicle id="Sd" type="car" depart="3800"/>
<vehicle id="Se" type="car" depart="250"/><vehicle id="Sf" type="car" depart="3700"/>
</routes>""")
    m = parse_tripinfo(p, route_file=r)
    # Se was scheduled at 250 s (warm-up) so it is excluded although it departed at 400 s.
    # measured: Wb (60, 20), Sc (20+80, 20+40), Sd unfinished (100, 40), Sf never inserted (200, 200)
    assert m["vehicles_measured"] == 4
    assert m["att"] == (60 + 100 + 100 + 200) / 4
    assert m["awt"] == (20 + 60 + 40 + 200) / 4
    assert m["att_completed"] == 70 and m["awt_completed"] == 30
    assert m["not_inserted"] == 1 and m["not_inserted_by_arm"] == {"south": 1}
    assert m["unfinished"] == 1
    assert m["throughput"] == 3  # Wb, Sc, Se arrived after the warm-up
    assert m["ped_wait"] == 12 and m["ped_count"] == 1
