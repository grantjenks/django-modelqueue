import datetime as dt
import modelqueue as mq
import pytest
from .models import Task


def nop(obj):
    pass


@pytest.mark.django_db
def test_run_waiting_finished():
    count = 10

    for num in range(count):
        task = Task(data=str(num))
        task.save()

    waiting = Task.objects.filter(
        status__gte=mq.MIN_WAITING,
        status__lte=mq.MAX_WAITING,
    )

    assert waiting.count() == count

    for num in range(count):
        tasks = Task.objects.all()
        task = mq.run(tasks, 'status', nop)
        assert task.data == str(num)

    assert mq.run(tasks, 'status', nop) is None

    finished = Task.objects.filter(
        status__gte=mq.MIN_FINISHED,
        status__lte=mq.MAX_FINISHED,
    )

    assert finished.count() == count


@pytest.mark.django_db
def test_run_created():
    count = 10

    for num in range(count):
        task = Task(data=str(num), status=mq.created())
        task.save()

    tasks = Task.objects.all()
    created = Task.objects.filter(
        status__gte=mq.MIN_CREATED,
        status__lte=mq.MAX_CREATED,
    )

    assert tasks.count() == count
    assert created.count() == count
    assert mq.run(tasks, 'status', nop) is None


def check_working(obj):
    assert mq.MIN_WORKING <= obj.status <= mq.MAX_WORKING


@pytest.mark.django_db
def test_run_working():
    task1 = Task(data=str(0))
    task1.save()
    task2 = mq.run(Task.objects.all(), 'status', check_working)
    assert task1 == task2
    state, _, _ = mq.parse(task2.status)
    assert state == mq.FINISHED


def always_fails(obj):
    raise RuntimeError


@pytest.mark.django_db
def test_run_canceled():
    task = Task(data=str(0))
    task.save()

    for attempt in range(3):
        try:
            mq.run(Task.objects.all(), 'status', always_fails)
        except RuntimeError:
            pass
        else:
            assert False, 'runtime error expected'

        task.refresh_from_db()
        state, _, attempts = mq.parse(task.status)
        assert state == mq.WAITING
        assert attempts == attempt + 1

    try:
        mq.run(Task.objects.all(), 'status', always_fails)
    except RuntimeError:
        pass
    else:
        assert False, 'runtime error expected'

    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.CANCELED
    assert attempts == 4


def control_c(obj):
    raise KeyboardInterrupt


@pytest.mark.django_db
def test_run_canceled_no_retry():
    task = Task(data=str(0))
    task.save()

    try:
        mq.run(Task.objects.all(), 'status', control_c, retry=0)
    except KeyboardInterrupt:
        pass
    else:
        assert False, 'keyboard interrupt expected'

    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.CANCELED
    assert attempts == 1


@pytest.mark.django_db
def test_run_keyboardinterrupt():
    task = Task(data=str(0))
    task.save()

    try:
        mq.run(Task.objects.all(), 'status', always_fails, retry=0)
    except RuntimeError:
        pass
    else:
        assert False, 'runtime error expected'

    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.CANCELED
    assert attempts == 1


@pytest.mark.django_db
def test_run_timeout():
    task = Task(data=str(0))
    task.save()
    state, moment, attempts = mq.parse(task.status)
    assert state == mq.WAITING
    moment -= dt.timedelta(hours=2)
    assert attempts == 0
    task.status = mq.combine(mq.WORKING, moment, attempts)
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop) == task
    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.FINISHED
    assert attempts == 2


@pytest.mark.django_db
def test_run_future():
    pass  # TODO, schedule in the future


@pytest.mark.django_db
def test_run_delay():
    pass  # TODO, set delay to ten minutes


@pytest.mark.django_db
def test_run_stress():
    pass  # TODO, fail randomly
