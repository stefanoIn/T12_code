param()

$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\UNI\THESIS"
$Notebook = Join-Path $ProjectRoot "datasets\Sen1Floods11_FCNN_Baselines_PW.ipynb"
$Venv = Join-Path $ProjectRoot ".venv"
$NbConvert = Join-Path $Venv "Scripts\jupyter-nbconvert.exe"

$ControlDir = Join-Path $ProjectRoot "remote_training"
$RunRoot = Join-Path $ProjectRoot "Sen1Floods11_runs"
$HeadlessDir = Join-Path $RunRoot "headless"
$LogDir = Join-Path $HeadlessDir "logs"
$ExecutedDir = Join-Path $HeadlessDir "executed"

$PidFile = Join-Path $ControlDir "training.pid"
$StateFile = Join-Path $ControlDir "training_state.json"

New-Item -ItemType Directory -Force -Path $ControlDir, $LogDir, $ExecutedDir | Out-Null

if (-not (Test-Path $Notebook)) {
    throw "Notebook not found: $Notebook"
}
if (-not (Test-Path $NbConvert)) {
    throw "jupyter-nbconvert.exe not found: $NbConvert. Install with: D:\UNI\THESIS\.venv\Scripts\python.exe -m pip install nbconvert"
}

if (Test-Path $PidFile) {
    $oldPidText = (Get-Content $PidFile -Raw).Trim()
    if ($oldPidText -match '^\d+$') {
        $oldProc = Get-Process -Id ([int]$oldPidText) -ErrorAction SilentlyContinue
        if ($oldProc) {
            throw "Training already appears to be running with PID $oldPidText"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutLog = Join-Path $LogDir "training_$stamp.out.log"
$stderrLog = Join-Path $LogDir "training_$stamp.err.log"
$executedName = "Sen1Floods11_executed_$stamp.ipynb"

$args = @(
    "--to", "notebook",
    "--execute", $Notebook,
    "--output", $executedName,
    "--output-dir", $ExecutedDir,
    "--ExecutePreprocessor.kernel_name=thesis-d-cuda",
    "--ExecutePreprocessor.timeout=-1"
)

$state = [ordered]@{
    status = "starting"
    started_at = (Get-Date).ToString("o")
    notebook = $Notebook
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
    executed_notebook = (Join-Path $ExecutedDir $executedName)
    child_pid = $null
    exit_code = $null
    finished_at = $null
}
$state | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8

$proc = Start-Process `
    -FilePath $NbConvert `
    -ArgumentList $args `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

$proc.Id | Set-Content $PidFile -Encoding ASCII

$state.status = "running"
$state.child_pid = $proc.Id
$state | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8

try {
    $proc.WaitForExit()
    $state.exit_code = $proc.ExitCode
    if ($proc.ExitCode -eq 0) {
        $state.status = "completed"
    } else {
        $state.status = "failed"
    }
}
finally {
    $state.finished_at = (Get-Date).ToString("o")
    $state | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
