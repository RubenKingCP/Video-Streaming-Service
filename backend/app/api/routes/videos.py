# Api router: groups endpoints
# HTTPException: Throws HTTP errors
from fastapi import APIRouter, HTTPException

#FileResponse: sends a file from disc in chunks
from fastapi.responses import FileResponse

# Settings
from app.core.config import settings

# Service thay finds video files
from app.services import video_service

# Video not found exception
from app.services.video_service import VideoNotFoundError

# endpoint prefix
router = APIRouter(prefix="/videos", tags=["videos"])

# GET /videos
@router.get("")
# Returns list of videos
def list_videos() -> dict:
    # Ask the service which video sexist
    video_ids = video_service.list_videos()
    return {
        # For every video get its id and the url of its playlist
        "videos": [{"id": v, "playlist": f"/videos/{v}/index.m3u8"} for v in video_ids],
        "instance": settings.instance_name
    }

# GET /videos/[video_id]/{filename}
@router.get("/{video_id}/{filename}")
# Fastapi filles video id and filenme automatically
def get_video_file(video_id: str, filename: str) -> FileResponse:
    try:
        path, media_type = video_service.resolve_video_file(video_id, filename)
    except VideoNotFoundError:
        # raise 404 error if not found
        raise HTTPException(status_code=404, detail="Video file not found") from None

    # Send the file
    return FileResponse(
        # Path of the file on disk
        path,
        # Content-Type
        media_type=media_type,
        # Header with instance name
        headers={"X-Served-By": settings.instance_name}
    )