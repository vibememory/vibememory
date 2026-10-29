"""Serve the same console and API from one origin for self-hosted installations."""

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_web(app, configured=None):
    if configured is not None:
        directory = Path(configured)
        if not (directory / "index.html").is_file():
            raise ValueError("MEMORY_WEB_DIR must contain index.html")
    else:
        # Wheels bundle web assets; editable source checkouts use the maintained landing files.
        packaged = Path(__file__).parent / "web"
        source = Path(__file__).resolve().parents[2] / "landing" / "dist"
        directory = packaged if (packaged / "index.html").is_file() else source
        if not (directory / "index.html").is_file():
            return

    @app.middleware("http")
    async def fresh_skills(request, call_next):
        response = await call_next(request)
        if (request.url.path.startswith("/skills/")
                or request.url.path == "/downloads/vibe-memory-skill.zip"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def page(filename):
        def response():
            return FileResponse(directory / filename, headers={"Cache-Control": "no-store"})

        return response

    for route, filename in [
        ("/", "index.html"),
        ("/login", "login.html"),
        ("/connect", "connect.html"),
        ("/capture", "capture.html"),
        ("/console", "console.html"),
        ("/admin", "admin.html"),
        ("/guide", "guide.html"),
    ]:
        app.add_api_route(route, page(filename), methods=["GET"], include_in_schema=False)
    # Register last: /auth, /v1, /health and API docs keep their own handlers.
    app.mount("/", StaticFiles(directory=directory, html=True), name="web")
