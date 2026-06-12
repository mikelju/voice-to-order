# serve.py
"""Dev server runner.

Why this file exists: on Windows, `uvicorn src.backend.app.main:app` runs the server on
a ProactorEventLoop (uvicorn picks its own loop factory) and psycopg async cannot run on
it. This runner sets the selector policy and drives uvicorn's Server.serve() inside a
plain asyncio.run(), which respects the policy.

Usage:
    python serve.py            # http://127.0.0.1:8000
    python serve.py 8080
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    config = uvicorn.Config("src.backend.app.main:app", host="127.0.0.1", port=port)
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
