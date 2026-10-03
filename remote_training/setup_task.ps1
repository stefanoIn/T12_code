param()

$ErrorActionPreference = "Stop"

$TaskName = "Sen1Floods11-Training"
$ProjectRoot = "D:\UNI\THESIS"
$ControlDir = Join-Path $ProjectRoot "remote_training"
$Runner = Join-Path $ControlDir "runner.ps1"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Runner)) {
    throw "runner.ps1 not found at $Runner"
}
if (-not (Test-Path $Python)) {
    throw "Python environment not found at $Python"
}

Write-Host "Installing/updating nbconvert in the CUDA venv..."
& $Python -m pip install nbconvert
if ($LASTEXITCODE -ne 0) {
    throw "nbconvert installation failed."
}

Write-Host "Verifying CUDA from the exact Python environment..."
& $Python -c "import torch; print('Torch:', torch.__version__); print('CUDA:', torch.version.cuda); print('Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
if ($LASTEXITCODE -ne 0) {
    throw "CUDA verification failed."
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""

$UserId = "$env:USERDOMAIN\$env:USERNAME"
$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Runs the Sen1Floods11 training notebook independently of the SSH/VS Code session." `
    -Force | Out-Null

Write-Host ""
Write-Host "Registered task: $TaskName"
Write-Host "Start:"
Write-Host "  powershell -File D:\UNI\THESIS\remote_training\start_training.ps1"
Write-Host "Status:"
Write-Host "  powershell -File D:\UNI\THESIS\remote_training\status_training.ps1"
Write-Host "Stop:"
Write-Host "  powershell -File D:\UNI\THESIS\remote_training\stop_training.ps1"
