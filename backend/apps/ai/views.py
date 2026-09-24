"""
ai/views.py

A single endpoint. `ai.use_assistant` gates it like every other permission
in this project -- the AI layer inherits the same RBAC as everything else,
it isn't a side door. A missing API key or a Claude-side failure both come
back as a clean error the frontend can show, never a raw traceback.
"""

from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasRolePermission

from . import services
from .claude_client import AIConfigurationError
from .serializers import AskAssistantInputSerializer, AskAssistantResponseSerializer


class AIServiceUnavailable(APIException):
    status_code = 503
    default_detail = "The AI assistant is not available right now."


class AskAssistantView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename_read = "ai.use_assistant"
    # POST is the only method, and it's a "read" in the sense that it
    # never mutates anything -- gated by the same read-style permission.
    required_permission_codename = "ai.use_assistant"

    def post(self, request):
        input_serializer = AskAssistantInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            result = services.ask_assistant(
                school=request.user.school,
                user=request.user,
                question=input_serializer.validated_data["question"],
            )
        except AIConfigurationError as exc:
            raise AIServiceUnavailable(str(exc)) from exc
        except services.AIAssistantError as exc:
            raise AIServiceUnavailable(str(exc)) from exc

        return Response(AskAssistantResponseSerializer(result).data)
