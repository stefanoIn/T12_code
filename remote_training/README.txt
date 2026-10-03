REMOTE SEN1FLOODS11 TRAINING CONTROL

EXPECTED LAYOUT
D:\UNI\THESIS\
  .venv\
  Sen1Floods11_FCNN_Baselines_LOCAL_REMOTE.ipynb
  remote_training\
    runner.ps1
    setup_task.ps1
    start_training.ps1
    status_training.ps1
    stop_training.ps1

FIRST-TIME SETUP
1. Copy the remote_training folder into D:\UNI\THESIS\
2. Verify the notebook is exactly:
   D:\UNI\THESIS\Sen1Floods11_FCNN_Baselines_LOCAL_REMOTE.ipynb
3. Run:
   powershell -ExecutionPolicy Bypass -File D:\UNI\THESIS\remote_training\setup_task.ps1

KEEP WINDOWS AWAKE
Run these once, using an elevated PowerShell if required:
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   powercfg /change monitor-timeout-ac 10

START
   powershell -ExecutionPolicy Bypass -File D:\UNI\THESIS\remote_training\start_training.ps1

STATUS
   powershell -ExecutionPolicy Bypass -File D:\UNI\THESIS\remote_training\status_training.ps1

KILL SWITCH
   powershell -ExecutionPolicy Bypass -File D:\UNI\THESIS\remote_training\stop_training.ps1

NOTES
- You can close VS Code, disconnect SSH, and turn off the Mac.
- The Windows PC must remain powered on and awake.
- This task uses the currently logged-in Windows user's interactive token.
  Locking Windows is fine. Do not sign out while training.
- If stopped during an epoch, that in-progress epoch is lost.
  The previous completed epoch's full resume checkpoint remains.
- Starting again executes the notebook again; with RESUME_IF_AVAILABLE=True,
  it resumes from the saved checkpoint.
- The headless run forces the Jupyter kernel named thesis-d-cuda.
