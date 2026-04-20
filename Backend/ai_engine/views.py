"""
AI Engine Views

This module contains function-based views for the AI Engine app.
Note: For API endpoints, please use the Ninja API in api.py instead.
"""

from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({'status': 'ok'})
