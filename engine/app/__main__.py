"""Start the local web app:  python -m engine.app  [--port 8765] [--no-browser]"""
import argparse

from .server import serve

if __name__ == "__main__":  # the guard matters on Windows, where worker processes re-import this module
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()
    serve(args.port, open_browser=not args.no_browser)
