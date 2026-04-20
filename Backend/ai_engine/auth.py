"""
JWT Bearer authentication for Django Ninja 1.x.

Provides JWTBearer — a Ninja HttpBearer subclass that validates JWT tokens
and sets request.auth (and request.user) to the Django User object.

Usage:
    from ai_engine.auth import JWTAuth

    router = Router(auth=JWTAuth())
    # or per-route:
    @router.get("/protected", auth=JWTAuth())
    def protected(request):
        user = request.auth  # Django User
        ...
"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja.security import HttpBearer  # pyright: ignore[reportMissingImports]
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JWTAuth(HttpBearer):
    """
    Ninja HttpBearer that validates JWT Bearer tokens and sets:
    - request.auth  → the authenticated Django User (Ninja convention)
    - request.user  → the authenticated Django User (Django convention)

    Both are set to avoid conflicts with Django's auth middleware.

    Usage:
        router = Router(auth=JWTAuth())
        @router.get("/me", auth=JWTAuth())
        def me(request):
            user = request.auth  # or request.user
            ...
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        """
        Validate the JWT access token and return the associated Django User.
        Sets both request.auth and request.user so Django's auth middleware
        does not overwrite with AnonymousUser.
        Returns None on failure (Ninja returns 401).
        """
        try:
            access_token = AccessToken(token)
            user_id_str = access_token.get("user_id")
            if user_id_str is None:
                return None
            # JWT stores user_id as string, convert to int for Django PK lookup
            user_id = int(user_id_str)
            user = User.objects.get(id=user_id, is_active=True)
            # Set both so Ninja (request.auth) and Django (request.user) work
            request.auth = user
            request.user = user
            return user
        except (InvalidToken, TokenError, User.DoesNotExist, ValueError):
            return None
