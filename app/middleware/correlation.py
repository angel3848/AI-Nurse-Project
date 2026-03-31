import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique correlation ID to every request/response cycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        logger.info(
            "request_start correlation_id=%s method=%s path=%s", correlation_id, request.method, request.url.path
        )

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id

        logger.info("request_end correlation_id=%s status=%s", correlation_id, response.status_code)

        return response
