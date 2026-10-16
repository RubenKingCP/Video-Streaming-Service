# Regular expressions
import re

#Path
from pathlib import Path

# Settings we take from hls_dir
from app.core.config import settings

# Playlist name that ffmpeg creatres in each video folder
PLAYLIST_NAME = "index.m3u8"

# Valid video id letters numbers and _
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# Valid filename
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.(m3u8|ts)$")

# What video types are allowed
MEDIA_TYPES = {
    # Official HLS type
    ".m3u8": "application/vnd.apple.mpegurl",
    # Officail MPEG-TS
    ".ts": "video/mp2t"
}

# Video check to see if exists or found
class VideoNotFoundError(Exception):
    pass

# Rerurns names of avaialvle videos
def list_videos() -> list[str]:
    # If folder not exists retur empty list
    hls_dir = settings.hls_dir
    if not hls_dir.is_dir():
        return []
    # Rerturns sorted video names
    return sorted(
        # Subfolder name
        d.name
        # For each folder 
        for d in hls_dir.iterdir()
        # Keep only folder that contain the playlist name
        if(d / PLAYLIST_NAME).is_file()
    )

# Checks to see if at least one video exists
def media_available() -> bool:
    return len(list_videos()) > 0

#Find specified video file
def resolve_video_file(video_id: str, filename: str) -> tuple[Path, str]:
    # Check tro see if video has allowed form
    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise VideoNotFoundError(video_id)

    # Check to see if video has allowed name
    if not FILENAME_PATTERN.fullmatch(filename):
        raise VideoNotFoundError(filename)

    # Get realitive path
    base = settings.hls_dir.resolve()
    path = (base / video_id / filename).resolve()

    # Check to see if file actually is isnide folder
    if not path.is_relative_to(base):
        raise VideoNotFoundError(filename)
    # Check to see if file exists in disc
    if not path.is_file():
        raise VideoNotFoundError(filename)

    # Rerturn path and type
    return path, MEDIA_TYPES[path.suffix]