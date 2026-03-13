#!/bin/bash
cd /home/dake/xhs2ig
source venv/bin/activate
exec python app_simple.py >> logs/app.log 2>&1