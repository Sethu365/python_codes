import time
import platform

from monitor.emitter import EventEmitter
from monitor.process_monitor import ProcessMonitor
from monitor.network_monitor import NetworkMonitor
from monitor.fs_monitor import FSMonitor
from monitor.registry_monitor import RegistryMonitor
from monitor.log_monitor import LogMonitor
from monitor.module_monitor import ModuleMonitor
from monitor.auth_monitor import AuthMonitor


def os_name():
    return platform.system().lower()


def main():
    print("\n===== Unified Monitor Menu =====")
    print("1 - Process Monitor")
    print("2 - File System Monitor")
    print("3 - Network Monitor")
    print("4 - Module Monitor")
    print("5 - Auth Monitor")
    print("6 - Log Monitor")
    print("7 - Registry / Config Monitor")
    print("8 - Run ALL Monitors")
    print("=======================================")

    choice = input("Enter choice (1-8 or 1,3,6): ").strip().split(",")
    choice = [c.strip() for c in choice]

    emitter = EventEmitter(out="stdout", output_format="table")
    print(f"\n[Emitter] Output: table, Target: stdout\n")

    monitor_map = {
        "1": lambda e: ProcessMonitor(e),
        "2": lambda e: FSMonitor(e, paths=["~"]),
        "3": lambda e: NetworkMonitor(e),
        "4": lambda e: ModuleMonitor(e),
        "5": lambda e: AuthMonitor(e),
        "6": lambda e: LogMonitor(e),
        "7": lambda e: RegistryMonitor(e),
    }

    monitors = []

    # Handle ALL
    if "8" in choice:
        monitors = [
            ProcessMonitor(emitter),
            FSMonitor(emitter, paths=["~"]),
            NetworkMonitor(emitter),
            ModuleMonitor(emitter),
            AuthMonitor(emitter),
            LogMonitor(emitter),
            RegistryMonitor(emitter),
        ]
    else:
        for c in choice:
            if c in monitor_map:
                try:
                    monitors.append(monitor_map[c](emitter))
                except Exception as ex:
                    print(f"[!] Failed to init monitor {c}: {ex}")

    if not monitors:
        print("[!] No valid monitors loaded. Exiting.")
        return

    print("\n[+] Starting active monitoring... Press CTRL+C to stop.\n")

    for mon in monitors:
        try:
            mon.start()
        except Exception as e:
            print(f"Error starting {type(mon).__name__}: {e}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping monitors...")
        for mon in monitors:
            try:
                mon.stop()
                mon.join()
            except:
                continue
        emitter.close()
        print("[✓] Shutdown complete.")


if __name__ == "__main__":
    main()


#sudo -E .venv/bin/python3 run_monitor.py
