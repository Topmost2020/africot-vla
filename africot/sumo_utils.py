"""Locate the pip-installed SUMO binaries and set SUMO_HOME."""
import os
import shutil


def sumo_home():
    if os.environ.get("SUMO_HOME") and os.path.isdir(os.environ["SUMO_HOME"]):
        return os.environ["SUMO_HOME"]
    import sumo
    os.environ["SUMO_HOME"] = sumo.SUMO_HOME
    return sumo.SUMO_HOME


def sumo_binary(name="sumo"):
    """Absolute path of a SUMO tool (sumo, netconvert, ...). Never sumo-gui."""
    path = os.path.join(sumo_home(), "bin", name)
    if os.path.exists(path):
        return path
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"SUMO binary {name!r} not found")
