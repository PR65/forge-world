"""Vercel entrypoint for the complete FORGE FastAPI application.

This intentionally imports the canonical server app rather than reimplementing
or trimming any route, model, dataset, or runtime behavior.
"""

from server.app import app

__all__ = ["app"]
