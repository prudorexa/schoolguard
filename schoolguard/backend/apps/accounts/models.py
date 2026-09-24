"""
accounts/models.py

Custom user model: email as the login identifier (not username), FK to the
school it belongs to (nullable only for Super Admins, who aren't scoped to
one school). Roles and their permissions are DATA (Role, Permission,
RolePermission, UserRole tables) rather than hardcoded role checks in code,
per the blueprint's RBAC section -- so adding a role or regranting a
permission is a data change, not a deploy.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from schools.models import School


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_super_admin", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    `is_super_admin` is SchoolGuard-platform-level (cross-school access for
    onboarding/support) -- distinct from Django's `is_superuser`, which just
    controls Django admin access. A user can be a platform Super Admin
    without being a Django admin superuser, and vice versa isn't meaningful
    here, so in practice the two are set together by create_superuser.
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="users", null=True, blank=True
    )
    is_super_admin = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def has_perm_code(self, codename: str) -> bool:
        """
        Check the DATA-driven permission system (Role -> RolePermission),
        not Django's built-in auth permissions. This is what
        HasRolePermission (accounts/permissions.py) calls.
        """
        if self.is_super_admin:
            return True
        return RolePermission.objects.filter(
            role__user_roles__user=self, permission__codename=codename
        ).exists()


class Permission(models.Model):
    """A single grantable action, e.g. 'expenses.approve', 'audit_logs.view'."""

    codename = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return self.codename


class Role(models.Model):
    """
    A named bundle of permissions. `school=None` means a platform-default
    role (Accountant, Principal, ...) available to every school out of the
    box; a school can also define its own custom roles later.
    """

    name = models.CharField(max_length=80)
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="custom_roles", null=True, blank=True
    )
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_role_per_school_or_platform"),
        ]

    def __str__(self) -> str:
        scope = self.school.code if self.school_id else "platform"
        return f"{self.name} ({scope})"


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("role", "permission")


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.role.name}"


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_history")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
