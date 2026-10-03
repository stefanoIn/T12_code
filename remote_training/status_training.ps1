param()

$ErrorActionPreference = "SilentlyContinue"

$TaskName = "Sen1Floods11-Training"
$ProjectRoot = "D:\UNI\THESIS"
$ControlDir = Join-Path $ProjectRoot "remote_training"
$PidFile = Join-Path $ControlDir "training.pid"
$StateFile = Join-Path $ControlDir "training_state.json"

Write-Host "=== TASK ==="
$task = Get-ScheduledTask -TaskName $TaskName
if ($task) {
    Write-Host "State:" $task.State
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "Last run:" $info.LastRunTime
    Write-Host "Last task result:" $info.LastTaskResult
} else {
    Write-Host "Task not registered."
}

Write-Host ""
Write-Host "=== PROCESS ==="
if (Test-Path $PidFile) {
    $pidText = (Get-Content $PidFile -Raw).Trim()
    Write-Host "PID file:" $pidText
    if ($pidText -match '^\d+$') {
        $p = Get-Process -Id ([int]$pidText)
        if ($p) {
            Write-Host "Process:" $p.ProcessName
            Write-Host "Started:" $p.StartTime
            Write-Host "CPU seconds:" ([math]::Round($p.CPU, 1))
        } else {
            Write-Host "PID is not currently alive."
        }
    }
} else {
    Write-Host "No training.pid file."
}

if (Test-Path $StateFile) {
    Write-Host ""
    Write-Host "=== RUN STATE ==="
    Get-Content $StateFile -Raw
}

Write-Host ""
Write-Host "=== LATEST TRAINING HISTORY ==="

$history = Get-ChildItem `
    -Path (Join-Path $ProjectRoot "Sen1Floods11_runs\results") `
    -Filter "training_history.json" `
    -Recurse `
    -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($history) {
    Write-Host "History file:" $history.FullName
    Write-Host "Updated:" $history.LastWriteTime
    try {
        $data = Get-Content $history.FullName -Raw | ConvertFrom-Json
        if ($data.Count -gt 0) {
            $last = $data[-1]
            Write-Host "Latest completed epoch:" $last.epoch
            Write-Host "Training loss:" $last.training_loss
            Write-Host "Training IoU:" $last.training_iou
            Write-Host "Validation loss:" $last.validation_loss
            Write-Host "Validation IoU:" $last.validation_iou
            Write-Host "Validation accuracy:" $last.validation_accuracy
        }
    } catch {
        Write-Host "Could not parse training_history.json yet."
    }
} else {
    Write-Host "No training_history.json found yet."
}

Write-Host ""
Write-Host "=== GPU ==="
& nvidia-smi
