from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import status
from fastapi.responses import JSONResponse

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # TEMP: Allow all requests without auth for testing
        response = await call_next(request)
        # Still add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response
        
        # Original auth logic (commented out for testing):
        # if (path.startswith("/docs") or 
        #     path.startswith("/openapi.json") or 
        #     path == "/" or 
        #     path.startswith("/health") or
        #     path.startswith("/api/v1/auth/signup") or
        #     path.startswith("/api/v1/auth/login")):
        #     response = await call_next(request)
        #     response.headers["X-Content-Type-Options"] = "nosniff"
        #     response.headers["X-Frame-Options"] = "DENY"
        #     response.headers["X-XSS-Protection"] = "1; mode=block"
        #     response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        #     return response
        # 
        # auth_header = request.headers.get("Authorization")
        # if not auth_header or not auth_header.startswith("Bearer "):
        #     return JSONResponse(
        #         {"detail": "Not authenticated"},
        #         status_code=status.HTTP_401_UNAUTHORIZED
        #     )
        # token = auth_header.split("Bearer ")[-1]