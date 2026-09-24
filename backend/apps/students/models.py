"""
students/models.py

Students are identified by admission_number, not name (per the blueprint --
names collide, admission numbers don't). Parents are separate from Django's
User model for now: not every parent needs portal login on day one, and
tying parent identity to auth is a decision better made when the Parent
Portal (blueprint section 9) is actually built, not forced here.

A student can have multiple guardians and a parent can have multiple
children -- StudentParent is a genuine many-to-many, not a shortcut FK.
"""

from django.db import models

from schools.models import Class, TenantScopedModel


class Student(TenantScopedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("graduated", "Graduated"),
        ("transferred", "Transferred"),
    ]

    admission_number = models.CharField(max_length=32)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    school_class = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")

    parents = models.ManyToManyField(
        "students.Parent", through="StudentParent", related_name="children"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "admission_number"], name="unique_admission_number_per_school"),
        ]
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.admission_number} - {self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Parent(TenantScopedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)

    # Set once the Parent Portal (blueprint section 9) grants login access.
    # Left nullable/optional deliberately -- a parent record can exist
    # (for invoices/contact) before that parent has portal credentials.
    user = models.OneToOneField(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="parent_profile"
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class StudentParent(TenantScopedModel):
    RELATIONSHIP_CHOICES = [
        ("mother", "Mother"),
        ("father", "Father"),
        ("guardian", "Guardian"),
        ("other", "Other"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="student_parent_links")
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="student_parent_links")
    relationship = models.CharField(max_length=16, choices=RELATIONSHIP_CHOICES, default="guardian")
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "parent"], name="unique_student_parent_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.parent} -> {self.student} ({self.relationship})"
