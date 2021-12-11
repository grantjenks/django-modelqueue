from django.contrib import admin

import modelqueue

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_filter = [
        modelqueue.admin_list_filter('status'),
    ]
