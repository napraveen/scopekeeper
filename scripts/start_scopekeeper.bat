@echo off
TITLE ScopeKeeper - 1-Click Launch Suite
COLOR 0A

echo ===============================================================================
echo   ScopeKeeper: Autonomous Multi-Agent Scope Governance on Switch Protocol
echo   Flip the Switch Hackathon (Track 1: Best Business Workflow)
echo ===============================================================================
echo.

cd /d "f:\2026 - Projects\scopekeeper"

set PYTHON_EXE=C:\Users\Natarajan\AppData\Roaming\switchdash\local-switch-server\native\switch-core\0.31.0\venv\Scripts\python.exe
set PG_EXE=C:\Users\Natarajan\AppData\Roaming\switchdash\local-switch-server\native\toolchain\bundle-057e6b8bca99\postgres\bin\postgres.exe
set PG_DATA=C:\Users\Natarajan\AppData\Roaming\switchdash\local-switch-server\native\pgdata

echo [1/4] Starting PostgreSQL Database Server on port 50417...
start /B "ScopeKeeper-Postgres" "%PG_EXE%" -D "%PG_DATA%" -p 50417 > nul 2>&1
timeout /t 2 /nobreak > nul

echo [2/4] Starting Switch Core 0.31 Server & Bridges on port 50415...
start /B "ScopeKeeper-SwitchCore" "%PYTHON_EXE%" "C:\Users\Natarajan\.gemini\antigravity\brain\9044bc89-36b8-4f14-8ec4-39d97767fdd2\scratch\run_switch_core.py" > nul 2>&1
timeout /t 3 /nobreak > nul

echo [3/4] Starting ScopeKeeper Web Dashboard on http://localhost:5173...
start /B "ScopeKeeper-Dashboard" cmd /c "cd /d f:\2026 - Projects\scopekeeper\dashboard && npm run dev" > nul 2>&1
timeout /t 2 /nobreak > nul

echo [4/4] Starting Multi-Agent Orchestrator (Telegram + Discord + Gemini AI)...
start /B "ScopeKeeper-Orchestrator" "%PYTHON_EXE%" -u "C:\Users\Natarajan\.gemini\antigravity\brain\9044bc89-36b8-4f14-8ec4-39d97767fdd2\scratch\orchestrator.py"

echo.
echo ===============================================================================
echo   All ScopeKeeper services are LIVE and active!
echo.
echo   • Telegram Client Desk : @AcmeClientDesk_bot (Client on mobile)
echo   • Discord Engineering  : #general (guild 1562043658843201609)
echo   • Mission Dashboard    : http://localhost:5173/
echo   • Switch Core Server   : http://localhost:50415/
echo   • FastMCP Tool Server  : python mcp_server.py
echo ===============================================================================
echo.
pause
