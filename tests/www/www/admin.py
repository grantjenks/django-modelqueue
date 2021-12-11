import modelqueue

from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_filter = [
        modelqueue.admin_list_filter('status'),
    ]
