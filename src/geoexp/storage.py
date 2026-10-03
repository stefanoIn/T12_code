from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import platform
import socket
import time
import uuid
from pathlib import Path

import psutil

TERMINAL = {"completed", "failed", "stopped"}
TRANSITIONS = {"queued": {"starting", "failed", "stopped"},
               "starting": {"running", "failed", "stopped"},
               "running": TERMINAL}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_id() -> str:
    host = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:8]
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + host + "-" + uuid.uuid4().hex[:8]


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_directory() -> Path:
    # Override is useful for isolated development/tests. Services inherit an explicit path.
    if os.environ.get("GEOEXP_STATE_DIR"):
        return Path(os.environ["GEOEXP_STATE_DIR"]).expanduser().resolve()
    if platform.system() == "Windows":
        return Path(os.environ["LOCALAPPDATA"]) / "GeoExp"
    return Path.home() / "Library" / "Application Support" / "GeoExp"


@contextlib.contextmanager
def lock(path: Path, timeout: float = 10):
    """OS locks release on crash; no stale sentinel can block the host permanently."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Another geoexp operation holds {path.name}")
                time.sleep(0.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def identity(pid: int) -> dict:
    return {"pid": pid, "create_time": psutil.Process(pid).create_time()}


def matching_process(record: dict | None):
    if not record:
        return None
    try:
        process = psutil.Process(record["pid"])
        if abs(process.create_time() - record["create_time"]) < 0.001 and process.status() != psutil.STATUS_ZOMBIE:
            return process
    except (psutil.NoSuchProcess, KeyError):
        pass
    return None


def terminate_tree(record: dict | None) -> None:
    parent = matching_process(record)
    if parent is None:
        return
    # Suspend parents first so descendants cannot keep spawning during enumeration.
    suspended = []
    try:
        parent.suspend()
        suspended.append(parent)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.suspend()
                suspended.append(child)
            except psutil.NoSuchProcess:
                pass
        for process in reversed(suspended):
            try:
                process.kill()  # psutil also guards against PID reuse.
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(suspended, timeout=5)
        if alive:
            raise RuntimeError("Some job processes could not be stopped; host remains reserved")
    finally:
        for process in suspended:
            try:
                process.resume()
            except psutil.NoSuchProcess:
                pass


def transition(run: Path, state: str, **fields) -> dict:
    previous = read_json(run / "status.json")
    if state != previous["state"] and state not in TRANSITIONS.get(previous["state"], set()):
        raise ValueError(f"Invalid transition {previous['state']} -> {state}")
    previous.update(fields, state=state, updated_at=utc_now())
    if state in TERMINAL:
        previous["finished_at"] = utc_now()
    atomic_json(run / "status.json", previous)
    return previous
