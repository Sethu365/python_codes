import subprocess
from datetime import datetime
from monitor.emitter import EventEmitter
from monitor.event import Event
import platform
import socket

class AuthMonitor:
    def __init__(self, emitter: EventEmitter):
        self.emitter = emitter
        self.journal_mode = self.detect_journalctl()

    def detect_journalctl(self):
        """Check if journalctl exists on Linux."""
        try:
            subprocess.check_output(["which", "journalctl"])
            return True
        except:
            return False

    def emit_event(self, level, details):
        """Convert to Event object before emitting."""
        event = Event(
            source="auth",
            subtype=level, 
            ts=datetime.now().timestamp(),
            host=socket.gethostname(),
            os=platform.platform(),
            data=details
        )
        self.emitter.emit(event)

    def monitor_journal(self):
        """Listen to live logs through journalctl."""
        process = subprocess.Popen(
            ["journalctl", "-f", "-u", "ssh", "-u", "sshd", "-u", "systemd-logind", "-o", "cat"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                self.emit_event("info", {"log": line})

    def start(self):
        """Start auth monitoring."""
        if platform.system().lower() != "linux":
            self.emit_event("error", {"msg": "Auth monitoring only supported on Linux"})
            return

        self.emit_event("info", {"msg": "Auth monitor started"})

        if self.journal_mode:
            return self.monitor_journal()

        self.emit_event("warning", {"msg": "journalctl not available — cannot monitor auth logs"})


if __name__ == "__main__":
    emitter = EventEmitter(output="table")
    monitor = AuthMonitor(emitter)
    monitor.start()



    #"Who logged in, who logged out, and what login events are happening on your system right now." ->>AUTH MONITOR
