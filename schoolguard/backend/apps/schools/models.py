"""
schools/models.py

`School` is the tenant. Every other tenant-scoped model in the project
inherits from `TenantScopedModel`, which is the *only* place `school` gets
defined -- so there's one thing to get right, not one per app.

`Department` is included here (rather than deferred to a later phase) as the
first real tenant-scoped model: it's simple, it's genuinely part of "school
configuration" per the blueprint, and it gives us something real to test
tenant isolation against instead of testing the abstraction in the dark.
"""

from django.db import models


class School(models.Model):
    """The tenant. Not itself tenant-scoped -- everything else scopes to it."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, unique=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)

    STATUS_CHOICES = [
        ("trial", "Trial"),
        ("active", "Active"),
        ("suspended", "Suspended"),
    ]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="trial")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class TenantScopedModel(models.Model):
    """
    Abstract base for every tenant-scoped table.

    Concrete subclasses get `school` for free. The enforcement that requests
    only ever see rows matching request.user.school lives in
    schools/permissions.py + schools/viewsets.py -- the field alone doesn't
    protect anything, the queryset filtering does.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(TenantScopedModel):
    name = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_department_per_school"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AcademicYear(TenantScopedModel):
    """e.g. '2026'. `is_current` marks the one active year per school --
    Student/invoice defaults will read this once fees exist (Phase 3)."""

    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_year_per_school"),
        ]
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name


class Term(TenantScopedModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "name"], name="unique_term_per_academic_year"),
        ]
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.academic_year.name})"


class Class(TenantScopedModel):
    """A class/grade, e.g. 'Grade 4 Blue'. Deliberately not named
    `SchoolClass`/`Klass` -- `Class` shadows the builtin only as an
    identifier, not a keyword, so it's safe and matches the blueprint's
    entity name."""

    name = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_class_per_school"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
