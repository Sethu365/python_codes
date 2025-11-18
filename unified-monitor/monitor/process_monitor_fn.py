# process_monitor_fn.py

import subprocess
import time
import platform
import socket
from datetime import datetime

from monitor.emitter import EventEmitter
from monitor.event import Event


def emit_event(emitter: EventEmitter, source: str, subtype: str, data: dict):
    """
    Small helper: wrap data into Event and send via emitter.
    We will reuse this pattern for all monitors.
    """
    event = Event(
        source=source,                  # e.g. "process"
        subtype=subtype,                # e.g. "start", "end", "info", "error"
        ts=datetime.now().timestamp(),  # Unix timestamp (float)
        host=socket.gethostname(),      # machine name
        os=platform.platform(),         # OS description
        data=data,                      # any additional fields
    )
    emitter.emit(event)


def get_process_snapshot() -> dict:
    """
    Run 'ps -eo pid,comm' and return a dict: {pid: name}.
    This is one snapshot of all running processes at the moment.
    """
    # Run Linux 'ps' command to list all processes with PID and command name
    out = subprocess.check_output(["ps", "-eo", "pid,comm"], text=True)

    # Split into lines, skip the header ("PID COMMAND")
    lines = out.strip().splitlines()
    if not lines:
        return {}

    lines = lines[1:]  # remove header line

    snapshot = {}

    for line in lines:
        # Split into: PID, NAME
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue

        pid_str, name = parts
        try:
            pid = int(pid_str)
        except ValueError:
            continue

        snapshot[pid] = name

    return snapshot


def monitor_processes(emitter: EventEmitter, interval: int = 3):
    """
    Light-weight process monitor using only the 'ps' Linux command.

    Every `interval` seconds:
      - Get current process list
      - Compare with previous list
      - Emit:
          source='process', subtype='start'  -> when a new PID appears
          source='process', subtype='end'    -> when a PID disappears
    """
    # Only support Linux for now
    if platform.system().lower() != "linux":
        emit_event(emitter, "process", "error", {"msg": "Process monitor only supports Linux"})
        return

    emit_event(emitter, "process", "info", {"msg": "Process monitor started"})

    prev = {}  # previous snapshot: {pid: name}

    while True:
        curr = get_process_snapshot()          # current snapshot
        prev_pids = set(prev.keys())
        curr_pids = set(curr.keys())

        # 1) New processes = present now, but not before
        for pid in curr_pids - prev_pids:
            emit_event(
                emitter,
                "process",
                "start",
                {"pid": pid, "name": curr[pid]},
            )

        # 2) Ended processes = present before, but not now
        for pid in prev_pids - curr_pids:
            emit_event(
                emitter,
                "process",
                "end",
                {"pid": pid, "name": prev[pid]},
            )

        # Update for next loop
        prev = curr

        # Sleep a bit before checking again
        time.sleep(interval)


if __name__ == "__main__":
    # Adjust args depending on how your EventEmitter is defined in your project.
    # In your unified runner you used something like:
    #   EventEmitter(out="stdout", output_format="table")
    # Here I keep a simple version; change if needed.
    emitter = EventEmitter(out="stdout", output_format="table")
    monitor_processes(emitter, interval=3)