"""
ai/claude_client.py

Thin factory so ai/services.py never constructs the SDK client directly --
tests inject a fake client instead of hitting the real API (this sandbox's
network policy doesn't include api.anthropic.com, so the real call is
implemented correctly but has not been exercised end-to-end here; a
person deploying this with a real ANTHROPIC_API_KEY should verify it).
"""

from django.conf import settings


class AIConfigurationError(Exception):
    pass


def get_client():
    if not settings.ANTHROPIC_API_KEY:
        raise AIConfigurationError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env to enable the AI assistant."
        )
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
