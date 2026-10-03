param()

$ErrorActionPreference = "Continue"

$TaskName = "Sen1Floods11-Training"
$ControlDir = "D:\UNI\THESIS\remote_training"
$PidFile = Join-Path $ControlDir "training.pid"

Write-Host "Stopping Sen1Floods11 training..."

if (Test-Path $PidFile) {
    $pidText = (Get-Content $PidFile -Raw).Trim()

    if ($pidText -match '^\d+$') {
        $trainingPid = [int]$pidText
        $p = Get-Process -Id $trainingPid -ErrorAction SilentlyContinue
        if ($p) {
            Write-Host "Killing training process tree rooted at PID $trainingPid ..."
            & taskkill.exe /PID $trainingPid /T /F
        } else {
            Write-Host "PID file exists, but PID $trainingPid is no longer running."
        }
    }
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "Task state:" $task.State
}

Write-Host ""
Write-Host "Kill switch complete."
Write-Host "The last fully completed epoch checkpoint remains on disk."
Write-Host "Starting again resumes from that checkpoint because RESUME_IF_AVAILABLE=True."
