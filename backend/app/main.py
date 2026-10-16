# Manages paths for both linux and windows
from pathlib import Path 

# Class who create the web app
from fastapi import FastAPI

# FileResponse: Sends file from disc, Response: general answer
from fastapi.responses import FileResponse, Response 

# Serves all files in a folder
from fastapi.staticfiles import StaticFiles
# Get routes used
from app.api.routes import videos, health

# Get settings used for the service
from app.core.config import settings

# Middleware that gets metrics for each request
from app.core.metrics import metrics_middleware

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest # Tools to exctract metrics

STATIC_DIR = Path(__file__).parent / "static" # Static folder  where index.html is located

app = FastAPI(title=settings.app_name) # Creates app

# Metric middleware runs on each http request
app.middleware("http")(metrics_middleware)

# Adds endpoints /health
app.include_router(health.router)

#Adds endpoints to /videos
app.include_router(videos.router)

# Servers the files of app.static under URL /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Endpoint that prometheus reads
@app.get("/metrics", include_in_schema=False)
# Functions that runs when someones ask for GET /metrics
def metrics() -> Response:
        #  Returns metrics as txt
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Landing page for browser demo
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")