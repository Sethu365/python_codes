from .base import BaseMonitor
import platform
import os
import time

try:
    import wmi   # Windows registry backend
except Exception:
    wmi = None

# Detect OS
IS_WINDOWS = platform.system().lower().startswith("win")
IS_LINUX = platform.system().lower().startswith("linux")


class RegistryMonitor(BaseMonitor):
    """
    Windows → monitors Registry
    Linux   → monitors system config folders (/etc, ~/.config)
    """

    def __init__(self, emitter, keys=None, poll_interval=2.0):
        super().__init__("registry", emitter, poll_interval)

        # Windows registry keys
        self.keys = keys or [
            r"HKEY_LOCAL_MACHINE\\SOFTWARE",
            r"HKEY_CURRENT_USER\\SOFTWARE"
        ]

        # Linux config folders
        self.linux_paths = [
            "/etc",
            os.path.expanduser("~/.config")
        ]

    # ------------------------------------------------------------------
    # MAIN DISPATCHER
    # ------------------------------------------------------------------
    def monitor(self):
        if IS_WINDOWS:
            self._monitor_windows_registry()
        elif IS_LINUX:
            self._monitor_linux_config()
        else:
            self.emit("warning", {"msg": "Unsupported OS"})

    # ------------------------------------------------------------------
    # WINDOWS REGISTRY MONITORING
    # ------------------------------------------------------------------
    def _monitor_windows_registry(self):
        if wmi is None:
            self.emit("error", {"msg": "WMI not installed. Install pywin32/wmi"})
            return

        self.emit("info", {"msg": "Windows Registry Monitoring started"})

        c = wmi.WMI()
        watcher = c.watch_for(
            notification_type='Creation',
            wmi_class='RegistryValueChangeEvent'
        )

        while not self.stopped():
            try:
                evt = watcher(timeout_ms=int(self.poll_interval * 1000))
                if not evt:
                    continue

                hive = getattr(evt, 'Hive', '')
                key = getattr(evt, 'KeyPath', '')
                value = getattr(evt, 'ValueName', '')

                self.emit("change", {
                    "hive": hive,
                    "key": key,
                    "value": value
                })

            except Exception as e:
                self.emit("error", {"stage": "windows_registry", "err": str(e)})
                time.sleep(self.poll_interval)

    # ------------------------------------------------------------------
    # LINUX CONFIG MONITORING
    # ------------------------------------------------------------------
    def _monitor_linux_config(self):
        """
        Linux alternative for registry monitoring:
        Watches /etc and ~/.config for modifications using mtime checking.
        """
        self.emit("info", {"msg": "Linux Config Monitoring started"})

        last_mtime = {}

        # Initialize timestamps
        for path in self.linux_paths:
            if os.path.exists(path):
                last_mtime[path] = os.path.getmtime(path)

        while not self.stopped():
            try:
                for path in self.linux_paths:
                    if not os.path.exists(path):
                        continue

                    current_m = os.path.getmtime(path)

                    # If changed → emit event
                    if path in last_mtime and current_m != last_mtime[path]:
                        self.emit("change", {
                            "file": path,
                            "msg": "Configuration directory changed"
                        })

                    last_mtime[path] = current_m

                time.sleep(self.poll_interval)

            except Exception as e:
                self.emit("error", {"stage": "linux_config", "err": str(e)})
                time.sleep(self.poll_interval)
