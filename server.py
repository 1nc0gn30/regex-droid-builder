#!/usr/bin/env python3
"""Regex Droid Studio Sovereign Server Launcher."""
import os
import sys
from pathlib import Path

# Add src to pythonpath
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from regex_droid_builder.ui_server import run_ui_server

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regex Droid Studio Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", "-p", type=int, default=8101, help="Port to listen on (default: 8101)")
    args = parser.parse_args()

    print(f"Starting Regex Droid Studio on {args.host}:{args.port}...")
    server = run_ui_server(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Regex Droid Studio Server...")
        server.server_close()
