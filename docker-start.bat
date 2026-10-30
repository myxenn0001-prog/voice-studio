@echo off
title Voice Studio (Docker)
cd /d "%~dp0"
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Starting it...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  echo Waiting for Docker to be ready...
  :wait
  timeout /t 5 /nobreak >nul
  docker info >nul 2>&1
  if errorlevel 1 goto wait
)
set FILES=-f docker-compose.yml
where nvidia-smi >nul 2>&1 && set FILES=%FILES% -f docker-compose.gpu.yml && echo NVIDIA GPU found, using it.
docker compose %FILES% up -d --build
echo Voice Studio is starting. The first start downloads models once.
timeout /t 3 >nul
start http://localhost:8000
