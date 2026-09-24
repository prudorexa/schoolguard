"""
audit/services.py

`log_action` is the ONLY way an AuditLog row gets created -- every other
app's services.py calls this at the point of a sensitive mutation, after
the mutation succeeds (so a log entry always reflects something that
actually happened, never an attempted-but-failed change).

Decimal/date values in previous_value/new_value are converted to strings
before storage -- JSONField can't serialize Decimal natively, and storing
as string avoids float-precision drift on money values.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .models import AuditLog


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return value


def log_action(
    *,
    school,
    user,
    action: str,
    entity_type: str,
    entity_id: int,
    reason: str = "",
    previous_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        school=school,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=_json_safe(previous_value) if previous_value is not None else None,
        new_value=_json_safe(new_value) if new_value is not None else None,
        reason=reason,
        ip_address=ip_address,
    )
