from django.contrib import admin

from .models import AIAnalysisRecord


@admin.register(AIAnalysisRecord)
class AIAnalysisRecordAdmin(admin.ModelAdmin):
    """Read-only, same as AuditLog -- this is itself an audit trail."""

    list_display = ["created_at", "school", "asked_by", "tool_called"]
    search_fields = ["question", "answer"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
