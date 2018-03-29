import pytest
from .models import Task


@pytest.mark.django_db
def test_task_save():
    task = Task(data='0')
    task.save()
    pk = task.pk
    task = Task.objects.get(pk=pk)
    assert task.data == '0'
