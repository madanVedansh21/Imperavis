"""
desktop_watchdog.py
-------------------
Spawned by Electron alongside the hermes backend.
Watches the Electron parent PID every 2 seconds.
If Electron is gone (hard-kill, crash, Task Manager), kills the
hermes backend process tree immediately.

Args:
  sys.argv[1] = electron_pid   (int)
  sys.argv[2] = backend_pid    (int)
  sys.argv[3] = platform       (win32 or darwin or linux)

Dependency-free for the liveness check: uses psutil if available,
falls back to WinAPI (ctypes) on Windows or os.kill(sig=0) on POSIX.
"""

import sys
import os
import time
import subprocess
import signal
import ctypes

POLL_INTERVAL = 2  # seconds


def is_pid_alive_windows(pid):
    SYNCHRONIZE = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return False
    result = ctypes.windll.kernel32.WaitForSingleObject(handle, 0)
    ctypes.windll.kernel32.CloseHandle(handle)
    return result != 0


def is_pid_alive_posix(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def is_pid_alive(pid, is_windows):
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        if is_windows:
            return is_pid_alive_windows(pid)
        return is_pid_alive_posix(pid)


def kill_tree_windows(pid):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass


def kill_tree_posix(pid):
    try:
        import psutil
        proc = psutil.Process(pid)
        for child in proc.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        proc.kill()
    except ImportError:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


def main():
    if len(sys.argv) < 4:
        sys.exit(1)

    electron_pid = int(sys.argv[1])
    backend_pid = int(sys.argv[2])
    platform = sys.argv[3]
    is_windows = platform == "win32"

    if not is_windows:
        try:
            os.setsid()
        except Exception:
            pass

    while True:
        time.sleep(POLL_INTERVAL)
        if not is_pid_alive(electron_pid, is_windows):
            if is_windows:
                kill_tree_windows(backend_pid)
            else:
                kill_tree_posix(backend_pid)
            sys.exit(0)


if __name__ == "__main__":
    main()
