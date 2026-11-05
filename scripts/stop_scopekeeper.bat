@echo off
TITLE ScopeKeeper - Stop Suite
COLOR 0C

echo Stopping ScopeKeeper processes...
taskkill /F /IM "node.exe" /T > nul 2>&1
echo Done.
