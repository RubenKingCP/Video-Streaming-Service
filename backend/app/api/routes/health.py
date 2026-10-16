# APIRouter: a group of endpoints that is plugged into the app with include_router (see main.py)
from fastapi import APIRouter

# JSONResponse: a JSON response where we choose the status code ourselves (e.g. 503)
from fastapi.responses import JSONResponse

# Settings, for the instance name
from app.core.config import settings

# The service, to check whether any videos exist
from app.services import video_service

# prefix: every endpoint here starts with /health. tags: groups them on the /docs page
router = APIRouter(prefix="/health", tags=["health"])


# GET /health/live
@router.get("/live")
# Liveness: if the app can run this function at all, it is alive
def live() -> dict:
    # FastAPI turns this into JSON with status 200. "instance" shows which Pod answered
    return {"status": "alive", "instance": settings.instance_name}


# GET /health/ready
@router.get("/ready")
# Readiness: can it actually serve videos?
def ready() -> JSONResponse:
    # Is there at least one ready video (a folder with index.m3u8)?
    if video_service.media_available():
        # Yes -> ready
        return JSONResponse(
            # Response body
            {"status": "ready", "instance": settings.instance_name},
            # 200 OK: Kubernetes will send traffic to this Pod
            status_code=200,
        )
    # No -> not ready
    return JSONResponse(
        # Explain the reason, for debugging
        {"status": "not ready", "reason": "no videos found", "instance": settings.instance_name},
        # 503 Service Unavailable: Kubernetes will stop sending traffic here
        status_code=503,
    )