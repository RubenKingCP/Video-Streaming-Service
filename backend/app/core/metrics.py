# Time: to claculate time 
import time

# Request: it is what contained all the inforamtion of the incoming request
from fastapi import Request

# Base metrics type
from prometheus_client import Counter, Gauge, Histogram

# What are metrics
# Counter: counts the total amount of request for example only goes up
# Gauge: Value that gors up and down used for example to calcualte how many requests 
# are bbeing handled now
# Histogram: sorts values into "bucekts", so we can get %

# TRequest Counter
REQUESTS_TOTAL = Counter(
    # Metric name
    "http_requests_total",
    # Metric description
    "Total amount of HTTP requests",
    # Labels: divides metrics based on method, endpoint and status
    ["method", "path", "status"]
)

# Count time to fully get a request
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Total amount of HTTP requests",
    ["method", "path"],
    # Bucket limit 
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Requests currently dealing with
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Total HTTP requests currently servicing"
)

# Total amount of bytes sent
BYTES_SENT_TOTAL = Counter(
    "http_response_bytes_total",
    "Total bytes send to clients",
    ["path"]
)

# Runs in every request
async def metrics_middleware(request: Request, call_next):
    # Not counting requests for metrics themselves
    if request.url.path == "/metrics":
        # Forward to not sque the metrics
        return await call_next(request)

    # Time of start
    start = time.perf_counter()
    # Increase requests servicing by one
    REQUESTS_IN_PROGRESS.inc()

    try:
        # Get endpoint
        response = await call_next(request)
    except Exception:
        REQUESTS_IN_PROGRESS.dec()
        # Raise throws the error back to fastapi to handle it tghere
        raise

    # Gets route that got matached
    route = request.scope.get("route")

    path = route.path if route else "unmatched"
    REQUESTS_TOTAL.labels(
        request.method,
        path,
        str(response.status_code)).inc()

    # Response body is sent in pieces
    original_body = response.body_iterator

    async def tracked_body():
        # Counts bytes
        sent = 0
        # Try fianlly ensures the metrics are counterd even if the client cuts
        try:
            # For every bit of data from file
            async for chunk in original_body:  
                # Count bytes
                sent += len(chunk)
                # Send it to client as is
                yield chunk
        # Acts when the sent is done either succesfully or not
        finally:
            # Count how many bytes were send
            BYTES_SENT_TOTAL.labels(path).inc(sent)

            # Count total time (now - start)
            REQUEST_DURATION.labels(
                request.method,
                path).observe(time.perf_counter() - start)

            # Remove after finish active request
            REQUESTS_IN_PROGRESS.dec()

            # Replace defualt repsonse body with our
    response.body_iterator = tracked_body()
    return response