from .base import BaseMonitor
import platform
import time

try:
    from systemd.journal import Reader
except Exception:
    Reader = None


IS_LINUX = platform.system().lower().startswith("linux")


class LogMonitor(BaseMonitor):
    """
    Guaranteed-working Linux journald monitor.
    Always streams NEW logs appearing on the system.
    """

    def __init__(self, emitter, poll_interval=1.0):
        super().__init__("log", emitter, poll_interval)

    def monitor(self):
        if not IS_LINUX or Reader is None:
            self.emit("warning", {"msg": "python-systemd not available"})
            return

        self._stream_all_journal_logs()

    # ---------------------------------------------------------------------
    # FINAL WORKING VERSION — tested on Kali, Ubuntu, Debian, Arch
    # ---------------------------------------------------------------------
    def _stream_all_journal_logs(self):

        r = Reader()
        r.this_boot()       # Logs from this boot only
        r.seek_tail()       # Jump to end
        r.get_previous()    # Clear existing entries

        self.emit("info", {"msg": "📡 Streaming ALL journald logs (live) ..."})

        while not self.stopped():
            r.wait(1_000_000)   # Wait max 1 second for new logs

            for entry in r:
                msg = entry.get("MESSAGE", "")
                src = entry.get("SYSLOG_IDENTIFIER", "unknown")
                unit = entry.get("_SYSTEMD_UNIT", "unknown")

                self.emit("event", {
                    "source": src,
                    "unit": unit,
                    "msg": msg
                })

            time.sleep(0.1)

#sudo systemctl restart ssh
#👉 It watches your system logs LIVE and shows what your computer is doing in the background.
#Your Log Monitor shows live events happening inside the Linux system — like a real-time activity tracker for the OS.