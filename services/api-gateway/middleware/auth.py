from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from config import settings

# Paths that do not require a valid JWT
PUBLIC_PATHS = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/health",
    "/health/breakers",
    "/docs",
    "/openapi.json",
}

# Prefix-based public path exemptions
PUBLIC_PREFIXES = ("/docs", "/openapi", "/redoc")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validates Bearer JWTs on all protected routes.
    On success, sets ``request.state.user_id`` for downstream handlers.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Exempt public paths / prefixes
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"},
            )

        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        if payload.get("type") != "access":
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token type"},
            )

        # Attach user_id so routers can read it without re-decoding
        request.state.user_id = payload.get("sub")
        return await call_next(request)
