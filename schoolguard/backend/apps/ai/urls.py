from django.urls import path

from .views import AskAssistantView

urlpatterns = [
    path("ai/ask/", AskAssistantView.as_view(), name="ai-ask"),
]
