from django.contrib import admin

from .models import Parent, Student, StudentParent

admin.site.register(Student)
admin.site.register(Parent)
admin.site.register(StudentParent)
