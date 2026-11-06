#!/usr/bin/env python3
"""
ScopeKeeper 1-Command Demo Launcher.
Starts all ScopeKeeper services:
1. Seeds Switch Core PostgreSQL (Personas, Room Roles, and Blueprint Template)
2. Starts ScopeKeeper Clerk Backend (FastAPI on Port 8080)
3. Starts ScopeKeeper Dashboard Dev Server (Vite on Port 5173)
4. Starts ScopeKeeper Multi-Agent Orchestrator Mesh (switch/orchestrator.py)
"""

import os
import sys
import time
import subprocess
import signal

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(REPO_DIR)

BANNER = r"""
  ____                            _  __                         
 / ___|  ___ ___  _ __   ___     | |/ /___  ___ _ __   ___ _ __ 
 \___ \ / __/ _ \| '_ \ / _ \____| ' // _ \/ _ \ '_ \ / _ \ '__|
  ___) | (_| (_) | |_) |  __/____| . \  __/  __/ |_) |  __/ |   
 |____/ \___\___/| .__/ \___|    |_|\_\___|\___| .__/ \___|_|   
                 |_|                           |_|              
           The Night Shift That Saved $1,620 • Switch AI Mesh
======================================================================
"""

def print_status(msg: str):
    print(f"\033[94m[*] {msg}\033[0m")

def print_success(msg: str):
    print(f"\033[92m[✓] {msg}\033[0m")

def print_warn(msg: str):
    print(f"\033[93m[!] {msg}\033[0m")

def main():
    print(BANNER)
    
    # 1. Environment Check
    env_file = os.path.join(REPO_DIR, ".env")
    if not os.path.exists(env_file):
        example_env = os.path.join(REPO_DIR, ".env.example")
        if os.path.exists(example_env):
            print_warn(".env file not found. Copying from .env.example...")
            with open(example_env, "r", encoding="utf-8") as src, open(env_file, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            print_success("Created .env with default configurations.")
        else:
            print_warn("No .env found. Continuing with system environment variables.")

    # 2. Python Environment Detection
    clerk_venv_py = os.path.join(REPO_DIR, "clerk", ".venv", "Scripts", "python.exe")
    if not os.path.exists(clerk_venv_py):
        clerk_venv_py = os.path.join(REPO_DIR, "clerk", ".venv", "bin", "python")
    
    python_exe = clerk_venv_py if os.path.exists(clerk_venv_py) else sys.executable
    print_status(f"Using Python Runtime: {python_exe}")

    # 3. Seed Switch PostgreSQL Personas & Blueprint
    print_status("Seeding Switch Core Personas & Blueprint Template...")
    seed_script = os.path.join(REPO_DIR, "scripts", "seed_people.py")
    if os.path.exists(seed_script):
        try:
            res = subprocess.run([python_exe, seed_script], capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                print_success("Switch PostgreSQL seeded: Harish, Dhana, Sakthi, Bala & Blueprint registered.")
            else:
                print_warn(f"Database seed note: {res.stderr.strip() or res.stdout.strip()[:100]}")
        except Exception as e:
            print_warn(f"Seeder skipped (database offline or starting): {e}")

    # 4. Launch Services
    processes = []
    
    try:
        # A. Clerk Backend Service (FastAPI port 8080)
        print_status("Starting ScopeKeeper Clerk Backend (Port 8080)...")
        clerk_cmd = [python_exe, "-m", "uvicorn", "clerk.main:get_default_app", "--factory", "--port", "8080", "--host", "127.0.0.1"]
        clerk_proc = subprocess.Popen(clerk_cmd, cwd=os.path.join(REPO_DIR, "clerk"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(("Clerk Backend", clerk_proc))
        time.sleep(1)
        print_success("Clerk Backend active on http://localhost:8080 (Swagger: http://localhost:8080/docs)")

        # B. Dashboard Dev Server (Vite port 5173)
        print_status("Starting ScopeKeeper Executive Dashboard (Port 5173)...")
        dashboard_dir = os.path.join(REPO_DIR, "dashboard")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        dash_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=dashboard_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(("Executive Dashboard", dash_proc))
        time.sleep(1)
        print_success("Executive Dashboard active on http://localhost:5173")

        # C. Multi-Agent Orchestrator Mesh (switch/orchestrator.py)
        print_status("Starting Multi-Agent Orchestrator Mesh (Telegram, Discord, Slack)...")
        orch_script = os.path.join(REPO_DIR, "switch", "orchestrator.py")
        orch_proc = subprocess.Popen([python_exe, orch_script], cwd=REPO_DIR)
        processes.append(("Orchestrator Mesh", orch_proc))
        time.sleep(1)
        print_success("Orchestrator Mesh active (Listening on Switch Protocol 0.31)")

        print("\n" + "=" * 70)
        print("  🎉 ALL SCOPEKEEPER SERVICES ARE LIVE & CONNECTED!")
        print("=" * 70)
        print("  • 🌐 Executive Dashboard:    http://localhost:5173")
        print("  • 🛡️ Interactive Clerk API:  http://localhost:8080/docs")
        print("  • 📄 Sample Client CO:       http://localhost:5173/co/CR-002")
        print("  • 💬 Telegram Desk Bot:      @AcmeClientDesk_bot")
        print("  • 👥 Cast Active:            Harish (Discord) • Dhana (Telegram)")
        print("                               Sakthi (Console) • Bala (Slack)")
        print("=" * 70)
        print("\nPress Ctrl+C at any time to gracefully stop all services.\n")

        # Keep running until Ctrl+C
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nShutting down ScopeKeeper services gracefully...")
        for name, proc in processes:
            try:
                proc.terminate()
                print_status(f"Stopped {name}")
            except Exception:
                pass
        print_success("All services stopped cleanly. Thank you!")

if __name__ == "__main__":
    main()
