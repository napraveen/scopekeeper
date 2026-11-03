"""Command-line entrypoint for running the ScopeKeeper Clerk server."""

from __future__ import annotations

import uvicorn

from clerk.main import create_app
from clerk.settings import Settings


def main() -> None:
    """Start the Clerk FastAPI server with background workers enabled."""
    settings = Settings()
    application = create_app(settings=settings, start_workers=True)
    uvicorn.run(
        application,
        host=settings.clerk_host,
        port=settings.clerk_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
