@echo off
title Jarvis Backend Server
set "PATH=C:\Users\Administrator\AppData\Local\Programs\Python\Python310;C:\Users\Administrator\AppData\Local\Programs\Python\Python310\Scripts;%PATH%"
cd /d "%~dp0backend"
python server.py
pause
