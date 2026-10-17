# Video Streaming Service

A containerized HLS video streaming service built with **FastAPI**, deployed on a multi-node
**Kubernetes** cluster and evaluated under a varying number of simulated concurrent viewers.

The video is pre-converted into HLS (a playlist plus 4-second segments). The service only delivers
files over HTTP, keeps no state, and exposes health and Prometheus metrics endpoints, so any number of
identical replicas can run side by side behind a Kubernetes Service.

## Project status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Video streaming service | Done |
| 2 | Containerization (Docker) | Done |
| 3 | Multi-node Kubernetes deployment | In progress |
| 4 | Workload generator (simulated viewers) | To do |
| 5 | Horizontal Pod Autoscaling | To do |
| 6 | Monitoring and performance evaluation | To do |

## Architecture

```
            Browser / load generator
                       │
                       ▼
         Service "video-streaming" (NodePort 30080)
          spreads requests over all READY Pods
           ┌───────────┼───────────┐
           ▼           ▼           ▼
         Pod 1       Pod 2       Pod 3        ← Deployment, spread over the nodes
       (node A)    (node B)    (node C)
    FastAPI + uvicorn, videos baked into the image
```

## Project structure

```
Video-Streaming-Service/
├── backend/
│   ├── app/
│   │   ├── main.py                  # creates the app, plugs in routers, /metrics and /
│   │   ├── core/
│   │   │   ├── config.py            # settings from environment variables / .env
│   │   │   └── metrics.py           # Prometheus metrics + middleware
│   │   ├── api/routes/
│   │   │   ├── health.py            # /health/live, /health/ready
│   │   │   └── videos.py            # /videos, /videos/{id}/{file}
│   │   ├── services/
│   │   │   └── video_service.py     # finds video files, path-traversal protection
│   │   └── static/                  # demo page (index.html, style.css, app.js)
│   └── requirements.txt
├── k8s/
│   ├── deployment.yaml              # replicas, resources, probes, spreading over nodes
│   └── service.yaml                 # NodePort Service (load balancing, service discovery)
├── media/                           # NOT in git: created locally
│   ├── source/                      # original videos (e.g. sample.mp4)
│   └── hls/<video_id>/              # index.m3u8 + seg_000.ts, seg_001.ts, ...
├── scripts/
│   └── prepare_media.py             # converts a video to HLS with ffmpeg
├── Dockerfile
└── .dockerignore
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Demo page with an HLS player and a log of every downloaded segment |
| `GET /videos` | JSON list of available videos and their playlist URLs |
| `GET /videos/{id}/index.m3u8` | HLS playlist of one video |
| `GET /videos/{id}/seg_NNN.ts` | One video segment |
| `GET /health/live` | Liveness probe: the process is running |
| `GET /health/ready` | Readiness probe: at least one video is available (503 otherwise) |
| `GET /metrics` | Prometheus metrics |
| `GET /docs` | Interactive API documentation |

Every video response carries an `X-Served-By` header with the name of the instance (container or Pod) that served it.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (on Windows with the WSL 2 backend)
- [minikube](https://minikube.sigs.k8s.io/) and [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [ffmpeg](https://ffmpeg.org/download.html) on the PATH (check with `ffmpeg -version`), to prepare the video
- Python 3.12+ (to run the preparation script, and optionally the service without Docker)

## 1. Prepare the video

Videos are not stored in git. Create the HLS files once, before building the image:

```bash
# Option A: convert your own video (put it in media/source/sample.mp4 first)
python scripts/prepare_media.py

# Option B: convert any file; the id becomes part of the URL
python scripts/prepare_media.py --input path/to/video.mp4 --id myvideo

