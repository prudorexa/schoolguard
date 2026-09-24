from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only even in Django admin -- no role, including platform staff
    using /admin/, gets to edit or delete audit history through this UI."""

    list_display = ["created_at", "school", "user", "action", "entity_type", "entity_id"]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_type", "reason"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
