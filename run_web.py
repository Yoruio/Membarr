#!/usr/bin/env python3
"""
run_web.py — Start the Membarr web admin UI.

Run from the project root (same directory as run.py):
    python3 run_web.py

Environment variables (can also be set in bot.env):
    WEB_PASSWORD    Admin password for the web UI (empty = open access with warning)
    WEB_SECRET_KEY  Secret for signing session cookies (auto-generated if not set)
    WEB_PORT        Port to listen on (default: 8080)
    WEB_HOST        Host to bind to (default: 0.0.0.0)
"""

import os
from dotenv import load_dotenv

if os.path.exists('bot.env'):
    load_dotenv('bot.env')

import uvicorn

if __name__ == '__main__':
    host = os.environ.get('WEB_HOST', '0.0.0.0')
    port = int(os.environ.get('WEB_PORT', 8080))
    print(f"Starting Membarr Web UI on http://{host}:{port}")
    if not os.environ.get('WEB_PASSWORD'):
        print("WARNING: WEB_PASSWORD is not set — the admin panel is open to everyone.")
    uvicorn.run('app.web.main:app', host=host, port=port, reload=False)
