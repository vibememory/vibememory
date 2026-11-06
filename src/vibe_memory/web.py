"""Serve the same console and API from one origin for self-hosted installations."""

import re
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

LEGACY_CLI_USER_AGENT = re.compile(r"^VibeMemoryCLI/(\d+)\.(\d+)\.(\d+)(?:\s|$)")


def needs_legacy_skill_manifest(user_agent):
    if user_agent.startswith("VibeMemoryBootstrap/"):
        return True
    match = LEGACY_CLI_USER_AGENT.match(user_agent)
    return bool(match and tuple(int(part) for part in match.groups()) < (3, 11, 0))


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

    def skill_manifest(request: Request):
        filename = (
            "skills/vibe-memory/manifest-v1.json"
            if needs_legacy_skill_manifest(request.headers.get("user-agent", ""))
            else "skills/vibe-memory/manifest.json"
        )
        return FileResponse(
            directory / filename,
            media_type="application/json",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    app.add_api_route(
        "/skills/vibe-memory/manifest.json",
        skill_manifest,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )

    for route, filename in [
        ("/", "index.html"),
        ("/login", "login.html"),
        ("/connect", "connect.html"),
        ("/capture", "capture.html"),
        ("/console", "console.html"),
        ("/admin", "admin.html"),
        ("/admin/requests", "admin/requests.html"),
        ("/admin/operators", "admin/operators.html"),
        ("/admin/users", "admin/users.html"),
        ("/guide", "guide.html"),
        ("/support", "support.html"),
    ]:
        app.add_api_route(route, page(filename), methods=["GET"], include_in_schema=False)
    # Register last: /auth, /v1, /health and API docs keep their own handlers.
    app.mount("/", StaticFiles(directory=directory, html=True), name="web")
