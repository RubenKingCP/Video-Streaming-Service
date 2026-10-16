# Gives access to hostname
import socket;

# Path: Handles paths
from pathlib import Path

# BaseSettings: Class that reads values from env vars
# SettingsConfigDict: Its settings
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sets project root by climbing 4 levels
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Each field of this class is a setting that gets autofilled my base settings
class Settings(BaseSettings):
    # Settings on how the values are read
    model_config = SettingsConfigDict(
        # Reads from file .env if exists 
        env_file=".env",
        # env file encoding
        env_file_encoding="utf-8",
        # Ignore values that are note mentioned here
        extra="ignore"
    )

    # App name. Env var = APP_NAME
    app_name: str = "Video Streaming Service"
    #Folder with videos
    media_dir: Path = PROJECT_ROOT / "media"
    # Machine name
    instance_name: str = socket.gethostname()

    @property
    # Folder with hls files
    def hls_dir(self) -> Path:
        return self.media_dir / "hls"

# Created one time 
settings = Settings()