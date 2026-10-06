"""S0 smoke test: build a tiny network and drive it through TraCI headless."""
import subprocess

import traci

from africot.sumo_utils import sumo_binary


def test_tiny_sim_through_traci(tmp_path):
    net = tmp_path / "tiny.net.xml"
    subprocess.run([sumo_binary("netgenerate"), "--grid", "--grid.number", "2",
                    "--grid.length", "100", "-o", str(net)], check=True,
                   capture_output=True)
    routes = tmp_path / "tiny.rou.xml"
    routes.write_text(
        '<routes><vType id="t"/>'
        '<flow id="f" type="t" begin="0" end="50" period="5" from="A0B0" to="B0B1"/>'
        '</routes>')
    traci.start([sumo_binary("sumo"), "-n", str(net), "-r", str(routes),
                 "--no-step-log", "--no-warnings"], label="smoke")
    conn = traci.getConnection("smoke")
    try:
        seen = set()
        for _ in range(60):
            conn.simulationStep()
            seen.update(conn.vehicle.getIDList())
        assert conn.simulation.getTime() == 60
        assert len(seen) > 0
    finally:
        conn.close()
