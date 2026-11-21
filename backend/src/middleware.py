import time
import uuid
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse

_hits = defaultdict(deque)

async def request_context(request: Request, call_next):
    started = time.perf_counter()
    request.state.request_id = uuid.uuid4().hex[:12]
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _hits[ip]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= 120:
        return JSONResponse(status_code=429, content={"detail": "请求过于频繁"})
    bucket.append(now)
    try:
        response = await call_next(request)
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "服务处理失败", "request_id": request.state.request_id})
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-ms"] = str(round((time.perf_counter() - started) * 1000, 2))
    return response
