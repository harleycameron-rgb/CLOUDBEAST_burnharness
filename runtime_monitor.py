"""Periodically report the local system's readiness."""

import hashlib
import time

from system_validation import system_heartbeat


def system_health_check():
    """Return the result of the local readiness checks."""
    return system_heartbeat()


def generate_integrity_hash(data):
    """Return the SHA-512 hex digest of a UTF-8 string."""
    return hashlib.sha512(data.encode("utf-8")).hexdigest()


def monitor_system(interval=10):
    print("Starting runtime monitor...")
    while True:
        ready = system_health_check()
        test_hash = generate_integrity_hash("sphere_interior")
        print(f"[{time.strftime('%H:%M:%S')}] System ready: {ready} | Hash: {test_hash[:16]}...")
        time.sleep(interval)


if __name__ == "__main__":
    monitor_system(interval=30)
