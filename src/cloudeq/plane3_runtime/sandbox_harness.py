"""Trusted harness copied to the remote sandbox; never used to run host tests."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if sys.platform != "linux" or not os.path.isdir("/tmp/forge-task"):
        raise RuntimeError("This harness runs only inside a prepared Linux sandbox.")
    # Render's base image launches exec sessions as root. The trusted launcher
    # drops that identity before loading any task file or starting pytest.
    import ctypes
    import resource

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise RuntimeError("Could not disable privilege escalation for generated tests.")
    if os.geteuid() == 0:
        # SDK uploads can arrive with owner-only modes. Allow the test identity
        # to read/traverse the immutable task tree, without granting writes.
        task = Path("/tmp/forge-task")
        for entry in task.rglob("*"):
            if entry.is_symlink():
                raise RuntimeError("Uploaded task unexpectedly contains a symlink.")
            entry.chmod(0o555 if entry.is_dir() else 0o444)
        task.chmod(0o555)
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)
    if os.geteuid() == 0:
        raise RuntimeError("Generated tests must run as a non-root sandbox user.")

    seconds, pids, memory = (int(value) for value in sys.argv[1:4])
    if not (1 <= seconds <= 600 and 1 <= pids <= 256 and memory > 0):
        raise ValueError("Invalid execution limits.")
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_NPROC, (pids, pids))
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest"],
            cwd="/tmp/forge-task",
            env={
                "PATH": "/tmp/forge-venv/bin:/usr/bin:/bin",
                "HOME": "/tmp",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_ADDOPTS": "-p no:cacheprovider",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
            timeout=seconds,
            check=False,
            start_new_session=True,
        )
        return completed.returncode
    except subprocess.TimeoutExpired:
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
