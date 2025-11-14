from .base import BaseMonitor
import os, time
from typing import List

# Linux inotify backend
try:
    from inotify_simple import INotify, flags
except Exception:
    INotify = None
    flags = None

# Cross-platform watchdog backend
try:
    from watchdog.observers import Observer as WatchdogObserver
    from watchdog.events import FileSystemEventHandler as WatchdogHandler
except Exception:
    WatchdogObserver = None
    WatchdogHandler = None


class FSMonitor(BaseMonitor):
    def __init__(self, emitter, paths: List[str], enable_integrity: bool = True, poll_interval: float = 1.0):
        super().__init__("fs", emitter, poll_interval)

        # FIX 1: expand "~" correctly
        self.paths = [os.path.expanduser(p) for p in paths]

        # FIX 2: keep only existing directories
        self.paths = [p for p in self.paths if os.path.isdir(p)]

        if not self.paths:
            emitter.emit("warning", {"msg": "No valid directories to watch"})

        self.enable_integrity = enable_integrity

    # ---------------- MAIN MONITOR ---------------------

    def monitor(self):
        if INotify is not None:
            self._monitor_inotify()
        elif WatchdogObserver is not None:
            self._monitor_watchdog()
        else:
            self.emit("warning", {"msg": "No FS backend available"})

    # ---------------- LINUX INOTIFY BACKEND ---------------------

    def _monitor_inotify(self):
        inotify = INotify()
        watches = {}

        mask = (
            flags.CREATE |
            flags.MODIFY |
            flags.DELETE |
            flags.MOVED_FROM |
            flags.MOVED_TO
        )

        # Add watches
        for p in self.paths:
            try:
                wd = inotify.add_watch(p, mask)
                watches[wd] = p
                self.emit("info", {"msg": f"📁 Watching (inotify): {p}"})
            except Exception as e:
                self.emit("warning", {"path": p, "err": str(e)})

        while not self.stopped():
            events = inotify.read(timeout=int(self.poll_interval * 1000))

            for e in events:
                base = watches.get(e.wd, "?")
                name = (
                    e.name.decode("utf-8", errors="ignore")
                    if isinstance(e.name, (bytes, bytearray))
                    else e.name
                )
                path = os.path.join(base, name) if name else base

                # determine event type
                if e.mask & flags.CREATE:
                    subtype = "create"
                elif e.mask & flags.MODIFY:
                    subtype = "modify"
                elif e.mask & flags.DELETE:
                    subtype = "delete"
                else:
                    subtype = "move"

                self.emit(subtype, {"path": path})

    # ---------------- WATCHDOG BACKEND ---------------------

    def _monitor_watchdog(self):
        class Handler(WatchdogHandler):
            def __init__(self, outer):
                self.outer = outer
                super().__init__()

            def on_created(self, event):
                if not event.is_directory:
                    self.outer.emit("create", {"path": event.src_path})

            def on_modified(self, event):
                if not event.is_directory:
                    self.outer.emit("modify", {"path": event.src_path})

            def on_moved(self, event):
                self.outer.emit("move", {"src": event.src_path, "dst": event.dest_path})

            def on_deleted(self, event):
                self.outer.emit("delete", {"path": event.src_path})

        obs = WatchdogObserver()
        handler = Handler(self)

        # Add directory watchers
        for p in self.paths:
            try:
                obs.schedule(handler, p, recursive=True)
                self.emit("info", {"msg": f"📁 Watching (watchdog): {p}"})
            except Exception as e:
                self.emit("warning", {"path": p, "err": str(e)})

        obs.start()

        try:
            while not self.stopped():
                time.sleep(self.poll_interval)
        finally:
            obs.stop()
            obs.join()



# ✅ 2. File System Monitor (2 lines)
# Watches the file system for any create, delete, modify, or move events.
# Useful for detecting unauthorized file changes or malware activity.