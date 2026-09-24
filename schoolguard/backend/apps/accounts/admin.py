from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import LoginHistory, Permission, Role, RolePermission, User, UserRole


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ["email"]
    list_display = ["email", "school", "is_super_admin", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "school")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "is_super_admin", "groups", "user_permissions")},
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(RolePermission)
admin.site.register(UserRole)
admin.site.register(LoginHistory)
