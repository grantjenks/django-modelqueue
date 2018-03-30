import modelqueue
from django.db import models

class Task(models.Model):
    data = models.TextField()
    status = modelqueue.StatusField(
        db_index=True,
        default=modelqueue.waiting,
    )

    def __str__(self):
        return 'Task(data={!r}, status={!r}'.format(
            self.data,
            self.status,
        )
