from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from .api.v1 import endpoints

app = FastAPI(
    title="PDF to Audiobook Weaver",
    description="A web service to convert PDF documents into downloadable audiobook files.",
    version="1.0.0",
)

# Mount static files for the frontend
app.mount(
    "/static",
    StaticFiles(directory=Path("frontend")),
    name="static",
)

# Include API endpoints
app.include_router(endpoints.router, prefix="/api/v1", tags=["Audiobook Conversion"])

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    """
    Serves the main frontend application.
    """
    with open(Path("frontend/index.html"), "r") as f:
        return f.read()

