# How to Run the Rutgers Index Course Sniper

## Quick Start

1. **Open PowerShell** (or Command Prompt)

2. **Navigate to the project directory:**
   ```powershell
   cd C:\Users\zaidt\RutgersSniper\rutgers_index_sniper
   ```

3. **Activate the virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   (If you get an execution policy error, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

4. **Run the application:**
   ```powershell
   python -m src.main
   ```

## To Stop the Application

Press `Ctrl+C` in the terminal where it's running.

## Alternative: Run Without Activating Virtual Environment

You can also run it directly without activating:
```powershell
cd C:\Users\zaidt\RutgersSniper\rutgers_index_sniper
.\venv\Scripts\python.exe -m src.main
```

## What You'll See

- Startup information showing which indexes are being watched
- Poll timestamps every 15 seconds
- Status updates showing how many watched indexes are open
- Alert messages when an index opens (with Discord notification)

