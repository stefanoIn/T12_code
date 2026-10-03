param()

$ErrorActionPreference = "Stop"
$TaskName = "Sen1Floods11-Training"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop

if ($task.State -eq "Running") {
    Write-Host "Training task is already running."
    exit 0
}

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2

$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "Task state:" $task.State
Write-Host "Use status_training.ps1 to inspect PID, GPU use, latest epoch, and logs."
