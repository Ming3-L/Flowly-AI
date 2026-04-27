from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("django.request")


class LogExceptionsMiddleware:
    """
    Railway 上出现 502（Application failed to respond）时，
    需要确保异常能落到 stdout，便于从 Deploy Logs 直接定位根因。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return self.get_response(request)
        except Exception:
            logger.exception("Unhandled exception while handling %s %s", request.method, request.path)
            raise

