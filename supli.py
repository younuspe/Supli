"""Supli entry point.

Runs the application/API layer with the bundled frontend.

    python supli.py                  # serve on http://127.0.0.1:8000
    python supli.py --port 9000
    python supli.py --db ./supli.db
"""

from __future__ import annotations

import argparse

from supli.api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="supli", description="Supli local development workspace")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=None, help="path to the SQLite state database")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn

    app = create_app(args.db)
    print(f"Supli running at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()