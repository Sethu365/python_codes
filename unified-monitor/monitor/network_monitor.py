import subprocess
import time
import platform
import socket
from datetime import datetime
from event import Event
from emitter import EventEmitter


# ------------------------------
# EVENT SENDER
# ------------------------------
def emit_event(emitter, subtype, data):
    event = Event(
        source="network",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data,
    )
    emitter.emit(event)


# ------------------------------
# PARSE A SINGLE ss LINE
# ------------------------------
def parse_ss_line(line):
    """
    Parse one line from: ss -tunH
    Format is stable:
    tcp ESTAB 0 0 127.0.0.1:43210 142.250.77.46:443
    """

    parts = line.split()

    # Should be >= 6 parts at minimum
    if len(parts) < 6:
        return None

    proto = parts[0].lower()
    state = parts[1].lower()

    # local = second last column
    # remote = last column
    local = parts[-2]
    remote = parts[-1]

    return proto, state, local, remote


# ------------------------------
# GET ALL ACTIVE CONNECTIONS
# ------------------------------
def get_connections():
    # -H removes the header → stable format
    out = subprocess.check_output(["ss", "-tunH"], text=True)
    lines = out.strip().splitlines()

    conns = set()

    for line in lines:
        parsed = parse_ss_line(line)
        if not parsed:
            continue

        proto, state, local, remote = parsed

        # Only established connections
        if "estab" not in state:
            continue

        conns.add(f"{proto}:{local}->{remote}")

    return conns


# ------------------------------
# MAIN MONITOR LOOP
# ------------------------------
def monitor_network(emitter, interval=3):
    if platform.system().lower() != "linux":
        emit_event(emitter, "error", {"msg": "Network monitor works only on Linux"})
        return

    emit_event(emitter, "info", {"msg": "Network monitor started"})

    prev = set()

    while True:
        curr = get_connections()

        # Detect new connections
        new = curr - prev
        for c in new:
            emit_event(emitter, "connection_new", {"connection": c})

        # Detect closed/old connections
        old = prev - curr
        for c in old:
            emit_event(emitter, "connection_old", {"connection": c})

        prev = curr
        time.sleep(interval)


# ------------------------------
# RUN DIRECTLY
# ------------------------------
if __name__ == "__main__":
    emitter = EventEmitter(out="stdout", output_format="table")
    monitor_network(emitter)
