@echo off
cd /d "%~dp0"
if "%SUPABASE_URL%"=="" (
  echo SUPABASE_URL is not set.
  echo Set it first, then run this file again.
  pause
  exit /b 1
)
if "%SUPABASE_KEY%"=="" if "%SUPABASE_SERVICE_ROLE_KEY%"=="" if "%SUPABASE_ANON_KEY%"=="" (
  echo SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, or SUPABASE_ANON_KEY is not set.
  echo Set one first, then run this file again.
  pause
  exit /b 1
)
py server.py
pause
