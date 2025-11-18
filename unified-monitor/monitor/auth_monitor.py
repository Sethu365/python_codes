import time
import platform
import socket
from datetime import datetime

from event import Event
from emitter import EventEmitter


# -------------------------------------------------------------
# PRINT CLEAN OUTPUT (C FORMAT)
# -------------------------------------------------------------
def print_clean(subtype, data):
    parts = [f"AUTH | {subtype}"]
    for key, value in data.items():
        if value is not None:
            parts.append(f"{key}={value}")
    print(" | ".join(parts))


# -------------------------------------------------------------
# EMIT EVENT (silent emitter)
# -------------------------------------------------------------
def emit_event(emitter, subtype, data):
    # Always print clean output
    print_clean(subtype, data)

    # Backend event (emitter is silent)
    event = Event(
        source="auth",
        subtype=subtype,
        ts=datetime.now().timestamp(),
        host=socket.gethostname(),
        os=platform.platform(),
        data=data
    )

    emitter.emit(event)   # silent → no printing


# -------------------------------------------------------------
# EXTRACTORS
# -------------------------------------------------------------
def extract_user(line):
    l = line.lower()

    # SSH login
    if "failed password" in l and " for " in l:
        return l.split("for ")[1].split()[0]
    if "accepted password" in l and " for " in l:
        return l.split("for ")[1].split()[0]

    # SUDO
    if "sudo:" in l:
        try:
            return l.split("sudo:")[1].split(":")[0].strip()
        except:
            return None

    # SU: "root on pts/3"
    if "su[" in l and ") " in l and " on pts" in l:
        try:
            after = l.split("):")[1].strip()
            return after.split()[0]
        except:
            return None

    # SU success
    if "session opened for user" in l:
        try:
            return l.split("session opened for user")[1].split("(")[0].strip()
        except:
            return None

    return None


def extract_target_user(line):
    if "(to " in line:
        try:
            return line.split("(to ")[1].split(")")[0]
        except:
            return None
    return None


def extract_ip(line):
    l = line.lower()
    if " from " in l:
        try:
            return l.split("from ")[1].split()[0]
        except:
            return None
    return None


def extract_tty(line):
    l = line.lower()

    if "tty=" in l:
        return l.split("tty=")[1].split()[0]

    if " on pts/" in l:
        return "pts/" + l.split("pts/")[1].split()[0]

    return None


def extract_command(line):
    if "COMMAND=" in line:
        try:
            return line.split("COMMAND=")[1].split()[0]
        except:
            return None
    return None


# -------------------------------------------------------------
# CLASSIFIER
# -------------------------------------------------------------
def classify(line):
    l = line.lower()

    # SSH
    if "failed password" in l:
        return "ssh_failed_login"
    if "accepted password" in l:
        return "ssh_successful_login"
    if "invalid user" in l:
        return "ssh_invalid_user"

    # SUDO
    if "sudo:" in l and "authentication failure" in l:
        return "sudo_failed_login"
    if "sudo:" in l and "command=" in l:
        return "sudo_success"

    # SU
    if "su[" in l and "(to " in l:
        return "su_switch_user"
    if "su:" in l and "authentication failure" in l:
        return "su_failed_login"
    if "su:" in l and "session opened" in l:
        return "su_success"

    # KEYRING
    if "gkr-pam: unlocked login keyring" in l:
        return "keyring_unlocked"

    # ACCOUNT LOCK/UNLOCK
    if "account locked" in l:
        return "account_locked"
    if "account unlocked" in l:
        return "account_unlocked"

    return "other"


# -------------------------------------------------------------
# ADD REASON IF NEEDED
# -------------------------------------------------------------
def build_extra(subtype, data):
    if subtype in ["ssh_failed_login", "sudo_failed_login", "su_failed_login"]:
        data["reason"] = "wrong_password"
    return data


# -------------------------------------------------------------
# MAIN FILE MONITOR
# -------------------------------------------------------------
def monitor_auth_file(emitter, logfile="/var/log/auth.log"):
    print(f"AUTH | info | monitoring={logfile}")

    with open(logfile, "r") as f:
        f.seek(0, 2)  # go to end

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.2)
                continue

            clean = line.strip()
            subtype = classify(clean)

            # Skip noise
            if subtype == "other":
                continue

            data = {
                "user": extract_user(clean),
                "target": extract_target_user(clean),
                "ip": extract_ip(clean),
                "tty": extract_tty(clean),
                "command": extract_command(clean),
            }

            data = build_extra(subtype, data)
            emit_event(emitter, subtype, data)


# -------------------------------------------------------------
# RUN
# -------------------------------------------------------------
if __name__ == "__main__":
    emitter = EventEmitter(out="silent", output_format="silent")
    monitor_auth_file(emitter)