# Option C: no video at hand, generate a 60-second test pattern
python scripts/prepare_media.py --test
```

The output goes to `media/hls/<id>/`. Run `python scripts/prepare_media.py --help` for all options.

## 2. Build and run with Docker

From the project root:

```bash
docker build -t video-streaming:1.0 .
docker run --rm -p 8000:8000 --name vs video-streaming:1.0
```

Open <http://localhost:8000/> and press **Play**. Verify with:

```bash
curl http://localhost:8000/health/ready
curl http://localhost:8000/videos
curl -I http://localhost:8000/videos/sample/seg_000.ts     # check Content-Type and X-Served-By
```

On Windows PowerShell use `curl.exe` instead of `curl`.

## 3. Deploy on Kubernetes (minikube, multi-node)

### Start a 3-node cluster

Docker Desktop must be running. First time:

```bash
minikube start --nodes 3 --driver=docker --cpus 2 --memory 2200
kubectl get nodes          # 3 nodes, all Ready
```

Afterwards `minikube start` is enough. Give Docker Desktop about 7 GB of memory (*Settings → Resources*).

### Load the image and deploy

The cluster cannot see images on the host, so load the image into its nodes:

```bash
docker build -t video-streaming:1.0 .
minikube image load video-streaming:1.0
kubectl apply -f k8s/
kubectl get pods -o wide   # 3 Pods, READY 1/1, spread over the nodes (NODE column)
```

### Open the service

```bash
minikube service video-streaming --url
```

Keep that terminal open (with the Docker driver on Windows it holds a tunnel), open the printed URL and
press **Play**. The segment log shows `served by: <pod name>`; different Pod names show that the Service
spreads the requests over the replicas.

### Kubernetes design choices

| Mechanism | Where | Choice |
|-----------|-------|--------|
| Replicas | `deployment.yaml` | 3 identical, stateless Pods |
| Resource management | `deployment.yaml` | requests 100m CPU / 128Mi, limits 500m CPU / 256Mi |
| Health checking | `deployment.yaml` | readiness `/health/ready` (traffic only when videos exist), liveness `/health/live` (restart if hung) |
| Workload placement | `deployment.yaml` | `topologySpreadConstraints` over `kubernetes.io/hostname`, max skew 1 |
| Service discovery / load balancing | `service.yaml` | NodePort Service selecting `app=video-streaming` |
| Image | `deployment.yaml` | `video-streaming:1.0` with `imagePullPolicy: IfNotPresent` (local image) |

### Useful commands

| Purpose | Command |
|---------|---------|
| Pods and their nodes | `kubectl get pods -o wide` |
| Logs of one Pod | `kubectl logs <pod>` |
| Why a Pod is not starting | `kubectl describe pod <pod>` |
| Scale manually | `kubectl scale deployment video-streaming --replicas=5` |
| Remove the app | `kubectl delete -f k8s/` |
| Stop / delete the cluster | `minikube stop` / `minikube delete` |

### Updating the app

Build with a **new tag**, load it, point the Deployment to it:

```bash
docker build -t video-streaming:1.1 .
minikube image load video-streaming:1.1
# edit k8s/deployment.yaml: image: video-streaming:1.1
kubectl apply -f k8s/
```

## Configuration

All settings come from environment variables, so the same image runs unchanged everywhere.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Video Streaming Service` | Name shown on `/docs` |
| `MEDIA_DIR` | `<project>/media` locally, `/app/media` in the image | Folder that contains `hls/` |
| `INSTANCE_NAME` | the hostname (container ID / Pod name) | Reported in `X-Served-By` and the JSON responses |

## Running without Docker (development)

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1     Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

## Metrics

| Metric | Type | Meaning |
|--------|------|---------|
| `http_requests_total` | Counter | Requests per method, route and status code |
| `http_request_duration_seconds` | Histogram | Time until the last byte of the response is sent |
| `http_requests_in_progress` | Gauge | Concurrent transfers |
| `http_response_bytes_total` | Counter | Bytes sent per route (throughput) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `"/media/hls": not found` during `docker build` | Run `scripts/prepare_media.py` first |
| Player shows `Playback error: bufferAppendError` | The browser can't decode the segments. Re-run `scripts/prepare_media.py` (it converts to 1080p max, H.264 High@4.2, stereo 48 kHz), then hard-refresh the page (Ctrl+Shift+R) so no old cached segments are mixed in |
| `ModuleNotFoundError: No module named 'app'` | Start uvicorn from inside `backend/` |
| `failed to connect to the docker API` | Start Docker Desktop and wait for "Engine running" |
| `port is already allocated` | Stop the other server, or use `-p 8001:8000` |
| Pod in `ErrImagePull` / `ImagePullBackOff` | `minikube image load video-streaming:1.0`; check the tag in `deployment.yaml` |
| Pod in `CrashLoopBackOff` | `kubectl logs <pod>`; check that `image:` is `video-streaming:1.0`, not a base image |
| Pod stays `READY 0/1` | Readiness fails: the image has no videos. Prepare them, rebuild, reload, `kubectl rollout restart deployment video-streaming` |
| Pod `Pending` | Not enough resources: `kubectl describe pod <pod>`, give minikube/Docker more memory |
