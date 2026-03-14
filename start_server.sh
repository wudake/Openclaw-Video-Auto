#!/bin/bash
cd /home/dake/Dake-Video-Auto
source venv/bin/activate
exec python app_simple.py >> logs/app.log 2>&1