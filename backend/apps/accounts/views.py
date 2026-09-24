from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer


class MeView(APIView):
    """Whoami for the currently authenticated user -- school, roles, etc.
    Drives the frontend's role-aware nav once that's built."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)
