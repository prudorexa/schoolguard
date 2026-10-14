"""
suppliers/models.py

Kept deliberately light for Phase 4 -- name/contact/tax info plus a status
flag. `total_paid`/`transaction_count`/risk scoring (blueprint section 14)
are derived from actual expense/payment history once that volume of data
exists, not stored fields that could drift from reality -- they'll be
computed properties or annotated querysets added when the reporting layer
(Phase 6) needs them, not guessed at here.
"""

from django.db import models

from schools.models import TenantScopedModel


class Supplier(TenantScopedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_supplier_name_per_school"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
