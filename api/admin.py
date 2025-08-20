from django.contrib import admin
from .models import Course, Module

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "level", "duration_weeks", "created_at")
    inlines = [ModuleInline]

admin.site.register(Module)
