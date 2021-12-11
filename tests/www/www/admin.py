from django.contrib import admin

import modelqueue

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    actions = [*modelqueue.admin_actions('status')]
    list_filter = [
        modelqueue.admin_list_filter('status'),
    ]

    def get_changeform_initial_data(self, request):
        return {'status': modelqueue.Status.waiting()}
