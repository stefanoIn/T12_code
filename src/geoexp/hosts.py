"""Native host service configuration; only explicit host commands mutate services."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

from .storage import atomic_json, read_json

TASK = "GeoExpWorker"


def require_windows() -> None:
    if platform.system() != "Windows":
        raise ValueError("geoexp host execution is supported on Windows only.")


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def powershell(script: str):
    import base64
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], check=True)


def windows_install_script(root: Path, state: Path) -> str:
    args = subprocess.list2cmdline(["-m", "geoexp", "_worker", "--repository", str(root), "--state", str(state)])
    return f"""$ErrorActionPreference = 'Stop'
$action = New-ScheduledTaskAction -Execute {ps_literal(sys.executable)} -Argument {ps_literal(args)} -WorkingDirectory {ps_literal(str(root))}
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
Register-ScheduledTask -TaskName '{TASK}' -Action $action -Principal $principal -Settings $settings -Trigger $trigger -Force | Out-Null
"""


def require_host(root: Path, state: Path):
    require_windows()
    config = state / "host.json"
    if not config.is_file() or read_json(config).get("repository") != str(root.resolve()):
        raise ValueError("Run geoexp host install from this checkout first (also after moving it).")


def install(root: Path, state: Path):
    require_windows()
    state.mkdir(parents=True, exist_ok=True)
    isolated = os.environ.copy()
    isolated.pop("PYTHONPATH", None)
    try:
        subprocess.run([sys.executable, "-c", "import geoexp"], cwd=state,
                       env=isolated, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Install the CLI in this interpreter first: uv tool install --editable .") from exc
    powershell(windows_install_script(root, state))
    atomic_json(state / "host.json", {
        "repository": str(root.resolve()), "python": sys.executable, "system": "Windows"
    })
    activate()


def activate():
    require_windows()
    powershell(f"$ErrorActionPreference='Stop'; Start-ScheduledTask -TaskName '{TASK}'")


def remove_legacy():
    require_windows()
    powershell("""$ErrorActionPreference='Stop'
$task = Get-ScheduledTask -TaskName 'Sen1Floods11-Training' -ErrorAction SilentlyContinue
if ($task) {
    if ($task.State -eq 'Running') { throw 'Stop legacy training before migration.' }
    Unregister-ScheduledTask -TaskName 'Sen1Floods11-Training' -Confirm:$false
}
""")


def legacy_must_be_inactive():
    require_windows()
    powershell("""$task = Get-ScheduledTask -TaskName 'Sen1Floods11-Training' -ErrorAction SilentlyContinue
if ($task -and $task.State -eq 'Running') { throw 'Stop legacy training before migration.' }
""")
