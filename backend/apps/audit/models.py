"""
audit/models.py

Append-only by policy: no view, serializer, or permission in this app ever
exposes update/delete -- AuditLogViewSet (views.py) is a ReadOnlyModelViewSet
and nothing else touches this table except services.log_action(). Corrections
happen by writing a NEW log entry (or a reversal in the originating app),
never by editing history.

entity_type/entity_id are a generic reference (not a real FK to every
possible model) so adding a newly-audited entity never requires a migration
here -- matches the blueprint's explicit reasoning for this design.
"""

from django.db import models


class AuditLog(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="audit_logs")

    action = models.CharField(max_length=64)  # e.g. "payment.recorded", "expense.approved"
    entity_type = models.CharField(max_length=64)  # e.g. "Payment", "Expense"
    entity_id = models.PositiveIntegerField()

    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "entity_type", "entity_id"]),
            models.Index(fields=["school", "created_at"]),
        ]

    def __str__(self) -> str:
        who = self.user.email if self.user else "system"
        return f"{who}: {self.action} {self.entity_type}#{self.entity_id}"
