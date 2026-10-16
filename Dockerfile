# Base image: official Python on a small Debian
FROM python:3.13-slim

# Python settings + where config.py finds the videos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDIA_DIR=/app/media

# Work inside /app
WORKDIR /app

# Install dependencies first (cached unless requirements.txt changes)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unprivileged user
RUN useradd --create-home --uid 1000 appuser

# Application code and prepared HLS videos
COPY backend/app ./app
COPY media/hls ./media/hls

# Run as the unprivileged user
USER appuser

# The server listens on 8000
EXPOSE 8000

# Start the server, reachable from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]